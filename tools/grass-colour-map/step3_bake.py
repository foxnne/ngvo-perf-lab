"""Bake the Tamriel grass colour map from the grass cache and the grass type table.

For every instance:  weight = visible blade area of its mesh (alpha-passing surface, units^2) * (instance scale)^2
Accumulated bilinearly on a 16-texel-per-cell grid (256 units), then filtered:
  LAI      = blur(sum weight) / texel area            (blade area per ground area)
  coverage = 1 - exp(-K * LAI)                         (share of the ground the grass hides at a distant, oblique view)
  colour   = blur(sum weight * linear colour) / blur(sum weight), filled outward from wider blurs where there is no grass
Output: out/work/bake.npz (float), out/grass_colour_tamriel.png (+ _rgb, _coverage), DDS in the staged mod folder.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

import cgid
import gcmlib as g

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
WORK = os.path.join(OUT, 'work')
K_COVER = 1.0
SIGMA = 1.5            # texels (384 units): soft drifts, no per-cell or per-patch blocks
UNDERWATER = ('waterkelp', 'watercoral', 'rockgrasswater')

types = json.load(open(os.path.join(WORK, 'grass_types.json')))
gdir = cgid.find_cache_dir()[0]
T = g.CELL / g.TEXELS
PAD = 4                                   # window margin in texels around the cell (instances may sit a little outside)
WIN = g.TEXELS + 2 * PAD
wsum = np.zeros((g.H + 2 * WIN, g.W + 2 * WIN))      # padded so windows never clip
csum = np.zeros((g.H + 2 * WIN, g.W + 2 * WIN, 3))
nsum = np.zeros((g.H + 2 * WIN, g.W + 2 * WIN))
t0 = time.time()
ninst = nskip_water = nskip_nocol = noutside = 0
for cx, cy, path in cgid.iter_world(gdir, 'tamriel'):
    X, Y, WG, COL = [], [], [], []
    for grp in cgid.read_cgid(path):
        n = len(grp['inst'])
        if not n:
            continue
        ty = types.get(grp['model'])
        base = os.path.basename(grp['model'])
        if base.lower().startswith(('medium_rocks_', 'pebbles_rocks_')):   # Rugged Ground stones: rock, not grass colour
            nskip_nocol += n
            continue
        if base.startswith(UNDERWATER):
            nskip_water += n
            continue
        if ty is None or 'linear' not in ty:
            nskip_nocol += n
            continue
        inst = grp['inst']
        s = 1.0 + inst[:, 13].astype(np.float64)
        wx, wy = cgid.world_xy(inst, cx, cy)
        X.append(wx - cx * g.CELL)
        Y.append(wy - cy * g.CELL)
        WG.append(ty['visible_area'] * s * s)
        COL.append(np.broadcast_to(np.array(ty['linear']), (n, 3)))
        ninst += n
    if not X:
        continue
    X, Y, WG, COL = np.concatenate(X), np.concatenate(Y), np.concatenate(WG), np.concatenate(COL)
    # window-local continuous texel coordinates: window column 0 = cell west edge - PAD texels, row 0 = cell north edge - PAD
    px = X / T + PAD - 0.5
    py = (g.CELL - Y) / T + PAD - 0.5
    ok = (px >= 0) & (px < WIN - 1) & (py >= 0) & (py < WIN - 1)
    noutside += int((~ok).sum())
    px, py, WG, COL = px[ok], py[ok], WG[ok], COL[ok]
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx, fy = px - x0, py - y0
    lw = np.zeros(WIN * WIN)
    lc = np.zeros((3, WIN * WIN))
    for dx, dy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        idx = (y0 + dy) * WIN + x0 + dx
        wv = WG * ww
        lw += np.bincount(idx, wv, WIN * WIN)
        for c in range(3):
            lc[c] += np.bincount(idx, wv * COL[:, c], WIN * WIN)
    ln = np.bincount(np.floor(py + 0.5).astype(np.int64) * WIN + np.floor(px + 0.5).astype(np.int64), minlength=WIN * WIN)
    r0 = (g.MAXY - cy) * g.TEXELS - PAD + WIN
    c0 = (cx - g.MINX) * g.TEXELS - PAD + WIN
    if r0 < 0 or c0 < 0 or r0 + WIN > wsum.shape[0] or c0 + WIN > wsum.shape[1]:
        noutside += len(px)
        continue
    wsum[r0:r0 + WIN, c0:c0 + WIN] += lw.reshape(WIN, WIN)
    csum[r0:r0 + WIN, c0:c0 + WIN] += lc.reshape(3, WIN, WIN).transpose(1, 2, 0)
    nsum[r0:r0 + WIN, c0:c0 + WIN] += ln.reshape(WIN, WIN)
print('instances baked %d, underwater types skipped %d, no colour %d, outside window/rectangle %d, %.0fs' % (ninst, nskip_water, nskip_nocol, noutside, time.time() - t0))
lost = wsum.sum() - wsum[WIN:-WIN, WIN:-WIN].sum()
print('weight falling outside the map rectangle: %.4f%%' % (100 * lost / wsum.sum()))
wsum = wsum[WIN:-WIN, WIN:-WIN]
csum = csum[WIN:-WIN, WIN:-WIN]
nsum = nsum[WIN:-WIN, WIN:-WIN]

lai_raw = wsum / (T * T)
wb = g.blur(wsum, SIGMA)
cb = g.blur(csum, SIGMA)
lai = wb / (T * T)
cover = 1.0 - np.exp(-K_COVER * lai)
# colour: finest scale where there is enough weight, wider scales elsewhere (so bilinear/mip sampling never meets black)
rgb = np.zeros_like(cb)
conf = np.zeros_like(wb)
eps = 0.02 * T * T      # weight of LAI 0.02
for sig in (SIGMA, 4.0, 12.0, 40.0, 120.0, 400.0):
    w_s = wb if sig == SIGMA else g.blur(wsum, sig)
    c_s = cb if sig == SIGMA else g.blur(csum, sig)
    col_s = c_s / np.maximum(w_s, 1e-9)[..., None]
    a = np.clip(w_s / eps, 0, 1) * (1 - conf)
    rgb += col_s * a[..., None]
    conf += a
mean_col = csum.sum((0, 1)) / wsum.sum()
rgb += mean_col * (1 - conf)[..., None]
print('map %dx%d, %.0f units per texel; texels with grass (raw) %.1f%%; coverage > 0.05: %.1f%%, > 0.5: %.1f%%; LAI where grass: median %.2f p90 %.2f max %.1f' % (
    g.W, g.H, T, 100 * (wsum > 0).mean(), 100 * (cover > 0.05).mean(), 100 * (cover > 0.5).mean(),
    np.median(lai[lai > 0.02]), np.percentile(lai[lai > 0.02], 90), lai.max()))
print('coverage-weighted mean colour: linear %s sRGB %s' % (np.round(mean_col, 4), np.round(g.lin2srgb(mean_col) * 255)))
np.savez_compressed(os.path.join(WORK, 'bake.npz'), rgb=rgb.astype(np.float32), cover=cover.astype(np.float32), lai=lai.astype(np.float32),
                    lai_raw=lai_raw.astype(np.float32), count=nsum.astype(np.float32))

# ---- images
srgb8 = np.round(g.lin2srgb(rgb) * 255).astype(np.uint8)
a8 = np.round(cover * 255).astype(np.uint8)
rgba = np.dstack([srgb8, a8])
Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, 'grass_colour_tamriel.png'))
Image.fromarray(srgb8, 'RGB').save(os.path.join(OUT, 'grass_colour_tamriel_rgb.png'))
Image.fromarray(a8, 'L').save(os.path.join(OUT, 'grass_colour_tamriel_coverage.png'))

# ---- DDS with a coverage-weighted mip chain
def mip_chain(rgb_lin, cov):
    levels = []
    while True:
        levels.append(np.dstack([np.round(g.lin2srgb(rgb_lin) * 255), np.round(cov * 255)]).astype(np.uint8))
        h, w = cov.shape
        if h == 1 and w == 1:
            break
        h2, w2 = max(1, h // 2), max(1, w // 2)
        r = rgb_lin[:h2 * 2 if h > 1 else 1, :w2 * 2 if w > 1 else 1]
        c = cov[:r.shape[0], :r.shape[1]]
        fy, fx = r.shape[0] // h2, r.shape[1] // w2
        cw = c.reshape(h2, fy, w2, fx)
        rw = r.reshape(h2, fy, w2, fx, 3)
        wt = cw + 1e-3                      # coverage-weighted colour, plain mean where nothing is covered
        rgb_lin = (rw * wt[..., None]).sum((1, 3)) / wt.sum((1, 3))[..., None]
        cov = cw.mean((1, 3))
    return levels

mips = mip_chain(rgb, cover)
mod = os.path.join(OUT, 'foxnne - Grass Colour Map', 'textures', 'GrassColour', 'GrassColourMaps')
os.makedirs(mod, exist_ok=True)
name = 'Tamriel.GrassColourMap.%d.%d.%d.%d.dds' % (g.MINX, g.MINY, g.MAXX, g.MAXY)
tmp = os.path.join(WORK, 'dds_tmp')
os.makedirs(tmp, exist_ok=True)
raw = os.path.join(tmp, name)
g.write_dds_rgba8(raw, mips, srgb=True)
print('uncompressed RGBA8 sRGB: %d bytes, %d mips' % (os.path.getsize(raw), len(mips)))
g.texconv(['-f', 'BC7_UNORM_SRGB', '-bc', 'x', '-o', mod, raw])
final = os.path.join(mod, name)
info = g.dds_info(open(final, 'rb').read(148))
print('wrote %s: %d bytes, %s' % (final, os.path.getsize(final), info))
# verify: decode BC7 back, compare every level with what was written
back, _ = g.read_dds_rgba(final, tmp, all_mips=True)
for i, (a, b) in enumerate(zip(mips, back)):
    d = np.abs(a.astype(np.float32) - b * 255.0)
    if i < 4 or i == len(mips) - 1:
        print('  level %d %s: BC7 error mean %.2f max %.0f (8-bit steps)' % (i, a.shape[:2], d.mean(), d.max()))
print('levels in file %d, expected %d' % (len(back), len(mips)))
os.remove(raw)


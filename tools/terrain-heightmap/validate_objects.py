"""Offline validation of the with-objects height map: previews, statistics, placement sanity check, CPU shadow simulation.
Reads objects_layers.npz / objects_intervals.npz / objects_sel.pkl written by build_heightmap_objects.py and the output DDS.
Writes PNGs to validation\\ and validation\\validation.txt."""
import os, sys, json, pickle, math, struct
import numpy as np
from PIL import Image, ImageDraw
import build_heightmap_objects as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'validation'); os.makedirs(OUT, exist_ok=True)
LOG = open(os.path.join(OUT, 'validation.txt' if __name__ == '__main__' else 'validation_rerun.txt'), 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n')

L = np.load(os.path.join(HERE, 'objects_layers.npz'))
land, surf, fin = L['land'].astype(np.float64), L['surf'].astype(np.float64), L['final'].astype(np.float64)   # north-up
rep = json.load(open(os.path.join(HERE, 'objects_report.json')))
Hh, Ww = land.shape

# ---- 0. re-read the written DDS exactly like the loader
b = open(rep['output'], 'rb').read()
h, w = struct.unpack_from('<II', b, 12); pff, fourcc, bits, rmask = struct.unpack_from('<I4sII', b, 80)
raw = np.frombuffer(b, '<u2', w * h, 128).reshape(h, w)
dec = -262136.0 + 524272.0 * (raw / 65535.0)
f = os.path.basename(rep['output'])[:-4].split('.')
assert len(f) == 9 and f[1] == 'Terrain' and f[2] == 'HeightMap'
zr = (int(f[7]) * 8.0, int(f[8]) * 8.0)
P('DDS', rep['output'])
P('  %dx%d, pixel format flags 0x%X, %d bpp, mask 0x%X, fourcc %r, %d bytes (legacy L16 -> R16_UNORM, same header as the 16-bit landscape map)' % (w, h, pff, bits, rmask, fourcc, len(b)))
P('  name fields: world %s cells %s..%s x %s..%s, zRange %g..%g units' % (f[0], f[3], f[5], f[4], f[6], zr[0], zr[1]))
P('  decoded (loader lerp) vs built grid: max |err| %.2f units ; decoded range %.1f..%.1f ; texels above zRange max: %d, below zRange min: %d' % (
    np.abs(dec - fin).max(), dec.min(), dec.max(), (dec > zr[1]).sum(), (dec < zr[0]).sum()))
P('  never below the landscape map: %s (min final-land = %.1f)' % ((fin >= land).all(), (fin - land).min()))

# ---- 1. statistics
d = fin - land; ds = surf - land
P('\nSTATISTICS (texel = 128 units, %d texels)' % d.size)
P('  raw top-down object surface above landscape: %d texels (%.1f%%), mean +%.0f, max +%.0f, highest point %.0f (landscape max %.0f)' % ((ds > 0).sum(), 100 * (ds > 0).mean(), ds[ds > 0].mean(), ds.max(), surf.max(), land.max()))
P('  final map raised: %d texels (%.1f%%)' % ((d > 0).sum(), 100 * (d > 0).mean()))
for t in (64, 128, 256, 512, 1000, 2000, 4000, 8000):
    P('    raised by more than %5d units: %8d texels (%.2f%%)' % (t, (d > t).sum(), 100 * (d > t).mean()))
r = d[d > 0]
P('  raise where raised: mean %.0f, median %.0f, p90 %.0f, p99 %.0f, max %.0f units' % (r.mean(), np.median(r), np.percentile(r, 90), np.percentile(r, 99), r.max()))
my, mx = np.unravel_index(np.argmax(d), d.shape)
P('  largest raise at world x %d y %d : land %.0f -> %.0f' % (B.X0 + mx * 128, B.Y0 + (Hh - 1 - my) * 128, land[my, mx], fin[my, mx]))
lost = surf - fin
P('  removed by the spike filter (raw surface - final): %d texels lowered, mean %.0f, p99 %.0f, max %.0f units' % ((lost > 0).sum(), lost[lost > 0].mean(), np.percentile(lost[lost > 0], 99), lost.max()))
P('  unsupported (overhang / bridge-like) object-texel intervals rejected: %d of %d' % (rep['intervals_rejected_unsupported'], rep['intervals']))
# single-texel spike test: texel higher than all 8 neighbours by > 256
def spikes(g, thr=256):
    p = np.pad(g, 1, mode='edge'); m = np.full(g.shape, -1e9)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1: continue
            np.maximum(m, p[dy:dy + g.shape[0], dx:dx + g.shape[1]], out=m)
    return int((g - m > thr).sum())
P('  single-texel spikes (texel > all 8 neighbours + 256): landscape %d, raw object surface %d, final %d' % (spikes(land), spikes(surf), spikes(fin)))
gx = np.abs(np.diff(fin, axis=1)); gl = np.abs(np.diff(land, axis=1))
P('  max step between adjacent texels: landscape %.0f, final %.0f ; steps > 1024: landscape %d, final %d' % (gl.max(), gx.max(), (gl > 1024).sum(), (gx > 1024).sum()))

# ---- 2. placement sanity check
sel = pickle.load(open(os.path.join(HERE, 'objects_sel.pkl'), 'rb'))
I = np.load(os.path.join(HERE, 'objects_intervals.npz'))
tex, top, bot, rid, rej = I['tex'], I['top'], I['bot'], I['rid'], I['rejected']
land_su = land[::-1].ravel()
order = np.argsort(rid, kind='stable'); rs = rid[order]
starts = np.flatnonzero(np.r_[True, rs[1:] != rs[:-1]]); ends = np.r_[starts[1:], len(rs)]
P('\nPLACEMENT SANITY (object vs landscape at its own footprint; a correctly placed rock straddles the ground:')
P('  its lowest sampled top is at/below the landscape while its highest is above)')
per = {}
rows = []
for s0, e0 in zip(starts, ends):
    k = order[s0:e0]; ri = int(rs[s0])
    dd = top[k] - land_su[tex[k]]
    m, c, pos, rot, sc, fk = sel[ri]
    per.setdefault(c, []).append((np.percentile(dd, 5), np.median(dd), dd.max(), (dd > 0).mean(), len(k)))
    rows.append((ri, len(k), np.percentile(dd, 5), np.median(dd), dd.max()))
for c, v in per.items():
    v = np.array(v)
    P('  %-10s %5d objects: p5(top-land) median %7.0f | median(top-land) median %6.0f | max(top-land) median %6.0f | objects with p5 > +256 (floating?): %d (%.1f%%)' % (
        c, len(v), np.median(v[:, 0]), np.median(v[:, 1]), np.median(v[:, 2]), (v[:, 0] > 256).sum(), 100 * (v[:, 0] > 256).mean()))
P('  examples (first refs of a few models, incl. tilted ones):')
shown = {}
for ri, n, p5, med, mx_ in rows:
    m, c, pos, rot, sc, fk = sel[ri]
    key = os.path.basename(m)
    if key in ('mountaintrim01.nif', 'mountaincliff02.nif', 'mountainpeak01.nif', 'rockcliff03.nif', 'rockpilel01.nif', 'dirtcliffs03.nif', 'glacierendlg01.nif', 'rocktundraland01.nif') and shown.get(key, 0) < 1 and abs(rot[0]) + abs(rot[1]) > 0.1:
        shown[key] = 1
        gi = int(round((pos[0] - B.X0) / 128)); gj = int(round((pos[1] - B.Y0) / 128))
        P('    %s:%06X %-22s pos (%.0f, %.0f, %.0f) rot deg (%.0f, %.0f, %.0f) scale %.2f : land at origin %.0f ; footprint %d texels, top-land p5 %.0f / median %.0f / max %.0f' % (
            fk[0], fk[1], key, pos[0], pos[1], pos[2], *(math.degrees(a) for a in rot), sc, land_su[gj * B.W + gi], n, p5, med, mx_))

# ---- 3. previews
def shade(g, az=315.0, el=45.0, zf=1.0):
    gy, gx_ = np.gradient(g * zf, 128.0)                 # rows go north->south, so +row = -y
    nx, ny, nz = -gx_, gy, np.ones_like(g)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    a, e = math.radians(az), math.radians(el)            # az clockwise from north = direction TO the light
    lx, ly, lz = math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)
    return np.clip((nx * lx + ny * ly + nz * lz) / n, 0, 1)

def relief(g, lo=-14000.0, hi=40000.0):
    s = shade(g)
    t = np.clip((g - lo) / (hi - lo), 0, 1)
    r = 0.35 + 0.65 * t; gg = 0.45 + 0.5 * t; bb = 0.40 + 0.6 * t
    sea = g < -14000
    rgb = np.dstack([r, gg, bb]) * (0.25 + 0.95 * s[..., None])
    rgb[sea] = rgb[sea] * 0.5 + np.array([0.05, 0.12, 0.25])
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)

def diffimg(dv, vmax=4000.0):
    t = np.clip(dv / vmax, 0, 1) ** 0.5
    rgb = np.dstack([t, np.clip(t * 1.6 - 0.6, 0, 1), np.clip(0.15 + t * 3 - 2.6, 0, 1)])
    rgb[dv <= 0] = (0.07, 0.07, 0.09)
    return (rgb * 255).astype(np.uint8)

def label(im, text):
    d_ = ImageDraw.Draw(im); d_.rectangle([0, 0, 8 + 6.2 * len(text), 16], fill=(0, 0, 0)); d_.text((4, 2), text, fill=(255, 255, 255)); return im

def crop_idx(x0, x1, y0, y1):
    i0 = int(round((x0 - B.X0) / 128)); i1 = int(round((x1 - B.X0) / 128))
    r0 = Hh - 1 - int(round((y1 - B.Y0) / 128)); r1 = Hh - 1 - int(round((y0 - B.Y0) / 128))
    return slice(r0, r1 + 1), slice(i0, i1 + 1)

def panel(imgs, labels, scale, path):
    ims = [label(Image.fromarray(a).resize((a.shape[1] * scale, a.shape[0] * scale), Image.NEAREST if scale > 1 else Image.BILINEAR), t) for a, t in zip(imgs, labels)]
    Wt = sum(i.width for i in ims) + 6 * (len(ims) - 1)
    o = Image.new('RGB', (Wt, ims[0].height), (30, 30, 30)); x = 0
    for i in ims:
        o.paste(i, (x, 0)); x += i.width + 6
    o.save(path); return path

Image.fromarray(relief(land)).save(os.path.join(OUT, 'full_relief_landscape.png'))
Image.fromarray(relief(fin)).save(os.path.join(OUT, 'full_relief_with_objects.png'))
Image.fromarray(diffimg(d)).save(os.path.join(OUT, 'full_difference.png'))
P('\nPREVIEWS in', OUT)
P('  full_relief_landscape.png, full_relief_with_objects.png, full_difference.png (3808x3008, 1 px = 1 texel, north up; difference: black 0 -> red -> yellow -> white >= 4000 units)')
CROPS = {'ilinalta': (-30000, -5000, -75000, -45000, 4), 'throat': (38000, 70000, -68000, -36000, 3)}
for name, (x0, x1, y0, y1, sc) in CROPS.items():
    sl = crop_idx(x0, x1, y0, y1)
    lo, hi = land[sl].min(), fin[sl].max()
    panel([relief(land, lo, hi)[sl], relief(surf, lo, hi)[sl], relief(fin, lo, hi)[sl], diffimg(d[sl])],
          ['landscape only', 'raw object surface (unfiltered)', 'FINAL (with objects, filtered)', 'final - landscape (white >= 4000)'], sc, os.path.join(OUT, 'crop_%s_relief.png' % name))
    dd = d[sl]
    P('  crop_%s_relief.png: world x %d..%d, y %d..%d (%dx%d texels, x%d): raised %.1f%% of texels, mean +%.0f, max +%.0f ; land max %.0f -> final max %.0f' % (
        name, x0, x1, y0, y1, dd.shape[1], dd.shape[0], sc, 100 * (dd > 0).mean(), dd[dd > 0].mean() if (dd > 0).any() else 0, dd.max(), land[sl].max(), fin[sl].max()))

# ---- 4. CPU terrain shadow simulation (same recurrence as ShadowUpdate.cs.hlsl, converged, hard edge at mid penumbra)
BIAS = 256.0
def shadow_height(g, az_from, el):
    """g north-up. az_from = compass bearing of the sun (deg clockwise from north). Light travels away from it.
    Recurrence along the major axis with linear interpolation on the minor axis, like the compute shader."""
    a = math.radians(az_from)
    dx, dy = -math.sin(a), -math.cos(a)                    # travel direction in world x (east), y (north)
    dcol, drow = dx, -dy                                   # in image space
    gg = g
    transposed = abs(drow) > abs(dcol)
    if transposed:
        gg = gg.T; dcol, drow = drow, dcol
    if dcol < 0:
        gg = gg[:, ::-1]
    m = drow / abs(dcol)                                   # rows per column step
    dz = 128.0 * math.sqrt(1 + m * m) * math.tan(math.radians(el))
    S = gg.copy(); n = gg.shape[0]
    rows = np.arange(n) - m
    r0 = np.clip(np.floor(rows).astype(int), 0, n - 1); r1 = np.clip(r0 + 1, 0, n - 1); fr = rows - np.floor(rows)
    for i in range(1, gg.shape[1]):
        prev = S[:, i - 1]
        S[:, i] = np.maximum(gg[:, i], prev[r0] * (1 - fr) + prev[r1] * fr - dz)
    if dcol < 0:
        S = S[:, ::-1]
    if transposed:
        S = S.T
    return S

def components(mask):
    """4-connected components (count, size of largest)."""
    m = mask.copy(); n = 0; big = 0
    Hm, Wm = m.shape
    ys, xs = np.nonzero(m)
    for y, x in zip(ys, xs):
        if not m[y, x]: continue
        n += 1; st = [(y, x)]; m[y, x] = False; sz = 0
        while st:
            cy, cx = st.pop(); sz += 1
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < Hm and 0 <= nx < Wm and m[ny, nx]:
                    m[ny, nx] = False; st.append((ny, nx))
        big = max(big, sz)
    return n, big

def maskimg(base_relief, mask, obj):
    rgb = base_relief.astype(np.float64)
    rgb[mask] = rgb[mask] * 0.22
    rgb[obj & ~mask] = rgb[obj & ~mask] * 0.75 + np.array([70, 40, 0])     # lit rock-object texels tinted orange
    return np.clip(rgb, 0, 255).astype(np.uint8)

P('\nSHADOW SIMULATION (receiver = raw top-down surface of landscape+objects, i.e. what is visible from above;')
P('  shadowed where receiver z < propagated shadow height - %d bias, as in TerrainShadows.hlsli; "truth" = caster is that same raw surface)' % BIAS)
x0, x1, y0, y1, sc = CROPS['ilinalta']
sl = crop_idx(x0, x1, y0, y1)
for tag, az, el in (('west_el8', 270.0, 8.0), ('west_el12', 270.0, 12.0), ('west_el15', 270.0, 15.0), ('wsw_el12', 250.0, 12.0)):
    S_land = shadow_height(land, az, el); S_fin = shadow_height(fin, az, el); S_true = shadow_height(surf, az, el)
    recv = surf
    m_land = recv < S_land - BIAS; m_fin = recv < S_fin - BIAS; m_true = recv < S_true - BIAS
    obj = (surf - land) > 64
    c = lambda m: m[sl]
    o = c(obj); t = c(m_true)
    P('  sun bearing %.0f deg, elevation %.0f deg  [%s]  Ilinalta crop (%d texels, %.0f%% covered by objects):' % (az, el, tag, o.size, 100 * o.mean()))
    for nm, m in (('landscape-only map', c(m_land)), ('with-objects map', c(m_fin)), ('ideal (raw surface)', t)):
        nc, big = components(m)
        nl, _ = components(~m & o)
        P('    %-20s shadowed %5.1f%% of crop | of object texels %5.1f%% | of landscape-only texels %5.1f%% | recall of true shadow %5.1f%% | shadow not in truth %4.1f%% of crop | shadow blobs %4d (largest %5.1f%% of shadow) | lit object islands %d' % (
            nm, 100 * m.mean(), 100 * m[o].mean(), 100 * m[~o].mean(), 100 * (m & t).sum() / max(t.sum(), 1), 100 * (m & ~t).mean(), nc, 100 * big / max(m.sum(), 1), nl))
    lo, hi = land[sl].min(), surf[sl].max()
    base = relief(surf, lo, hi)[sl]
    panel([maskimg(base, c(m_land), o), maskimg(base, c(m_fin), o), maskimg(base, t, o)],
          ['landscape-only map: shadow (dark), lit rock objects (orange)', 'with-objects map', 'ideal: unfiltered surface as caster'], sc, os.path.join(OUT, 'shadow_ilinalta_%s.png' % tag))
    if tag == 'west_el8':
        # whole-map numbers and Throat crop for the same sun
        P('    whole map: shadowed %.1f%% (landscape-only) vs %.1f%% (with objects) vs %.1f%% (ideal); object texels shadowed %.1f%% vs %.1f%% vs %.1f%%' % (
            100 * m_land.mean(), 100 * m_fin.mean(), 100 * m_true.mean(), 100 * m_land[obj].mean(), 100 * m_fin[obj].mean(), 100 * m_true[obj].mean()))
        xs0, xs1, ys0, ys1, sc2 = CROPS['throat']; sl2 = crop_idx(xs0, xs1, ys0, ys1)
        base2 = relief(surf, land[sl2].min(), surf[sl2].max())[sl2]
        panel([maskimg(base2, m_land[sl2], obj[sl2]), maskimg(base2, m_fin[sl2], obj[sl2]), maskimg(base2, m_true[sl2], obj[sl2])],
              ['landscape-only map', 'with-objects map', 'ideal'], sc2, os.path.join(OUT, 'shadow_throat_west_el8.png'))
        # false self-shadow test: sun-facing object texels (lit in truth) that the map darkens
        P('    with-objects map darkens %.2f%% of truly lit texels (landscape-only map: %.2f%%)' % (100 * (m_fin & ~m_true).sum() / (~m_true).sum(), 100 * (m_land & ~m_true).sum() / (~m_true).sum()))
P('  images: shadow_ilinalta_<sun>.png (3 panels), shadow_throat_west_el8.png')
LOG.close()

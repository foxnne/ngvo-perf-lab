"""Mock-up on the in-game frame: project the grass colour map into the screenshot through the terrain height map and tint
the terrain beyond the grass draw distance. Camera: harness view "plains_west" (player 19157,-7419,-3612 + 700 up, yaw 270,
3 degrees up, FOV 65 = 81.1 degrees horizontal at 3440x1440, fitted to the mountain skyline)."""
import colorsys
import math
import os
import numpy as np
from PIL import Image, ImageDraw
import gcmlib as g
import framecast

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FRAME = r'C:\Users\foxnn\dev\ngvo-perf-lab\results\sky_sweep\realism\4_shoulder_only_0.5_from_0.6__h13.png'
CAM = (19157.0, -7419.0, -3612.0 + 700.0)
YAW, PITCH, FOVH = 270.0, 3.0, 81.1
GRASS_END0, GRASS_END1 = 12000.0, 17000.0      # where the grass visibly thins out and ends in this frame (estimated from it)
LUMA_KEEP = 0.5
HAZE_DIST = 150000.0

im = Image.open(FRAME).convert('RGB')
W, H = im.size
frame = np.asarray(im, np.float64) / 255
hm = np.load(os.path.join(OUT, 'work', 'height_128.npy')).astype(np.float64)
bk = np.load(os.path.join(OUT, 'work', 'bake.npz'))
rgbmap, cover = bk['rgb'].astype(np.float64), bk['cover'].astype(np.float64)
cw, ch = -(-W // 3), -(-H // 3)
cache = os.path.join(OUT, 'work', 'cast_plains_west.npz')
if os.path.exists(cache):
    z = np.load(cache)
    X, Y, D = z['X'], z['Y'], z['D']
else:
    X, Y, D = framecast.cast(hm, CAM, YAW, PITCH, FOVH, cw, ch)
    np.savez_compressed(cache, X=X, Y=Y, D=D)
hit = np.isfinite(D)
Xs, Ys = np.where(hit, X, 0), np.where(hit, Y, 0)
mrgb = g.sample_map(rgbmap, Xs, Ys)
mcov = g.sample_map(cover, Xs, Ys) * hit
Dn = np.where(hit, D, 1e9)


def up(a):
    a = np.asarray(a, np.float64)
    return g.upsample_bilinear(a, 3)[:H, :W]


mrgb, mcov, Dn = up(mrgb), up(mcov), up(np.minimum(Dn, 1e6))
lin = g.srgb2lin(frame)
mx, mn = frame.max(2), frame.min(2)
sat = (mx - mn) / np.maximum(mx, 1e-4)
hue = np.zeros_like(mx)
r, gg, b = frame[..., 0], frame[..., 1], frame[..., 2]
d = np.maximum(mx - mn, 1e-6)
hue = np.where(mx == r, ((gg - b) / d) % 6, np.where(mx == gg, (b - r) / d + 2, (r - gg) / d + 4)) * 60


def sstep(a, b_, x):
    t = np.clip((x - a) / (b_ - a), 0, 1)
    return t * t * (3 - 2 * t)


# pixels that look like bare ground (tan / ochre): warm hue, some saturation, not dark, not snow or grey rock
ground = sstep(8, 18, hue) * (1 - sstep(52, 66, hue)) * sstep(0.10, 0.20, sat) * sstep(0.22, 0.36, mx)
ground = g.blur(ground, 1.0)

# ---- does the map match the foreground? compare where grass is on screen (3000..11000 units, coverage > 0.6)
near = (Dn > 3000) & (Dn < 11000) & (mcov > 0.6) & (hue > 8) & (hue < 100) & (sat > 0.12) & (mx > 0.2)
k = np.median(lin[near] / np.maximum(mrgb[near], 1e-4), axis=0)
kl = float(np.median((lin[near] @ [0.2126, 0.7152, 0.0722]) / np.maximum(mrgb[near] @ [0.2126, 0.7152, 0.0722], 1e-4)))
fm = lin[near].mean(0)
mm = mrgb[near].mean(0)


def chroma(c):
    c = np.asarray(c)
    return c / c.sum()


print('near-field grass pixels compared: %d' % near.sum())
print('  frame mean (linear) %s  chromaticity r,g,b %s  sRGB %s' % (np.round(fm, 3), np.round(chroma(fm), 3), np.round(g.lin2srgb(fm) * 255)))
print('  map   mean (linear) %s  chromaticity r,g,b %s  sRGB %s' % (np.round(mm, 3), np.round(chroma(mm), 3), np.round(g.lin2srgb(mm) * 255)))
print('  map x one gain %.2f -> sRGB %s ; per-channel gain frame/map %s' % (kl, np.round(g.lin2srgb(mm * kl) * 255), np.round(k, 2)))
# spatial agreement of the red/green balance on a coarse screen grid
rg_f, rg_m, wts = [], [], []
B = 40
for y0 in range(0, H - B, B):
    for x0 in range(0, W - B, B):
        s = near[y0:y0 + B, x0:x0 + B]
        if s.sum() > 0.5 * B * B:
            f = lin[y0:y0 + B, x0:x0 + B][s].mean(0)
            m = mrgb[y0:y0 + B, x0:x0 + B][s].mean(0)
            rg_f.append(f[0] / f[1]); rg_m.append(m[0] / m[1])
print('  red/green ratio over %d screen blocks of %d px: frame %.2f..%.2f (mean %.2f), map %.2f..%.2f (mean %.2f), correlation %.2f' % (
    len(rg_f), B, min(rg_f), max(rg_f), np.mean(rg_f), min(rg_m), max(rg_m), np.mean(rg_m), np.corrcoef(rg_f, rg_m)[0, 1]))
far = (Dn > 20000) & (Dn < 60000) & (ground > 0.5)
ff = lin[far].mean(0)
print('far bare plain (20k-60k units, ground-coloured pixels): frame mean sRGB %s chromaticity %s; map there sRGB %s x gain -> %s, mean coverage %.2f' % (
    np.round(g.lin2srgb(ff) * 255), np.round(chroma(ff), 3), np.round(g.lin2srgb(mrgb[far].mean(0)) * 255), np.round(g.lin2srgb(mrgb[far].mean(0) * kl) * 255), mcov[far].mean()))

# ---- tint
Y = lin @ np.array([0.2126, 0.7152, 0.0722])
Ylow = np.maximum(g.blur(Y, 6.0), 1e-4)
detail = np.maximum(Y, 1e-4) / Ylow
lit = mrgb * k[None, None, :]                    # how this grass colour looks under the frame's light and grade
Yg = np.maximum(lit @ np.array([0.2126, 0.7152, 0.0722]), 1e-4)
base = Yg * (1 - LUMA_KEEP) + Ylow * LUMA_KEEP
target = lit / Yg[..., None] * (base * detail)[..., None]
wd = sstep(GRASS_END0, GRASS_END1, Dn) * (Dn < 9e5)
haze = np.exp(-Dn / HAZE_DIST)
results = {}
for s in (0.5, 1.0):
    t = np.clip(mcov * s, 0, 1) * ground * wd * haze
    o = lin * (1 - t[..., None]) + target * t[..., None]
    results[s] = np.round(g.lin2srgb(o) * 255).astype(np.uint8)
    Image.fromarray(results[s]).save(os.path.join(OUT, 'mockup_frame_strength_%.1f.png' % s))
Image.fromarray(np.round(np.clip(np.dstack([wd * mcov * ground * haze] * 3), 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, 'mockup_frame_weight.png'))
# comparison sheet: full frames stacked, and a 1:1 crop of the plain
before = np.round(frame * 255).astype(np.uint8)
lab = [('before (as captured)', before), ('predicted, strength 0.5', results[0.5]), ('predicted, strength 1.0', results[1.0])]
sheet = Image.new('RGB', (W, (H + 40) * 3), (16, 16, 16))
dr = ImageDraw.Draw(sheet)
for i, (t_, a) in enumerate(lab):
    sheet.paste(Image.fromarray(a), (0, i * (H + 40) + 40))
    dr.text((12, i * (H + 40) + 12), t_ + '   (mock-up: only ground-coloured pixels beyond ~%d units are changed)' % GRASS_END0, fill=(255, 255, 0))
sheet.save(os.path.join(OUT, 'mockup_frame_before_after.png'))
x0, y0, x1, y1 = 300, 760, 3000, 1150
crop = Image.new('RGB', (x1 - x0, (y1 - y0 + 30) * 3), (16, 16, 16))
dr = ImageDraw.Draw(crop)
for i, (t_, a) in enumerate(lab):
    crop.paste(Image.fromarray(a[y0:y1, x0:x1]), (0, i * (y1 - y0 + 30) + 30))
    dr.text((8, i * (y1 - y0 + 30) + 8), t_, fill=(255, 255, 0))
crop.save(os.path.join(OUT, 'mockup_frame_crop_plain.png'))
crop.resize((1500, int(1500 * crop.size[1] / crop.size[0])), Image.LANCZOS).save(os.path.join(OUT, 'work', 'view', 'mock_crop.jpg'), quality=88)
Image.fromarray(np.round(np.clip(np.dstack([wd * mcov * ground * haze] * 3), 0, 1) * 255).astype(np.uint8)).resize((1200, 502)).save(os.path.join(OUT, 'work', 'view', 'mock_w.jpg'), quality=80)


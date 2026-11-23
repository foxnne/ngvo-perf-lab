"""Previews: grass colour over the terrain height map (whole Tamriel) and the Whiterun tundra validation sheet."""
import os
import numpy as np
from PIL import Image, ImageDraw
import gcmlib as g

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
b = np.load(os.path.join(OUT, 'work', 'bake.npz'))
rgb, cover, lai_raw, count = b['rgb'], b['cover'], b['lai_raw'], b['count']

z = np.load(r'C:\Users\foxnn\dev\terrain-heightmap\land_tamriel.npz')
hm = np.full((g.NY * 32, g.NX * 32), -27000.0, np.float32)
for (x, y), h in zip(z['cells'], z['heights']):
    if g.MINX <= x <= g.MAXX and g.MINY <= y <= g.MAXY:
        hm[(y - g.MINY) * 32:(y - g.MINY + 1) * 32, (x - g.MINX) * 32:(x - g.MINX + 1) * 32] = h[:32, :32]
hm = hm[::-1]                                   # row 0 north, 128 units per texel
np.save(os.path.join(OUT, 'work', 'height_128.npy'), hm)


def hillshade(h, unit):
    gy, gx = np.gradient(h.astype(np.float64), unit)
    n = np.dstack([-gx, gy, np.ones_like(gx)])           # image y runs south, so +gy points north-facing
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    l = np.array([-0.5, -0.5, 0.7]); l /= np.linalg.norm(l)   # light from the north-west (image up-left)
    return np.clip((n * l).sum(2), 0, 1)


def base_image(h, unit):
    s = hillshade(h, unit)
    grey = 0.25 + 0.6 * s
    img = np.dstack([grey, grey, grey])
    sea = h < -14000
    img[sea] = img[sea] * 0.35 + np.array([0.10, 0.16, 0.24]) * 0.65
    return img


# ---- whole map, map resolution
h2 = hm.reshape(g.H, 2, g.W, 2).mean((1, 3))
base = base_image(h2, 256.0)
over = base * (1 - cover[..., None]) + g.lin2srgb(rgb) * cover[..., None]
Image.fromarray(np.round(over * 255).astype(np.uint8)).save(os.path.join(OUT, 'preview_tamriel_over_heightmap.png'))
sat = g.lin2srgb(np.clip(rgb * 2.0, 0, 1))        # same map, colour doubled in brightness to read the hues
over2 = base * (1 - cover[..., None]) + sat * cover[..., None]
Image.fromarray(np.round(over2 * 255).astype(np.uint8)).save(os.path.join(OUT, 'preview_tamriel_over_heightmap_bright.png'))

# ---- Whiterun tundra validation: cells -10..16 x -14..6
X0, X1, Y0, Y1 = -10, 16, -14, 6
ZOOM = 3
c0, c1 = (X0 - g.MINX) * g.TEXELS, (X1 + 1 - g.MINX) * g.TEXELS
r0, r1 = (g.MAXY - Y1) * g.TEXELS, (g.MAXY - Y0 + 1) * g.TEXELS


def up(a):
    return np.repeat(np.repeat(a, ZOOM, 0), ZOOM, 1)


hb = base_image(hm[r0 * 2:r1 * 2, c0 * 2:c1 * 2], 128.0)
hb = np.asarray(Image.fromarray(np.round(hb * 255).astype(np.uint8)).resize(((c1 - c0) * ZOOM, (r1 - r0) * ZOOM), Image.BILINEAR), np.float64) / 255
dens = up(np.clip(count[r0:r1, c0:c1] / 40.0, 0, 1))                # raw instances per 256-unit texel, unfiltered
dimg = np.dstack([dens, dens, dens])
cov = up(cover[r0:r1, c0:c1])
col = up(g.lin2srgb(np.clip(rgb[r0:r1, c0:c1] * 2.0, 0, 1)))
ov = hb * (1 - cov[..., None]) + col * cov[..., None]
flat = up(g.lin2srgb(np.clip(rgb[r0:r1, c0:c1] * 2.0, 0, 1)))
panels = [hb, dimg, ov, flat]
titles = ['terrain height map (hillshade, 128 u)', 'raw instance count per 256 u texel (unfiltered)', 'grass colour x coverage over terrain (colour x2)', 'RGB channel alone (colour x2, filled)']
ph, pw = hb.shape[:2]
sheet = Image.new('RGB', (pw * 2 + 12, ph * 2 + 12 + 40), (20, 20, 20))
marks = {'Whiterun (camera of the frame)': (19157, -7419), 'Western Watchtower': (-1500, -9300), 'Fort Greymoor': (-8200, -4700)}
for i, (p, t) in enumerate(zip(panels, titles)):
    im = Image.fromarray(np.round(np.clip(p, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for cx in range(X0, X1 + 2):
        if cx % 4 == 0:
            xx = (cx - X0) * g.TEXELS * ZOOM
            d.line([(xx, 0), (xx, ph)], fill=(255, 255, 255) if i == 1 else (60, 60, 60), width=1)
            d.text((xx + 3, 2), str(cx), fill=(255, 255, 0))
    for cy in range(Y0, Y1 + 2):
        if cy % 4 == 0:
            yy = (Y1 + 1 - cy) * g.TEXELS * ZOOM
            d.line([(0, yy), (pw, yy)], fill=(255, 255, 255) if i == 1 else (60, 60, 60), width=1)
            d.text((2, yy - 12), str(cy), fill=(255, 255, 0))
    for name, (wx, wy) in marks.items():
        px = (wx - X0 * g.CELL) / (g.CELL / g.TEXELS) * ZOOM
        py = ((Y1 + 1) * g.CELL - wy) / (g.CELL / g.TEXELS) * ZOOM
        d.ellipse([px - 5, py - 5, px + 5, py + 5], outline=(255, 60, 60), width=2)
        d.text((px + 8, py - 6), name, fill=(255, 60, 60))
    d.text((6, ph - 16), t, fill=(255, 255, 0))
    sheet.paste(im, ((i % 2) * (pw + 12), (i // 2) * (ph + 12)))
sheet.save(os.path.join(OUT, 'validation_whiterun_tundra.png'))
# numbers: grass vs sea, grass vs slope
hs = h2
sea = hs < -14000
gy, gx = np.gradient(h2.astype(np.float64), 256.0)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
has = count > 0
print('texels below sea level (-14000): %.1f%% of the map; of the texels holding land grass instances, below sea level: %.3f%%' % (100 * sea.mean(), 100 * (has & sea).sum() / has.sum()))
for lo, hi in ((0, 10), (10, 25), (25, 40), (40, 60), (60, 90)):
    m = (slope >= lo) & (slope < hi) & ~sea
    print('  slope %2d-%2d deg: %5.1f%% of land texels, %4.1f%% of them carry grass, mean coverage %.2f' % (lo, hi, 100 * m.sum() / (~sea).sum(), 100 * has[m].mean(), cover[m].mean()))

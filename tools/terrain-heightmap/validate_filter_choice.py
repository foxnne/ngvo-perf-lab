"""Sub-texel check of the filter choice. Truth = objects re-rasterised at 32 units over the Ilinalta region and shadowed
geometrically. Map shadows = 128-unit height map variants propagated like the compute shader and sampled BILINEARLY at the
32-unit receivers with the 256 bias, like TerrainShadows.hlsli. Reports recall of true shadow and false darkening."""
import os, sys, pickle, math, numpy as np
from PIL import Image
import build_heightmap_objects as B
import validate_objects as V            # reuses loaded layers + shadow_height (re-runs its report; harmless)
HERE = os.path.dirname(os.path.abspath(__file__))
out = open(os.path.join(V.OUT, 'filter_choice.txt'), 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); out.write(s + '\n')
land, surf = V.land, V.surf
I = np.load(os.path.join(HERE, 'objects_intervals.npz')); sel = pickle.load(open(os.path.join(HERE, 'objects_sel.pkl'), 'rb'))
variants = {}
for name, f, r in (('landscape only', None, 0), ('objects, no filter', 'none', 0), ('objects, open r1 (default)', 'open', 1), ('objects, erode r1', 'erode', 1), ('objects, erode r2', 'erode', 2)):
    variants[name] = land if f is None else B.compose(land.astype(np.float32), I['tex'], I['top'], I['bot'], 256.0, f, r)[0].astype(np.float64)
# hi-res region (extended west so the casters are inside)
F = 4; x0, x1, y0, y1 = -62000.0, -5000.0, -75000.0, -45000.0
i0 = int(round((x0 - B.X0) / 128)); i1 = int(round((x1 - B.X0) / 128)); j0 = int(round((y0 - B.Y0) / 128)); j1 = int(round((y1 - B.Y0) / 128))
nx, ny = (i1 - i0) * F + 1, (j1 - j0) * F + 1
def upsample(g_nu):          # north-up coarse grid -> hi-res south-up bilinear over the region
    g = g_nu[::-1]
    xs = i0 + np.arange(nx) / F; ys = j0 + np.arange(ny) / F
    xi = np.minimum(xs.astype(int), g.shape[1] - 2); yi = np.minimum(ys.astype(int), g.shape[0] - 2); fx = xs - xi; fy = ys - yi
    a = g[np.ix_(yi, xi)]; b = g[np.ix_(yi, xi + 1)]; c = g[np.ix_(yi + 1, xi)]; d = g[np.ix_(yi + 1, xi + 1)]
    return a * (1 - fx) * (1 - fy)[:, None] + b * fx * (1 - fy)[:, None] + c * (1 - fx) * fy[:, None] + d * fx * fy[:, None]
land_hi = upsample(land)
B.TEX = 128.0 / F; B.X0 = B.X0 + i0 * 128.0; B.Y0 = B.Y0 + j0 * 128.0; B.W = nx; B.H = ny
store = B.MeshStore(); T, Z, Bo = [], [], []; n = 0
for m, c, pos, rot, s, fk in sel:
    if not (x0 - 9000 < pos[0] < x1 + 9000 and y0 - 9000 < pos[1] < y1 + 9000): continue
    v, t, _ = store.get(m)
    for k in range(0, len(t), 4000):
        r = B.raster_ref(v, t[k:k + 4000], pos, rot, s)
        if r is not None: T.append(r[0]); Z.append(r[1]); Bo.append(r[2])
    n += 1
# note: chunking triangles splits intervals across chunks; bottoms are only used for the support test, so take top with bottom from the same chunk (slightly more permissive)
tex, top, bot = np.concatenate(T), np.concatenate(Z), np.concatenate(Bo)
surf_hi, rej, it = B.support_pass(land_hi.astype(np.float32), tex, top, bot, 256.0)
surf_hi = surf_hi.astype(np.float64)
P('hi-res truth: %d refs, %dx%d samples at %.0f units, %.1f%% covered by objects' % (n, nx, ny, B.TEX, 100 * (surf_hi > land_hi + 32).mean()))
obj = surf_hi > land_hi + 32
cs = slice((int(round((-30000 - x0) / 128)) * F), None)           # evaluation = the Ilinalta mountain crop (x >= -30000)
def true_shadow(el):
    S0 = upsample(V.shadow_height(surf, 270.0, el))[:, 0]          # shadow entering from the west edge
    S = surf_hi.copy(); S[:, 0] = np.maximum(S[:, 0], S0); dz = B.TEX * math.tan(math.radians(el))
    for i in range(1, nx):
        S[:, i] = np.maximum(surf_hi[:, i], S[:, i - 1] - dz)
    return surf_hi < S - 16.0
imgs = {}
for el in (8.0, 12.0, 15.0, 20.0, 30.0):
    tr = true_shadow(el)[:, cs]; o = obj[:, cs]; rec = surf_hi[:, cs]
    P('sun due west, elevation %.0f deg: true shadow covers %.1f%% of the Ilinalta crop (%.1f%% of object samples)' % (el, 100 * tr.mean(), 100 * tr[o].mean()))
    for name, g in variants.items():
        S = upsample(V.shadow_height(g, 270.0, el))[:, cs]
        m = rec < S - 256.0
        P('   %-28s shadowed %5.1f%% | recall of true shadow %5.1f%% (on objects %5.1f%%) | FALSE dark: %5.2f%% of truly lit samples, %5.2f%% of truly lit OBJECT samples' % (
            name, 100 * m.mean(), 100 * (m & tr).sum() / max(tr.sum(), 1), 100 * (m & tr & o).sum() / max((tr & o).sum(), 1), 100 * (m & ~tr).sum() / max((~tr).sum(), 1), 100 * (m & ~tr & o).sum() / max((~tr & o).sum(), 1)))
        if el in (12.0, 15.0): imgs[(el, name)] = (m, tr, o)
# picture: per variant, grey = correct shadow, white = correct lit, red = false dark, blue = missed shadow
for el in (12.0, 15.0):
    tiles = []
    for name in variants:
        m, tr, o = imgs[(el, name)]
        rgb = np.zeros(m.shape + (3,), np.uint8)
        rgb[~m & ~tr] = (225, 225, 215); rgb[m & tr] = (60, 60, 70); rgb[m & ~tr] = (230, 40, 40); rgb[~m & tr] = (60, 120, 240)
        rgb[o & ~m & ~tr] = (240, 205, 150)
        tiles.append(rgb[::-1])
    V.panel(tiles, list(variants), 1, os.path.join(V.OUT, 'filter_choice_el%d.png' % el))
P('images filter_choice_el12.png / el15.png: dark grey = correctly shadowed, light = correctly lit (tan = lit rock objects), BLUE = shadow missed, RED = falsely darkened')

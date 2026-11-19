import numpy as np, hmlib, os, struct
from PIL import Image, ImageDraw
g = np.load('tamriel_true_heights.npy').astype(np.float64)       # image orientation, row 0 = north
assert g.shape == (3008, 3808)
assert np.all(np.mod(g, 8) == 0), 'heights are not multiples of 8'
zmin, zmax = int(g.min() // 8), int(-(-g.max() // 8))
print('zMin/zMax fields (height/8):', zmin, zmax)
raw = g / 8 + 32767            # xLODGen convention, verified exact on the shipped 16-bit MarkarthWorld map
assert raw.min() >= 0 and raw.max() <= 65535
raw = raw.astype('<u2')
name = 'Tamriel.Terrain.HeightMap.-57.-43.61.50.%d.%d.dds' % (zmin, zmax)
out = os.path.join(r'C:\Users\foxnn\dev\terrain-heightmap\mod\textures\terrain\HeightMaps', name)
os.makedirs(os.path.dirname(out), exist_ok=True)
template = hmlib.SHIPPED_DIR + r'\MarkarthWorld.Terrain.HeightMap.-48.-3.-31.5.-3375.2609.dds'
hmlib.write_l16(out, raw, template)
print('wrote', out, os.path.getsize(out), 'bytes; same name as shipped:', name == os.path.basename(hmlib.SHIPPED_TAMRIEL))
b = open(out, 'rb').read(128); t = open(template, 'rb').read(128)
print('header differs from Markarth template only at byte offsets:', [i for i in range(128) if b[i] != t[i]])
# parse the file name exactly like ParseHeightmapPath
f = os.path.basename(out)[:-4].split('.')
assert len(f) == 9 and f[1] == 'Terrain' and f[2] == 'HeightMap'
pos0 = (int(f[3]) * 4096.0, (int(f[6]) + 1) * 4096.0, -32767 * 8.0); pos1 = ((int(f[5]) + 1) * 4096.0, int(f[4]) * 4096.0, 32767 * 8.0)
zr = (int(f[7]) * 8.0, int(f[8]) * 8.0)
print('parsed: worldspace', f[0], 'pos0', pos0, 'pos1', pos1, 'zRange', zr)

# ---- re-read and verify against LAND source
t01, rr, fmt = hmlib.read_dds(out)
H2 = hmlib.texel_to_height(t01)
Hh, W = H2.shape
print('re-read', fmt, H2.shape, 'decoded range %.2f..%.2f ; distinct values %d' % (H2.min(), H2.max(), len(np.unique(rr))))
z = np.load('land_tamriel.npz'); cells, LH = z['cells'], z['heights']
rng = np.random.default_rng(12345)
errs = []
for _ in range(1000):
    k = rng.integers(len(cells)); r = rng.integers(32); c = rng.integers(32)
    cx, cy = int(cells[k][0]), int(cells[k][1])
    wx = cx * 4096 + c * 128.0; wy = cy * 4096 + r * 128.0
    # loader UV: uv = pos*Scale + Offset ; Scale = 1/(pos1-pos0) ; Offset = -pos0*Scale + (0.5/W, -0.5/H)
    u = (wx - pos0[0]) / (pos1[0] - pos0[0]) + 0.5 / W
    v = (wy - pos0[1]) / (pos1[1] - pos0[1]) - 0.5 / Hh
    px, py = u * W - 0.5, v * Hh - 0.5        # texel index whose centre is at uv
    assert abs(px - round(px)) < 1e-6 and abs(py - round(py)) < 1e-6, (px, py)
    errs.append(H2[int(round(py)), int(round(px))] - float(LH[k][r, c]))
errs = np.array(errs)
print('1000 random LAND vertices via loader UV mapping: err min %.3f max %.3f mean %.3f ; max|err| %.3f (must be <= 8)' % (errs.min(), errs.max(), errs.mean(), np.abs(errs).max()))
assert np.abs(errs).max() <= 8
full = np.abs(H2 - g)
print('whole grid vs source: max|err| %.3f mean %.3f' % (full.max(), full.mean()))
zn = (H2 - zr[0]) / (zr[1] - zr[0])
print('normalised by zRange: min %.6f max %.6f (texels outside 0..1: %d, clamp loss <= %.1f units)' % (zn.min(), zn.max(), ((zn < 0) | (zn > 1)).sum(), max(zr[0] - H2.min(), H2.max() - zr[1], 0)))

# ---- before/after profile across the Throat of the World summit (west-east)
S = np.load('shipped_bc4_heights.npy').astype(np.float64)
yy, xx = np.unravel_index(np.argmax(g), g.shape)
cx, cy = xx // 32 - 57, (3007 - yy) // 32 - 43
print('summit texel', xx, yy, 'cell', (cx, cy), 'world x,y', -57 * 4096 + xx * 128, -43 * 4096 + (3007 - yy) * 128, 'z', g[yy, xx])
x0, x1 = xx - 160, xx + 161
a, bq = H2[yy, x0:x1], S[yy, x0:x1]
with open('profile_throat_before_after.txt', 'w') as fh:
    fh.write('# West-east cross-section through the Throat of the World summit (image row %d, world y %d)\n' % (yy, -43 * 4096 + (3007 - yy) * 128))
    fh.write('# px  world_x  shipped_BC4  new_16bit  diff\n')
    for i in range(x1 - x0):
        fh.write('%5d %8d %10.1f %10.1f %8.1f\n' % (x0 + i, -57 * 4096 + (x0 + i) * 128, bq[i], a[i], bq[i] - a[i]))
runs = np.flatnonzero(np.diff(bq) != 0)
print('profile %d texels (%.0f units): shipped has %d distinct levels and %d steps (sizes: %s); new has %d distinct levels, max step between texels %.0f' % (
    len(a), len(a) * 128, len(np.unique(np.round(bq, 1))), len(runs), sorted(set(np.round(np.abs(np.diff(bq)[runs])).astype(int).tolist())), len(np.unique(a)), np.abs(np.diff(a)).max()))
print('longest flat run in shipped profile: %d texels = %d units' % (np.diff(np.r_[-1, runs, len(bq) - 1]).max(), np.diff(np.r_[-1, runs, len(bq) - 1]).max() * 128))
# PNG plot
Wp, Hp, m = 1400, 700, 60
im = Image.new('RGB', (Wp, Hp), 'white'); d = ImageDraw.Draw(im)
lo, hi = min(a.min(), bq.min()) - 500, max(a.max(), bq.max()) + 500
X = lambda i: m + i * (Wp - 2 * m) / (len(a) - 1)
Y = lambda zv: Hp - m - (zv - lo) * (Hp - 2 * m) / (hi - lo)
for zt in range(int(lo // 4000 * 4000), int(hi) + 1, 4000):
    if zt < lo: continue
    d.line([(m, Y(zt)), (Wp - m, Y(zt))], fill=(220, 220, 220)); d.text((4, Y(zt) - 6), str(zt), fill='black')
for i in range(0, len(a), 32):
    d.line([(X(i), m), (X(i), Hp - m)], fill=(235, 235, 235)); d.text((X(i) - 14, Hp - m + 6), str(-57 * 4096 + (x0 + i) * 128), fill='black')
d.line([(X(i), Y(v)) for i, v in enumerate(a)], fill=(20, 110, 200), width=2)
pts = []
for i, v in enumerate(bq):
    pts += [(X(i - 0.5), Y(v)), (X(i + 0.5), Y(v))]
d.line(pts, fill=(210, 40, 40), width=2)
d.text((m, 10), 'Throat of the World, west-east section through the summit (world y %d). x = world x, y = height (game units)' % (-43 * 4096 + (3007 - yy) * 128), fill='black')
d.text((m, 26), 'red: shipped BC4 8-bit map as the shader decodes it (step 2056 units)   blue: new 16-bit map (step 8 units)', fill='black')
im.save('profile_throat_before_after.png')
# count real terrain differences vs shipped beyond BC4 error
rec = hmlib.texel_to_height(np.floor((g / 8 + 32767) / 257) / 255)
dd = np.abs(S - rec)
print('texels where shipped differs from floor-8-bit(ours) by more than one 8-bit step (true data differences): %d in cells %s' % ((dd > 2100).sum(), sorted({(int(x // 32 - 57), int((3007 - y) // 32 - 43)) for y, x in zip(*np.nonzero(dd > 2100))})))

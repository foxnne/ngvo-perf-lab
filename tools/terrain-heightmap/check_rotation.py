"""Rotation-convention check: tilted, ground-hugging objects must follow the landscape only with the right convention."""
import pickle, math, numpy as np, re, sys
import build_heightmap_objects as B
sel = pickle.load(open('objects_sel.pkl', 'rb'))
land = B.read_land(B.DEFAULT_LAND)[::-1].ravel()
store = B.MeshStore()
def mats(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, sx], [0, -sx, cx]]); Ry = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]]); Rz = np.array([[cz, sz, 0], [-sz, cz, 0], [0, 0, 1]])
    return Rx, Ry, Rz
C = {
 'Rz*Ry*Rx clockwise (floating-mesh nif.py)': lambda rx, ry, rz: (lambda X, Y, Z: Z @ Y @ X)(*mats(rx, ry, rz)),
 'Rx*Ry*Rz clockwise (USED)':        lambda rx, ry, rz: (lambda X, Y, Z: X @ Y @ Z)(*mats(rx, ry, rz)),
 'Rz*Ry*Rx counter-clockwise': lambda rx, ry, rz: (lambda X, Y, Z: Z @ Y @ X)(*mats(-rx, -ry, -rz)),
 'Rx*Ry*Rz counter-clockwise': lambda rx, ry, rz: (lambda X, Y, Z: X @ Y @ Z)(*mats(-rx, -ry, -rz)),
 'Ry*Rx*Rz clockwise':        lambda rx, ry, rz: (lambda X, Y, Z: Y @ X @ Z)(*mats(rx, ry, rz)),
 'Rx*Ry*Rz, Z cw, X/Y ccw':   lambda rx, ry, rz: (lambda X, Y, Z: X @ Y @ Z)(*mats(-rx, -ry, rz)),
 'Rx*Ry*Rz, X cw, Y ccw':   lambda rx, ry, rz: (lambda X, Y, Z: X @ Y @ Z)(*mats(rx, -ry, rz)),
 'Rx*Ry*Rz, X ccw, Y cw':   lambda rx, ry, rz: (lambda X, Y, Z: X @ Y @ Z)(*mats(-rx, ry, rz)),
 'Rz*Rx*Ry clockwise':        lambda rx, ry, rz: (lambda X, Y, Z: Z @ X @ Y)(*mats(rx, ry, rz)),
 'Rz only (tilt ignored)':    lambda rx, ry, rz: mats(0, 0, rz)[2],
 'Z clockwise, X/Y counter':  lambda rx, ry, rz: (lambda X, Y, Z: Z @ Y @ X)(*mats(-rx, -ry, rz)),
}
pat = re.compile(r'rockpilel0[234]|rocktundraland|dirtcliffsisland|volcanicplateau|rockpilem01')
cand = [s for s in sel if pat.search(s[0]) and max(abs(s[3][0]), abs(s[3][1])) > 0.2 and min(abs(s[3][0]), abs(s[3][1])) > 0.08]
rng = np.random.default_rng(1); rng.shuffle(cand); cand = cand[:400]
print('tilted ground-hugging refs tested:', len(cand), '(|rx| or |ry| > 0.2 rad and both > 0.08 rad)')
for name, fn in C.items():
    sc = []
    for m, c, pos, rot, s, fk in cand:
        v, t, _ = store.get(m)
        r = B.raster_ref(v, t, pos, rot, s, rot_fn=fn)
        if r is None: continue
        d = r[1] - land[r[0]]
        sc.append((np.median(np.abs(d - np.median(d))), np.median(d)))
    sc = np.array(sc)
    print('%-30s spread of (object top - landscape) within footprint: median %.1f  p90 %.1f ; median offset %.1f' % (name, np.median(sc[:, 0]), np.percentile(sc[:, 0], 90), np.median(sc[:, 1])))

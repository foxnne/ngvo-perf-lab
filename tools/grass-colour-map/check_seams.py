import sys, os, numpy as np
sys.path.insert(0, r'C:\Users\foxnn\dev\skyrimnet-wardrobe')
import tes5, gcmlib as g
b = tes5.BSA(r'C:\Modlists\NGVO 8.0 Beta\mods\Cleaned Skyrim SE Textures\Skyrim - Textures7.bsa')
mod = r'out\foxnne - Terrain LOD Grass Tint TEST (current LOD, strength 0.8)\textures\terrain\tamriel'
tmp = r'out\work\dds_tmp'
def orig(t): return g.read_dds_rgba(b.read('textures\\terrain\\tamriel\\tamriel.%s.dds' % t), tmp)[0][..., :3] * 255
def new(t): return g.read_dds_rgba(os.path.join(mod, 'Tamriel.%s.dds' % t), tmp)[0][..., :3] * 255
for w, e in (('4.-4.-4', '4.0.-4'), ('4.-8.-4', '4.-4.-4'), ('8.-8.-8', '8.0.-8')):
    ow, oe, nw, ne = orig(w), orig(e), new(w), new(e)
    print('%s | %s  step across the shared edge (mean abs, 8-bit): original %.2f, tinted %.2f ; one column inside the tile: original %.2f, tinted %.2f' % (
        w, e, np.abs(ow[:, -1] - oe[:, 0]).mean(), np.abs(nw[:, -1] - ne[:, 0]).mean(), np.abs(ow[:, -2] - ow[:, -1]).mean(), np.abs(nw[:, -2] - nw[:, -1]).mean()))
s, n = '4.-4.-4', '4.-4.0'
os_, on, ns, nn = orig(s), orig(n), new(s), new(n)
print('%s (south) | %s (north): original %.2f, tinted %.2f' % (s, n, np.abs(os_[0] - on[-1]).mean(), np.abs(ns[0] - nn[-1]).mean()))
fs = os.listdir(mod); print(len(fs), 'files', round(sum(os.path.getsize(os.path.join(mod, f)) for f in fs) / 1e6, 1), 'MB')

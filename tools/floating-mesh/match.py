"""Project the DynDOLOD mineral-pool LOD mesh at its SAVE position onto the screenshots (decisive shape test)."""
import sys, os, pickle, math, struct, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from cam import *
from nif import *
from bsa import BSA
from ess import *
from PIL import Image, ImageDraw

SAVE = r"C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/saves/preRestart_auri.ess"
SHOTS = r"C:/Users/foxnn/dev/ngvo-perf-lab/results/sky_sweep/"
M = pickle.load(open(os.path.join(HERE, 'meshidx.pkl'), 'rb'))
mi = M['idx']
m = os.path.join('water', 'mineralpoolsmwater01_water_shadow.nif')
src = mi.get(m)
print('loose:', src)
if not src:
    for p in M['bsas']:
        b = BSA(p)
        if os.path.join('meshes', m) in b.files:
            src = b.read(os.path.join('meshes', m)); print('bsa', p); break
sh, blk, strs = shapes(src)
print([t for t, _, _ in blk])
info, formids, forms = parse(SAVE)
tgt = None
for refid, cflags, t, ver, l2, data in forms:
    fid = resolve(refid, formids)
    if fid is None:
        continue
    if (fid & 0xFFFFFF) == 0x057209 and (fid >> 24) < 0xFE:
        if l2: data = zlib.decompress(data)
        print('save form %08X flags %08X type %d ver %d len %d' % (fid, cflags, t, ver, len(data)), data[:40].hex())
        tgt = struct.unpack_from('<6f', data, 3); print(tgt)
    if (fid >> 24) == 0xFE and info['light'][(fid >> 12) & 0xFFF].lower().startswith('ccbgssse018'):
        dd = zlib.decompress(data) if l2 else data
        print('shadowrend form %08X flags %08X type %d len %d' % (fid, cflags, t, len(dd)), dd[:40].hex())
print('plugin idx 0x6E in save =', info['plugins'][0x6E])
c = Cam(pitch=3.0)
pos = np.array(tgt[:3]); R = ref_matrix(*tgt[3:])
for tag, f in [('a', 'terrainlod-plains/00_sunlit__h12.png'), ('b', 'nocloudmesh-plains/00_mist_removed_height_fog_off__h12.png')]:
    x0, y0, x1, y1 = 2680, 440, 2810, 505; S = 10
    im = Image.open(SHOTS + f).convert('RGB').crop((x0, y0, x1, y1)).resize(((x1 - x0) * S, (y1 - y0) * S), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    for s, col in zip(sh, [(255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 255, 255)]):
        w = s['v'] @ R.T + pos; d = w - c.pos; zz = d @ c.f
        X = W / 2 + c.focal * (d @ c.r) / zz; Y = H / 2 - c.focal * (d @ c.u) / zz
        if tag == 'a':
            print(s['name'], len(s['v']), 'verts local bbox', s['v'].min(0).round(), s['v'].max(0).round(), 'screen bbox x', X.min().round(1), X.max().round(1), 'y', Y.min().round(1), Y.max().round(1), 'depth', zz.min().round(), zz.max().round())
        for t in s['tris']:
            dr.polygon([((X[i] - x0) * S, (Y[i] - y0) * S) for i in t], outline=col)
    im.save(os.path.join(HERE, 'match_%s.png' % tag))

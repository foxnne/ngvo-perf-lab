"""Region statistics per file + a front/side picture of the decoration triangles coloured by atlas region over the trunk (grey).
usage: view3d.py [basename ...]  -> work/view_<name>.png ; with no args: stats for all standing targets."""
import json, os, sys, collections
import numpy as np
from PIL import Image, ImageDraw
import vfsidx, niflib, geom, regions
W = vfsidx.WORK
tg = json.load(open(os.path.join(W, 'targets.json')))
COL = {'leaf': (40, 220, 40), 'stem': (255, 140, 0), 'twig': (200, 60, 200), 'cap': (255, 255, 0), 'fern': (0, 200, 255), 'fung': (255, 0, 0),
       'bark': (255, 255, 255), 'tend': (120, 120, 255), 'othe': (255, 0, 255)}
want = [a.lower() for a in sys.argv[1:]]
for rel, m in sorted(tg.items()):
    if m['kind'] != 'standing' or 'tree of life' in rel: continue
    base = os.path.basename(rel)[:-4]
    nif = niflib.Nif(vfsidx.read(rel))
    shapes = {}
    for i, t in enumerate(nif.btypes):
        if t in niflib.SHAPE_TYPES:
            s = nif.shape(i)
            L, raw, pos, uv, tris = geom.read(nif, i)
            shapes[i] = (s, pos, uv, tris)
    for i, (s, pos, uv, tris) in shapes.items():
        tex = s['textures'][0].lower() if s['textures'] else ''
        if 'ivy' not in tex: continue
        atlas = os.path.basename(tex).split('_')[0]
        cls = regions.classify(atlas, uv[tris])
        cnt = collections.Counter(cls)
        print('%-40s %s' % (base, ' '.join('%s=%d' % kv for kv in sorted(cnt.items()))))
        if base in want:
            S = 900
            allp = np.concatenate([p for (_, p, _, _) in shapes.values()])
            lo, hi = allp.min(0), allp.max(0)
            sc = (S - 20) / max(hi[2] - lo[2], hi[0] - lo[0], hi[1] - lo[1])
            im = Image.new('RGB', (S * 2, S), (20, 20, 20))
            d = ImageDraw.Draw(im)
            for view, ax in ((0, 0), (1, 1)):
                def P(p):
                    return (view * S + S / 2 + (p[ax] - (lo[ax] + hi[ax]) / 2) * sc, S - 10 - (p[2] - lo[2]) * sc)
                for j, (s2, pos2, uv2, tris2) in shapes.items():
                    if j == i: continue
                    isleaf = 'lea' in s2['name'].lower()
                    if isleaf: continue
                    for t in pos2[tris2]:
                        d.polygon([P(p) for p in t], fill=(70, 70, 70))
                for t, c in zip(pos[tris], cls):
                    d.polygon([P(p) for p in t], fill=COL.get(c[:4], (255, 0, 255)))
            im.save(os.path.join(W, 'view_%s.png' % base))

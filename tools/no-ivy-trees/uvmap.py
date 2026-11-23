"""Draw the UV footprint of the ivy-atlas shapes of the standing NotWL trees over the atlas, per atlas (aggregate) -> work/uv_<atlas>.png
and print per file a coarse 8x8 histogram of triangle UV centroids."""
import json, os, sys, collections
import numpy as np
from PIL import Image, ImageDraw
import vfsidx, niflib, geom
W = vfsidx.WORK
tg = json.load(open(os.path.join(W, 'targets.json')))
agg = collections.defaultdict(list)
for rel, m in sorted(tg.items()):
    if m['kind'] != 'standing': continue
    nif = niflib.Nif(vfsidx.read(rel))
    for i, t in enumerate(nif.btypes):
        if t in niflib.SHAPE_TYPES:
            s = nif.shape(i)
            if s['textures'] and 'ivy' in s['textures'][0].lower():
                L, raw, pos, uv, tris = geom.read(nif, i)
                key = os.path.basename(s['textures'][0]).lower().split('_')[0]
                agg[key].append((rel, uv, tris))
                c = uv[tris].mean(1)
                print(os.path.basename(rel), s['name'], 'nv', L['nvert'], 'nt', L['ntri'], 'uv range', uv.min(0).round(2), uv.max(0).round(2), 'fullprec', L['fullprec'], 'skin', s['skin'], 'flags %x %x' % (s['f1'], s['f2']))
for key, lst in agg.items():
    src = os.path.join(W, 'tex', key + '_summer.png')
    im = Image.open(src).convert('RGBA')
    bg = Image.new('RGBA', im.size, (40, 40, 40, 255)); bg.alpha_composite(im)
    S = 2
    bg = bg.resize((im.size[0] * S, im.size[1] * S))
    d = ImageDraw.Draw(bg, 'RGBA')
    n = bg.size[0]
    for rel, uv, tris in lst:
        for t in uv[tris]:
            d.polygon([(float(x % 1.0 if not (0 <= x <= 1) else x) * n, float(y % 1.0 if not (0 <= y <= 1) else y) * n) for x, y in t], outline=(255, 0, 0, 90))
    bg.convert('RGB').save(os.path.join(W, 'uv_%s.png' % key))
    print(key, len(lst), 'shapes')

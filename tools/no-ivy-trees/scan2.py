"""Phase 2: parse the phase-1 hits, list shapes that are ivy (texture path or shape/node name). -> work/hits2.json"""
import json, os, re, sys, collections
import vfsidx, niflib
h = json.load(open(os.path.join(vfsidx.WORK, 'hits1.json')))
IVY = re.compile(r'ivy|vine', re.I)
FALSE = re.compile(r'divine|vinegar|trellisvines', re.I)
out = {}
errs = collections.Counter()
for rel in sorted(h):
    b = vfsidx.read(rel)
    try:
        n = niflib.Nif(b)
    except Exception as e:
        errs['hdr:' + str(e)[:40]] += 1
        if any(k in rel for k in ('landscape', 'tree', 'plant', 'lod')): print('HDR-ERR', rel, e)
        continue
    shapes = []
    legacy = [t for t in n.btypes if t in ('NiTriShape', 'NiTriStrips')]
    for i, t in enumerate(n.btypes):
        if t in niflib.SHAPE_TYPES:
            s = n.shape(i)
            tex = [x for x in s['textures'] if x]
            ivy = any(IVY.search(x) for x in tex[:1]) or bool(IVY.search(s['name']))
            shapes.append(dict(i=i, name=s['name'], nv=s['nvert'], nt=s['ntri'], tex=tex[:2], ivy=ivy, skin=s['skin'] >= 0, type=t))
    nodes = [n.name(i) for i, t in enumerate(n.btypes) if t in niflib.NODE_TYPES and IVY.search(n.name(i))]
    if any(s['ivy'] for s in shapes) or nodes or legacy:
        out[rel] = dict(win=h[rel]['win'], root=n.btypes[0], types=sorted(set(n.btypes)), shapes=shapes, ivynodes=nodes, legacy=len(legacy))
json.dump(out, open(os.path.join(vfsidx.WORK, 'hits2.json'), 'w'), indent=1)
print(len(out), 'files with ivy shapes/nodes or legacy geometry;', dict(errs))
for rel, d in sorted(out.items()):
    iv = [s for s in d['shapes'] if s['ivy']]
    if not iv and not d['ivynodes']:
        continue
    print('%s | %s | root %s | shapes %d ivy %d | %s' % (d['win'][1], rel, d['root'], len(d['shapes']), len(iv), '; '.join('%s[%s nv%d]' % (s['name'], os.path.basename(s['tex'][0]) if s['tex'] else '-', s['nv']) for s in iv)))

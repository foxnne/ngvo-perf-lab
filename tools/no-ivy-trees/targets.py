"""Ivy meshes (tree folders + Lux Via ivy statics) -> winning base records that use them. -> work/targets.json"""
import json, os, pickle, re, collections
BS = chr(92)
W = r'C:\Users\foxnn\dev\no-ivy-trees\work'
h2 = json.load(open(os.path.join(W, 'hits2.json')))
B = pickle.load(open(os.path.join(W, 'bases.pkl'), 'rb'))
bases = B['bases']
FALLEN = re.compile(r'stump|log\d|log_|hollow|uprooted|fallen|dead_?log|trunk_?fallen|broken', re.I)
models = {}
for r, d in h2.items():
    iv = [s for s in d['shapes'] if s['ivy'] and ('ivy' in s['name'].lower() or (s['tex'] and 'ivy' in s['tex'][0].lower()) or 'vine' in (s['tex'][0].lower() if s['tex'] else ''))]
    if not iv: continue
    if (BS + 'landscape' + BS + 'trees' + BS) in r:
        kind = 'fallen' if FALLEN.search(os.path.basename(r)) else 'standing'
    elif r.startswith('meshes' + BS + 'ivy' + BS):
        kind = 'ivy-static'
    else:
        continue
    models[r] = dict(kind=kind, mod=d['win'][1], src=d['win'][0], root=d['root'], ivy=[(s['name'], s['nv'], s['nt'], s['tex'][0] if s['tex'] else '') for s in iv],
                     nshapes=len(d['shapes']), bases=[])
bymodel = collections.defaultdict(list)
for fk, b in bases.items():
    if b['model'] in models:
        models[b['model']]['bases'].append(dict(fk='%s:%06X' % fk, type=b['type'], edid=b['edid'], plugin=b['plugin'], chain=b['chain']))
json.dump(models, open(os.path.join(W, 'targets.json'), 'w'), indent=1)
for r, m in sorted(models.items(), key=lambda x: (x[1]['kind'], x[0])):
    print('%-10s %-26s %s | ivy %s | %s' % (m['kind'], m['mod'][:26], r[len('meshes/landscape/'):], ','.join('%s nv%d' % (a, b) for a, b, c, d in m['ivy']),
          '; '.join('%s %s %s <%s>' % (b['type'], b['edid'], b['fk'], b['plugin']) for b in m['bases']) or 'NO BASE RECORD'))

import json, os, pickle, collections, re, sys
import vfsidx, swaps
BS = chr(92)
W = vfsidx.WORK
rep = json.load(open(os.path.join(W, 'build_report.json')))
tg = json.load(open(os.path.join(W, 'targets.json')))
refs = pickle.load(open(os.path.join(W, 'refs.pkl'), 'rb'))
B = pickle.load(open(os.path.join(W, 'bases.pkl'), 'rb'))['bases']
fixed = {r['rel'] for r in rep['files']}
b2m = {}
for fk, b in B.items():
    if b['model'] in tg: b2m[fk] = b
tot = collections.Counter(); rw = collections.Counter(); plug = collections.defaultdict(collections.Counter); rwlist = collections.defaultdict(list); worlds = collections.defaultdict(collections.Counter)
dyn = collections.Counter()
for rk, d in refs.items():
    b = b2m.get(d['base'])
    if not b or d['flags'] & 0x820: continue
    if rk[0].startswith('dyndolod'):
        dyn[b['model']] += 1; continue
    m = b['model']
    tot[m] += 1; plug[m][d['first']] += 1; worlds[m][d['world']] += 1
    if d['world'] == ('skyrim.esm', 0x3C) and d['pos']:
        cx, cy = int(d['pos'][0] // 4096), int(d['pos'][1] // 4096)
        if 2 <= cx <= 8 and -16 <= cy <= -9:
            rw[m] += 1; rwlist[m].append((cx, cy, '%s:%06X' % rk, b['edid']))
for kind in ('standing', 'fallen', 'ivy-static'):
    print('==', kind)
    T = R = 0
    for rel, m in sorted(tg.items()):
        if m['kind'] != kind: continue
        T += tot[rel]; R += rw[rel]
        print('%-58s %s total %4d  riverwood %3d  %s %s' % (rel[len('meshes/landscape/'):], 'FIXED' if rel in fixed else '     ', tot[rel], rw[rel],
              ','.join('%s x%d' % (p[:28], n) for p, n in plug[rel].most_common(3)), ('| dyndolod helper refs %d' % dyn[rel]) if dyn[rel] else ''))
        if kind == 'standing':
            print('        bases:', '; '.join('%s %s [%s]' % (b['type'], b['edid'], b['plugin']) for b in m['bases']))
            if rwlist[rel]: print('        riverwood cells:', ', '.join('(%d,%d) %s' % (a, b, c) for a, b, c, e in sorted(rwlist[rel])))
    print('   sum total %d riverwood %d' % (T, R))
# swaps mentioning these bases
edids = {b['edid'].lower() for m in tg.values() if m['kind'] == 'standing' for b in m['bases'] if b['edid']}
fids = {(b['fk'].split(':')[0], int(b['fk'].split(':')[1], 16)) for m in tg.values() if m['kind'] == 'standing' for b in m['bases']}
hits = 0
for k, (mod, p) in sorted(swaps.swap_files().items()):
    try: txt = open(p, encoding='utf-8', errors='replace').read()
    except Exception: continue
    for ln in txt.splitlines():
        l = ln.lower()
        if l.startswith(';'): continue
        if any(e in l for e in edids) or any(('0x%x~%s' % (i, o)) in l for o, i in fids) or 'nature of the wild lands.esp' in l:
            hits += 1
            if hits < 15: print('SWAP', k, '|', ln[:160])
print('swap lines touching these bases / NotWL forms:', hits)

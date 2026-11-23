"""Census of every tree-like placement (TREE bases + any base with a model under landscape\\trees) in the Riverwood area and world-wide,
by winning model, with the non-trunk/leaf 'decoration' shapes of each model. step 1 (arg 'targets'): write extra_targets.json; step 2: report."""
import json, os, pickle, sys, collections, re
import vfsidx, niflib
BS = chr(92)
W = vfsidx.WORK
B = pickle.load(open(os.path.join(W, 'bases.pkl'), 'rb'))['bases']
sel = {fk: b for fk, b in B.items() if b['model'] and (b['type'] == 'TREE' or (BS + 'landscape' + BS + 'trees' + BS) in b['model'] or b['model'].startswith('meshes' + BS + 'ivy' + BS))}
if sys.argv[1:] == ['targets']:
    json.dump([list(k) for k in sel], open(os.path.join(W, 'extra_targets.json'), 'w'))
    print(len(sel), 'bases'); sys.exit()
refs = pickle.load(open(os.path.join(W, 'refs.pkl'), 'rb'))
tot = collections.Counter(); rw = collections.Counter()
for rk, d in refs.items():
    if d['base'] not in sel or d['flags'] & 0x820 or rk[0].startswith('dyndolod') or d['plugin'].lower().startswith('dyndolod'): continue
    m = sel[d['base']]['model']
    tot[m] += 1
    if d['world'] == ('skyrim.esm', 0x3C) and d['pos']:
        cx, cy = int(d['pos'][0] // 4096), int(d['pos'][1] // 4096)
        if 2 <= cx <= 8 and -16 <= cy <= -9: rw[m] += 1
json.dump({'tot': tot, 'rw': rw}, open(os.path.join(W, 'census.json'), 'w'))
print('Riverwood area tree-like refs:', sum(rw.values()), ' world:', sum(tot.values()))
for m, n in rw.most_common(70):
    w = vfsidx.winner(m)
    desc = 'MISSING'
    if w:
        try:
            nf = niflib.Nif(vfsidx.read(m))
            sh = []
            for i, t in enumerate(nf.btypes):
                if t in niflib.SHAPE_TYPES:
                    s = nf.shape(i)
                    sh.append('%s[%s]' % (s['name'][:14], os.path.basename(s['textures'][0])[:-4] if s['textures'] else '-'))
            desc = w[1][:18] + ' | ' + ' '.join(sh)
        except Exception as e:
            desc = w[1][:18] + ' | ERR ' + str(e)[:40]
    print('%4d %5d %-62s %s' % (n, tot[m], m[len('meshes/landscape/'):], desc[:230]))

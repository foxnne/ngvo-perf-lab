import os, pickle, collections
d = pickle.load(open('refs.pkl', 'rb'))
refs, bases, names = d['refs'], d['bases'], d['names']
c = collections.Counter(); info = {}
c2 = collections.Counter()
STD = tuple(x.replace('/', os.sep) for x in ('landscape/rocks', 'landscape/mountains', 'landscape/ice', 'landscape/dirtcliffs', 'landscape/tundra'))
for fk, h in refs.items():
    r = h[-1]
    if 'data' not in r or r['flags'] & 0x820: continue
    b = bases.get(r.get('base'))
    if not b or not b[2]: continue
    m = os.path.normpath(b[2].lower())
    if m.startswith('meshes' + os.sep): m = m[7:]
    if os.sep not in m:
        c[m] += 1; info[m] = (b[0], b[1], names[b[3]], b[5])
    if any(k in m for k in ('rock', 'cliff', 'mountain', 'glacier', 'boulder', 'mtn')) and not m.startswith(STD):
        o = b[5] or (0,)*6
        c2[(m, o[3]-o[0], o[4]-o[1], o[5]-o[2])] += 1
for m, n in c.most_common(30): print(n, m, info[m])
print()
for m, n in c2.most_common(80): print(n, m)

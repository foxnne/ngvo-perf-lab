import os, pickle, collections
d = pickle.load(open('refs.pkl', 'rb'))
refs, bases = d['refs'], d['bases']
agg = {}
for fk, h in refs.items():
    r = h[-1]
    if 'data' not in r or r['flags'] & 0x820: continue
    b = bases.get(r.get('base'))
    if not b or not b[2]: continue
    m = os.path.normpath(b[2].lower())
    if m.startswith('meshes' + os.sep): m = m[7:]
    o = b[5] or (0,)*6
    s = r.get('scale') or 1.0
    a = agg.setdefault(m, [0, b[0], o, 0.0])
    a[0] += 1; a[3] = max(a[3], s)
dirs = collections.defaultdict(list)
for m, (n, t, o, smax) in agg.items():
    dirs[os.path.dirname(m)].append((n, os.path.basename(m), t, o[3]-o[0], o[4]-o[1], o[5]-o[2], smax))
import sys
want = sys.argv[1:]
if want:
    for dn in sorted(dirs):
        if any(dn.startswith(w) for w in want):
            print('==', dn, sum(x[0] for x in dirs[dn]))
            for x in sorted(dirs[dn], reverse=True): print('   %5d %-45s %s  %5d x %5d x %5d  smax %.2f' % x)
else:
    # big things outside landscape\mountains|rocks|trees
    out = []
    for m, (n, t, o, smax) in agg.items():
        ext = max(o[3]-o[0], o[4]-o[1])
        if ext >= 1500 and not m.startswith(('landscape\mountains', 'landscape\rocks', 'landscape\trees')) and t in ('STAT','MSTT','ACTI'):
            out.append((n, m, t, o[3]-o[0], o[4]-o[1], o[5]-o[2]))
    dd = collections.Counter()
    for x in out: dd[os.path.dirname(x[1])] += x[0]
    for k, v in dd.most_common(80): print('%6d %s' % (v, k))

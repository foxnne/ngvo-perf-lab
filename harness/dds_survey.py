"""Survey .dds files under a folder by sub-folder and largest edge. usage: python dds_survey.py <folder> [name-filter]"""
import os, struct, sys, collections
root = sys.argv[1]; flt = sys.argv[2].lower() if len(sys.argv) > 2 else ''
tot = collections.Counter(); n = collections.Counter(); ex = {}
for dp, dn, fn in os.walk(root):
    for f in fn:
        if not f.lower().endswith('.dds') or flt not in f.lower(): continue
        p = os.path.join(dp, f)
        with open(p, 'rb') as fh: b = fh.read(148)
        h, w = struct.unpack_from('<II', b, 12); fmt = b[84:88]; dx = struct.unpack_from('<I', b, 128)[0] if fmt == b'DX10' else 0
        key = (os.path.relpath(dp, root).replace(os.sep, '/')[:60], max(w, h))
        tot[key] += os.path.getsize(p); n[key] += 1; ex[key] = (f, fmt.decode('latin1'), dx)
for k, v in sorted(tot.items(), key=lambda x: -x[1])[:20]:
    print('%-62s edge %5d  %4d files  %7.0f MB  e.g. %s %s %s' % (k[0], k[1], n[k], v / 1e6, ex[k][0][:44], ex[k][1], ex[k][2]))
print('total %.0f MB in %d files' % (sum(tot.values()) / 1e6, sum(n.values())))

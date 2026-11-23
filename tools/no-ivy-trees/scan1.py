"""Phase 1: find every winning nif whose bytes mention ivy / vine (texture paths and names are plain text). -> work/hits1.json"""
import json, os, re, sys, collections
import vfsidx
BS = chr(92)
v = vfsidx.get()
SKIP = ('meshes\\actors\\', 'meshes\\armor\\', 'meshes\\clothes\\', 'meshes\\weapons\\', 'meshes\\interface\\')
pat = re.compile(rb'ivy|vine', re.I)
allrel = set(v['loose']) | set(v['bsa'])
hits = {}
n = 0
for rel in sorted(allrel):
    if rel.startswith(SKIP) or 'facegeom' in rel or 'hair' in rel.split(BS)[1] or 'bodyslide' in rel:
        continue
    try:
        b = vfsidx.read(rel)
    except Exception as e:
        print('ERR', rel, e); continue
    n += 1
    m = set(x.lower() for x in pat.findall(b))
    if m:
        # collect the strings around
        ctx = set()
        for mm in pat.finditer(b):
            s = b[max(0, mm.start() - 60):mm.end() + 30]
            t = re.findall(rb'[\x20-\x7e]{4,}', s)
            for x in t:
                if pat.search(x): ctx.add(x.decode('latin1'))
        hits[rel] = {'win': vfsidx.winner(rel)[:2] + (vfsidx.winner(rel)[2],), 'ctx': sorted(ctx)[:12]}
print(n, 'read', len(hits), 'hits')
json.dump(hits, open(os.path.join(vfsidx.WORK, 'hits1.json'), 'w'), indent=1)
c = collections.Counter((h['win'][1], BS.join(r.split(BS)[:4])) for r, h in hits.items())
for k, n in sorted(c.items()): print(n, k)

import json, os, collections
import vfsidx, niflib
tg = json.load(open(os.path.join(vfsidx.WORK, 'targets.json')))
types = collections.Counter()
for rel, m in sorted(tg.items()):
    if m['kind'] != 'standing': continue
    b = vfsidx.read(rel); n = niflib.Nif(b)
    rt = n.tobytes() == b
    try:
        reach = n.reachable(); ok = len(reach) == len(n.blocks)
    except Exception as e:
        ok = 'ERR %s' % e
    types.update(n.btypes)
    print(os.path.basename(rel), len(b), 'roundtrip', rt, 'allreach', ok, 'roots', n.roots, 'nblocks', len(n.blocks))
print(types)

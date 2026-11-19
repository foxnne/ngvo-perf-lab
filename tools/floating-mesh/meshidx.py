import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan import read_profile, ROOT
mods, active, order, pl = read_profile()
idx = {}; bsas = []
srcs = [os.path.join(ROOT, 'overwrite')] + [os.path.join(ROOT, 'mods', m) for m in mods] + [os.path.join(ROOT, 'Stock Game', 'Data')]
for s in srcs:
    try: ents = os.listdir(s)
    except OSError: continue
    for e in ents:
        if e.lower().endswith('.bsa'): bsas.append(os.path.join(s, e))
        if e.lower() == 'meshes':
            base = os.path.join(s, e)
            for dp, dn, fn in os.walk(base):
                rel = os.path.relpath(dp, base).lower()
                for f in fn:
                    if f.lower().endswith(('.nif', '.bto')):
                        idx.setdefault(os.path.normpath(os.path.join(rel, f.lower())), os.path.join(dp, f))
pickle.dump(dict(idx=idx, bsas=bsas), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meshidx.pkl'), 'wb'))
print(len(idx), 'loose meshes', len(bsas), 'bsas')

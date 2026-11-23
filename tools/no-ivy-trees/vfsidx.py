"""Mesh VFS index for the profile (read-only). loose winner per path + BSA providers. Cached to work/vfs.pkl"""
import os, sys, pickle, time
sys.path.insert(0, r'C:\Users\foxnn\dev\biome-flora\tools')
import flib, tes5
BS = chr(92)
WORK = r'C:\Users\foxnn\dev\no-ivy-trees\work'

def build():
    lo = flib.load_order(); lol = [p.lower() for p in lo]
    stems = {os.path.splitext(p)[0]: i for i, p in enumerate(lol)}
    loose = {}   # rel -> (mod, fullpath) winner ; also all providers
    allp = {}
    bsas = []    # (order, label, path)
    dirs = [('<Stock Game>', flib.GAME)] + [(m, os.path.join(flib.MODS, m)) for m in reversed(flib.enabled_mods())] + [('<overwrite>', os.path.join(flib.ROOT, 'overwrite'))]
    for label, d in dirs:
        try: ents = list(os.scandir(d))
        except OSError: continue
        for e in ents:
            n = e.name.lower()
            if n.endswith('.bsa') and e.is_file():
                st = n[:-4]
                o = None
                if st in stems: o = stems[st]
                else:
                    for suf in (' - textures', ' - meshes'):
                        if st.endswith(suf) and st[:-len(suf)] in stems: o = stems[st[:-len(suf)]]
                    if o is None and label == '<Stock Game>': o = -1
                bsas.append((o, label, e.path))
            elif n == 'meshes' and e.is_dir():
                for dp, dn, fn in os.walk(e.path):
                    for f in fn:
                        if f.lower().endswith('.nif'):
                            full = os.path.join(dp, f)
                            rel = ('meshes' + BS + os.path.relpath(full, e.path)).lower()
                            loose[rel] = (label, full)
                            allp.setdefault(rel, []).append(label)
    bsaidx = {}
    for o, label, path in sorted([b for b in bsas if b[0] is not None], key=lambda x: x[0]):
        try: names = tes5.bsa_list(path)
        except Exception as ex:
            print('BSA skip', path, ex); continue
        for n in names:
            if n.endswith('.nif'):
                bsaidx[n] = (label, path); allp.setdefault(n, []).insert(0, 'BSA:' + label)
    inactive = [(l, p) for o, l, p in bsas if o is None]
    return {'loose': loose, 'bsa': bsaidx, 'all': allp, 'inactive_bsas': inactive}

_v = None
def get():
    global _v
    if _v is None:
        p = os.path.join(WORK, 'vfs.pkl')
        if os.path.exists(p): _v = pickle.load(open(p, 'rb'))
        else:
            t = time.time(); _v = build(); pickle.dump(_v, open(p, 'wb')); print('vfs built %.0fs' % (time.time() - t), file=sys.stderr)
    return _v

_b = {}
def winner(rel):
    v = get(); rel = rel.lower().replace('/', BS)
    if rel in v['loose']: return ('loose',) + v['loose'][rel]
    if rel in v['bsa']: return ('bsa',) + v['bsa'][rel]
    return None
def read(rel):
    w = winner(rel); rel = rel.lower().replace('/', BS)
    if not w: return None
    if w[0] == 'loose': return open(w[2], 'rb').read()
    if w[2] not in _b: _b[w[2]] = tes5.BSA(w[2])
    return _b[w[2]].read(rel)

if __name__ == '__main__':
    v = get(); print(len(v['loose']), 'loose nifs', len(v['bsa']), 'bsa nifs', 'inactive bsas:', len(v['inactive_bsas']))
    for l, p in v['inactive_bsas']: print('  inactive', l, os.path.basename(p))

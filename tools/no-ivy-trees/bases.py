"""Pass A: winning base records with a model, over the active load order. -> work/bases.pkl
{formkey(origin lower, objid): dict(type, edid, model(lower, 'meshes\\...'), plugin(winner), chain[plugins])}"""
import os, sys, pickle, struct
sys.path.insert(0, r'C:\Users\foxnn\dev\biome-flora\tools')
import flib
WORK = r'C:\Users\foxnn\dev\no-ivy-trees\work'
TYPES = {b'TREE', b'STAT', b'MSTT', b'ACTI', b'FLOR', b'FURN', b'CONT', b'SCOL'}


def run():
    lo = flib.load_order()
    out = {}
    for name in lo:
        try:
            pl = flib.plugin(name)
        except KeyError:
            print('missing plugin', name); continue
        for r in pl.top_records(TYPES):
            fk = pl.resolve(r.fid)
            edid = model = None
            for s, v in flib.subs(r.data):
                if s == b'EDID': edid = flib.zs(v)
                elif s == b'MODL' and model is None: model = flib.zs(v)
            m = None
            if model:
                m = model.lower().replace('/', chr(92)).lstrip(chr(92))
                if not m.startswith('meshes' + chr(92)): m = 'meshes' + chr(92) + m
            prev = out.get(fk)
            out[fk] = dict(type=r.sig.decode(), edid=edid, model=m, plugin=name, chain=(prev['chain'] if prev else []) + [name], flags=r.flags)
    pickle.dump({'lo': lo, 'bases': out}, open(os.path.join(WORK, 'bases.pkl'), 'wb'))
    print(len(lo), 'plugins', len(out), 'bases')


if __name__ == '__main__':
    run()

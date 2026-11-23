"""Pass B: placed references of the target bases (winning override per reference). -> work/refs.pkl
ref formkey -> dict(base fk, world fk or None, cell (interior cell fk) , pos, flags, plugin (winner), origin)"""
import json, os, pickle, struct, sys, zlib, time
sys.path.insert(0, r'C:\Users\foxnn\dev\biome-flora\tools')
import flib
W = r'C:\Users\foxnn\dev\no-ivy-trees\work'


def walk(pl, targets, out, stats):
    b = pl.b
    n = len(b)
    masters = [m.lower() for m in pl.masters]
    me = pl.name.lower()
    nm = len(masters)

    def fk(fid):
        mi = fid >> 24
        return (masters[mi] if mi < nm else me, fid & 0xFFFFFF)

    def group(p, e, world):
        while p < e:
            sig = b[p:p + 4]
            size, a, c = struct.unpack_from('<III', b, p + 4)
            if sig == b'GRUP':
                gtype = struct.unpack_from('<i', b, p + 12)[0]
                w = world
                if gtype == 1:
                    w = fk(a)
                group(p + 24, p + size, w)
                p += size
                continue
            if sig == b'REFR':
                flags, fid = a, c
                d = b[p + 24:p + 24 + size]
                if flags & 0x00040000:
                    d = zlib.decompress(d[4:])
                stats[0] += 1
                # NAME is early; scan subrecords
                q = 0
                base = None
                pos = None
                scale = 1.0
                L = len(d)
                while q + 6 <= L:
                    s = d[q:q + 4]
                    l = struct.unpack_from('<H', d, q + 4)[0]
                    if s == b'NAME':
                        base = fk(struct.unpack_from('<I', d, q + 6)[0])
                    elif s == b'DATA':
                        pos = struct.unpack_from('<6f', d, q + 6)
                    elif s == b'XSCL':
                        scale = struct.unpack_from('<f', d, q + 6)[0]
                    elif s == b'XXXX':
                        break
                    q += 6 + l
                rk = fk(fid)
                if base in targets or rk in out:
                    out[rk] = dict(base=base, world=world, pos=pos, scale=scale, flags=flags, plugin=pl.name, first=out.get(rk, {}).get('first', pl.name))
            p += 24 + size

    p = pl.start
    while p < n:
        gsize = struct.unpack_from('<I', b, p + 4)[0]
        label = b[p + 8:p + 12]
        if label in (b'CELL', b'WRLD'):
            group(p + 24, p + gsize, None)
        p += gsize


def run():
    t = time.time()
    tg = json.load(open(os.path.join(W, 'targets.json')))
    targets = set()
    for m in tg.values():
        for bb in m['bases']:
            o, i = bb['fk'].rsplit(':', 1)
            targets.add((o, int(i, 16)))
    extra = os.path.join(W, 'extra_targets.json')
    if os.path.exists(extra):
        for o, i in json.load(open(extra)): targets.add((o, i))
    out = {}
    stats = [0]
    for name in flib.load_order():
        try:
            pl = flib.Plugin(flib.plugin_paths()[name.lower()][0], name)
        except KeyError:
            continue
        walk(pl, targets, out, stats)
    pickle.dump(out, open(os.path.join(W, 'refs.pkl'), 'wb'))
    print(stats[0], 'REFR records walked;', len(out), 'refs to target bases; %.0fs' % (time.time() - t))


if __name__ == '__main__':
    run()

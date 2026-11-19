"""Scan active plugins of an MO2 profile: all REFRs in Tamriel + base record EDID/MODL.
Read-only on the modlist. Output: refs.pkl in this folder.
Formkey = (owning plugin name lower, local id & 0xFFFFFF)."""
import os, sys, struct, zlib, time, pickle, ctypes

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

ROOT = r'C:\Modlists\NGVO 8.0 Beta'
PROFILE = 'foxnne-nsfw'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'refs.pkl')
HDR = struct.Struct('<4sIIIIHH')
BASE_ESMS = ['Skyrim.esm', 'Update.esm', 'Dawnguard.esm', 'HearthFires.esm', 'Dragonborn.esm']
SKIP_TOP = {b'WRLD', b'CELL', b'DIAL', b'NAVI', b'QUST', b'NPC_', b'PACK', b'SCEN', b'INFO', b'LAND', b'IDLE',
            b'ARMA', b'OTFT', b'LVLI', b'LVLN', b'COBJ', b'KYWD', b'GLOB', b'GMST', b'FACT',
            b'HDPT', b'TXST', b'MGEF', b'ENCH', b'PERK', b'SNDR', b'SOUN', b'MUSC', b'MUST', b'FLST',
            b'RACE', b'CLAS', b'AVIF', b'SMQN', b'SMBN', b'SMEN', b'DLBR', b'DLVW', b'STRG', b'CAMS',
            b'IMGS', b'IMAD', b'WTHR', b'CLMT', b'REGN', b'LCTN', b'LCRT', b'MESG', 
            b'IPCT', b'IPDS', b'EFSH', b'ANIO', b'MATO', b'COLL', b'RFCT', b'WOOP', 
            b'ECZN', b'CSTY', b'LSCR', b'VTYP', b'EQUP', b'RELA',
            b'ASTP', b'OTFT', b'MATT', b'SNCT', b'SOPM', b'REVB', b'LGTM', b'CPTH', b'FSTP', b'FSTS', b'DOBJ',
            b'LTEX', b'GRAS', b'WATR', b'EYES', b'MOVT', b'DUAL', b'ASPC', b'NAVM',
            b'VOLI', b'LENS', b'SPGD', b'DEBR', b'BPTD', b'CLFM', b'PARW', b'ACHR', b'TES4', b'WRDS'}


def read_profile():
    pdir = os.path.join(ROOT, 'profiles', PROFILE)
    mods = [l.rstrip('\r\n')[1:] for l in open(os.path.join(pdir, 'modlist.txt'), encoding='utf-8', errors='replace') if l.startswith('+')]
    active = set()
    plist = []
    for l in open(os.path.join(pdir, 'plugins.txt'), encoding='utf-8', errors='replace'):
        l = l.strip()
        if l.startswith('*'):
            active.add(l[1:].lower()); plist.append(l[1:])
    order = [l.strip() for l in open(os.path.join(pdir, 'loadorder.txt'), encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
    return mods, active, order, plist


def plugin_index(mods):
    sources = [os.path.join(ROOT, 'overwrite')] + [os.path.join(ROOT, 'mods', m) for m in mods] + [os.path.join(ROOT, 'Stock Game', 'Data')]
    out = {}
    for path in sources:
        try:
            for e in os.scandir(path):
                ln = e.name.lower()
                if ln.endswith(('.esp', '.esm', '.esl')) and e.is_file():
                    out.setdefault(ln, e.path)
        except OSError:
            pass
    return out


def subrecords(body):
    pos, n = 0, len(body)
    big = None
    while pos + 6 <= n:
        sig = body[pos:pos + 4]
        sz = struct.unpack_from('<H', body, pos + 4)[0]
        if sig == b'XXXX':
            big = struct.unpack_from('<I', body, pos + 6)[0]
            pos += 6 + sz
            continue
        if big is not None:
            sz, big = big, None
        yield sig, body[pos + 6:pos + 6 + sz]
        pos += 6 + sz


def body_of(blob, pos, size, flags):
    b = blob[pos + 24:pos + 24 + size]
    if flags & 0x40000:
        b = zlib.decompress(b[4:])
    return b


def zs(b):
    return b.split(b'\0', 1)[0].decode('cp1252', 'replace')


class Plugin:
    def __init__(self, name, blob):
        self.name = name
        self.lname = name.lower()
        typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, 0)
        assert typ == b'TES4', name
        self.flags = flags
        self.masters = [zs(sd).lower() for st, sd in subrecords(blob[24:24 + size]) if st == b'MAST']
        self.body_start = 24 + size

    def fk(self, fid):
        mi = fid >> 24
        return (self.masters[mi] if mi < len(self.masters) else self.lname, fid & 0xFFFFFF)


TAMRIEL = ('skyrim.esm', 0x3C)


def main():
    t0 = time.time()
    mods, active, order, plist = read_profile()
    idx = plugin_index(mods)
    base_l = [b.lower() for b in BASE_ESMS]
    # CC plugins listed in Skyrim.ccc load always when present in Data
    ccc = os.path.join(ROOT, 'Stock Game', 'Skyrim.ccc')
    cc = [l.strip() for l in open(ccc)] if os.path.exists(ccc) else []
    ccl = {c.lower() for c in cc}
    lo = list(BASE_ESMS) + [p for p in order if (p.lower() in active or (p.lower() in ccl and p.lower() in idx)) and p.lower() not in base_l]
    cc_extra = [c for c in cc if c.lower() not in {p.lower() for p in lo} and c.lower() in idx]
    print('load order', len(lo), 'cc not active in plugins.txt but present:', len(cc_extra), cc_extra[:5])
    bases = {}     # fk -> (type, edid, modl, plugin idx)   last wins
    refs = {}      # fk -> list of dict (one per plugin that defines/overrides)
    cells = {}     # cell fk -> dict(grid, edid) last wins
    names, pflags, pmasters, missing = [], [], [], []
    for pname in lo:
        path = idx.get(pname.lower())
        if not path:
            missing.append(pname); continue
        blob = open(path, 'rb').read()
        try:
            pl = Plugin(pname, blob)
        except Exception as e:
            print('bad', pname, e); continue
        pi = len(names)
        names.append(pname); pflags.append(pl.flags); pmasters.append(pl.masters)
        pos, n = pl.body_start, len(blob)
        while pos + 24 <= n:
            typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
            if typ != b'GRUP':
                pos += 24 + size; continue
            label = blob[pos + 8:pos + 12]
            if label == b'WRLD':
                walk_wrld_top(pl, pi, blob, pos + 24, pos + size, refs, cells)
            elif label not in SKIP_TOP:
                walk_bases(pl, pi, blob, pos + 24, pos + size, bases)
            pos += max(size, 24)
    print('plugins', len(names), 'missing', missing, 'refs', len(refs), 'bases', len(bases), 'time %.1f' % (time.time() - t0))
    pickle.dump(dict(names=names, pflags=pflags, pmasters=pmasters, bases=bases, refs=refs, cells=cells, missing=missing), open(OUT, 'wb'), protocol=4)


def walk_bases(pl, pi, blob, pos, end, bases):
    while pos + 24 <= end:
        typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
        if typ == b'GRUP':
            walk_bases(pl, pi, blob, pos + 24, pos + size, bases)
            pos += max(size, 24); continue
        try:
            body = body_of(blob, pos, size, flags)
            edid = modl = ''
            obnd = None
            for st, sd in subrecords(body):
                if st == b'EDID':
                    edid = zs(sd)
                elif st == b'OBND' and len(sd) >= 12:
                    obnd = struct.unpack('<6h', sd[:12])
                elif st == b'MODL':
                    modl = zs(sd); break
                elif st in (b'DATA', b'DNAM', b'VMAD') and typ not in (b'STAT', b'MSTT', b'ACTI', b'TREE', b'FURN', b'CONT', b'DOOR', b'LIGH', b'FLOR', b'MISC', b'SCOL'):
                    pass
            bases[pl.fk(fid)] = (typ.decode(), edid, modl, pi, flags, obnd)
        except Exception as e:
            pass
        pos += 24 + size


def walk_wrld_top(pl, pi, blob, pos, end, refs, cells):
    while pos + 24 <= end:
        typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
        if typ == b'GRUP':
            label, gtype = struct.unpack_from('<II', blob, pos + 8)
            if gtype == 1 and pl.fk(label) == TAMRIEL:
                walk_world(pl, pi, blob, pos + 24, pos + size, refs, cells, None, 0)
            pos += max(size, 24); continue
        pos += 24 + size


def walk_world(pl, pi, blob, pos, end, refs, cells, cellkey, ctx):
    while pos + 24 <= end:
        typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
        if typ == b'GRUP':
            label, gtype = struct.unpack_from('<II', blob, pos + 8)
            if gtype in (4, 5):
                walk_world(pl, pi, blob, pos + 24, pos + size, refs, cells, None, 0)
            elif gtype == 6:
                walk_world(pl, pi, blob, pos + 24, pos + size, refs, cells, pl.fk(label), 0)
            elif gtype in (8, 9, 10):
                walk_world(pl, pi, blob, pos + 24, pos + size, refs, cells, cellkey, gtype)
            pos += max(size, 24); continue
        if typ == b'CELL':
            try:
                body = body_of(blob, pos, size, flags)
                d = cells.setdefault(pl.fk(fid), {})
                for st, sd in subrecords(body):
                    if st == b'XCLC' and len(sd) >= 8:
                        d['grid'] = struct.unpack_from('<ii', sd)
                    elif st == b'EDID':
                        d['edid'] = zs(sd)
                d['flags'] = flags
            except zlib.error:
                pass
        elif typ == b'REFR':
            try:
                body = body_of(blob, pos, size, flags)
                r = dict(pi=pi, flags=flags, cell=cellkey, ctx=ctx)
                for st, sd in subrecords(body):
                    if st == b'NAME':
                        r['base'] = pl.fk(struct.unpack('<I', sd[:4])[0])
                    elif st == b'DATA' and len(sd) >= 24:
                        r['data'] = struct.unpack('<6f', sd[:24])
                    elif st == b'XSCL':
                        r['scale'] = struct.unpack('<f', sd[:4])[0]
                    elif st == b'XESP':
                        p, fl = struct.unpack('<II', sd[:8])
                        r['xesp'] = (pl.fk(p), fl)
                    elif st == b'EDID':
                        r['edid'] = zs(sd)
                    elif st == b'XLRT':
                        r['xlrt'] = True
                refs.setdefault(pl.fk(fid), []).append(r)
            except Exception as e:
                print('REFR err', pl.name, hex(fid), e)
        pos += 24 + size


if __name__ == '__main__':
    main()

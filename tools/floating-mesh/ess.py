"""Skyrim SE .ess reader: change forms of placed references (REFR/ACHR/...) with position 'initial data'."""
import struct, zlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsa import lz4_block

def load(path):
    b = open(path, 'rb').read()
    assert b[:13] == b'TESV_SAVEGAME'
    hs = struct.unpack_from('<I', b, 13)[0]; p = 17
    ver, savenum = struct.unpack_from('<II', b, p); q = p + 8
    def ws(q):
        n = struct.unpack_from('<H', b, q)[0]; return b[q + 2:q + 2 + n].decode('cp1252', 'replace'), q + 2 + n
    name, q = ws(q); lvl = struct.unpack_from('<I', b, q)[0]; q += 4
    loc, q = ws(q); date, q = ws(q); race, q = ws(q)
    q += 2 + 4 + 4 + 8
    sw, sh = struct.unpack_from('<II', b, q); q += 8
    comp = struct.unpack_from('<H', b, q)[0]; q += 2
    assert q == 17 + hs, (q, hs)
    q += sw * sh * (4 if ver >= 12 else 3)
    info = dict(version=ver, name=name, location=loc, date=date, comp=comp)
    if comp:
        ulen, clen = struct.unpack_from('<II', b, q); q += 8
        if comp == 2:
            out = bytearray(); lz4_block(b[q:q + clen], out); body = bytes(out)
        else:
            body = zlib.decompress(b[q:q + clen])
        assert len(body) == ulen, (len(body), ulen)
        base = q - 8      # offsets in the file location table are relative to an uncompressed file
    else:
        body = b[q:]; base = q
    return info, body, base

def parse(path):
    info, d, base = load(path)
    p = 0
    formver = d[p]; p += 1
    pis = struct.unpack_from('<I', d, p)[0]; p += 4
    pe = p + pis
    n = d[p]; p += 1; plugins = []
    for _ in range(n):
        l = struct.unpack_from('<H', d, p)[0]; plugins.append(d[p + 2:p + 2 + l].decode('cp1252', 'replace')); p += 2 + l
    light = []
    if p < pe:
        n = struct.unpack_from('<H', d, p)[0]; p += 2
        for _ in range(n):
            l = struct.unpack_from('<H', d, p)[0]; light.append(d[p + 2:p + 2 + l].decode('cp1252', 'replace')); p += 2 + l
    p = pe
    flt = struct.unpack_from('<10I', d, p)
    fidoff, unk3off, g1off, g2off, cfoff, g3off, g1c, g2c, g3c, cfcount = flt
    info.update(formver=formver, plugins=plugins, light=light, flt=flt, base=base)
    def off(o): return o - base
    q = off(fidoff)
    nf = struct.unpack_from('<I', d, q)[0]
    formids = struct.unpack_from('<%dI' % nf, d, q + 4)
    forms = []
    p = off(cfoff)
    for i in range(cfcount):
        r = d[p:p + 3]; refid = (r[0] << 16) | (r[1] << 8) | r[2]; p += 3
        cflags, typ, ver = struct.unpack_from('<IBB', d, p); p += 6
        ls = typ >> 6; t = typ & 0x3F
        if ls == 0: l1, l2 = d[p], d[p + 1]; p += 2
        elif ls == 1: l1, l2 = struct.unpack_from('<HH', d, p); p += 4
        else: l1, l2 = struct.unpack_from('<II', d, p); p += 8
        data = d[p:p + l1]; p += l1
        forms.append((refid, cflags, t, ver, l2, data))
    return info, formids, forms

def resolve(refid, formids):
    k = refid >> 22; v = refid & 0x3FFFFF
    if k == 0: return formids[v - 1] if 0 < v <= len(formids) else 0
    if k == 1: return v
    if k == 2: return 0xFF000000 | v
    return None

if __name__ == '__main__':
    info, formids, forms = parse(sys.argv[1])
    print({k: v for k, v in info.items() if k not in ('plugins', 'light')}, len(info['plugins']), len(info['light']), len(formids), len(forms))
    import collections
    print(collections.Counter(f[2] for f in forms).most_common(12))

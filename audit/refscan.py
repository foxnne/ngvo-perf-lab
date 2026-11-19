# Light-weight exterior reference census for Tamriel cells in a bounding box.
# Walks GRUP headers only, seeks past everything outside the box. Counts NEW refs per plugin by base record type.
# Read-only. Output: refscan.json  (cell -> plugin -> basetype -> count), plus light details.
import struct, os, sys, zlib, json, collections

INST = r"C:/Modlists/NGVO 8.0 Beta"
PROFILE = INST + "/profiles/foxnne-nsfw"
DATA = INST + "/Stock Game/Data"
X0, X1, Y0, Y1 = -2, 12, -9, 4
BASETYPES = {b'LIGH', b'TREE', b'STAT', b'MSTT', b'FLOR', b'ACTI', b'FURN', b'CONT', b'DOOR', b'MISC', b'GRAS',
             b'SOUN', b'TXST', b'NPC_', b'LVLN', b'IDLM', b'HAZD', b'ADDN', b'ALCH', b'INGR', b'WEAP', b'ARMO', b'BOOK', b'ARTO', b'SCRL', b'AMMO', b'KEYM', b'SLGM', b'TACT', b'PROJ', b'LVLI', b'APPA', b'ASPC', b'ENCH', b'SPEL'}

def plugin_paths():
    enabled = []
    for l in open(PROFILE + "/modlist.txt", encoding='utf-8', errors='replace'):
        l = l.rstrip('\r\n')
        if l.startswith('+'): enabled.append(l[1:])
    paths = {}
    # lowest priority first so higher priority overwrites
    for f in os.listdir(DATA):
        if f.lower().endswith(('.esp', '.esm', '.esl')): paths[f.lower()] = DATA + '/' + f
    for m in reversed(enabled):
        d = INST + "/mods/" + m
        try: fs = os.listdir(d)
        except OSError: continue
        for f in fs:
            if f.lower().endswith(('.esp', '.esm', '.esl')): paths[f.lower()] = d + '/' + f
    ov = INST + "/overwrite"
    for f in os.listdir(ov):
        if f.lower().endswith(('.esp', '.esm', '.esl')): paths[f.lower()] = ov + '/' + f
    return paths

def active_plugins():
    out = ['Skyrim.esm', 'Update.esm', 'Dawnguard.esm', 'HearthFires.esm', 'Dragonborn.esm']
    for l in open(PROFILE + "/plugins.txt", encoding='utf-8', errors='replace'):
        l = l.strip()
        if l.startswith('*'):
            n = l[1:]
            if n not in out: out.append(n)
    return out

def subrecords(body):
    p = 0; n = len(body); big = None
    while p + 6 <= n:
        t = body[p:p + 4]; s, = struct.unpack_from('<H', body, p + 4); p += 6
        if t == b'XXXX':
            big, = struct.unpack_from('<I', body, p); p += s; continue
        if big is not None: s = big; big = None
        yield t, body[p:p + s]; p += s

def body_of(f, size, flags):
    b = f.read(size)
    if flags & 0x00040000:
        try: b = zlib.decompress(b[4:])
        except Exception: b = b''
    return b

class Plugin:
    def __init__(self, path):
        self.path = path; self.f = open(path, 'rb'); self.size = os.path.getsize(path)
        h = self.f.read(24)
        t, size, flags = struct.unpack_from('<4sII', h)
        self.masters = []
        if t == b'TES4':
            for st, sb in subrecords(self.f.read(size)):
                if st == b'MAST': self.masters.append(sb.rstrip(b'\0').decode('latin1').lower())
        self.top = {}
        p = self.f.tell()
        while p + 24 <= self.size:
            self.f.seek(p); h = self.f.read(24)
            t, size, label, gt = struct.unpack_from('<4sI4sI', h)
            if t != b'GRUP' or size < 24: break
            if gt == 0: self.top[label] = (p, size)
            p += size
        self.types = None
    def resolve(self, fid, name):
        i = fid >> 24
        m = self.masters[i] if i < len(self.masters) else name
        return m, fid & 0xFFFFFF
    def typemap(self):
        if self.types is not None: return self.types
        self.types = {}; self.lights = {}
        for label, (p, size) in self.top.items():
            if label not in BASETYPES: continue
            end = p + size; q = p + 24
            while q + 24 <= end:
                self.f.seek(q); h = self.f.read(24)
                t, s, flags, fid = struct.unpack_from('<4sIII', h)
                if t == b'GRUP': q += s; continue
                self.types[fid & 0xFFFFFF if (fid >> 24) >= len(self.masters) else -1 - fid] = t  # own records keyed by local id
                if t == b'LIGH' and (fid >> 24) >= len(self.masters):
                    for st, sb in subrecords(body_of(self.f, s, flags)):
                        if st == b'DATA' and len(sb) >= 12:
                            self.lights[fid & 0xFFFFFF] = (struct.unpack_from('<I', sb, 4)[0], struct.unpack_from('<I', sb, 12)[0] if len(sb) >= 16 else 0)
                q += 24 + s
        return self.types

def main():
    paths = plugin_paths(); plugs = {}
    def get(name):
        k = name.lower()
        if k not in plugs:
            plugs[k] = Plugin(paths[k]) if k in paths else None
        return plugs[k]
    cells = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    summary = {}
    names = active_plugins()
    scanned = 0
    for name in names:
        pl = get(name)
        if pl is None or b'WRLD' not in pl.top: continue
        f = pl.f; nm = name.lower()
        p, size = pl.top[b'WRLD']; end = p + size; q = p + 24
        cnt = collections.Counter()
        while q + 24 <= end:
            f.seek(q); h = f.read(24)
            t, s, a, b = struct.unpack_from('<4sIII', h)
            if t != b'GRUP': q += 24 + s; continue
            # world children group: label = WRLD formid
            if b == 1:
                m, lid = pl.resolve(a, nm)
                if not (m == 'skyrim.esm' and lid == 0x3C): q += s; continue
                scanned += 1
                walk_world(pl, nm, q + 24, q + s, cells, cnt, get)
            q += s
        if cnt: summary[name] = dict(cnt)
    out = {'cells': {"%d,%d" % k: {pn: dict(c) for pn, c in v.items()} for k, v in cells.items()}, 'summary': summary}
    json.dump(out, open(os.path.dirname(os.path.abspath(__file__)) + '/refscan.json', 'w'))
    print('plugins with Tamriel WRLD data:', scanned, 'of', len(names))

def base_type(pl, nm, base, get):
    m, lid = pl.resolve(base, nm)
    mp = get(m) if m != nm else pl
    if mp is None: return 'unk', None
    t = mp.typemap().get(lid)
    if t is None: return 'unk', None
    t = t.decode()
    if t == 'LIGH':
        fl = mp.lights.get(lid, (0, 0))
        return ('LIGH_shadow' if fl[0] & 0x1C00 else 'LIGH'), None
    return t, None

def do_refs(pl, nm, start, end, cellxy, persistent, cells, cnt, get):
    f = pl.f; q = start
    while q + 24 <= end:
        f.seek(q); h = f.read(24)
        t, s, flags, fid = struct.unpack_from('<4sIII', h)
        if t == b'GRUP':
            do_refs(pl, nm, q + 24, q + s, cellxy, persistent, cells, cnt, get); q += s; continue
        if t in (b'REFR', b'ACHR'):
            new = (fid >> 24) >= len(pl.masters)
            if not new:
                if flags & 0x800: cnt['override_initially_disabled'] += 1
                if flags & 0x20: cnt['override_deleted'] += 1
                if not persistent or True:
                    q += 24 + s; continue
            body = body_of(f, s, flags); base = None; pos = None
            for st, sb in subrecords(body):
                if st == b'NAME': base = struct.unpack('<I', sb[:4])[0]
                elif st == b'DATA' and len(sb) >= 12: pos = struct.unpack_from('<3f', sb)
            xy = cellxy
            if persistent and pos:
                xy = (int(pos[0] // 4096), int(pos[1] // 4096))
            if xy and X0 <= xy[0] <= X1 and Y0 <= xy[1] <= Y1 and base is not None:
                bt = 'ACHR' if t == b'ACHR' else base_type(pl, nm, base, get)[0]
                if flags & 0x800: bt += '_disabled'
                cells[xy][nm][bt] += 1; cnt[bt] += 1
        q += 24 + s

def walk_world(pl, nm, start, end, cells, cnt, get):
    f = pl.f; q = start; cur = None; persistent_next = True
    while q + 24 <= end:
        f.seek(q); h = f.read(24)
        t, s, a, b = struct.unpack_from('<4sIII', h)
        if t == b'GRUP':
            if b in (4, 5):
                gy, gx = struct.unpack('<hh', struct.pack('<I', a))
                k = 32 if b == 4 else 8
                x0, y0 = gx * k, gy * k
                if x0 > X1 or x0 + k - 1 < X0 or y0 > Y1 or y0 + k - 1 < Y0: q += s; continue
                walk_world(pl, nm, q + 24, q + s, cells, cnt, get)
            elif b == 6:
                if cur == 'persist':
                    do_refs(pl, nm, q + 24, q + s, None, True, cells, cnt, get)
                elif cur is not None and X0 <= cur[0] <= X1 and Y0 <= cur[1] <= Y1:
                    do_refs(pl, nm, q + 24, q + s, cur, False, cells, cnt, get)
            q += s; continue
        if t == b'CELL':
            flags = a
            body = body_of(f, s, flags); cur = 'persist'
            for st, sb in subrecords(body):
                if st == b'XCLC' and len(sb) >= 8: cur = struct.unpack_from('<ii', sb)
        q += 24 + s

if __name__ == '__main__':
    main()

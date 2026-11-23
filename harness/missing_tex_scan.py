"""List textures referenced by the meshes of the given mods that no enabled mod provides (loose files or BSAs of enabled
mods; vanilla BSAs in Stock Game Data too). Purple surfaces in game = a missing diffuse.
usage: python missing_tex_scan.py "Mod A" "Mod B" ..."""
import os, re, struct, sys
R = 'C:/Modlists/NGVO 8.0 Beta'
mods = [l.rstrip('\r\n')[1:] for l in open(R + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l[:1] == '+']
mods = [m for m in mods if not m.endswith('_separator')]
def bsa_names(path):
    try:
        f = open(path, 'rb'); h = f.read(36)
        if h[:4] != b'BSA\0': return []
        ver, off, aflags, nfold, nfile, lfold, lfile, fflags = struct.unpack('<8I', h[4:36])
        if ver not in (104, 105): return []
        folders = [struct.unpack('<QIIQ' if ver == 105 else '<QII', f.read(24 if ver == 105 else 16)) for _ in range(nfold)]
        recs = []
        for fo in folders:
            n = f.read(1)[0]; name = f.read(n)[:-1].decode('cp1252').replace(chr(92), '/').lower()
            for _ in range(fo[1]): f.read(16); recs.append(name)
        names = f.read(lfile).split(b'\0')
        return [d + '/' + n.decode('cp1252').lower() for d, n in zip(recs, names)]
    except Exception: return []
have = set()
for root in [R + '/overwrite'] + [R + '/mods/' + m for m in mods] + [R + '/Stock Game/Data']:
    if not os.path.isdir(root): continue
    for fn in os.listdir(root):
        p = root + '/' + fn
        if fn.lower().endswith('.bsa'): have.update(bsa_names(p))
        elif fn.lower() == 'textures' and os.path.isdir(p):
            for r, _, fs in os.walk(p):
                for x in fs: have.add(('textures/' + os.path.join(r, x).replace(chr(92), '/')[len(p) + 1:]).lower())
print('known textures', len(have), flush=True)
pat = re.compile(rb'(?i)[a-z0-9_ \-\\/\.\(\)\']+\.dds')
total = 0
for m in sys.argv[1:]:
    miss = {}
    for r, _, fs in os.walk(R + '/mods/' + m):
        for x in fs:
            if not x.lower().endswith('.nif'): continue
            data = open(os.path.join(r, x), 'rb').read()
            for t in set(pat.findall(data)):
                t = t.decode('latin1').replace(chr(92), '/').lower().strip().lstrip('/')
                if not t.startswith('textures/'): t = 'textures/' + t
                if t not in have: miss.setdefault(t, set()).add(os.path.relpath(os.path.join(r, x), R + '/mods/' + m))
    if miss:
        total += len(miss); print('== %s: %d missing textures' % (m, len(miss)))
        for t, ns in sorted(miss.items())[:40]: print('   %s   <- %s%s' % (t, sorted(ns)[0], ' (+%d)' % (len(ns) - 1) if len(ns) > 1 else ''))
print('total missing', total)

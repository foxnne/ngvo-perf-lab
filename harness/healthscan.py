"""Read-only health scans of the MO2 profile (enabled mods only). usage: python healthscan.py plugins|dlls|papyrus|dds
plugins: light plugins with HEDR < 1.71 that own FormIDs below 0x800 (crash source on 1.6.1130+)
dlls:    SKSE plugin DLLs that are not 64-bit
papyrus: Papyrus.0.log error / warning / stack dump summary
dds:     block-compressed textures whose width or height is not a multiple of 4 (runs at background I/O priority)
Writes audit/health_<name>.md and prints a summary.
"""
import collections, ctypes, os, re, struct, sys
ROOT = 'C:/Modlists/NGVO 8.0 Beta'; PROF = ROOT + '/profiles/foxnne-nsfw'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audit')
what = sys.argv[1]


def enabled_mods():      # highest priority first
    mods = [l[1:].strip() for l in open(PROF + '/modlist.txt', encoding='utf-8-sig') if l.startswith('+')]
    return [ROOT + '/overwrite'] + [f'{ROOT}/mods/{m}' for m in mods] + [ROOT + '/Stock Game/Data']


def write(name, text):
    with open(os.path.join(OUT, f'health_{name}.md'), 'w', encoding='utf-8') as f: f.write(text)


if what == 'plugins':
    active = [l[1:].strip() for l in open(PROF + '/plugins.txt', encoding='utf-8-sig') if l.startswith('*')]
    index = {}
    for d in enabled_mods():
        try: names = os.listdir(d)
        except OSError: continue
        for n in names:
            if n.lower().endswith(('.esp', '.esm', '.esl')): index.setdefault(n.lower(), os.path.join(d, n))
    bad = []; old_light = 0; light = 0; missing = []
    for p in active:
        path = index.get(p.lower())
        if not path: missing.append(p); continue
        with open(path, 'rb') as f: d = f.read()
        if d[:4] != b'TES4': continue
        size, flags = struct.unpack_from('<II', d, 4)
        hedr = d.find(b'HEDR', 24, 24 + size)
        version = struct.unpack_from('<f', d, hedr + 6)[0] if hedr >= 0 else 0
        masters = d[24:24 + size].count(b'MAST')
        is_light = bool(flags & 0x200) or p.lower().endswith('.esl')
        if not is_light: continue
        light += 1
        if version >= 1.705: continue
        old_light += 1
        pos = 24 + size; low = 0; total = 0; example = None
        while pos + 24 <= len(d):
            typ = d[pos:pos + 4]
            if typ == b'GRUP': pos += 24; continue
            dsize, _, formid = struct.unpack_from('<III', d, pos + 4)
            if (formid >> 24) >= masters:
                total += 1
                if (formid & 0xFFF) < 0x800 or (formid & 0xFFFFFF) > 0xFFF:
                    if (formid & 0xFFFFFF) < 0x800: low += 1; example = example or f'{typ.decode(errors="replace")} {formid:08X}'
            pos += 24 + dsize
        if low: bad.append((p, version, low, total, example, path))
    txt = f'# Light plugins with old headers\n\nActive plugins {len(active)}, light {light}, light with HEDR < 1.71: {old_light}, of those owning FormIDs below 0x800: {len(bad)}. Not found on disk: {len(missing)} {missing[:10]}\n\n'
    for b in bad: txt += f'- {b[0]} (HEDR {b[1]:.2f}): {b[2]} of {b[3]} own records below 0x800, e.g. {b[4]} - {b[5]}\n'
    write('plugins', txt); print(txt)

elif what == 'dlls':
    seen = {}; bad = []
    for d in enabled_mods():
        p = os.path.join(d, 'SKSE', 'Plugins')
        try: names = os.listdir(p)
        except OSError: continue
        for n in names:
            if not n.lower().endswith('.dll') or n.lower() in seen: continue
            seen[n.lower()] = 1
            with open(os.path.join(p, n), 'rb') as f: h = f.read(4096)
            try:
                pe = struct.unpack_from('<I', h, 0x3C)[0]; machine = struct.unpack_from('<H', h, pe + 4)[0]
            except struct.error: machine = -1
            if machine != 0x8664: bad.append(f'- {n}: machine 0x{machine:X} - {p}')
    txt = f'# SKSE plugin DLL architecture\n\n{len(seen)} winning DLLs in SKSE/Plugins, not x64: {len(bad)}\n' + '\n'.join(bad) + '\n'
    write('dlls', txt); print(txt)

elif what == 'papyrus':
    p = 'C:/Users/foxnn/Documents/My Games/Skyrim Special Edition/Logs/Script/Papyrus.0.log'
    if not os.path.exists(p): sys.exit('no Papyrus.0.log (logging off?)')
    err = collections.Counter(); warn = collections.Counter(); dumps = 0; lines = 0; first = last = ''
    for l in open(p, encoding='utf-8', errors='ignore'):
        lines += 1
        m = re.match(r'\[(.*?)\]', l)
        if m: last = m[1]; first = first or m[1]
        if 'Dumping stack' in l: dumps += 1
        low = l.lower()
        if ' error: ' in low or low.startswith('error:'):
            s = re.sub(r'\(?[0-9A-Fa-f]{8}\)?', '#', l.split('rror: ', 1)[-1])[:110].strip(); err[s] += 1
        elif 'warning: ' in low:
            s = re.sub(r'\(?[0-9A-Fa-f]{8}\)?', '#', l.split('arning: ', 1)[-1])[:110].strip(); warn[s] += 1
    txt = f'# Papyrus.0.log\n\n{lines} lines, {first} to {last}, modified {__import__("time").ctime(os.path.getmtime(p))}. Errors {sum(err.values())}, warnings {sum(warn.values())}, stack dumps {dumps}.\n\n## Top errors\n'
    txt += ''.join(f'- {c}x {s}\n' for s, c in err.most_common(15)) + '\n## Top warnings\n' + ''.join(f'- {c}x {s}\n' for s, c in warn.most_common(10))
    write('papyrus', txt); print(txt)

elif what == 'dds':
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00100000)   # background mode: lowest CPU and I/O priority
    BC = {b'DXT1', b'DXT2', b'DXT3', b'DXT4', b'DXT5', b'ATI1', b'ATI2', b'BC4U', b'BC5U', b'BC4S', b'BC5S'}
    BC10 = set(range(70, 85)) | set(range(94, 100))
    n = 0; bad = []; unreadable = 0
    for d in enabled_mods():
        for dp, dn, fn in os.walk(d):
            for f in fn:
                if not f.lower().endswith('.dds'): continue
                n += 1
                try:
                    with open(os.path.join(dp, f), 'rb') as fh: h = fh.read(148)
                    if h[:4] != b'DDS ' or len(h) < 128: unreadable += 1; continue
                    height, width = struct.unpack_from('<II', h, 12); cc = h[84:88]
                    comp = cc in BC or (cc == b'DX10' and len(h) >= 132 and struct.unpack_from('<I', h, 128)[0] in BC10)
                    if comp and (width % 4 or height % 4) and (width > 4 or height > 4): bad.append(f'- {width}x{height} {cc.decode(errors="replace")} {os.path.join(dp, f)[len(ROOT) + 1:]}')
                except OSError: unreadable += 1
    txt = f'# Compressed textures with sizes not divisible by 4\n\nLoose .dds scanned in enabled mods: {n} (BSA contents not scanned; overridden copies included). Unreadable or not DDS: {unreadable}. Flagged: {len(bad)}\n\n' + '\n'.join(sorted(bad)) + '\n'
    write('dds', txt); print(txt[:3000])

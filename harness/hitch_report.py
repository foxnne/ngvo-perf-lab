"""Name the call chains in HitchSampler reports: '+X' = Community Shaders DLL offset (resolved with the build's PDB,
cs_symbols.py), 'exe < X' = SkyrimSE.exe RVA (Address Library 1.6.1170 + community names).
usage: python hitch_report.py [min_ms=300]     reads SKSE/BottledShaders.log (the current game session's)"""
import bisect, importlib.util, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs_symbols
spec = importlib.util.spec_from_file_location('al', os.path.join(HERE, 'addrlib.py')); al = importlib.util.module_from_spec(spec); spec.loader.exec_module(al)
DB = al.load(r'C:\Modlists\NGVO 8.0 Beta\mods\Address Library for SKSE Plugins\SKSE\Plugins\versionlib-1-6-1170-0.bin')  # NOT -0-1.bin
OFFS = [o for o, _ in DB]
NAMES = {}
for line in open(r'C:\Users\foxnn\dev\re-refs\AddressLibraryDatabase\skyrimae.rename', encoding='utf-8', errors='replace'):
    p = line.split(None, 1)
    if len(p) == 2 and p[0].isdigit(): NAMES[int(p[0])] = p[1].strip().replace('_*', '')


def exe(h):
    v = int(h, 16); k = bisect.bisect_right(OFFS, v) - 1; i = DB[k][1]
    return '%d%s' % (i, ':' + NAMES[i] if i in NAMES else '')


def cs(h):
    n = cs_symbols.name(int(h, 16))
    return 'CS:' + re.sub(r'\+0x[0-9A-F]+$', '', n)


MIN = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1][0].isdigit() else 300
LOG = os.path.expanduser(r'~\Documents\My Games\Skyrim Special Edition\SKSE\BottledShaders.log')
for l in open(LOG, encoding='utf-8', errors='replace'):
    m = re.search(r'\[HitchSampler\] frame (\d+) took (\d+) ms, (\d+) samples[^:]*: (.*)', l)
    if not m or float(m.group(2)) < MIN: continue
    print('\n### %s frame %s, %s ms, %s samples' % (l[1:24], m.group(1), m.group(2), m.group(3)))
    for part in m.group(4).split(' | '):
        part = part.strip()
        if part.startswith('exe <'):
            print('        game: ' + ' < '.join(exe(x) for x in re.findall(r'[0-9A-F]{4,}', part)))
            continue
        g = re.match(r'(\d+)% (in|at) (\S+)(.*)', part)
        if not g: continue
        pct, kind, where, rest = g.groups()
        top = cs(where[1:]) if where.startswith('+') else where
        chain = ' < '.join(cs(x) for x in re.findall(r'\+([0-9A-F]+)', rest))
        print('  %3s%% %s%s' % (pct, top, ' < ' + chain if chain else ''))


def dump_summary(path, top=25):
    """Every sample of one long frame (SKSE/HitchSamples/*.txt): inclusive share per function, game and CS."""
    rows = [[x.strip() for x in l.split('|')] for l in open(path, encoding='utf-8', errors='replace') if l.strip()]
    n = len(rows); incl = {}; self_ = {}
    for r in rows:
        where, csc, exc = (r + ['', '', ''])[:3]
        seen = set()
        if where.startswith('cs:'): s = cs(where[3:])
        elif where.startswith('exe:'): s = 'game ' + exe(where[4:])
        else: s = where.split('+')[0]
        self_[s] = self_.get(s, 0) + 1
        for x in csc.split(): seen.add(cs(x))
        for x in exc.split(): seen.add('game ' + exe(x))
        for f in seen: incl[f] = incl.get(f, 0) + 1
    print('\n### %s: %d samples' % (os.path.basename(path), n))
    print('  where the main thread was (self):')
    for f, c in sorted(self_.items(), key=lambda kv: -kv[1])[:10]: print('   %4.1f%% %s' % (100 * c / n, f))
    print('  inside (inclusive, any depth of the sampled chain):')
    for f, c in sorted(incl.items(), key=lambda kv: -kv[1])[:top]: print('   %4.1f%% %s' % (100 * c / n, f))


if '--dump' in sys.argv:
    d = os.path.join(os.path.dirname(LOG), 'HitchSamples')
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        dump_summary(os.path.join(d, f))

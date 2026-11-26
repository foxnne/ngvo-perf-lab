"""Fast-travel move frames by subsystem: every sample of a HitchSampler dump (SKSE/HitchSamples/*.txt) put in one bucket
(IO-task wait, 3D teardown, Havok, CS grass, render, cell records, actor predestroy, ...), as ms of the frame.
Exe ids: Address Library 1.6.1170 (+ community names); CS offsets are named only for dumps newer than the deployed PR-Tracy
build (cs_symbols.py needs that build's PDB). See harness/RESEARCH-apex-stall-2026-11-25.md.
usage: python apex_buckets.py [dump file names ...]     (no names: the 12 newest dumps; --since HHMM: dumps named after it)"""
import bisect, importlib.util, os, re, sys, collections, time
H = r'C:\Users\foxnn\dev\ngvo-perf-lab\harness'; sys.path.insert(0, H)
spec = importlib.util.spec_from_file_location('al', os.path.join(H, 'addrlib.py')); al = importlib.util.module_from_spec(spec); spec.loader.exec_module(al)
DB = al.load(r'C:\Modlists\NGVO 8.0 Beta\mods\Address Library for SKSE Plugins\SKSE\Plugins\versionlib-1-6-1170-0.bin')
OFFS = [o for o, _ in DB]
def fid(v): return DB[bisect.bisect_right(OFFS, v) - 1][1]
import cs_symbols
D = r'C:\Users\foxnn\Documents\My Games\Skyrim Special Edition\SKSE\HitchSamples'
IO = {75676, 75695, 75696, 75633, 75706, 75712, 75643}
ACT = {37176, 41336, 41331, 37175, 40288, 37399}
REC = {20456, 20460, 13362, 13980, 13977, 13972, 69417, 69418, 14034, 14033, 69029, 69020, 13984, 13990, 20532, 20559, 14018}
REL = {69192, 69164, 70294, 76328, 106559, 77297, 36098, 68242, 68243, 70321}
HK = lambda i: 60000 <= i < 65000 or 77790 <= i <= 78700 or i in (57364, 57049, 57050, 57011, 67111, 67114, 64980, 62359, 104804)
RND = lambda i: 105600 <= i <= 108400 or i in (77263, 77386)
GRASS = {15375, 15374, 15373, 15383, 13278, 13623}
def bucket(where, csc, exc, new):
    ch = [fid(int(x, 16)) for x in exc.split()]
    s = set(ch)
    if where.startswith('cs:'):
        if new:
            n = cs_symbols.name(int(where[3:], 16)); return 'CS ' + n.split('::')[0].split('<')[0]
        return 'CS (old build)'
    if s & IO: return 'IO task wait (take+run, lock-free queue walk)'
    if s & ACT: return 'Actor::Predestroy (start area actors)'
    if s & REC: return 'CELL record reads (TESFile)'
    if s & GRASS: return 'grass (engine)'
    if s & REL: return '3D teardown (NiNode/string release, EF free)'
    if any(HK(i) for i in ch) or (where.startswith('exe:') and HK(fid(int(where[4:], 16)))): return 'Havok (add/remove/shift)'
    if any(RND(i) for i in ch): return 'render (BSBatchRenderer)'
    if 82075 in s or 36555 in s or 36559 in s: return 'main loop / present / FG wait'
    return 'other: ' + (where.split('+')[0] if not where.startswith('exe:') else 'exe %d' % fid(int(where[4:], 16)))
NEWBUILD = os.path.getmtime(r'C:\Users\foxnn\dev\skyrim-community-shaders\build\PR-Tracy\Release\CommunityShaders.dll')
files = [a for a in sys.argv[1:] if not a.startswith('--') and not a.isdigit()]
if '--since' in sys.argv:
    since = sys.argv[sys.argv.index('--since') + 1]
    files = sorted((f for f in os.listdir(D) if re.search(r'_(\d{6})\.\d{3}\.txt$', f) and re.search(r'_(\d{6})\.', f).group(1)[:4] >= since),
                   key=lambda f: re.search(r'_(\d{6}\.\d{3})\.txt$', f).group(1))
if not files:
    files = sorted(os.listdir(D), key=lambda f: os.path.getmtime(os.path.join(D, f)))[-12:]
for f in files:
    p = os.path.join(D, f); new = os.path.getmtime(p) > NEWBUILD
    rows = [[x.strip() for x in l.split('|')] for l in open(p, encoding='utf-8', errors='replace') if l.strip()]
    c = collections.Counter(bucket(*(r + ['', '', ''])[:3], new) for r in rows)
    ms = int(re.search(r'_(\d+)ms', f).group(1)); n = len(rows)
    print('\n## %s  %s  %d samples (1 sample ~ %.2f ms; first 38 ms not sampled)' % (f, time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(p))), n, (ms - 38) / max(n, 1)))
    for k, v in c.most_common(14):
        print('  %5.1f%% %5.0f ms  %s' % (100 * v / n, v * (ms - 38) / n, k))

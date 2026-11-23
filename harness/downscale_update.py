"""Bring `foxnne - 2K Downscale (winning 4K textures)` up to date with the current modlist (MO2 closed for the final move).
Winners are found ignoring the 2K mod itself. For each winning loose DDS > 2048 (outside the exclusions) a 2K copy is made;
a copy is rebuilt when its source changed since it was made (source recorded in _sources.json; the first run treats the
2026-11-16 scan, tex_scan.json, as the record). Copies whose path now wins at <= 2048, or is excluded, are deleted.
usage: python downscale_update.py [--dry] [--workers N]"""
import json, os, struct, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
R = 'C:/Modlists/NGVO 8.0 Beta'
NAME = 'foxnne - 2K Downscale (winning 4K textures)'
OUT = R + '/mods/' + NAME
TEXCONV = R + '/tools/DynDOLOD/Edit Scripts/Texconvx64.exe'
OLD_SCAN = 'C:/Users/foxnn/AppData/Local/Temp/claude/3faf89cbf3e7ed47/f00ecae3-865a-43f6-bdb9-8828c99c0a95/scratchpad/tex_scan.json'
SRC = OUT + '/_sources.json'
DRY = '--dry' in sys.argv
WORKERS = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
EXCL = ('textures/dyndolod/', 'textures/ashandfrost/paperloadscreens', 'textures/water/flowmaps', 'textures/interface/',
        'textures/lod/', 'textures/terrain/', 'textures/landscape/mountains/')   # mountains stay 4K (user)
DX10 = {98: 'BC7_UNORM', 99: 'BC7_UNORM_SRGB', 72: 'BC1_UNORM_SRGB', 71: 'BC1_UNORM', 80: 'BC4_UNORM', 77: 'BC3_UNORM',
        78: 'BC3_UNORM_SRGB', 83: 'BC5_UNORM', 84: 'BC5_SNORM', 95: 'BC6H_UF16', 74: 'BC2_UNORM'}
FOURCC = {'DXT5': 'BC3_UNORM', 'DXT1': 'BC1_UNORM', 'DXT3': 'BC2_UNORM', 'BC4U': 'BC4_UNORM', 'ATI2': 'BC5_UNORM', 'BC5U': 'BC5_UNORM'}

mods = [l.rstrip('\r\n')[1:] for l in open(R + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l[:1] == '+']
mods = [m for m in mods if not m.endswith('_separator') and m != NAME]
win = {}
for name, root in [('overwrite', R + '/overwrite')] + [(m, R + '/mods/' + m) for m in mods]:
    for tname in ('textures', 'Textures'):
        tdir = root + '/' + tname
        if not os.path.isdir(tdir): continue
        for r, _, fs in os.walk(tdir):
            for f in fs:
                if f.lower().endswith('.dds'):
                    full = os.path.join(r, f).replace(chr(92), '/'); rel = 'textures/' + full[len(tdir) + 1:].lower()
                    win.setdefault(rel, (name, full))
        break
print('winning loose dds', len(win), flush=True)
src = json.load(open(SRC)) if os.path.exists(SRC) else {o[0]: o[1] for o in json.load(open(OLD_SCAN))}
have = set()
for r, _, fs in os.walk(OUT + '/textures'):
    for f in fs:
        if f.lower().endswith('.dds'): have.add(('textures/' + os.path.join(r, f).replace(chr(92), '/')[len(OUT + '/textures') + 1:]).lower())

def info(full):
    with open(full, 'rb') as fh: h = fh.read(148)
    if h[:4] != b'DDS ': return None
    hh, ww = struct.unpack('<2I', h[12:20]); fourcc = h[84:88].decode('latin1'); dx10 = struct.unpack('<I', h[128:132])[0] if fourcc == 'DX10' else 0
    cube = struct.unpack('<I', h[112:116])[0] & 0x200
    return ww, hh, (DX10.get(dx10) if fourcc == 'DX10' else FOURCC.get(fourcc)), cube

jobs, dele, keep, skipped = [], [], 0, 0
for rel, (mod, full) in win.items():
    if rel.startswith(EXCL) or mod in ('foxnne - Mountain Textures 4K',):
        if rel in have: dele.append(rel)
        continue
    try: i = info(full)
    except Exception: i = None
    if not i: continue
    w, h, fmt, cube = i
    if max(w, h) <= 2048:
        if rel in have: dele.append(rel)
        continue
    if not fmt or cube: skipped += 1; continue
    if rel in have and src.get(rel) == mod: keep += 1; continue
    k = 2048 / max(w, h); jobs.append((rel, full, fmt, max(4, round(w * k)), max(4, round(h * k)), mod))
stale = [r for r in have if r not in win]          # source gone entirely: the copy would override nothing real
print('convert', len(jobs), 'keep', keep, 'delete', len(dele), 'stale (no winner)', len(stale), 'skipped', skipped, flush=True)
from collections import Counter
for m, n in Counter(j[5] for j in jobs).most_common(25): print('  %5d %s' % (n, m))
if DRY: sys.exit(0)
for rel in dele + stale:
    try: os.remove(OUT + '/' + rel); src.pop(rel, None)
    except FileNotFoundError: pass
t0 = time.time(); done = [0, 0]
def run(j):
    rel, full, fmt, nw, nh, mod = j
    outdir = os.path.dirname(OUT + '/' + rel); os.makedirs(outdir, exist_ok=True)
    tmp = outdir + '/_tmp_' + str(abs(hash(rel)))
    os.makedirs(tmp, exist_ok=True)
    p = subprocess.run([TEXCONV, '-nologo', '-y', '-w', str(nw), '-h', str(nh), '-m', '0', '-f', fmt, '-sepalpha', '-o', tmp, full], capture_output=True, text=True)
    made = os.path.join(tmp, os.path.basename(full))
    ok = p.returncode == 0 and os.path.exists(made)
    if ok: os.replace(made, OUT + '/' + rel); src[rel] = mod
    try: os.rmdir(tmp)
    except OSError: pass
    done[0 if ok else 1] += 1
    if not ok: print('FAIL', rel, (p.stdout + p.stderr)[-200:], flush=True)
    if sum(done) % 200 == 0: print('%d ok %d fail %.0fs' % (done[0], done[1], time.time() - t0), flush=True)
with ThreadPoolExecutor(WORKERS) as ex: list(ex.map(run, jobs))
for rel in have:
    if rel not in src and os.path.exists(OUT + '/' + rel): src[rel] = src.get(rel, '?')
json.dump(src, open(SRC, 'w'))
print('DONE ok %d fail %d %.0fs' % (done[0], done[1], time.time() - t0), flush=True)

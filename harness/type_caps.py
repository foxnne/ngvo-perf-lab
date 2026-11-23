"""Per-type texture caps into `foxnne - 2K Downscale (winning 4K textures)`: specular/mask/glow/parallax/env/PBR-material
maps above 1024 become 1024. Diffuse and normal maps are untouched (they stay at the 2K cap). Characters, faces and
mountains are skipped. Loose winners are converted from the original; copies we already made from BSAs are reduced from
our 2K copy. Records sources in _sources.json as '<mod>@1k'. usage: python type_caps.py [--dry] [--workers N] [--cap 1024]"""
import json, os, re, struct, subprocess, sys, time, tempfile, shutil
from concurrent.futures import ThreadPoolExecutor
R = 'C:/Modlists/NGVO 8.0 Beta'
NAME = 'foxnne - 2K Downscale (winning 4K textures)'
OUT = R + '/mods/' + NAME
TEXCONV = R + '/tools/DynDOLOD/Edit Scripts/Texconvx64.exe'
DRY = '--dry' in sys.argv
WORKERS = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 8
CAP = int(sys.argv[sys.argv.index('--cap') + 1]) if '--cap' in sys.argv else 1024
# _m env mask / spec, _s spec or PBR subsurface, _g glow, _p parallax, _e env, _em env mask, _rmaos PBR material, _cnr coat
TYPE = re.compile(r'_(m|s|g|p|e|em|rmaos|cnr|f)\.dds$')
SKIP = ('textures/actors/character/', 'textures/facegendata/', 'textures/landscape/mountains/', 'textures/interface/',
        'textures/lod/', 'textures/terrain/', 'textures/dyndolod/', 'textures/cubemaps/', 'textures/sky/', 'textures/effects/')
DX10 = {98: 'BC7_UNORM', 99: 'BC7_UNORM_SRGB', 72: 'BC1_UNORM_SRGB', 71: 'BC1_UNORM', 80: 'BC4_UNORM', 77: 'BC3_UNORM',
        78: 'BC3_UNORM_SRGB', 83: 'BC5_UNORM', 84: 'BC5_SNORM', 95: 'BC6H_UF16', 74: 'BC2_UNORM'}
FOURCC = {'DXT5': 'BC3_UNORM', 'DXT1': 'BC1_UNORM', 'DXT3': 'BC2_UNORM', 'BC4U': 'BC4_UNORM', 'ATI2': 'BC5_UNORM', 'BC5U': 'BC5_UNORM'}
def info(full):
    with open(full, 'rb') as fh: h = fh.read(148)
    if h[:4] != b'DDS ': return None
    hh, ww = struct.unpack('<2I', h[12:20]); fourcc = h[84:88].decode('latin1'); dx10 = struct.unpack('<I', h[128:132])[0] if fourcc == 'DX10' else 0
    return ww, hh, (DX10.get(dx10) if fourcc == 'DX10' else FOURCC.get(fourcc)), struct.unpack('<I', h[112:116])[0] & 0x200
mods = [l.rstrip('\r\n')[1:] for l in open(R + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l[:1] == '+']
mods = [m for m in mods if not m.endswith('_separator') and m != NAME and m != 'NPC Plugin Chooser Output']
win = {}
for name, root in [('overwrite', R + '/overwrite')] + [(m, R + '/mods/' + m) for m in mods]:
    for tname in ('textures', 'Textures'):
        tdir = root + '/' + tname
        if not os.path.isdir(tdir): continue
        for r, _, fs in os.walk(tdir):
            for f in fs:
                if TYPE.search(f.lower()):
                    full = os.path.join(r, f).replace(chr(92), '/'); win.setdefault('textures/' + full[len(tdir) + 1:].lower(), (name, full))
        break
src = json.load(open(OUT + '/_sources.json')) if os.path.exists(OUT + '/_sources.json') else {}
mine = {}
for r, _, fs in os.walk(OUT + '/textures'):
    for f in fs:
        if TYPE.search(f.lower()):
            full = os.path.join(r, f).replace(chr(92), '/'); mine['textures/' + full[len(OUT + '/textures') + 1:].lower()] = full
jobs = []; saved = 0
for rel in set(win) | set(mine):
    if rel.startswith(SKIP) or not TYPE.search(rel): continue
    mod = None
    if rel in mine and str(src.get(rel, '')).endswith('(bsa)'):
        full, mod = mine[rel], src[rel]                      # packed original: reduce our own 2K copy
    elif rel in win:
        mod, full = win[rel]
        if mod == 'foxnne - Mountain Textures 4K': continue
    else: continue
    if src.get(rel) == mod + '@1k': continue
    try: i = info(full)
    except Exception: continue
    if not i: continue
    w, h, fmt, cube = i
    if max(w, h) <= CAP or not fmt or cube: continue
    k = CAP / max(w, h); jobs.append((rel, full, fmt, max(4, round(w * k)), max(4, round(h * k)), mod))
    saved += os.path.getsize(full) * (1 - k * k)
from collections import Counter
print('maps to cap at %d: %d, about %.2f GB less (file size)' % (CAP, len(jobs), saved / 1e9), flush=True)
for m, n in Counter(j[5] for j in jobs).most_common(20): print('  %5d %s' % (n, m), flush=True)
if DRY: sys.exit(0)
done = [0, 0]; t0 = time.time()
def run(j):
    rel, full, fmt, nw, nh, mod = j
    tmp = tempfile.mkdtemp(prefix='tcap_')
    try:
        p = subprocess.run([TEXCONV, '-nologo', '-y', '-w', str(nw), '-h', str(nh), '-m', '0', '-f', fmt, '-sepalpha', '-o', tmp, full], capture_output=True, text=True)
        made = os.path.join(tmp, os.path.basename(full)); ok = p.returncode == 0 and os.path.exists(made)
        if ok:
            dst = OUT + '/' + rel; os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.move(made, dst); src[rel] = mod + '@1k'
        else: print('FAIL', rel, (p.stdout + p.stderr)[-200:], flush=True)
    finally: shutil.rmtree(tmp, ignore_errors=True)
    done[0 if ok else 1] += 1
    if sum(done) % 500 == 0: print('%d ok %d fail %.0fs' % (done[0], done[1], time.time() - t0), flush=True)
with ThreadPoolExecutor(WORKERS) as ex: list(ex.map(run, jobs))
json.dump(src, open(OUT + '/_sources.json', 'w'))
print('DONE ok %d fail %d %.0fs' % (done[0], done[1], time.time() - t0), flush=True)

"""Downscale oversized textures packed in the BSAs of enabled mods into `foxnne - 2K Downscale (winning 4K textures)`.
Loose files win over BSA contents, so a 2K loose copy replaces the packed 4K one. Paths that already have a loose winner
(any mod, overwrite) are left alone. Among BSAs, the higher modlist priority wins (approximation of plugin order).
usage: python bsa_downscale.py [--dry] [--only "Mod Name"] [--workers N]"""
import json, os, struct, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
import lz4.frame
R = 'C:/Modlists/NGVO 8.0 Beta'
NAME = 'foxnne - 2K Downscale (winning 4K textures)'
OUT = R + '/mods/' + NAME
TEXCONV = R + '/tools/DynDOLOD/Edit Scripts/Texconvx64.exe'
DRY = '--dry' in sys.argv
ONLY = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
WORKERS = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
EXCL = ('textures/dyndolod/', 'textures/interface/', 'textures/lod/', 'textures/terrain/', 'textures/water/flowmaps', 'textures/landscape/mountains/')
DX10 = {98: 'BC7_UNORM', 99: 'BC7_UNORM_SRGB', 72: 'BC1_UNORM_SRGB', 71: 'BC1_UNORM', 80: 'BC4_UNORM', 77: 'BC3_UNORM',
        78: 'BC3_UNORM_SRGB', 83: 'BC5_UNORM', 84: 'BC5_SNORM', 95: 'BC6H_UF16', 74: 'BC2_UNORM'}
FOURCC = {'DXT5': 'BC3_UNORM', 'DXT1': 'BC1_UNORM', 'DXT3': 'BC2_UNORM', 'BC4U': 'BC4_UNORM', 'ATI2': 'BC5_UNORM', 'BC5U': 'BC5_UNORM'}

def read_bsa(path):
    """-> list of (relpath, offset, size, compressed) for .dds entries (SSE v105)."""
    f = open(path, 'rb'); h = f.read(36)
    if h[:4] != b'BSA\0': return []
    ver, off, aflags, nfold, nfile, lfold, lfile, fflags = struct.unpack('<8I', h[4:36])
    if ver != 105: return []
    comp_default = bool(aflags & 4); embed = bool(aflags & 0x100)
    folders = [struct.unpack('<QIIQ', f.read(24)) for _ in range(nfold)]
    recs = []
    for _ in folders:
        n = f.read(1)[0]; name = f.read(n)[:-1].decode('cp1252').replace(chr(92), '/').lower()
        cnt = _[1]
        for _i in range(cnt):
            hsh, size, offset = struct.unpack('<QII', f.read(16)); recs.append((name, size, offset))
    names = f.read(lfile).split(b'\0')
    out = []
    for (folder, size, offset), fn in zip(recs, names):
        fn = fn.decode('cp1252').lower()
        if not fn.endswith('.dds'): continue
        comp = comp_default ^ bool(size & 0x40000000)
        out.append((folder + '/' + fn, offset, size & 0x3FFFFFFF, comp, embed))
    return out

def read_entry(path, offset, size, comp, embed, header_only=False):
    with open(path, 'rb') as f:
        f.seek(offset)
        if embed:
            n = f.read(1)[0]; f.read(n); size -= n + 1
        if not comp: return f.read(148 if header_only else size)
        orig = struct.unpack('<I', f.read(4))[0]; data = f.read(size - 4)
        if header_only:
            d = lz4.frame.LZ4FrameDecompressor(); return d.decompress(data, max_length=148)
        return lz4.frame.decompress(data)

mods = [l.rstrip('\r\n')[1:] for l in open(R + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l[:1] == '+']
mods = [m for m in mods if not m.endswith('_separator') and m != NAME]
loose = set()
for m in ['../overwrite'] + mods:
    for tname in ('textures', 'Textures'):
        t = R + '/mods/' + m + '/' + tname
        if os.path.isdir(t):
            for r, _, fs in os.walk(t):
                for fn in fs:
                    if fn.lower().endswith('.dds'): loose.add(('textures/' + os.path.join(r, fn).replace(chr(92), '/')[len(t) + 1:]).lower())
            break
mine = set()
for r, _, fs in os.walk(OUT + '/textures'):
    for fn in fs: mine.add(('textures/' + os.path.join(r, fn).replace(chr(92), '/')[len(OUT + '/textures') + 1:]).lower())
loose -= set()  # (our own copies are not in `mods` list, so they are not counted as loose winners)
win = {}
SKIPMODS = ('Imperfect Skin Overlays', 'Community Overlays', 'Rin Daughter', 'Remiel', 'Identity Crisis', 'Vailyn', "Nether's", 'Wayrest Sellsword', 'Northern Roadwatch')
for m in mods:
    if ONLY and m != ONLY: continue
    if m.startswith(SKIPMODS): continue
    d = R + '/mods/' + m
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.lower().endswith('.bsa'): continue
        for rel, off, size, comp, embed in read_bsa(d + '/' + fn):
            if rel in loose or rel in win or rel.startswith(EXCL): continue
            win[rel] = (m, d + '/' + fn, off, size, comp, embed)
print('packed dds candidates', len(win), flush=True)
jobs = []
from collections import Counter
cnt = Counter(); gb = Counter()
for rel, (m, bsa, off, size, comp, embed) in win.items():
    try: hd = read_entry(bsa, off, size, comp, embed, header_only=True)
    except Exception as e: continue
    if len(hd) < 148 or hd[:4] != b'DDS ': continue
    hh, ww = struct.unpack('<2I', hd[12:20]); fourcc = hd[84:88].decode('latin1')
    dx10 = struct.unpack('<I', hd[128:132])[0] if fourcc == 'DX10' else 0
    if max(ww, hh) <= 2048 or struct.unpack('<I', hd[112:116])[0] & 0x200: continue
    fmt = DX10.get(dx10) if fourcc == 'DX10' else FOURCC.get(fourcc)
    if not fmt: continue
    if rel in mine: continue
    k = 2048 / max(ww, hh); jobs.append((rel, m, bsa, off, size, comp, embed, fmt, max(4, round(ww * k)), max(4, round(hh * k))))
    cnt[m] += 1; gb[m] += size
print('to convert', len(jobs), flush=True)
for m, n in cnt.most_common(30): print('  %5d  %5.2f GB packed  %s' % (n, gb[m] / 1e9, m), flush=True)
if DRY: sys.exit(0)
src = json.load(open(OUT + '/_sources.json')) if os.path.exists(OUT + '/_sources.json') else {}
done = [0, 0]; t0 = time.time()
def run(j):
    rel, m, bsa, off, size, comp, embed, fmt, nw, nh = j
    tmp = tempfile.mkdtemp(prefix='bsads_')
    try:
        raw = read_entry(bsa, off, size, comp, embed)
        srcf = os.path.join(tmp, os.path.basename(rel)); open(srcf, 'wb').write(raw)
        outdir = os.path.join(tmp, 'o'); os.makedirs(outdir)
        p = subprocess.run([TEXCONV, '-nologo', '-y', '-w', str(nw), '-h', str(nh), '-m', '0', '-f', fmt, '-sepalpha', '-o', outdir, srcf], capture_output=True, text=True)
        made = os.path.join(outdir, os.path.basename(rel)); ok = p.returncode == 0 and os.path.exists(made)
        if ok:
            dst = OUT + '/' + rel; os.makedirs(os.path.dirname(dst), exist_ok=True); os.replace(made, dst); src[rel] = m + ' (bsa)'
        else: print('FAIL', rel, (p.stdout + p.stderr)[-200:], flush=True)
    finally:
        for r2, ds, fs in os.walk(tmp, topdown=False):
            for x in fs: os.remove(os.path.join(r2, x))
            for x in ds: os.rmdir(os.path.join(r2, x))
        os.rmdir(tmp)
    done[0 if ok else 1] += 1
    if sum(done) % 100 == 0: print('%d ok %d fail %.0fs' % (done[0], done[1], time.time() - t0), flush=True)
with ThreadPoolExecutor(WORKERS) as ex: list(ex.map(run, jobs))
json.dump(src, open(OUT + '/_sources.json', 'w'))
print('DONE ok %d fail %d %.0fs' % (done[0], done[1], time.time() - t0), flush=True)

"""Shrink DynDOLOD's CS-grass LOD atlases (textures/DynDOLOD/LOD/DynDOLOD_GrassOptimizations_*.dds) in the active DynDOLOD output:
4096 -> 2048 (BC7, full mip chain), and move atlases no LOD/grass nif references into the backup. Originals are moved to
C:/Modlists/backups/grasslod-4k-<stamp>/ first. The complex-grass marker (flat unit normal in the bottom-left texel of mip 0)
is checked on every result. Takes effect at the next game launch.
usage: python grass_lod_tex_shrink.py [--dry-run]"""
import os, re, shutil, struct, subprocess, sys, time, glob
import numpy as np
I = 'C:/Modlists/NGVO 8.0 Beta'; DRY = '--dry-run' in sys.argv
mods = [l.strip()[1:] for l in open(I + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l.startswith('+foxnne - DynDOLOD Output')]
OUT = I + '/mods/' + mods[0]; TEX = OUT + '/textures/DynDOLOD/LOD'
BK = 'C:/Modlists/backups/grasslod-4k-' + time.strftime('%Y%m%d'); TMP = os.path.join(os.environ['TEMP'], 'grasslod_shrink')
TEXCONV = glob.glob(I + '/tools/**/Texconvx64.exe', recursive=True)[0]


def dims(p):
    with open(p, 'rb') as fh: b = fh.read(148)
    h, w = struct.unpack_from('<II', b, 12); return w, h


refs = set()
for root in ('Meshes/LOD/Grass', 'Meshes/landscape/grass'):
    d = os.path.join(OUT, root)
    for f in os.listdir(d) if os.path.isdir(d) else []:
        b = open(os.path.join(d, f), 'rb').read()
        for m in re.findall(rb'[\x20-\x7e]{6,}\.dds', b): refs.add(m.decode('latin1').lower().replace('\\', '/').split('/')[-1])
have = sorted(f for f in os.listdir(TEX) if f.lower().startswith('dyndolod_grassoptimizations_'))
unref = [f for f in have if f.lower() not in refs]; big = [f for f in have if f.lower() in refs and max(dims(os.path.join(TEX, f))) > 2048]
size = lambda fs: sum(os.path.getsize(os.path.join(TEX, f)) for f in fs) / 1e6
print('output:', mods[0]); print('grass LOD atlases %d (%.0f MB) | referenced %d | unreferenced %d (%.0f MB) | to shrink %d (%.0f MB)' % (len(have), size(have), len(have) - len(unref), len(unref), size(unref), len(big), size(big)))
if DRY: sys.exit()
os.makedirs(BK, exist_ok=True); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
for f in unref: shutil.move(os.path.join(TEX, f), os.path.join(BK, f))
bad = []
for i, f in enumerate(big):
    src = os.path.join(TEX, f); w, h = dims(src)
    r = subprocess.run([TEXCONV, '-nologo', '-y', '-w', str(w // 2), '-h', str(h // 2), '-m', '0', '-sepalpha', '-f', 'BC7_UNORM', '-bc', 'q', '-o', TMP, src], capture_output=True, text=True)
    out = os.path.join(TMP, f)
    if r.returncode or not os.path.exists(out): bad.append((f, 'texconv')); continue
    chk = subprocess.run([TEXCONV, '-nologo', '-y', '-m', '1', '-f', 'R8G8B8A8_UNORM', '-px', 'chk_', '-o', TMP, out], capture_output=True, text=True)
    c = os.path.join(TMP, 'chk_' + f); b = open(c, 'rb').read(); hh, ww = struct.unpack_from('<II', b, 12); off = 128 + (20 if b[84:88] == b'DX10' else 0)
    t = np.frombuffer(b, np.uint8, ww * hh * 4, off).reshape(hh, ww, 4)[hh - 1, 0, :3].astype(float) / 255 * 2 - 1; os.remove(c)
    if not (t[2] > 0 and abs(np.linalg.norm(t) - 1) < 0.02): bad.append((f, 'marker %.3f' % np.linalg.norm(t))); os.remove(out); continue
    shutil.move(src, os.path.join(BK, f)); shutil.move(out, src)
    if i % 20 == 0: print('  %d/%d' % (i + 1, len(big)), flush=True)
left = [f for f in os.listdir(TEX) if f.lower().startswith('dyndolod_grassoptimizations_')]
print('done: now %d atlases, %.0f MB | originals in %s | problems: %s' % (len(left), size(left), BK, bad or 'none'))

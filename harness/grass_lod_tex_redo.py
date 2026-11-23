"""Redo the grass LOD atlas shrink from the backed-up 4096 originals with -sepalpha (the first pass resized with coupled alpha,
which wipes RGB where alpha is 0: marker texel, normals in gloss-0 areas, colour at blade edges).
For every 4096 original in the backup that a LOD/grass nif references: 2048 BC7 with full mips -> the DynDOLOD output.
Checks on each result: marker texel (bottom-left of mip 0) equals the original's, and mean RGB of alpha-0 texels is preserved.
usage: python grass_lod_tex_redo.py"""
import os, re, shutil, struct, subprocess, sys, time, glob
import numpy as np
I = 'C:/Modlists/NGVO 8.0 Beta'
mods = [l.strip()[1:] for l in open(I + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l.startswith('+foxnne - DynDOLOD Output')]
OUT = I + '/mods/' + mods[0]; TEX = OUT + '/textures/DynDOLOD/LOD'; BK = 'C:/Modlists/backups/grasslod-4k-20261122'
TMP = os.path.join(os.environ['TEMP'], 'grasslod_redo'); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
TEXCONV = glob.glob(I + '/tools/**/Texconvx64.exe', recursive=True)[0]


def run(args):
    for _ in range(4):
        if subprocess.run([TEXCONV, '-nologo', '-y'] + args, capture_output=True, text=True).returncode == 0: return True
        time.sleep(2)
    return False


def decode(p, tag):
    d = os.path.join(TMP, tag); os.makedirs(d, exist_ok=True)
    if not run(['-m', '1', '-f', 'R8G8B8A8_UNORM', '-o', d, p]): return None
    c = os.path.join(d, os.path.basename(p)); b = open(c, 'rb').read(); h, w = struct.unpack_from('<II', b, 12); off = 128 + (20 if b[84:88] == b'DX10' else 0)
    a = np.frombuffer(b, np.uint8, w * h * 4, off).reshape(h, w, 4).copy(); os.remove(c); return a


refs = set()
for root in ('Meshes/LOD/Grass', 'Meshes/landscape/grass'):
    d = os.path.join(OUT, root)
    for f in os.listdir(d) if os.path.isdir(d) else []:
        b = open(os.path.join(d, f), 'rb').read()
        for m in re.findall(rb'[\x20-\x7e]{6,}\.dds', b): refs.add(m.decode('latin1').lower().replace('\\', '/').split('/')[-1])
todo = []
for f in sorted(os.listdir(BK)):
    if f.lower() not in refs: continue
    with open(os.path.join(BK, f), 'rb') as fh: b = fh.read(32)
    h, w = struct.unpack_from('<II', b, 12)
    if max(w, h) > 2048: todo.append(f)
if len(sys.argv) > 1:
    only = set(x.strip().lower() for x in open(sys.argv[1]).read().splitlines()); todo = [f for f in todo if f.lower() in only]
print('to convert from backup:', len(todo), flush=True)
ok = 0; bad = []
o = os.path.join(TMP, 'o'); os.makedirs(o)
for i, f in enumerate(todo):
    src = os.path.join(BK, f); A = decode(src, 'a')
    if A is None: bad.append((f, 'decode')); continue
    h, w = A.shape[:2]
    if not run(['-w', str(w // 2), '-h', str(h // 2), '-m', '0', '-sepalpha', '-f', 'BC7_UNORM', '-bc', 'q', '-o', o, src]): bad.append((f, 'encode')); continue
    out = os.path.join(o, f); B = decode(out, 'b')
    if B is None: bad.append((f, 'decode2')); continue
    m0 = A[h - 1, 0, :3].astype(int); m1 = B[B.shape[0] - 1, 0, :3].astype(int)
    z0 = A[..., 3] == 0; z1 = B[..., 3] == 0
    c0 = A[z0][:, :3].mean(0) if z0.any() else np.zeros(3); c1 = B[z1][:, :3].mean(0) if z1.any() else np.zeros(3)
    if np.abs(m0 - m1).max() > 6 or (z0.mean() > 0.01 and np.abs(c0 - c1).max() > 12):
        bad.append((f, 'marker %s->%s alpha0 rgb %s->%s' % (m0.tolist(), m1.tolist(), np.round(c0).tolist(), np.round(c1).tolist()))); os.remove(out); continue
    shutil.move(out, os.path.join(TEX, f)); ok += 1
    if i % 20 == 0: print('  %d/%d' % (i + 1, len(todo)), flush=True)
shutil.rmtree(TMP, ignore_errors=True)
left = [f for f in os.listdir(TEX) if f.lower().startswith('dyndolod_grassoptimizations_')]
print('converted %d of %d | atlases now %d, %.0f MB | problems: %s' % (ok, len(todo), len(left), sum(os.path.getsize(os.path.join(TEX, f)) for f in left) / 1e6, bad or 'none'))

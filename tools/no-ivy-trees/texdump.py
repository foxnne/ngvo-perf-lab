"""Extract textures (winning loose, else NotWL textures BSA) to work/tex and convert to PNG with texconv for a look."""
import os, subprocess, sys
sys.path.insert(0, r'C:\Users\foxnn\dev\biome-flora\tools')
import flib, tes5
W = r'C:\Users\foxnn\dev\no-ivy-trees\work\tex'
os.makedirs(W, exist_ok=True)
TEXCONV = r'C:\Modlists\NGVO 8.0 Beta\tools\DynDOLOD\Edit Scripts\Texconvx64.exe'
want = sys.argv[1:]
mods = flib.enabled_mods()
for rel in want:
    rel = rel.lower()
    data = None
    for m in mods:
        p = os.path.join(flib.MODS, m, rel)
        if os.path.exists(p):
            data = open(p, 'rb').read(); print(rel, '<- loose', m); break
    if data is None:
        for m in mods:
            d = os.path.join(flib.MODS, m)
            for f in os.listdir(d) if os.path.isdir(d) else []:
                if f.lower().endswith('.bsa') and 'wild lands' in f.lower() or f.lower().startswith('notwl'):
                    try:
                        bsa = tes5.BSA(os.path.join(d, f))
                    except Exception:
                        continue
                    rb = rel.replace('/', chr(92))
                    if rb in bsa.files:
                        data = bsa.read(rb); print(rel, '<- bsa', f); break
            if data is not None: break
    if data is None:
        print('NOT FOUND', rel); continue
    out = os.path.join(W, os.path.basename(rel))
    open(out, 'wb').write(data)
    subprocess.run([TEXCONV, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-w', '768', '-h', '768', '-m', '1', '-o', W, out], capture_output=True)

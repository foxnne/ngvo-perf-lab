"""Queue job (game + MO2 closed): install a downloaded archive as a new MO2 mod (extracted with 7-Zip), ticked right below a named
mod in modlist.txt; any .esp/.esl/.esm in its root is activated in plugins.txt/loadorder.txt directly BEFORE DynDOLOD.esp (after
all grass plugins, so the grass cache's light-plugin form IDs do not shift). --park DIR moves a top-level folder of the archive
into '<mod>/optional/' (not loaded by the game).
usage: python install_archive.py "<archive in downloads>" "<mod name>" "<mod it goes below>" [--park textures]"""
import os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
for _ in range(30):
    if not bench.running(): break
    time.sleep(4)
else: sys.exit('game open')
bench.close_mo2()
I = 'C:/Modlists/NGVO 8.0 Beta'; P = I + '/profiles/foxnne-nsfw'
arch, mod, below = sys.argv[1], sys.argv[2], sys.argv[3]; park = sys.argv[sys.argv.index('--park') + 1] if '--park' in sys.argv else None
dst = f'{I}/mods/{mod}'
if os.path.exists(dst): shutil.rmtree(dst)
r = subprocess.run(['C:/Program Files/7-Zip/7z.exe', 'x', '-y', '-o' + dst, f'{I}/downloads/{arch}'], capture_output=True, text=True)
if r.returncode: sys.exit(r.stdout[-400:])
DATA = ('skse', 'textures', 'meshes', 'scripts', 'interface', 'sound')
top = os.listdir(dst)
if len(top) == 1 and os.path.isdir(os.path.join(dst, top[0])) and top[0].lower() not in DATA:
    inner = os.path.join(dst, top[0])                        # archive wrapped in one folder
    for e in os.listdir(inner): shutil.move(os.path.join(inner, e), os.path.join(dst, e))
    os.rmdir(inner)
if park:
    for e in os.listdir(dst):
        if e.lower() == park.lower():
            os.makedirs(os.path.join(dst, 'optional'), exist_ok=True); shutil.move(os.path.join(dst, e), os.path.join(dst, 'optional', e))
plugins = [f for f in os.listdir(dst) if f.lower().endswith(('.esp', '.esl', '.esm'))]
F = P + '/modlist.txt'; L = open(F, encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[1].endswith('\r') else ''
L = [l for l in L if l.rstrip('\r')[1:] != mod]
i = next(k for k, l in enumerate(L) if l.rstrip('\r')[1:].startswith(below))
L.insert(i + 1, '+' + mod + cr); open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L))
for f, star in (('plugins.txt', '*'), ('loadorder.txt', '')):
    X = open(f'{P}/{f}', encoding='utf-8-sig').read().split('\n'); c2 = '\r' if X[1].endswith('\r') else ''
    have = {l.rstrip('\r').lstrip('*').lower() for l in X}
    j = next(k for k, l in enumerate(X) if l.rstrip('\r').lstrip('*').lower() == 'dyndolod.esp')
    for p in plugins:
        if p.lower() not in have: X.insert(j, star + p + c2); j += 1
    open(f'{P}/{f}', 'w', encoding='utf-8', newline='').write('\n'.join(X))
print('installed', mod, '| top-level:', sorted(os.listdir(dst)), '| plugins activated:', plugins)

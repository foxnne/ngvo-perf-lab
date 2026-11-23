"""Queue job (game + MO2 closed): install a mod folder built outside the list and tick it right BELOW a named mod (lower priority than it,
higher than everything after). usage: python install_built_mod.py "<source folder>" "<mod it goes directly below>"   |  undo: add 'undo' as 3rd arg"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time as _t
for _i in range(30):
    if not bench.running(): break
    _t.sleep(4)
else: sys.exit('game open')
bench.close_mo2()
SRC = sys.argv[1]; MOD = os.path.basename(SRC.rstrip('/')); I = 'C:/Modlists/NGVO 8.0 Beta'; F = I + '/profiles/foxnne-nsfw/modlist.txt'; DST = I + '/mods/' + MOD
L = open(F, encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[1].endswith('\r') else ''
L = [l for l in L if l.rstrip('\r')[1:] != MOD]
if len(sys.argv) > 3 and sys.argv[3] == 'undo':
    shutil.rmtree(DST, ignore_errors=True); print('removed', MOD)
else:
    shutil.copy2(F, F + '.bak-pre-' + ''.join(c if c.isalnum() else '_' for c in MOD)[-40:])
    if os.path.exists(DST): shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    i = next(k for k, l in enumerate(L) if l.rstrip('\r')[1:].startswith(sys.argv[2]))
    L.insert(i + 1, '+' + MOD + cr)
    print('installed', MOD, sum(len(f) for _, _, f in os.walk(DST)), 'files, modlist line', i + 2)
open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L))

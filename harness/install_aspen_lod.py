"""Queue job (game + MO2 closed): install 'foxnne - Aspens Ablaze 3D LOD' (built in C:/Users/foxnn/dev/aspen-lod/out) into the
mod list, enabled, right above 'foxnne - Aspen Yellow Variants'. usage: python install_aspen_lod.py [undo]"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time as _t
for _i in range(30):
    if not bench.running(): break
    _t.sleep(4)
else: sys.exit('game open')
bench.close_mo2()
MOD = 'foxnne - Aspens Ablaze 3D LOD'; I = 'C:/Modlists/NGVO 8.0 Beta'; F = I + '/profiles/foxnne-nsfw/modlist.txt'
SRC = 'C:/Users/foxnn/dev/aspen-lod/out/' + MOD; DST = I + '/mods/' + MOD
L = open(F, encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[0].endswith('\r') else ''
L = [l for l in L if l.rstrip('\r')[1:] != MOD]
if len(sys.argv) > 1 and sys.argv[1] == 'undo':
    shutil.rmtree(DST, ignore_errors=True)
else:
    shutil.copy2(F, F + '.bak-pre-aspenlod-20261121')
    if os.path.exists(DST): shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    i = next(k for k, l in enumerate(L) if l.rstrip('\r')[1:] == 'foxnne - Aspen Yellow Variants')
    L.insert(i, '+' + MOD + cr)
    print('installed', sum(len(f) for _, _, f in os.walk(DST)), 'files at modlist line', i + 1)
open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L))

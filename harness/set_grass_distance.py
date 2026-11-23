"""Queue job (game closed): extended-grass distance per the CS Grass Optimizations guide
(dragonbornsfate.moddinglinked.com/extendedgrass.html): NGIO Overwrite-grass-distance = 40000, Overwrite-grass-fade-range = 0.
usage: python set_grass_distance.py [DISTANCE | undo]   (backup GrassControl.ini.bak-pre-grassdist-20261121)"""
import os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
F = 'C:/Modlists/NGVO 8.0 Beta/mods/No Grass In Objects - Grass Control/SKSE/Plugins/GrassControl.ini'
BK = F + '.bak-pre-grassdist-20261121'
arg = sys.argv[1] if len(sys.argv) > 1 else '40000'
if arg == 'undo':
    shutil.copy2(BK, F); print('GrassControl.ini restored'); sys.exit()
if not os.path.exists(BK):
    shutil.copy2(F, BK)
s = open(F, encoding='utf-8', newline='').read()
for k, v in (('Overwrite-grass-distance', float(arg)), ('Overwrite-grass-fade-range', 0.0)):
    s, n = re.subn(r'(?m)^(%s\s*=\s*)[-0-9.]+' % re.escape(k), lambda m: m.group(1) + '%.6f' % v, s)
    print(k, '->', v, '' if n else '(KEY NOT FOUND)')
open(F, 'w', encoding='utf-8', newline='').write(s)

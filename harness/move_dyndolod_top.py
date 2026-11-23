"""Queue job (game + MO2 closed): give the active 'foxnne - DynDOLOD Output*' mod top priority (first line of modlist.txt) so its
CS Grass Optimizations assets (atlas-updated full grass NIFs + LOD\\Grass\\*_lod1.nif) win over our grass mods, as DynDOLOD's
Community Shaders docs require. Before this (2026-11-21) QW Grass, FFF, Grass Coverage and their LOD mods overrode 181 of its files.
usage: python move_dyndolod_top.py [undo]   (undo restores modlist.txt.bak-pre-dyntop-20261121)"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
bench.close_mo2()
F = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/modlist.txt'; BK = F + '.bak-pre-dyntop-20261121'
if len(sys.argv) > 1 and sys.argv[1] == 'undo':
    shutil.copy2(BK, F); print('modlist restored'); sys.exit()
shutil.copy2(F, BK)
raw = open(F, encoding='utf-8-sig').read(); L = raw.split('\n')
i = next(k for k, l in enumerate(L) if l.startswith('+foxnne - DynDOLOD Output'))
line = L.pop(i)
j = next(k for k, l in enumerate(L) if not l.startswith('#'))     # after MO2's header comment
L.insert(j, line)
open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('moved', line.strip(), 'from line', i + 1, 'to line', j + 1)

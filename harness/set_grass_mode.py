"""Queue job (game closed): GrassControl.ini -> DynDOLOD-Grass-Mode = 1, Extend-grass-distance = false (backup once). 'undo' restores."""
import os, re, shutil, sys
F = 'C:/Modlists/NGVO 8.0 Beta/mods/No Grass In Objects - Grass Control/SKSE/Plugins/GrassControl.ini'; B = F + '.bak-pre-grassmode1-20261121'
if len(sys.argv) > 1 and sys.argv[1] == 'undo': shutil.copy2(B, F); print('restored'); sys.exit()
if not os.path.exists(B): shutil.copy2(F, B)
t = open(F, encoding='utf-8-sig').read()
t = re.sub(r'(?m)^DynDOLOD-Grass-Mode\s*=.*$', 'DynDOLOD-Grass-Mode = 1', t)
t = re.sub(r'(?m)^Extend-grass-distance\s*=.*$', 'Extend-grass-distance = false', t)
open(F, 'w', encoding='utf-8-sig', newline='').write(t)
print([l for l in t.splitlines() if l.startswith(('DynDOLOD-Grass-Mode', 'Extend-grass-distance'))])

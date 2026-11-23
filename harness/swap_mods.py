"""Queue job (MO2 closed): python swap_mods.py NAME  -- named modlist swaps for memory bisects (backup each time; 'restore' undoes).
  ngvo-lod    : foxnne DynDOLOD/TexGen Output 2026-11-21 off, NGVO - DynDOLOD Output + NGVO - TexGen Output on (same plugin names)
  no-terrain  : foxnne - xLODGen Terrain 2026-11-21 off
  restore     : back to the modlist saved before the first swap of this series"""
import os, shutil, subprocess, sys
P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw'; ML = P + '/modlist.txt'; BAK = ML + '.bak-memory-bisect'
if 'modorganizer.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower(): sys.exit('MO2 open')
name = sys.argv[1]
if name == 'restore':
    shutil.copy2(BAK, ML); print('restored'); sys.exit()
if not os.path.exists(BAK): shutil.copy2(ML, BAK)
else: shutil.copy2(BAK, ML)            # each swap starts from the saved state
SW = {'ngvo-lod': ({'foxnne - DynDOLOD Output 2026-11-21', 'foxnne - TexGen Output 2026-11-21'}, {'NGVO - DynDOLOD Output', 'NGVO - TexGen Output'}),
      'no-terrain': ({'foxnne - xLODGen Terrain 2026-11-21'}, set())}[name]
off, on = SW
L = open(ML, encoding='utf-8-sig').read().split('\n')
L = [('-' + l[1:]) if l.rstrip('\r')[1:] in off else (('+' + l[1:]) if l.rstrip('\r')[1:] in on else l) for l in L]
open(ML, 'w', encoding='utf-8', newline='').write('\n'.join(L)); print('swap', name, 'off', off, 'on', on)

"""Queue job (game and MO2 closed): python toggle_rugged.py off|on -- disable/enable the Rugged Ground mods and plugins (backup on 'off')."""
import shutil, sys, subprocess, time
P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw'
if 'modorganizer.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower(): sys.exit('MO2 open')
MODS = ['Rugged Ground - Stones & Scree', 'foxnne - Rugged Ground 2K', 'foxnne - Rugged Ground Patch']
ESPS = ['Rugged Ground - Stones & Scree.esp', 'foxnne - Rugged Ground Patch.esp']
on = sys.argv[1] == 'on'
if not on:
    for f in ('modlist.txt', 'plugins.txt'): shutil.copy2(f'{P}/{f}', f'{P}/{f}.bak-rugged-off')
L = open(f'{P}/modlist.txt', encoding='utf-8-sig').read().split('\n')
L = [(('+' if on else '-') + l[1:]) if l.rstrip('\r')[1:] in MODS else l for l in L]
open(f'{P}/modlist.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))
L = open(f'{P}/plugins.txt', encoding='utf-8-sig').read().split('\n')
L = [(('*' if on else '') + l.lstrip('*')) if l.rstrip('\r').lstrip('*') in ESPS else l for l in L]
open(f'{P}/plugins.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('rugged ground', 'on' if on else 'off')

"""Queue job (MO2 closed): python toggle_rg2k.py off|on  -- untick/tick 'foxnne - Rugged Ground 2K' (original 4K Rugged Ground atlas when off)."""
import subprocess, sys
ML = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/modlist.txt'
if 'modorganizer.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower(): sys.exit('MO2 open')
on = sys.argv[1] == 'on'; M = 'foxnne - Rugged Ground 2K'
L = open(ML, encoding='utf-8-sig').read().split('\n')
L = [(('+' if on else '-') + l[1:]) if l.rstrip('\r')[1:] == M else l for l in L]
open(ML, 'w', encoding='utf-8', newline='').write('\n'.join(L)); print(M, 'on' if on else 'off')

"""Queue job (MO2 closed): put the Rugged Ground plugins back right after foxnne - Grass Coverage.esp (plugins.txt active, loadorder.txt)."""
import subprocess, sys
P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw'
if 'modorganizer.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower(): sys.exit('MO2 open')
ESPS = ['Rugged Ground - Stones & Scree.esp', 'foxnne - Rugged Ground Patch.esp']
for f, star in (('plugins.txt', True), ('loadorder.txt', False)):
    L = open(f'{P}/{f}', encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[0].endswith('\r') else ''
    L = [l for l in L if l.rstrip('\r').lstrip('*') not in ESPS]
    i = [k for k, l in enumerate(L) if l.rstrip('\r').lstrip('*') == 'foxnne - Grass Coverage.esp'][0]
    for n, e in enumerate(ESPS): L.insert(i + 1 + n, ('*' if star else '') + e + cr)
    open(f'{P}/{f}', 'w', encoding='utf-8', newline='').write('\n'.join(L)); print(f, 'restored')

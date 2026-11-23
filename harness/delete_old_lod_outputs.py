"""Queue job (game + MO2 closed): delete superseded foxnne DynDOLOD / TexGen output mods (user OK 2026-11-21), keeping the ones
ticked in modlist.txt and everything named NGVO. Removes their modlist lines too. Refuses to delete an enabled mod.
usage: python delete_old_lod_outputs.py"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time as _t
for _i in range(30):
    if not bench.running(): break
    _t.sleep(4)
else: sys.exit('game open')
bench.close_mo2()
I = 'C:/Modlists/NGVO 8.0 Beta'; F = I + '/profiles/foxnne-nsfw/modlist.txt'
L = open(F, encoding='utf-8-sig').read().split('\n'); shutil.copy2(F, F + '.bak-pre-lodcleanup-20261121')
enabled = {l.rstrip('\r')[1:] for l in L if l.startswith('+')}
other = set()
for p in os.listdir(I + '/profiles'):
    f2 = f'{I}/profiles/{p}/modlist.txt'
    if p != 'foxnne-nsfw' and os.path.exists(f2):
        other |= {l.rstrip('\r')[1:] for l in open(f2, encoding='utf-8-sig').read().split('\n') if l.startswith('+')}
gone, freed = [], 0
for m in sorted(os.listdir(I + '/mods')):
    if not m.startswith(('foxnne - DynDOLOD Output', 'foxnne - TexGen Output')): continue
    if m in enabled or m in other: print('keep (enabled):', m); continue
    p = os.path.join(I, 'mods', m)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs)
    shutil.rmtree(p); gone.append(m); freed += size; print('deleted %s (%.1f GB)' % (m, size / 2**30), flush=True)
L = [l for l in L if l.rstrip('\r')[1:] not in gone]
open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('freed %.1f GB' % (freed / 2**30))

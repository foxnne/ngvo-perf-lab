"""Queue job (game + MO2 closed): install the grass cache without Rugged Ground as a full replacement cache mod.
New mod 'foxnne - Grass Cache 2026-11-21 no-rugged' = old cache files, replaced by the cleaned ones from
C:/Users/foxnn/dev/qw-drj-patch/out/cache-no-rugged/Grass; cells left with zero grass types are omitted. The old cache mod is unticked (kept).
usage: python install_clean_cache.py [undo]"""
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
OLD = 'foxnne - Grass Cache 2026-11-21 forest'; NEW = 'foxnne - Grass Cache 2026-11-21 no-rugged'
CLEAN = 'C:/Users/foxnn/dev/qw-drj-patch/out/cache-no-rugged/Grass'
L = open(F, encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[1].endswith('\r') else ''
if len(sys.argv) > 1 and sys.argv[1] == 'undo':
    L = [('+' + OLD + cr) if l.rstrip('\r')[1:] == OLD else l for l in L if l.rstrip('\r')[1:] != NEW]
    open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L)); print('old cache re-enabled'); sys.exit()
shutil.copy2(F, F + '.bak-pre-cleancache-20261121')
dst = f'{I}/mods/{NEW}/Grass'
if os.path.exists(f'{I}/mods/{NEW}'): shutil.rmtree(f'{I}/mods/{NEW}')
os.makedirs(dst)
clean = {f.lower(): f for f in os.listdir(CLEAN)}
n_old = n_clean = n_skip = 0
for f in os.listdir(f'{I}/mods/{OLD}/Grass'):
    c = clean.get(f.lower())
    if c:
        p = os.path.join(CLEAN, c)
        if os.path.getsize(p) <= 4: n_skip += 1; continue
        shutil.copy2(p, os.path.join(dst, f)); n_clean += 1
    else:
        shutil.copy2(f'{I}/mods/{OLD}/Grass/{f}', os.path.join(dst, f)); n_old += 1
i = next(k for k, l in enumerate(L) if l.rstrip('\r')[1:] == OLD)
L[i] = '-' + OLD + cr; L = [l for l in L if l.rstrip('\r')[1:] != NEW]; L.insert(i, '+' + NEW + cr)
open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('new cache: %d cleaned + %d unchanged files, %d rock-only cells omitted' % (n_clean, n_old, n_skip))

"""Queue job (game + MO2 closed): quick mip test without a DynDOLOD regen. 'on': builds a temporary top-priority mod
'foxnne - TEST QW grass meshes' with the original QW grass meshes (+ the QW Grass Complex patched ones) so they win over the DynDOLOD
output's grass mesh copies (which point at DynDOLOD's own textures), and sets CS Grass Optimizations EnableMeshLOD=false so every
instance uses the full mesh with the re-mipped QW textures. 'off': removes the mod and restores the setting.
usage: python grass_mip_test.py on|off"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time as _t
for _i in range(30):
    if not bench.running(): break
    _t.sleep(4)
else: sys.exit('game open')
bench.close_mo2()
I = 'C:/Modlists/NGVO 8.0 Beta'; F = I + '/profiles/foxnne-nsfw/modlist.txt'; MOD = 'foxnne - TEST QW grass meshes'; DST = I + '/mods/' + MOD
S = I + '/mods/CS Settings/SKSE/Plugins/CommunityShaders/SettingsUser.json'
L = [l for l in open(F, encoding='utf-8-sig').read().split('\n') if l.rstrip('\r')[1:] != MOD]; cr = '\r' if L[1].endswith('\r') else ''
d = json.load(open(S))
if sys.argv[1] == 'on':
    if os.path.exists(DST): shutil.rmtree(DST)
    n = 0
    for src in (I + '/mods/foxnne - QW Grass', I + '/mods/foxnne - QW Grass Complex'):      # later copy wins
        g = os.path.join(src, 'meshes', 'landscape', 'grass')
        if not os.path.isdir(g): print('missing', g); continue
        os.makedirs(os.path.join(DST, 'meshes', 'landscape', 'grass'), exist_ok=True)
        for f in os.listdir(g):
            shutil.copy2(os.path.join(g, f), os.path.join(DST, 'meshes', 'landscape', 'grass', f)); n += 1
    j = next(k for k, l in enumerate(L) if not l.startswith('#'))
    L.insert(j, '+' + MOD + cr)
    d['Grass Optimizations']['EnableMeshLOD'] = False
    print('test mod on:', n, 'mesh copies; EnableMeshLOD off')
else:
    shutil.rmtree(DST, ignore_errors=True)
    d['Grass Optimizations']['EnableMeshLOD'] = True
    print('test mod removed; EnableMeshLOD on')
open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L)); json.dump(d, open(S, 'w'), indent=2)

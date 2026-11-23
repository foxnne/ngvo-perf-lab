"""Queue job (game closed): small reversible config switches for VRAM / hitch A/B runs.
usage: python cfg_toggle.py sps1024|sps2048|lodoff|lodon
 sps1024/sps2048: texture streamer max edge (overwrite/SKSE/Plugins/SPS_User.ini fMaxEdge)
 lodoff/lodon:    untick/tick the active foxnne DynDOLOD, TexGen and xLODGen terrain outputs + the DynDOLOD plugins (state saved in cfg_toggle.lod.json)"""
import json, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time as _t
for _i in range(30):
    if not bench.running(): break
    _t.sleep(4)
else: sys.exit('game open')
I = 'C:/Modlists/NGVO 8.0 Beta'; P = I + '/profiles/foxnne-nsfw'; mode = sys.argv[1]
if mode.startswith('sps'):
    f = I + '/overwrite/SKSE/Plugins/SPS_User.ini'; s = open(f, encoding='utf-8-sig', newline='').read()
    s, n = re.subn(r'(?m)^(fMaxEdge\s*=\s*)\d+', lambda m: m.group(1) + mode[3:], s)
    open(f, 'w', encoding='utf-8-sig', newline='').write(s); print('fMaxEdge ->', mode[3:], 'ok' if n else 'KEY NOT FOUND')
elif mode.startswith('lod4='):                      # fBlockLevel0Distance: how far the detailed LOD4 ring (3D trees) reaches
    f = P + '/skyrimprefs.ini'; s = open(f, encoding='utf-8-sig', newline='').read()
    s, n = re.subn(r'(?m)^(fBlockLevel0Distance\s*=\s*)[0-9.]+', lambda m: m.group(1) + '%.4f' % float(mode[5:]), s)
    open(f, 'w', encoding='utf-8', newline='').write(s); print('fBlockLevel0Distance ->', mode[5:], 'ok' if n else 'KEY NOT FOUND')
elif mode.startswith(('modoff=', 'modon=')):        # untick / tick one mod by exact name (no plugin handling: for DLL-only mods)
    bench.close_mo2(); F = P + '/modlist.txt'; name = mode.split('=', 1)[1]; on = mode.startswith('modon=')
    L = open(F, encoding='utf-8-sig').read().split('\n'); n = 0
    for i, l in enumerate(L):
        if l.rstrip('\r')[1:] == name: L[i] = ('+' if on else '-') + l[1:]; n += 1
    open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L)); print(name, 'on' if on else 'off', 'ok' if n else 'NOT FOUND')
elif mode in ('terrainlodoff', 'terrainlodon'):       # our xLODGen terrain LOD mod off = the game's vanilla terrain LOD meshes/textures
    bench.close_mo2(); F = P + '/modlist.txt'; L = open(F, encoding='utf-8-sig').read().split('\n')
    L = [(('-' if mode == 'terrainlodoff' else '+') + l[1:]) if l.rstrip('\r')[1:].startswith('foxnne - xLODGen Terrain') else l for l in L]
    open(F, 'w', encoding='utf-8', newline='').write('\n'.join(L)); print([l.strip() for l in L if 'xLODGen Terrain' in l])
elif mode in ('lodshadowson', 'lodshadowsoff'):       # LOD Shadows feature switch with the settings recommended for the stability fix
    f = I + '/mods/CS Settings/SKSE/Plugins/CommunityShaders/SettingsUser.json'; d = json.load(open(f))
    d['LOD Shadows'] = {'EnableLODShadows': mode == 'lodshadowson', 'UpdateBudgetMs': 0.2, 'DepthBias': 8.0, 'TexelBias': 1.0, 'CrownBias': 256.0, 'DirectionStepDegrees': 0.5, 'FarMapLimit': 0.0}
    json.dump(d, open(f, 'w'), indent=2); print('LOD Shadows:', d['LOD Shadows'])
elif mode.startswith('ngio:'):                      # ngio:Key=value[,Key=value] edits GrassControl.ini (backup .bak-cfgtoggle once)
    f = I + '/mods/No Grass In Objects - Grass Control/SKSE/Plugins/GrassControl.ini'
    if not os.path.exists(f + '.bak-cfgtoggle'): shutil.copy2(f, f + '.bak-cfgtoggle')
    s = open(f, encoding='utf-8', newline='').read()
    for kv in mode[5:].split(','):
        k, v = kv.split('=', 1)
        s, n = re.subn(r'(?m)^(%s\s*=\s*)[^\r\n]*' % re.escape(k), lambda m: m.group(1) + v, s)
        print(k, '->', v, 'ok' if n else 'KEY NOT FOUND')
    open(f, 'w', encoding='utf-8', newline='').write(s)
elif mode in ('csgrassoff', 'csgrasson'):            # Community Shaders Grass Optimizations disabled at boot (A/B: who culls far grass?)
    f = I + '/mods/CS Settings/SKSE/Plugins/CommunityShaders/SettingsUser.json'; d = json.load(open(f))
    d.setdefault('Disable at Boot', {})['GrassOptimizations'] = (mode == 'csgrassoff')
    json.dump(d, open(f, 'w'), indent=2); print('Disable at Boot:', d['Disable at Boot'])
elif mode in ('lodoff', 'lodon'):
    bench.close_mo2(); S = os.path.join(HERE, 'cfg_toggle.lod.json')
    files = ('modlist.txt', 'plugins.txt', 'loadorder.txt')
    if mode == 'lodoff':
        if os.path.exists(S): sys.exit('already off (state file exists)')
        for f in files: shutil.copy2(f'{P}/{f}', f'{P}/{f}.bak-cfgtoggle-lod')
        L = open(f'{P}/modlist.txt', encoding='utf-8-sig').read().split('\n'); off = []
        for i, l in enumerate(L):
            if l.startswith(('+foxnne - DynDOLOD Output', '+foxnne - TexGen Output', '+foxnne - xLODGen Terrain')):
                L[i] = '-' + l[1:]; off.append(l.strip())
        open(f'{P}/modlist.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))
        X = open(f'{P}/plugins.txt', encoding='utf-8-sig').read().split('\n')
        X = [('' + l.lstrip('*')) if l.rstrip('\r').lstrip('*').lower() in ('dyndolod.esm', 'dyndolod.esp', 'occlusion.esp') else l for l in X]
        open(f'{P}/plugins.txt', 'w', encoding='utf-8', newline='').write('\n'.join(X))
        json.dump(off, open(S, 'w')); print('LOD outputs off:', off)
    else:
        for f in files: shutil.copy2(f'{P}/{f}.bak-cfgtoggle-lod', f'{P}/{f}')
        if os.path.exists(S): os.remove(S)
        print('LOD outputs restored')
else:
    sys.exit('unknown mode')

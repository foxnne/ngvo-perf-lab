"""Queue job (game closed): hitch fixes from the 2026-11-20 fast-travel Hitch Hunter / SPS logs. Backs up each file.
- SPS TextureStream: budget mode (only shrink when VRAM is tight) instead of always-by-distance, which reloaded
  50-176 MB of textures per frame during the fast-travel flight.
- Skyrim.ini [Papyrus] fPostLoadUpdateTimeMS 2000 -> 500 (Hitch Hunter: +1.5 s per loading screen).
- Apocrypha Menu Framework bLoadSkyUIScriptMenus 1 -> 0 (its SkyUI-script MCM scan blocked the main thread 120-160 ms
  repeatedly after loads; MCM Helper pages still load). usage: python hitch_fixes_job.py TAG"""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
R = 'C:/Modlists/NGVO 8.0 Beta'; STAMP = time.strftime('%Y%m%d-%H%M%S')
def edit(path, section, key, value):
    shutil.copy2(path, path + '.bak-pre-hitchfix-' + STAMP)
    raw = open(path, 'rb').read(); bom = raw.startswith(b'\xef\xbb\xbf'); nl = '\r\n' if b'\r\n' in raw else '\n'
    L = raw.decode('utf-8-sig').split(nl); sec = None; done = False
    for i, l in enumerate(L):
        s = l.strip()
        if s.startswith('[') and s.endswith(']'): sec = s[1:-1].lower(); continue
        if sec == section.lower() and re.match(r'\s*%s\s*=' % re.escape(key), l, re.I):
            L[i] = re.sub(r'=.*$', ('= ' if ' = ' in l else '=') + value, l); done = True; break
    if not done:
        idx = [i for i, l in enumerate(L) if l.strip().lower() == '[%s]' % section.lower()]
        if idx: L.insert(idx[0] + 1, '%s = %s' % (key, value))
        else: L += ['[%s]' % section, '%s = %s' % (key, value)]
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + nl.join(L).encode('utf-8'))
    print(os.path.basename(path), section, key, '->', value, flush=True)
edit(R + '/overwrite/SKSE/Plugins/SPS_User.ini', 'TextureStream', 'bBudgetMode', 'true')
edit(R + '/profiles/foxnne-nsfw/skyrim.ini', 'Papyrus', 'fPostLoadUpdateTimeMS', '500')
edit(R + '/mods/Apocrypha Menu Framework/SKSE/Plugins/ApocryphaMenuFramework.ini', 'MCM', 'bLoadSkyUIScriptMenus', '0')

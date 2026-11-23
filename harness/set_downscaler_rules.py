"""Queue job: add or set folder rules in the Texture Downscaler ini (game and MO2 closed).
usage: python set_downscaler_rules.py TAG 'key=value' ['key=value' ...]   keys as in the [Folders] section, e.g. '\plants\=0'"""
import shutil, sys, time
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
P = 'C:/Modlists/NGVO 8.0 Beta/mods/Texture Downscaler/SKSE/Plugins/TextureDownscaler.ini'
shutil.copy2(P, P + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
t = open(P, 'rb').read().decode('utf-8', 'replace'); nl = '\r\n' if '\r\n' in t else '\n'; L = t.split(nl)
fi = [i for i, l in enumerate(L) if l.strip().lower() == '[folders]'][0]
for kv in sys.argv[2:]:
    k, v = kv.rsplit('=', 1); hit = [i for i, l in enumerate(L) if l.split('=')[0] == k]
    if hit: L[hit[0]] = k + '=' + v
    else: L.insert(fi + 1, k + '=' + v)       # first match wins in the plugin? put new rules at the top of the section
    print('set', k + '=' + v, flush=True)
open(P, 'wb').write(nl.join(L).encode('utf-8'))

"""Queue job: install the final 'foxnne - Snow Match' (jsons + one ESL plugin) over the settings-only copy and activate
the plugin at the end of the load order (it needs only to load after Tomato's PBR Landscapes.esp). Game and MO2 closed.
usage: python install_snow_final.py TAG"""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
SRC = 'C:/Users/foxnn/dev/snow-audit/out/final/foxnne - Snow Match'; DST = 'C:/Modlists/NGVO 8.0 Beta/mods/foxnne - Snow Match'
if not os.path.isdir(DST): sys.exit('settings-only snow mod is not installed yet')
n = 0
for r, _, fs in os.walk(SRC):
    for f in fs:
        if f.lower().endswith('.md'): continue
        rel = os.path.relpath(os.path.join(r, f), SRC); d = os.path.join(DST, rel); os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(r, f), d); n += 1
print('copied', n, 'files', flush=True)
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, 'add_plugin.py'), 'snowfinal', 'foxnne - Snow Match.esp']))

"""Queue job: install Seamless Fast Travel from the extracted archive (game and MO2 closed), free look and forced clear weather off."""
import os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
src = sys.argv[1]; name = 'Sky Above - Seamless Fast Travel'; dst = 'C:/Modlists/NGVO 8.0 Beta/mods/' + name
if not os.path.isdir(dst): shutil.copytree(src, dst)
ini = dst + '/SKSE/Plugins/SeamlessFastTravel.ini'; t = open(ini, encoding='utf-8').read()
for k in ('bFreeLook', 'bClearWeather'): t = re.sub(r'(?m)^%s=.*$' % k, k + '=0.000000', t)
open(ini, 'w', encoding='utf-8').write(t)
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, 'enable_mod.py'), name]))

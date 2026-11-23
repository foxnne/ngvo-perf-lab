"""Queue job: set the Texture Downscaler cap for mountain normal maps (game and MO2 closed).
usage: python set_downscaler.py TAG VALUE   (0 = no cap, 2048 = the cap used before 2026-11-19)"""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
P = 'C:/Modlists/NGVO 8.0 Beta/mods/Texture Downscaler/SKSE/Plugins/TextureDownscaler.ini'; val = sys.argv[2]
shutil.copy2(P, P + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
t = open(P, 'rb').read().decode('utf-8', 'replace'); key = 'Normal:' + chr(92) + 'landscape' + chr(92) + 'mountains' + chr(92) + '='
lines = t.split('\n'); hit = [i for i, l in enumerate(lines) if l.startswith(key)]
if len(hit) != 1: sys.exit('mountain normal line not found')
cr = '\r' if lines[hit[0]].endswith('\r') else ''; lines[hit[0]] = key + val + cr
open(P, 'wb').write('\n'.join(lines).encode('utf-8')); print('set', key + val, flush=True)

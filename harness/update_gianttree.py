"""Queue job: replace the giant tree mod with the sidecar-mask version (no mesh) and enable it (game and MO2 closed)."""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
name = 'foxnne - Giant Tree Wind'; dst = 'C:/Modlists/NGVO 8.0 Beta/mods/' + name; src = 'C:/Users/foxnn/dev/giant-tree-wind/out/mod/' + name
if os.path.isdir(dst + '/Meshes'): shutil.rmtree(dst + '/Meshes')
shutil.copytree(src, dst, dirs_exist_ok=True)
for r, d, f in os.walk(dst): print(r, f)
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, 'enable_mod.py'), name]))

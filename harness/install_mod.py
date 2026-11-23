"""Queue job: install an extracted archive as an MO2 mod and enable it at the top (game and MO2 closed). usage: python install_mod.py TAG SRC_DIR "Mod Name" """
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
src, name = sys.argv[2], sys.argv[3]; dst = 'C:/Modlists/NGVO 8.0 Beta/mods/' + name
if not os.path.isdir(dst): shutil.copytree(src, dst)
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, 'enable_mod.py'), name]))

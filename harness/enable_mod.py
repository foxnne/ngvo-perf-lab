"""Queue job: enable an MO2 mod at the top of the foxnne-nsfw modlist (game and MO2 closed). usage: python enable_mod.py "Mod Folder Name" """
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
name = sys.argv[1]; P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/modlist.txt'
if not os.path.isdir('C:/Modlists/NGVO 8.0 Beta/mods/' + name): sys.exit('no such mod folder')
shutil.copy2(P, P + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
raw = open(P, 'rb').read(); nl = '\r\n' if b'\r\n' in raw else '\n'; L = raw.decode('utf-8-sig').split(nl)
L = [l for l in L if l[1:] != name]; L.insert(1 if L[0].startswith('#') else 0, '+' + name)
open(P, 'wb').write(nl.join(L).encode()); print('enabled at top:', name)

"""Queue job: disable an MO2 mod in the foxnne-nsfw modlist (game and MO2 closed). usage: python disable_mod.py TAG "Mod Folder Name" """
import shutil, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
name = sys.argv[2]; P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/modlist.txt'
shutil.copy2(P, P + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
raw = open(P, 'rb').read(); nl = '\r\n' if b'\r\n' in raw else '\n'; L = raw.decode('utf-8-sig').split(nl)
n = 0
for i, l in enumerate(L):
    if l == '+' + name: L[i] = '-' + name; n += 1
open(P, 'wb').write(nl.join(L).encode()); print('disabled' if n else 'not found enabled', name)

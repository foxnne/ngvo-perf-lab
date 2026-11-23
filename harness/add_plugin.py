"""Queue job: activate a plugin at the end of plugins.txt and loadorder.txt (game and MO2 closed). usage: python add_plugin.py TAG Plugin.esp"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
name = sys.argv[2]; P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/'
for f, line in (('plugins.txt', '*' + name), ('loadorder.txt', name)):
    p = P + f; shutil.copy2(p, p + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
    raw = open(p, 'rb').read(); nl = '\r\n' if b'\r\n' in raw else '\n'; L = [l for l in raw.decode('utf-8-sig').split(nl) if l.strip()]
    if not any(l.lstrip('*').lower() == name.lower() for l in L): L.append(line)
    open(p, 'wb').write((nl.join(L) + nl).encode('utf-8')); print(f, 'ok')

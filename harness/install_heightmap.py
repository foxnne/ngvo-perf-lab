"""Installs the 16-bit Tamriel terrain height map as its own MO2 mod above 'Bottled Shaders - foxnne' (game and MO2 closed)."""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game is running')
if bench.mo2_running(): bench.close_mo2(); time.sleep(6)
ROOT = 'C:/Modlists/NGVO 8.0 Beta'; NAME = 'foxnne - Terrain Height Map 16-bit'
SRC = 'C:/Users/foxnn/dev/terrain-heightmap/mod'; DST = f'{ROOT}/mods/{NAME}'
ML = f'{ROOT}/profiles/foxnne-nsfw/modlist.txt'
if not os.path.isdir(DST): shutil.copytree(SRC, DST)
open(os.path.join(DST, 'meta.ini'), 'w').write('[General]\nmodid=0\nversion=1.0\ncomments=16-bit Tamriel height map for Terrain Shadows, built from this load order (ngvo terrain-heightmap). Replaces the 8-bit BC4 map shipped with Bottled Shaders.\n')
raw = open(ML, 'rb').read(); shutil.copy2(ML, ML + '.bak-pre-heightmap-20261118')
nl = b'\r\n' if b'\r\n' in raw else b'\n'; lines = raw.split(nl)
if any(l.strip() in (('+' + NAME).encode(), ('-' + NAME).encode()) for l in lines): print('already in modlist')
else:
    i = next(k for k, l in enumerate(lines) if l.strip() == b'+Bottled Shaders - foxnne')
    lines.insert(i, ('+' + NAME).encode())            # nearer the top = higher priority: wins the file conflict
    open(ML, 'wb').write(nl.join(lines)); print('inserted above Bottled Shaders - foxnne at line', i + 1)
print('installed', os.path.getsize(os.path.join(DST, 'textures/terrain/HeightMaps', os.listdir(os.path.join(DST, 'textures/terrain/HeightMaps'))[0])), 'bytes')

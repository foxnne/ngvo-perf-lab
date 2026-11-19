"""Swap the Tamriel terrain height map in the MO2 mod for another build (game and MO2 closed). usage: python install_heightmap_objects.py objects|landscape"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
NAME = 'Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds'
DST = 'C:/Modlists/NGVO 8.0 Beta/mods/foxnne - Terrain Height Map 16-bit/textures/terrain/HeightMaps/' + NAME
SRC = {'objects': 'C:/Users/foxnn/dev/terrain-heightmap/mod-objects/textures/terrain/HeightMaps/' + NAME,
       'landscape': 'C:/Users/foxnn/dev/terrain-heightmap/mod/textures/terrain/HeightMaps/' + NAME}[sys.argv[1]]
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
shutil.copy2(SRC, DST); print('installed', sys.argv[1], os.path.getsize(DST), time.strftime('%H:%M:%S'))

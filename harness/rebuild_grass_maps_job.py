"""Queue job (no game needed): rebuild the grass colour map and the grass level map from the grass cache that is
enabled now, into their staged mod folders under C:/Users/foxnn/dev. usage: python rebuild_grass_maps_job.py TAG"""
import os, subprocess, sys, time
G = 'C:/Users/foxnn/dev/grass-colour-map'; C = 'C:/Users/foxnn/dev/ground-cover'
for cwd, script in ((G, 'step1_survey.py'), (G, 'step2_types.py'), (G, 'step2b_table.py'), (G, 'step3_bake.py'), (C, 'bake_level_map.py')):
    t = time.time(); r = subprocess.run([sys.executable, script], cwd=cwd, capture_output=True, text=True)
    print('%s rc %d %.0f s\n%s' % (script, r.returncode, time.time() - t, (r.stdout + r.stderr)[-700:]), flush=True)
    if r.returncode: sys.exit(script + ' failed')
for p in (G + '/out/foxnne - Grass Colour Map/textures/GrassColour/GrassColourMaps/Tamriel.GrassColourMap.-57.-43.61.50.dds',
          C + '/out/foxnne - Ground Cover Level Map/textures/GrassColour/GrassColourMaps/Tamriel.GrassLevelMap.-57.-43.61.50.dds'):
    if not os.path.exists(p) or time.time() - os.path.getmtime(p) > 1800: sys.exit('not rebuilt: ' + p)
    print('ok', p, os.path.getsize(p), flush=True)

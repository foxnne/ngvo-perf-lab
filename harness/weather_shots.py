"""Shots of a list of weathers at given hours from the plains view. usage: python weather_shots.py TAG hour[,hour] weather [weather ...]"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; HOURS = [float(h) for h in sys.argv[2].split(',')]; WX = sys.argv[3:]
OUT = os.path.join(os.path.dirname(HERE), 'results', 'weather_shots', TAG); os.makedirs(OUT, exist_ok=True)
s = bench.state_()
if s['cell']['interior'] or s['cell']['editorID'] != 'WhiterunExterior04':
    bench.console('coc WhiterunExterior04'); time.sleep(45)
s = bench.state_()
if s['cell']['interior']: sys.exit('still indoors')
p = s['position']
try:
    for w in WX:
        for h in HOURS:
            cs.world(action='hour', value=h); cs.world(action='weather', name=w, instant=True, lock=True)
            for i, (yaw, pitch) in enumerate(((270, -3), (250, 22))):
                cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 700, 'pitch': -3 if i == 0 else -22, 'yaw': yaw, 'fov': 65})
                time.sleep(28 if i == 0 else 7); cs.world(action='hour', value=h); time.sleep(3)
                f = cs.shot('wx') or cs.shot('wx2'); d = os.path.join(OUT, '%s_h%02d_%s.png' % (w, int(h), 'land' if i == 0 else 'sky')); shutil.move(f, d); print(d, flush=True)
finally:
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    cs.world(action='weather', name='SunnyPF', instant=False, lock=False)

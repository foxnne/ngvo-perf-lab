"""Queue job: forest floor views in dense forest cells (FFF forest grass check). cow Tamriel x y, settle, hour 13 outside,
free camera at eye height on the player, two headings per cell. usage: python forest_views.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'forest', TAG); os.makedirs(OUT, exist_ok=True)
CELLS = [(4, -12), (2, -14), (5, -11)]
bench.launch(); bench.all_on()
try:
    for x, y in CELLS:
        bench.console('cow Tamriel %d %d' % (x, y)); time.sleep(10); bench.settle()
        cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(14)
        p = bench.state_()['position']
        for yaw in (0.0, 135.0):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 150.0, 'pitch': -12.0, 'yaw': yaw, 'fov': 75.0}); time.sleep(4)
            src = cs.shot('fv-%s-%d-%d-%d' % (TAG, x, y, int(yaw))); time.sleep(0.4)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'cell_%d_%d__yaw%03d.png' % (x, y, int(yaw)))); print('shot', x, y, yaw, flush=True)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

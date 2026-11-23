"""Shoot a saved view (views.json) at several hours. usage: python view_times.py VIEW TAG [hours...] [--weather SunnyPF]"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
a = [x for x in sys.argv[1:] if not x.startswith('--')]; V = json.load(open(os.path.join(HERE, 'views.json')))[a[0]]; TAG = a[1]
W = sys.argv[sys.argv.index('--weather') + 1] if '--weather' in sys.argv else 'SunnyPF'; a = [x for x in a if x != W]
hours = [float(h) for h in a[2:]] or [5.5, 6.5, 8, 10, 12, 14.5, 16.5, 17.5, 18.5, 19.25, 20.5, 23.5]
OUT = os.path.join(os.path.dirname(HERE), 'results', 'views', TAG); os.makedirs(OUT, exist_ok=True)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
p = bench.state_()['position']; w = V['player']
if abs(p['x'] - w['x']) > 300 or abs(p['y'] - w['y']) > 300:
    bench.console(V['travel'] if 'travel' in V else 'coc ' + V['cell']); time.sleep(V.get('settle_seconds', 30))
    for _ in range(10):
        s = bench.state_()
        if not s['cell']['interior']: break
        time.sleep(5)
    cs.world(action='teleport', x=w['x'], y=w['y'], z=w['z']); time.sleep(8)
p = bench.state_()['position']; c = V['camera']
if bench.state_()['cell']['interior']: sys.exit('indoors')
try:
    for h in hours:
        cs.world(action='weather', name=W, instant=True, lock=True); cs.world(action='hour', value=h)
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c['dx'], 'y': p['y'] + c['dy'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']})
        time.sleep(14); cs.world(action='hour', value=h); time.sleep(4)
        f = cs.shot('vt-%s' % TAG) or cs.shot('vt2-%s' % TAG); d = os.path.join(OUT, '%s_h%04d.png' % (sys.argv[1], round(h * 100))); shutil.move(f, d); print(d, flush=True)
finally:
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    s = bench.state_(); cs.world(action='weather', name=s['weather']['editorID'], instant=False, lock=False)

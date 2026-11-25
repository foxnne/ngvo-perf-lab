"""Cloud specimens: one bespoke cloud type per variant, set live on a clear weather (the scene pack does not drive SunnyPF),
shot at midday and at low sun from a raised plains camera. usage: python cloud_specimens.py TAG [name ...]
Variants: C:/Users/foxnn/dev/nat3-volclouds/draft/sweeps-storm/specimens.json  ({"name", "label", "set": PhysicalSky delta})"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, saved_fix
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'cloud_specimens', TAG); os.makedirs(OUT, exist_ok=True)
VARS = json.load(open('C:/Users/foxnn/dev/nat3-volclouds/draft/sweeps-storm/specimens.json'))
want = sys.argv[2:] or [v['name'] for v in VARS]
VIEWS = (('h13_west', 13.0, 270), ('h1815_east_lit', 18.25, 90), ('h1815_west_backlit', 18.25, 270))


def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        else: dst[k] = v


m = bench.menus()
if m.get('messageBoxOpen'): sys.exit('a message box is open in game')
s = bench.state_()
if s['cell']['interior']: sys.exit('indoors')
p = s['position']
try:
    for v in VARS:
        if v['name'] not in want: continue
        saved_fix.fix(); cs.call('communityshaders.settings', {'action': 'load'}); time.sleep(2.5)
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); st = copy.deepcopy(g.get('settings', g)); merge(st, v.get('set', {}))
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': st})
        cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
        first = True
        for tag, hour, yaw in VIEWS:
            cs.world(action='hour', value=hour)
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 1500, 'pitch': -12, 'yaw': yaw, 'fov': 70})
            time.sleep(18 if first else 10); first = False; cs.world(action='hour', value=hour); time.sleep(2)
            f = cs.shot('sp') or cs.shot('sp2'); d = os.path.join(OUT, '%s_%s.png' % (v['name'], tag)); shutil.move(f, d); print(d, cs.stats(d)['mean'], flush=True)
finally:
    saved_fix.fix(); cs.call('communityshaders.settings', {'action': 'load'})
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    cs.world(action='weather', name='SunnyPF', instant=False, lock=False); cs.world(action='hour', value=13.0)

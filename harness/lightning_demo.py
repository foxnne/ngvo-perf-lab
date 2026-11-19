"""Hold a storm on the Whiterun view with Physical Sky lightning turned up, for live viewing, and grab frames.
usage: python lightning_demo.py [hour] [intensity] [rate_per_min]   output: results/lightning_demo/"""
import copy, json, os, shutil, sys, time, atexit
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
HOUR = float(sys.argv[1]) if len(sys.argv) > 1 else 20.5; RATE = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
OUT = os.path.join(os.path.dirname(HERE), 'results', 'lightning_demo'); os.makedirs(OUT, exist_ok=True)
V = json.load(open(os.path.join(HERE, 'views.json')))['plains_west']
T = [t for t in json.load(open(os.path.join(HERE, 'sweeps', 'sky_types.json'))) if 'thunderstorm' in t['name']][0]
def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), list) and set(v) <= set('xyzw'):
            for a, i in zip('xyzw', range(4)):
                if a in v and i < len(dst[k]): dst[k][i] = v[a]
        elif isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        else: dst[k] = v
bench.launch(save='harness_view_plains_west'); DONE = []
atexit.register(lambda: (not DONE) and bench.running() and bench.quit_game())
bench.console('tgm'); bench.all_on()
if bench.LOADED_SAVE != 'harness_view_plains_west': bench.goto(V['cell']); cs.world(action='teleport', **V['player']); time.sleep(12)
p = bench.state_()['position']; c = V['camera']
cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + c['dz'], 'pitch': -8.0, 'yaw': c['yaw'], 'fov': 75.0})
cs.world(action='timescale', value=1); cs.world(action='hour', value=HOUR); cs.world(action='weather', name=T['weather'], instant=True, lock=True); time.sleep(8)
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); orig = g.get('settings', g)
def opt(n, d=None): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
DIST = [float(x) for x in opt('--dist').split(',')] if opt('--dist') else None      # min,max strike distance in km
HAZE = float(opt('--haze')) if opt('--haze') else None                              # multiplier on the storm's haze
FOG = float(opt('--fog')) if opt('--fog') else None                                 # height fog strength
FOG_ORIG = []
LEVELS = [float(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else ['0.05', '0.15', '0.4'])]
for INT in LEVELS:                                    # each level is held for about a minute so it can be watched live
    s = copy.deepcopy(orig); merge(s, T['set']); s['lightningIntensity'] = INT; s.setdefault('lightning', {})['rate'] = RATE
    if DIST: s['lightning']['distanceRange'] = DIST
    if HAZE is not None:
        for k in ('aerosolScatter', 'aerosolAbsorption'): s[k] = [x * HAZE for x in s[k]]
    if FOG is not None:
        f = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'ExponentialHeightFog'}); f = f.get('settings', f); FOG_ORIG.append(copy.deepcopy(f)) if not FOG_ORIG else None; f['vanillaFogStrength'] = FOG; cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'ExponentialHeightFog', 'settings': f})
    print('intensity', INT, 'applied', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s}).get('applied'), flush=True)
    time.sleep(10); base = 0
    for i in range(22):                               # a flash lasts a fraction of a second: most frames miss it
        src = cs.shot(f'lightning-{INT:g}-{i:02d}'); time.sleep(0.4); st = cs.stats(src); dst = os.path.join(OUT, f'storm_h{HOUR:g}_i{INT:g}_{i:02d}.png')
        shutil.move(src, dst); print(INT, i, round(st['mean'], 3), flush=True); time.sleep(1.6)
        base = base if i else st['mean']
        if i not in (0, 11, 21) and st['mean'] < base * 1.15: os.remove(dst)   # keep only flashes and three plain frames per level
cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': orig})
if FOG_ORIG: cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'ExponentialHeightFog', 'settings': FOG_ORIG[0]})
cs.world(action='weather', name='SunnyPF', instant=True, lock=False)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); DONE.append(1); bench.finish()

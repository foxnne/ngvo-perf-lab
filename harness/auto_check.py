"""Queue job: does auto exposure work when it is set ONCE and left alone (no per-shot settings writes)?
Sets Histogram Auto Exposure to a free range with no compensation, then for each view: travel, wait, and shoot
at 5 s, 15 s and 30 s. Restores the live Post Processing settings at the end (nothing saved).
usage: python auto_check.py TAG [view ...]   Output results/sky_sweep/TAG/<view>__<t>s.png"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
FLAGS = [a for a in sys.argv[2:] if a.startswith('--')]; TAG = sys.argv[1]; VIEWS = [a for a in sys.argv[2:] if not a.startswith('--')] or ['plains_west', 'inn_bannered_mare']
OUT = os.path.join(os.path.dirname(HERE), 'results', 'sky_sweep', TAG); os.makedirs(OUT, exist_ok=True)
V = json.load(open(os.path.join(HERE, 'views.json')))
bench.launch(); bench.all_on()
get = lambda: (lambda g: g.get('settings', g))(cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PostProcessing'}))
orig = get(); pp = copy.deepcopy(orig)
NR0 = None
if '--nr-off' in FLAGS:
    g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'NeuralRendering'}); NR0 = g.get('settings', g); n = copy.deepcopy(NR0); n['enabled'] = False
    print('nr off', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': n}).get('applied'), flush=True)
h = pp['Histogram Auto Exposure'].setdefault('settings', {})
r = [-10.0, 18.0]
h.update({'AdaptationRange': r, 'NightAdaptationRange': r, 'InteriorAdaptationRange': r, 'ExposureCompensation': 0.0,
          'NightExposureCompensation': 0.0, 'InteriorExposureCompensation': 0.0, 'BrightSceneCompression': 0.0, 'AdaptSpeed': 1.5})
HAE = [a.split('=', 1)[1] for a in FLAGS if a.startswith('--hae=')]
if HAE: h.update(json.load(open(HAE[0])))
HOURS = [float(a.split('=', 1)[1]) for a in FLAGS if a.startswith('--hour=')] or [13.0]
for st in ('LUT', 'Look Grade'): pp[st]['enabled'] = False
print('set', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PostProcessing', 'settings': pp}).get('applied'), flush=True)
try:
    for vn in VIEWS:
        v = V[vn]; bench.goto(v['cell'])
        if v.get('player'): cs.world(action='teleport', **v['player'])
        time.sleep(v.get('settle_seconds', 12))
        if 'Interior' not in vn and 'inn' not in vn and 'dungeon' not in vn:
            cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=HOURS[0])
        p = bench.state_()['position']; c = v['camera']
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c['dx'], 'y': p['y'] + c['dy'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']})
        t0 = time.time()
        for t in (5, 15, 30):
            time.sleep(max(0, t - (time.time() - t0)))
            src = cs.shot('auto-%s-%s-%d' % (TAG, vn, t)); time.sleep(0.5)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, '%s__%02ds.png' % (vn, t)))
            try: ex = cs.call('communityshaders.inspect', {'kind': 'exposure'})
            except Exception as e: ex = {'error': str(e)[:80]}
            print(vn, t, 's', json.dumps(ex), flush=True)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PostProcessing', 'settings': orig})
    if NR0 is not None: cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': NR0})
    try: cs.world(action='weather', name='SunnyPF', instant=True, lock=False)
    except Exception: pass
bench.finish()

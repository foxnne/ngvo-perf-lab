"""Queue job: Light Shafts quality vs GPU cost. Riverwood forest floor at 16:30 (low sun through the trees), clear.
For Quality 0-3: set live, wait, read the profiler's LightShafts passes, shoot. Restores the setting (nothing saved).
usage: python lightshaft_q.py TAG   Output results/sky_sweep/TAG/q<N>.png + cost printed"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'sky_sweep', TAG); os.makedirs(OUT, exist_ok=True)
V = json.load(open(os.path.join(HERE, 'views.json')))['riverwood_floor']
def get(short): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return g.get('settings', g)
def put(short, s): return cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
bench.launch(); bench.all_on(); bench.goto(V['cell']); time.sleep(V.get('settle_seconds', 12))
cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='timescale', value=1); cs.world(action='hour', value=16.5); time.sleep(10)
p = bench.state_()['position']; c = V['camera']
cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c['dx'], 'y': p['y'] + c['dy'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': 250.0, 'fov': c['fov']})
LS0 = get('LightShafts'); res = {}
try:
    for q, k in ((0, None), (1, None), (2, None), (3, None), (2, 0.2), (2, 0.1)):
        s = copy.deepcopy(LS0); s['Quality'] = q
        if k is not None: s['SunStrength'] = k
        q = '%d%s' % (q, '' if k is None else '_sun%.2f' % k); put('LightShafts', s); time.sleep(6)
        prof = cs.call('communityshaders.inspect', {'kind': 'profiler', 'filter': 'LightShaft'})
        passes = [(x.get('name'), x.get('gpuAvgMs')) for x in prof.get('passes', [])]
        res[q] = {'gpuMs': round(sum(v or 0 for _, v in passes), 3), 'frameMs': (prof.get('frame') or {}).get('avgMs'), 'passes': passes}
        src = cs.shot('lsq-%s-%s' % (TAG, q)); time.sleep(0.5)
        if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'q%s.png' % q))
        print('quality', q, json.dumps(res[q]), flush=True)
finally:
    put('LightShafts', LS0)
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=True, lock=False)
    except Exception: pass
json.dump(res, open(os.path.join(OUT, 'cost.json'), 'w'), indent=1)
bench.finish()

"""Queue job: outdoor haze from bloom? Whiterun plains (plains_west pose) + Rift aspens, 13:00 SunnyPF, free camera from views.json.
COD Bloom threshold/blend: 3.14/0.05 (old), 2.0/0.10, 1.0/0.15 (saved now). Live only. usage: python bloom_ext_ab.py TAG"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'bloom_ext', TAG); os.makedirs(OUT, exist_ok=True)
V = json.load(open(os.path.join(HERE, 'views.json'), encoding='utf-8'))
bench.launch(); bench.all_on()
PP0 = (lambda g: g.get('settings', g))(cs.feat('get', 'PostProcessing'))
VARS = [(3.14, 0.05), (2.0, 0.10), (1.0, 0.15)]
rep = []
try:
    for vn in ('plains_west', 'rift_aspens'):
        v = V[vn]
        if v.get('cell'): bench.goto(v['cell'])
        else: bench.console(v['travel']); time.sleep(8); bench.settle()
        if v.get('player'): cs.world(action='teleport', **v['player'])
        time.sleep(v.get('settle_seconds', 12))
        cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(15)
        p = bench.state_()['position']; c = v['camera']
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c.get('dx', 0), 'y': p['y'] + c.get('dy', 0), 'z': p['z'] + c.get('dz', 0), 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']}); time.sleep(4)
        for t, b in VARS:
            pp = copy.deepcopy(PP0); pp['COD Bloom'].setdefault('settings', {}).update(Threshold=t, BlendFactor=b); cs.feat('set', 'PostProcessing', pp); time.sleep(5)
            name = '%s__bloom_%.2f_%.2f' % (vn, t, b); src = cs.shot('bx-%s-%s' % (TAG, name)); time.sleep(0.3)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, name + '.png')); r = {'shot': name, 'stats': cs.stats(os.path.join(OUT, name + '.png'))}; rep.append(r); print(json.dumps(r), flush=True)
        cs.feat('set', 'PostProcessing', PP0)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.feat('set', 'PostProcessing', PP0); cs.world(action='weather', lock=False)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

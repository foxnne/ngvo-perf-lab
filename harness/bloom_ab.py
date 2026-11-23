"""Queue job: soft glow around interior lights. Bannered Mare + Dragonsreach (hour 13 set outside, Helios-safe), free camera.
Variants (live only): as is, COD Bloom threshold/blend 1.5/0.10 and 1.0/0.15, Physical Glare on (if the pipeline has it).
usage: python bloom_ab.py TAG"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [('inn', 'WhiterunBanneredMare', {'x': -80.0, 'y': 496.0, 'z': 68.3}, {'x': -80.0, 'y': 496.0, 'z': 253.3, 'pitch': 2.0, 'yaw': 183.0, 'fov': 75.0}),
          ('dragonsreach', 'WhiterunDragonsreach', {'x': -448.0, 'y': -128.0, 'z': -318.0}, {'x': -448.0, 'y': -128.0, 'z': -133.0, 'pitch': 2.0, 'yaw': 359.0, 'fov': 75.0})]
bench.launch(); bench.all_on()
getf = lambda s: (lambda g: g.get('settings', g))(cs.feat('get', s))
PP0 = getf('PostProcessing'); print('PP stages:', [k for k in PP0 if isinstance(PP0[k], dict)], flush=True)
glare = next((k for k in PP0 if 'Glare' in k), None)
def variant(name):
    pp = copy.deepcopy(PP0)
    if name.startswith('bloom'):
        _, t, b = name.split('_'); pp['COD Bloom'].setdefault('settings', {}).update(Threshold=float(t), BlendFactor=float(b))
    elif name == 'glare' and glare: pp[glare]['enabled'] = True
    return pp
VARS = ['as_is', 'bloom_1.5_0.10', 'bloom_1.0_0.15'] + (['glare'] if glare else [])
rep = []
try:
    bench.goto('WhiterunExterior04'); time.sleep(8); cs.world(action='weather', lock=False); cs.world(action='hour', value=13.0); time.sleep(8)
    for place, cell, tp, cam in PLACES:
        bench.goto(cell); time.sleep(10); cs.world(action='teleport', **tp); time.sleep(8)
        cs.world(action='freeze', on=True); time.sleep(1); cs.call('communityshaders.testbed', {'action': 'camera', **cam}); time.sleep(3)
        for v in VARS:
            if v != 'as_is': cs.feat('set', 'PostProcessing', variant(v))
            time.sleep(5); src = cs.shot('bloom-%s-%s-%s' % (TAG, place, v)); time.sleep(0.3); dst = os.path.join(OUT, '%s__%s.png' % (place, v))
            if src and os.path.exists(src): shutil.move(src, dst); r = {'place': place, 'variant': v, 'stats': cs.stats(dst)}; rep.append(r); print(json.dumps(r), flush=True)
            cs.feat('set', 'PostProcessing', PP0)
        cs.world(action='freeze', on=False)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.feat('set', 'PostProcessing', PP0); cs.world(action='freeze', on=False)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

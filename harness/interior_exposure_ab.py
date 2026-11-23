"""Queue job: interior exposure compensation, with my interior Scene Manager layer gone. Same cameras as interior_ab.
Per place: InteriorExposureCompensation -4.7 (saved), -3.7, -3.2, each after 10 s of adaptation; plus the live NR values.
Live only, restored at the end. usage: python interior_exposure_ab.py TAG   Output results/interior_ab/TAG/"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [('dragonsreach', 'WhiterunDragonsreach', {'x': -448.0, 'y': -128.0, 'z': -318.0}, {'x': -448.0, 'y': -128.0, 'z': -133.0, 'pitch': 2.0, 'yaw': 359.0, 'fov': 75.0}),
          ('inn', 'WhiterunBanneredMare', {'x': -80.0, 'y': 496.0, 'z': 68.3}, {'x': -80.0, 'y': 496.0, 'z': 253.3, 'pitch': 2.0, 'yaw': 183.0, 'fov': 75.0}),
          ('bleakfalls', 'BleakFallsBarrow01', {'x': -7411.0, 'y': 1082.0, 'z': 573.5}, {'x': -7411.0, 'y': 1082.0, 'z': 758.5, 'pitch': -4.0, 'yaw': 90.0, 'fov': 75.0})]
COMPS = [-4.7, -3.7, -3.2]
bench.launch(); bench.all_on()
getf = lambda s: (lambda g: g.get('settings', g))(cs.feat('get', s))
PP0 = getf('PostProcessing'); NR = getf('NeuralRendering')
report = {'nr_live': {k: NR.get(k) for k in NR if not isinstance(NR.get(k), dict)}, 'shots': []}
print('NR live', report['nr_live'], flush=True)
def set_comp(v):
    pp = copy.deepcopy(PP0); pp['Histogram Auto Exposure'].setdefault('settings', {})['InteriorExposureCompensation'] = v
    return cs.feat('set', 'PostProcessing', pp).get('applied')
def snap(place, name):
    src = cs.shot('iexp-%s-%s-%s' % (TAG, place, name)); time.sleep(0.5)
    dst = os.path.join(OUT, '%s__%s.png' % (place, name))
    if src and os.path.exists(src):
        shutil.move(src, dst); e = cs.call('communityshaders.inspect', {'kind': 'exposure'})
        rec = {'place': place, 'variant': name, 'stats': cs.stats(dst), 'meteredEV100': e.get('meteredEV100'), 'preExposure': e.get('preExposure')}
        report['shots'].append(rec); print(json.dumps(rec), flush=True)
try:
    for place, cell, tp, cam in PLACES:
        bench.goto(cell); time.sleep(10)
        cs.world(action='teleport', **tp); time.sleep(8); cs.world(action='hour', value=13.0); time.sleep(4)
        cs.world(action='freeze', on=True); time.sleep(1)
        cs.call('communityshaders.testbed', {'action': 'camera', **cam}); time.sleep(3)
        for v in COMPS:
            print('comp', v, set_comp(v), flush=True); time.sleep(10); snap(place, 'comp%+.1f' % v)
        set_comp(PP0['Histogram Auto Exposure']['settings'].get('InteriorExposureCompensation', -4.7))
        cs.world(action='freeze', on=False)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.feat('set', 'PostProcessing', PP0)
    except Exception: pass
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump(report, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

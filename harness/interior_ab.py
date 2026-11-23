"""Queue job: what makes interiors look off (sepia, flat pale-blue chairs, smoky haze on walls)? Same camera as the lab's
Dragonsreach frame (and the Bannered Mare spawn turned around), one change per shot, live only (nothing saved):
as is, each suspect feature toggled off, and the Scene Manager interior layer neutralised (ambient/directional/IBL x1).
usage: python interior_ab.py TAG   Output results/interior_ab/TAG/<place>__<variant>.png + report.json"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [('dragonsreach', 'WhiterunDragonsreach', {'x': -448.0, 'y': -128.0, 'z': -318.0}, {'x': -448.0, 'y': -128.0, 'z': -133.0, 'pitch': 2.0, 'yaw': 359.0, 'fov': 75.0}),
          ('inn', 'WhiterunBanneredMare', {'x': -80.0, 'y': 496.0, 'z': 68.3}, {'x': -80.0, 'y': 496.0, 'z': 253.3, 'pitch': 2.0, 'yaw': 183.0, 'fov': 75.0}),
          ('bleakfalls', 'BleakFallsBarrow01', {'x': -7411.0, 'y': 1082.0, 'z': 573.5}, {'x': -7411.0, 'y': 1082.0, 'z': 758.5, 'pitch': -4.0, 'yaw': 90.0, 'fov': 75.0})]
bench.launch(); bench.all_on()
feats = cs.call('communityshaders.feature', {'action': 'list'}); feats = feats if isinstance(feats, list) else feats.get('features', [])
names = {f.get('shortName'): f for f in feats}
print('features:', sorted(n for n in names if n), flush=True)
SUSPECTS = [n for n in ('LightLimitFix', 'NeuralRendering', 'ScreenSpaceGI', 'LightShafts', 'VolumetricLighting', 'ImageBasedLighting', 'Skylighting',
                        'SubsurfaceScattering', 'ExponentialHeightFog', 'LinearLighting') if n in names and names[n].get('loaded')]
print('suspects loaded:', SUSPECTS, flush=True)
def get(short): g = cs.feat('get', short); return g.get('settings', g)
def toggle(short, on):
    r = cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': short, 'enabled': on}); time.sleep(3); return r
LAYER = [('LinearLighting', 'ambientMult'), ('LinearLighting', 'directionalLightMult'), ('ImageBasedLighting', 'EnvIBLScale')]
report = {'suspects': SUSPECTS, 'shots': []}
def snap(place, name):
    time.sleep(4)
    src = cs.shot('intab-%s-%s-%s' % (TAG, place, name)); time.sleep(0.5)
    dst = os.path.join(OUT, '%s__%s.png' % (place, name))
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst); report['shots'].append({'place': place, 'variant': name, **st}); print(place, name, st, flush=True)
try:
    for place, cell, tp, cam in PLACES:
        bench.goto(cell); time.sleep(10)
        cs.world(action='teleport', **tp); time.sleep(8); cs.world(action='hour', value=13.0); time.sleep(4)
        cs.world(action='freeze', on=True); time.sleep(1)
        cs.call('communityshaders.testbed', {'action': 'camera', **cam}); time.sleep(3)
        try: report.setdefault('exposure', {})[place] = cs.call('communityshaders.inspect', {'kind': 'exposure'})
        except Exception as e: report.setdefault('exposure', {})[place] = str(e)
        print(place, 'exposure', report['exposure'][place], flush=True)
        snap(place, '0_as_is')
        for k, short in enumerate(SUSPECTS, 1):
            toggle(short, False); snap(place, '%d_%s_off' % (k, short)); toggle(short, True)
        orig = {}
        for f, key in LAYER:
            s = get(f)
            if isinstance(s, dict) and key in s: orig[(f, key)] = s[key]; s = dict(s); s[key] = 1.0; cs.feat('set', f, s)
        time.sleep(2)
        report.setdefault('layer_readback', {})[place] = {'%s.%s' % k: (get(k[0]) or {}).get(k[1]) for k in orig}
        snap(place, '9_interior_layer_x1')
        for (f, key), v in orig.items():
            s = dict(get(f)); s[key] = v; cs.feat('set', f, s)
        cs.world(action='freeze', on=False)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    for short in SUSPECTS:
        try: toggle(short, True)
        except Exception: pass
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump(report, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

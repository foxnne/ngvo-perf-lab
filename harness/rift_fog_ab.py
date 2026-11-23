"""Queue job: which fog layer overwhelms Riften at sunrise/sunset? At the Rift lake, at 06:30 and 18:30 (region weather, not forced),
shoot: everything on, Ground Fog off, Volumetric Lighting exterior off, Exponential Height Fog off. Full settings are read and restored.
usage: python rift_fog_ab.py TAG   Output results/rift_fog-TAG.json (shot paths + weather per shot)"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; rep = []


def get(short):
    r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return r.get('settings', r)


def put(short, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})


VARIANTS = [('all_on', None, None), ('ground_fog_off', 'GroundFog', 'Enabled'), ('vol_lighting_off', 'VolumetricLighting', 'ExteriorEnabled'), ('height_fog_off', 'ExponentialHeightFog', 'enabled')]
bench.launch(); bench.all_on()
bench.console('fw 81a'); time.sleep(3)                      # SkyrimClear, then release so the region picks its own weather
bench.console('cow Tamriel 40 -24'); time.sleep(8); bench.settle()
for hour in (6.5, 18.5):
    bench.console('set gamehour to %s' % hour); time.sleep(30)
    for name, short, key in VARIANTS:
        orig = None
        if short:
            orig = get(short); off = dict(orig); off[key] = False if isinstance(orig[key], bool) else 0
            put(short, off); time.sleep(8)
        w = cs.world(action='state')
        rep.append(dict(hour=hour, variant=name, weather=w['weather']['editorID'], shot=cs.shot('riftfog-%s-h%s-%s' % (TAG, hour, name))))
        print(rep[-1], flush=True)
        if short: put(short, orig); time.sleep(5)
json.dump(rep, open(os.path.join(os.path.dirname(HERE), 'results', 'rift_fog-%s.json' % TAG), 'w'), indent=1)
if '--leave-open' in sys.argv:
    bench.console('set gamehour to 13'); print('left open for the user', flush=True)
else:
    bench.finish()

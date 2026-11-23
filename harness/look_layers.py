"""Queue job: which layer washes the image out? Fixed view on the Whiterun plains (yaw 250, fov 25 = the reference zoom shot, and fov 70),
13:00 SunnyPF, each layer switched off live one at a time (full settings read -> key changed -> set -> shot -> restored):
Volumetric Lighting exterior, Exponential Height Fog, View Atmosphere (aerial perspective), Local Exposure, COD Bloom, and all haze layers
together. For every shot: luminance p1/p50/p99 in the near, mid and far bands, written to results/look_layers/TAG/stats.json.
usage: python look_layers.py TAG"""
import json, os, shutil, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'look_layers', TAG); os.makedirs(OUT, exist_ok=True)


def get(short):
    r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return r.get('settings', r)


def put(short, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})


def stats(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255; Y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]; H = Y.shape[0]
    r = {}
    for name, sl in (('far', slice(int(H * .15), int(H * .45))), ('mid', slice(int(H * .5), int(H * .75))), ('near', slice(int(H * .75), H))):
        p = np.percentile(Y[sl], [1, 50, 99]); r[name] = dict(p1=round(float(p[0]), 3), p50=round(float(p[1]), 3), p99=round(float(p[2]), 3))
    return r


def pp_get():      # Post Processing stages live in one feature
    return get('PostProcessing')


bench.launch(); bench.all_on()
rep = {}; restore = []
try:
    bench.goto('WhiterunExterior04')
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(20)
    try:
        tb = get('TerrainBlending'); tb['Enabled'] = 1; put('TerrainBlending', tb)      # a previous test in this session may have left it off
    except Exception: pass
    p = bench.state_()['position']
    S = {k: get(k) for k in ('VolumetricLighting', 'ExponentialHeightFog', 'ViewAtmosphere')}
    PP = pp_get(); print('post processing keys:', list(PP.keys())[:30], flush=True)
    json.dump(dict(features=S, post=PP), open(os.path.join(OUT, 'settings_before.json'), 'w'), indent=1, default=str)

    def off(short, key, val=False):
        s = dict(S[short]); s[key] = val if not isinstance(S[short].get(key), (int, float)) or isinstance(S[short].get(key), bool) else type(S[short][key])(val)
        return (short, s)

    def pp_variant(path, val):
        d = json.loads(json.dumps(PP)); node = d
        for k in path[:-1]: node = node[k]
        node[path[-1]] = val; return ('PostProcessing', d)

    VAR = [('baseline', []),
           ('vol_lighting_off', [off('VolumetricLighting', 'ExteriorEnabled')]),
           ('vol_haze_0', [off('VolumetricLighting', 'ExteriorDayHaze', 0.0)]),
           ('height_fog_off', [off('ExponentialHeightFog', 'enabled', 0)]),
           ('aerial_exaggeration_1', [off('ViewAtmosphere', 'distanceExaggeration', 1.0)]),
           ('all_haze_off', [off('VolumetricLighting', 'ExteriorEnabled'), off('ExponentialHeightFog', 'enabled', 0), off('ViewAtmosphere', 'distanceExaggeration', 1.0)])]
    for name, path, val in (('local_exposure_off', ['Local Exposure', 'enabled'], False), ('local_exposure_strength_0', ['Local Exposure', 'settings', 'Strength'], 0.0),
                            ('bloom_off', ['COD Bloom', 'enabled'], False)):
        try: VAR.append((name, [pp_variant(path, val)]))
        except Exception as e: print('skip', name, e, flush=True)
    for fov, pitch in ((25.0, -2.0), (70.0, -5.0)):
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 250.0, 'pitch': pitch, 'yaw': 250.0, 'fov': fov}); time.sleep(7)
        for name, changes in VAR:
            for short, s in changes: put(short, s)
            time.sleep(7)
            src = cs.shot('ll-%s-%s-%d' % (TAG, name, int(fov))); time.sleep(0.4)
            dst = os.path.join(OUT, 'fov%02d__%s.png' % (int(fov), name))
            if src and os.path.exists(src): shutil.move(src, dst); rep['fov%02d__%s' % (int(fov), name)] = stats(dst); print(name, fov, rep['fov%02d__%s' % (int(fov), name)], flush=True)
            for short, _ in changes: put(short, PP if short == 'PostProcessing' else S[short])
            time.sleep(3)
finally:
    json.dump(rep, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1)
    try:
        for k, v in S.items(): put(k, v)
        put('PostProcessing', PP); cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

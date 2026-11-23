"""Queue job: measure the proposed realistic baseline (audit/lighting_settings_audit_20261122.md) live, in one game session.
Cumulative variants, each shot from fixed views with luminance stats per depth band:
 v0 current | v1 + Local Exposure off | v2 safe set (bloom blend 0.012, PsychoV highlights 1.0, SSGI Thickness 0.06, VL day haze 0.15)
 v3 + PsychoV contrast 1.25 | v4 + sun on surfaces 1.35, sky-fill saturation 0.85, cloud shadow remap [0, 0.75]
Views: Whiterun plains yaw 250 (fov 25 and 70) and the Ilinalta west reference view, 13:00 SunnyPF. Everything is restored at the end.
usage: python look_proposal.py TAG   Output results/look_proposal/TAG/ (shots, stats.json, applied.json = exact values per variant)"""
import copy, json, os, shutil, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'look_proposal', TAG); os.makedirs(OUT, exist_ok=True)
VIEWS = json.load(open(os.path.join(HERE, 'views.json')))


def get(short):
    r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return r.get('settings', r)


def put(short, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})


def stats(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255; Y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]; H = Y.shape[0]
    r = {}
    for name, sl in (('far', slice(int(H * .15), int(H * .45))), ('mid', slice(int(H * .5), int(H * .75))), ('near', slice(int(H * .75), H))):
        p = np.percentile(Y[sl], [1, 50, 99]); r[name] = dict(p1=round(float(p[0]), 3), p50=round(float(p[1]), 3), p99=round(float(p[2]), 3))
    return r


def setpath(d, path, val):
    node = d
    for k in path[:-1]: node = node[k]
    old = node.get(path[-1]) if isinstance(node, dict) else node[path[-1]]
    node[path[-1]] = val; return old


FEATS = ['PostProcessing', 'ScreenSpaceGI', 'VolumetricLighting', 'LinearLighting', 'ImageBasedLighting', 'PhysicalSky']
bench.launch(); bench.all_on()
ORIG = {}; rep = {}; applied = {}
try:
    for f in FEATS:
        try:
            s = get(f)
            if 'error' not in s: ORIG[f] = s
            else: print('feature not available:', f, s, flush=True)
        except Exception as e: print('feature read failed:', f, str(e)[:100], flush=True)
    json.dump(ORIG, open(os.path.join(OUT, 'settings_before.json'), 'w'), indent=1, default=str)
    CUR = copy.deepcopy(ORIG)

    def change(feat, path, val):
        if feat not in CUR: print('  skip (no feature)', feat, path, flush=True); return
        try:
            old = setpath(CUR[feat], path, val); print('  %s %s: %s -> %s' % (feat, '/'.join(map(str, path)), old, val), flush=True)
        except Exception as e: print('  skip (path)', feat, path, str(e)[:80], flush=True)

    def tm(idx, val):                       # PsychoV tonemapParams[0][idx]
        t = CUR['PostProcessing']['Color Grading and Tone Mapping']['settings']['tonemapParams']; old = t[0][idx]; t[0][idx] = val
        print('  tonemapParams[0][%d]: %s -> %s' % (idx, old, val), flush=True)

    STEPS = [
        ('v0_current', lambda: None),
        ('v1_local_exposure_off', lambda: change('PostProcessing', ['Local Exposure', 'enabled'], False)),
        ('v2_safe_set', lambda: (change('PostProcessing', ['COD Bloom', 'settings', 'BlendFactor'], 0.012), tm(1, 1.0),
                                 change('ScreenSpaceGI', ['Thickness'], 0.06), change('VolumetricLighting', ['ExteriorDayHaze'], 0.15))),
        ('v3_contrast_125', lambda: tm(3, 1.25)),
        ('v4_sun_fill_clouds', lambda: (change('LinearLighting', ['directionalLightMult'], 1.35), change('ImageBasedLighting', ['SkyIBLSaturation'], 0.85),
                                        change('PhysicalSky', ['cloudShadowRemapRange'], [0.0, 0.75]))),
    ]
    SITES = [('plains', 'WhiterunExterior04', None, [(250.0, 25.0, -2.0, 250.0), (250.0, 70.0, -5.0, 250.0)]),
             ('ilinalta', VIEWS['ilinalta_west']['cell'], VIEWS['ilinalta_west'], None)]
    for site, cell, view, cams in SITES:
        for f in ORIG: put(f, ORIG[f])
        CUR = copy.deepcopy(ORIG)
        bench.goto(cell)
        if view:
            pl = view['player']; bench.console('player.setpos x %s' % pl['x']); bench.console('player.setpos y %s' % pl['y']); bench.console('player.setpos z %s' % pl['z']); time.sleep(view.get('settle_seconds', 10))
        cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(20)
        p = bench.state_()['position']
        if view:
            c = view['camera']; cams = [(c['yaw'], c['fov'], c['pitch'], c['dz'])]
        for name, fn in STEPS:
            print(site, name, flush=True); fn()
            for f in CUR: put(f, CUR[f])
            applied[name] = copy.deepcopy({k: CUR[k] for k in CUR})
            time.sleep(12)                                   # let auto exposure settle
            for yaw, fov, pitch, dz in cams:
                cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + dz, 'pitch': pitch, 'yaw': yaw, 'fov': fov}); time.sleep(6)
                src = cs.shot('lp-%s-%s-%s-%d' % (TAG, site, name, int(fov))); time.sleep(0.4)
                key = '%s_fov%02d__%s' % (site, int(fov), name); dst = os.path.join(OUT, key + '.png')
                if src and os.path.exists(src): shutil.move(src, dst); rep[key] = stats(dst); print('   ', key, rep[key], flush=True)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    json.dump(rep, open(os.path.join(OUT, 'stats.json'), 'w'), indent=1)
    json.dump(applied, open(os.path.join(OUT, 'applied.json'), 'w'), indent=1, default=str)
    try:
        for f in ORIG: put(f, ORIG[f])
        cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

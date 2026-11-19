"""Apply the agreed sky base in a running game and save it to the user settings file through the bridge.
Base = the set behind the 2026-11-18 reference frames (cloud base 1200 m, 900 m thick, author tile, Continental haze 0.4,
sun x10, vanilla cloud layers off) + clear-leaning coverage (primary inMin 0.1) + high layer at 0.3, plus the
integration fixes on the other features. usage: python save_sky_base.py"""
import copy, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
v = json.load(open(os.path.join(HERE, 'sweeps', 'sunlit.json')))[0]
SET = copy.deepcopy(v['set']); FEAT = copy.deepcopy(v['features'])
SET['cloudLayer']['cirrus']['densityScale'] = 0.3
SET.setdefault('cloudMap', {}).setdefault('procedural', {}).setdefault('parameters', {}).setdefault('primary', {})['range'] = [0.1, 0.65, 0.0, 0.65]
SET['cloudMap']['localCloud'] = {'states': []}            # the terrain cloud map is not ready: keep it out of the base
def merge(dst, src):
    for k, val in src.items():
        if isinstance(val, dict) and isinstance(dst.get(k), dict): merge(dst[k], val)
        else: dst[k] = val
def get(short):
    g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return g.get('settings', g)
bench.launch(); bench.console('tgm'); bench.all_on()
s = get('PhysicalSky'); merge(s, SET)
s0 = copy.deepcopy(s); s0['aerosolType'] = 0
cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s0}); time.sleep(1.5)
print('sky', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s}).get('applied'), flush=True)
for short, ch in FEAT.items():
    f = get(short); merge(f, ch); print(short, cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': f}).get('applied'), flush=True)
time.sleep(6)
rb = get('PhysicalSky'); print('readback', {k: rb.get(k) for k in ('aerosolType', 'aerosolLoading', 'aerosolScatter', 'sunlightColor', 'enableVanillaClouds')}, rb['cloudLayer']['low'], rb['cloudLayer']['cirrus'].get('densityScale'), flush=True)
print('save', cs.call('communityshaders.settings', {'action': 'save'}), flush=True); time.sleep(8)
bench.quit_game()

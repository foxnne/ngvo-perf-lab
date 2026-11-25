"""40 fps candidates (user-approved 2026-11-24): measure each live change alone and together, forest + stables, 13:00 clear.
usage: python perf40.py TAG"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
TAG = sys.argv[1]; OUT = os.path.join(shots.ROOT, 'results', 'perf40', TAG); os.makedirs(OUT, exist_ok=True)
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings', g)
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
FEATS = ('PhysicalSky', 'ScreenSpaceReflections', 'ScreenSpaceGI', 'Upscaling'); BASE = {n: get(n) for n in FEATS}
CH = {'clouds': ('PhysicalSky', {'marchStepScale': 1.0, 'rayMarchRange': 24.0, 'cloudBlurRadius': 2, 'halfResApShadow': True}),
      'ssr64': ('ScreenSpaceReflections', {'SpecMaxSteps': 64}),
      'ssgiq': ('ScreenSpaceGI', {'HalfRes': False, 'QuarterRes': True}),
      'balanced': ('Upscaling', {'qualityMode': 2})}
VAR = [('base', []), ('clouds', ['clouds']), ('ssr64', ['ssr64']), ('ssgiq', ['ssgiq']), ('balanced', ['balanced']), ('three (no balanced)', ['clouds', 'ssr64', 'ssgiq']), ('all four', ['clouds', 'ssr64', 'ssgiq', 'balanced']), ('base again', [])]
def apply(keys):
    s = copy.deepcopy(BASE)
    for k in keys: s[CH[k][0]].update(CH[k][1])
    for n in FEATS: put(n, s[n])
rows = []
try:
    for place, where in (('forest', 'cow Tamriel -2 -14'), ('stables', 'coc WhiterunExterior01')):
        shots.tb(action='camera', mode='player'); bench.console(where); time.sleep(10); shots.ready(25, 150)
        cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); cs.world(action='timescale', value=1); time.sleep(10)
        for label, keys in VAR:
            apply(keys); time.sleep(26 if 'balanced' in keys or label.startswith('base') or 'all' in label else 22)
            pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']; rows.append((place, label, pr['avgMs'], pr['p95Ms'])); print('%-8s %-20s avg %.1f ms  p95 %.1f' % (place, label, pr['avgMs'], pr['p95Ms']), flush=True)
            if label in ('base', 'three (no balanced)', 'all four'):
                f = shots.grab('p4'); shutil.move(f, os.path.join(OUT, '%s_%s.png' % (place, label.split()[0])))
finally:
    for n in FEATS: put(n, BASE[n])
    cs.world(action='timescale', value=20); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w'))

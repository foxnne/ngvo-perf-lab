"""Distant grass thinning test: apply Grass Optimizations variants live (not saved), measure frame time and grass cost
from the player's own view, and shoot an oblique view from above plus a straight-down probe 3 cells ahead.
usage: python grass_thin.py TAG [travel command]"""
import copy, json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image
TAG = sys.argv[1]; tb = shots.tb; OUT = os.path.join(shots.ROOT, 'results', 'grass_thin', TAG); os.makedirs(OUT, exist_ok=True)
VAR = [('A_as_now', {}), ('B_drop_under_2px', {'MinPixelSize': 2.0}), ('C_min_density_25', {'MinDensity': 0.25}),
       ('D_both', {'MinPixelSize': 2.0, 'MinDensity': 0.25}), ('E_both_simpler_sooner', {'MinPixelSize': 2.0, 'MinDensity': 0.25, 'MidLODPixelSize': 6.0, 'FarLODPixelSize': 6.0, 'SimpleShadingPixelSize': 14.0}),
       ('F_strong', {'MinPixelSize': 3.0, 'MinDensity': 0.15, 'MidLODPixelSize': 8.0, 'FarLODPixelSize': 8.0, 'SimpleShadingPixelSize': 16.0}), ('A2_as_now_again', {})]
def get(): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'GrassOptimizations'}); return g.get('settings', g)
TRAVEL = [x for x in sys.argv[2:] if x != '--shots']
if TRAVEL:
    tb(action='camera', mode='player'); bench.console(' '.join(TRAVEL)); time.sleep(8); shots.ready(25, 150)
base = get(); cs.world(action='hour', value=13.0); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
tb(action='camera', mode='player'); time.sleep(2); p = tb(action='view_get')['player']; yw = math.radians(p['yaw']); rows = []
def measure():
    shots.ready(12, 150); time.sleep(9); f = []; g = []; d = []
    for _ in range(3):
        pr = cs.call('communityshaders.inspect', {'kind': 'profiler'}); dc = cs.call('communityshaders.inspect', {'kind': 'drawcalls'})
        f.append(pr['frame']['avgMs']); g.append(sum(x.get('gpuAvgMs', 0) for x in pr['passes'] if 'grass' in x.get('name', '').lower())); d.append(dc['shaders'].get('Grass', {}).get('drawCalls', 0)); time.sleep(2.5)
    return sum(f) / 3, sum(g) / 3, sum(d) / 3
try:
    for name, ch in VAR:
        s = copy.deepcopy(base); s.update(ch); cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'GrassOptimizations', 'settings': s})
        ms, gms, draws = measure(); rows.append((name, ms, gms, draws)); print('%-24s frame %.1f ms (%.1f fps)  grass passes %.2f ms  grass draws %.0f' % (name, ms, 1000 / ms, gms, draws), flush=True)
    if '--shots' in sys.argv:
        for name, ch in VAR[:-1]:
            s = copy.deepcopy(base); s.update(ch); cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'GrassOptimizations', 'settings': s})
            for tag, cam in (('oblique', dict(x=p['x'], y=p['y'], z=p['z'] + 4000, pitch=15, yaw=p['yaw'], fov=60)),
                             ('probe3', dict(x=p['x'] + math.sin(yw) * 12288, y=p['y'] + math.cos(yw) * 12288, z=p['z'] + 5000, pitch=88, yaw=p['yaw'], fov=50))):
                tb(action='camera', mode='override', **cam); shots.ready(6, 40); f = shots.grab('gt'); shutil.move(f, os.path.join(OUT, '%s_%s.png' % (name, tag)))
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'GrassOptimizations', 'settings': base})
    tb(action='camera', mode='player'); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w'))

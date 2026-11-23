"""Queue job: what makes the Rift hazy? rift_aspens view (views.json), 13:00 SunnyPF, free camera. One source off per shot (live):
as is, ViewAtmosphere off, ExponentialHeightFog off, GroundFog off, VolumetricLighting off, exaggeration 3. Reports distant contrast.
usage: python haze_ab.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
import numpy as np
from PIL import Image
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'haze', TAG); os.makedirs(OUT, exist_ok=True)
V = json.load(open(os.path.join(HERE, 'views.json'), encoding='utf-8'))
bench.launch(); bench.all_on()
def toggle(short, on): r = cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': short, 'enabled': on}); time.sleep(4); return r
rep = []
def snap(name):
    time.sleep(5); src = cs.shot('hz-%s-%s' % (TAG, name)); time.sleep(0.3); dst = os.path.join(OUT, name + '.png')
    if src and os.path.exists(src):
        shutil.move(src, dst); a = np.asarray(Image.open(dst).convert('L')).astype(float) / 255
        far = a[int(a.shape[0] * 0.30):int(a.shape[0] * 0.55), :]
        r = {'variant': name, 'far_mean': round(float(far.mean()), 3), 'far_contrast': round(float(far.std()), 3), 'p1': round(float(np.percentile(a, 1)), 3)}
        rep.append(r); print(json.dumps(r), flush=True)
try:
    v = V['rift_aspens']; bench.console(v['travel']); time.sleep(8); bench.settle()
    time.sleep(v.get('settle_seconds', 12)); cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(15)
    p = bench.state_()['position']; c = v['camera']
    cs.world(action='freeze', on=True); time.sleep(1)
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c.get('dx', 0), 'y': p['y'] + c.get('dy', 0), 'z': p['z'] + c.get('dz', 0), 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']}); time.sleep(4)
    snap('0_as_is')
    for k, short in enumerate(('ViewAtmosphere', 'ExponentialHeightFog', 'GroundFog', 'VolumetricLighting'), 1):
        toggle(short, False); snap('%d_%s_off' % (k, short)); toggle(short, True)
    g = cs.feat('get', 'ViewAtmosphere'); VA0 = g.get('settings', g)
    cs.feat('set', 'ViewAtmosphere', dict(VA0, distanceExaggeration=3.0)); snap('5_exaggeration_3'); cs.feat('set', 'ViewAtmosphere', VA0)
    print('exaggeration in this run', VA0.get('distanceExaggeration'), flush=True)
finally:
    for short in ('ViewAtmosphere', 'ExponentialHeightFog', 'GroundFog', 'VolumetricLighting'):
        try: toggle(short, True)
        except Exception: pass
    try: cs.world(action='freeze', on=False); cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

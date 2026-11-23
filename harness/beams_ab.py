"""Queue job: which Linear Lighting effect multiplier controls the Bleak Falls light-beam meshes, and does dimming them
remove the Neural Rendering hooks? Hour 13 set OUTSIDE (Helios), then enter; same free camera as interior_ab.
Variants (live only): as is, otherEffectMult / deferredEffectMult / projectedEffectMult / membraneEffectMult / effectLightingMult
at 0.4 one at a time, NR off. Full frame + beam crop. usage: python beams_ab.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
getf = lambda s: (lambda g: g.get('settings', g))(cs.feat('get', s))
LL0 = getf('LinearLighting'); NR0 = getf('NeuralRendering')
rep = []
def snap(name):
    time.sleep(5); src = cs.shot('beam-%s-%s' % (TAG, name)); time.sleep(0.3)
    dst = os.path.join(OUT, name + '.png')
    if src and os.path.exists(src):
        shutil.move(src, dst); Image.open(dst).crop((1700, 350, 2900, 1000)).save(os.path.join(OUT, name + '__crop.png'))
        r = {'variant': name, 'stats': cs.stats(dst)}; rep.append(r); print(json.dumps(r), flush=True)
try:
    bench.goto('WhiterunExterior04'); time.sleep(8); cs.world(action='weather', lock=False); cs.world(action='hour', value=13.0); time.sleep(8)
    bench.goto('BleakFallsBarrow01'); time.sleep(10); cs.world(action='teleport', x=-7411.0, y=1082.0, z=573.5); time.sleep(8)
    cs.world(action='freeze', on=True); time.sleep(1)
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': -7411.0, 'y': 1082.0, 'z': 758.5, 'pitch': -4.0, 'yaw': 90.0, 'fov': 75.0}); time.sleep(3)
    print('weather', cs.world(action='state').get('weather'), flush=True)
    snap('0_as_is')
    for k in ('otherEffectMult', 'deferredEffectMult', 'projectedEffectMult', 'membraneEffectMult', 'effectLightingMult'):
        s = dict(LL0); s[k] = 0.4; cs.feat('set', 'LinearLighting', s); snap('1_%s_0.4' % k); cs.feat('set', 'LinearLighting', LL0)
    n = dict(NR0); n['enabled'] = False; cs.feat('set', 'NeuralRendering', n); snap('2_nr_off'); cs.feat('set', 'NeuralRendering', NR0)
finally:
    try: cs.feat('set', 'LinearLighting', LL0); cs.feat('set', 'NeuralRendering', NR0)
    except Exception: pass
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump({'ll_live': LL0, 'shots': rep}, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

"""Queue job (needs the sky readout DLL): does an indoor hour change reset the sky root's north rotation, and does
re-applying it (Sky Sync ReassertSkyRotation) bring the Interior Sun window light back? Dragonsreach, player camera.
usage: python interior_sun_rotation.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
g = cs.feat('get', 'SkySync'); S0 = g.get('settings', g)
if 'ReassertSkyRotation' not in S0: sys.exit('this DLL has no ReassertSkyRotation setting')
rep = []
def snap(name, wait=6):
    time.sleep(wait); sky = cs.call('communityshaders.inspect', {'kind': 'sky'}); h = cs.world(action='state').get('gameHour')
    src = cs.shot('isr-%s-%s' % (TAG, name)); time.sleep(0.5); dst = os.path.join(OUT, name + '.png'); st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'gameHour': h, 'sky': sky, 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
try:
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0)
    snap('0_arrival', 10)
    cs.world(action='hour', value=13.0); snap('1_hour13')
    print('set', cs.feat('set', 'SkySync', dict(S0, ReassertSkyRotation=True)), flush=True); snap('2_reassert_on')
    cs.world(action='hour', value=16.0); snap('3_hour16_reassert_on')
    cs.world(action='console', command='set gamehour to 10'); snap('4_console_h10_reassert_on')
finally:
    try: cs.feat('set', 'SkySync', S0)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

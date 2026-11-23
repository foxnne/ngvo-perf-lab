"""Queue job: which harness step turns interior window lights off? Dragonsreach, shot + LLF light tally after each step:
arrive (coc), +teleport, +hour 13, +freeze, +free camera, then unfreeze with the free camera kept, then player camera.
usage: python freeze_lights_check.py TAG   Output results/interior_ab/TAG/"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
def step(name, wait=6):
    time.sleep(wait); t = cs.call('communityshaders.inspect', {'kind': 'lights'})
    win = [d for d in t.get('dropped', []) if 'Window' in d.get('name', '')]
    src = cs.shot('frz-%s-%s' % (TAG, name)); time.sleep(0.5); dst = os.path.join(OUT, name + '.png')
    st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'pushed': t.get('pushed'), 'droppedFaded': t.get('droppedFaded'), 'windowLightsDropped': len(win), 'stats': st}
    rep.append(r); print(json.dumps(r), flush=True)
try:
    bench.goto('WhiterunDragonsreach'); step('1_arrive', 12)
    cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); step('2_teleport', 8)
    cs.world(action='hour', value=13.0); step('3_hour13', 5)
    cs.world(action='freeze', on=True); step('4_freeze', 5)
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': -448.0, 'y': -128.0, 'z': -133.0, 'pitch': 2.0, 'yaw': 359.0, 'fov': 75.0}); step('5_free_camera', 4)
    cs.world(action='freeze', on=False); step('6_unfrozen_free_camera', 6)
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); step('7_player_camera', 5)
finally:
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

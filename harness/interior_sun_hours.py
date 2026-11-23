"""Queue job: does setting the hour kill Interior Sun window light, or is it just the sun angle? Dragonsreach, player camera.
Shot at arrival (its own hour), then hours 8, 10, 13, 16, 18, then back to the arrival hour; also via console 'set gamehour'.
usage: python interior_sun_hours.py TAG   Output results/interior_ab/TAG/"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
def snap(name, wait=6):
    time.sleep(wait); h = cs.world(action='state').get('gameHour')
    src = cs.shot('ish-%s-%s' % (TAG, name)); time.sleep(0.5); dst = os.path.join(OUT, name + '.png'); st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'gameHour': h, 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
try:
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0)
    snap('0_arrival', 10); h0 = rep[-1]['gameHour']
    for h in (8.0, 10.0, 13.0, 16.0, 18.0):
        cs.world(action='hour', value=h); snap('1_bridge_h%02d' % int(h))
    cs.world(action='hour', value=h0); snap('2_back_to_arrival')
    for h in (10.0, 13.0):
        cs.world(action='console', command='set gamehour to %g' % h); snap('3_console_h%02d' % int(h))
finally:
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

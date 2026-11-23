"""Queue job: after an indoor time jump, does the Dragonsreach window light come back by itself, and how fast?
Player camera. arrival, then bridge hour 13 and console 'set gamehour to 16', each followed by shots at 2/5/10/20/40/60 s.
usage: python interior_sun_recovery.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
def snap(name):
    h = cs.world(action='state').get('gameHour'); src = cs.shot('isrec-%s-%s' % (TAG, name)); time.sleep(0.3)
    dst = os.path.join(OUT, name + '.png'); st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'gameHour': h, 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
def series(prefix):
    t0 = time.time()
    for t in (2, 5, 10, 20, 40, 60):
        time.sleep(max(0, t - (time.time() - t0))); snap('%s_%02ds' % (prefix, t))
try:
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); time.sleep(10); snap('0_arrival')
    cs.world(action='hour', value=13.0); series('1_bridge_h13')
    cs.world(action='console', command='set gamehour to 16'); series('2_console_h16')
finally:
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

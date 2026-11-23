"""Queue job: is the Dragonsreach window light following the outside weather? Player camera. Records the current weather.
arrival -> hour 13 (weather free) -> lock SunnyPF -> hour 16 locked -> lock OvercastPF -> lock SunnyPF again.
usage: python interior_sun_weather.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
def snap(name, wait=8):
    time.sleep(wait); st0 = cs.world(action='state'); w = st0.get('weather'); h = st0.get('gameHour')
    src = cs.shot('isw-%s-%s' % (TAG, name)); time.sleep(0.3); dst = os.path.join(OUT, name + '.png'); st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'gameHour': h, 'weather': w, 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
try:
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); snap('0_arrival', 10)
    cs.world(action='hour', value=13.0); snap('1_hour13_free')
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); snap('2_sunny_locked')
    cs.world(action='hour', value=16.0); snap('3_hour16_sunny_locked')
    cs.world(action='weather', name='OvercastPF', instant=True, lock=True); snap('4_overcast_locked')
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); snap('5_sunny_again')
finally:
    try: cs.world(action='weather', lock=False)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

"""Queue job: is Sky Sync's time-jump transition what kills Interior Sun window light? Dragonsreach, player camera.
arrival -> hour 13 (bridge, with transition) -> Sky Sync off -> Sky Sync on -> hour 13 without transition (fresh coc first)
-> walk out to Whiterun and back in. Shot after each. usage: python interior_sun_skysync.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
def snap(name, wait=6):
    time.sleep(wait); h = cs.world(action='state').get('gameHour')
    src = cs.shot('iss-%s-%s' % (TAG, name)); time.sleep(0.5); dst = os.path.join(OUT, name + '.png'); st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'gameHour': h, 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
def arrive():
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0)
try:
    arrive(); snap('0_arrival', 10)
    cs.world(action='hour', value=13.0); snap('1_hour13_transition')
    print(cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'SkySync', 'enabled': False}), flush=True); snap('2_skysync_off')
    print(cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'SkySync', 'enabled': True}), flush=True); snap('3_skysync_on')
    bench.goto('WhiterunExterior04'); time.sleep(10); arrive(); snap('4_out_and_back_in', 10)
    cs.world(action='hour', value=15.0, transition=False); snap('5_hour15_no_transition')
finally:
    try: cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'SkySync', 'enabled': True})
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

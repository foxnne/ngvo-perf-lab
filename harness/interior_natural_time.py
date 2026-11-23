"""Queue job: does Helios keep interior window light right when time passes naturally inside (like waiting)?
Hour 9 set outside, enter Dragonsreach, then timescale 1500 (about 25 game min per real s) with a shot + weather readback
every ~10 real seconds for ~6 game hours; timescale restored. usage: python interior_natural_time.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
def snap(name):
    st0 = cs.world(action='state'); src = cs.shot('int-%s-%s' % (TAG, name)); time.sleep(0.3)
    dst = os.path.join(OUT, name + '.png'); st = None
    if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
    r = {'step': name, 'gameHour': st0.get('gameHour'), 'weather': (st0.get('weather') or {}).get('editorID'), 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
try:
    bench.goto('WhiterunExterior04'); time.sleep(8); cs.world(action='weather', lock=False); cs.world(action='hour', value=9.0); time.sleep(8)
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); time.sleep(10); snap('00_enter_h9')
    cs.world(action='timescale', value=1500)
    try: rep.append({'step':'lights','tally':cs.call('communityshaders.inspect', {'kind': 'lights'}).get('localShadowCacheActive')})
    except Exception: pass
    for i in range(1, 16):
        time.sleep(10); snap('%02d_natural' % i)
        if (rep[-1].get('gameHour') or 0) > 20.5: break
finally:
    try: cs.world(action='timescale', value=20)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'steps.json'), 'w'), indent=1)
bench.finish()

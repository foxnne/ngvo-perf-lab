"""Queue job (needs the foxnne/llf-shadowless-spots DLL): what does Light Limit Fix do with each interior light, and do the
window/sunbeam spots come back when shadowless spots are kept? Per place: tally + shot as is, then KeepShadowlessSpots on.
usage: python light_tally_ab.py TAG   Output results/interior_ab/TAG/<place>__<variant>.png + tally.json"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [('dragonsreach', 'WhiterunDragonsreach', {'x': -448.0, 'y': -128.0, 'z': -318.0}, {'x': -448.0, 'y': -128.0, 'z': -133.0, 'pitch': 2.0, 'yaw': 359.0, 'fov': 75.0}),
          ('bleakfalls', 'BleakFallsBarrow01', {'x': -7411.0, 'y': 1082.0, 'z': 573.5}, {'x': -7411.0, 'y': 1082.0, 'z': 758.5, 'pitch': -4.0, 'yaw': 90.0, 'fov': 75.0}),
          ('inn', 'WhiterunBanneredMare', {'x': -80.0, 'y': 496.0, 'z': 68.3}, {'x': -80.0, 'y': 496.0, 'z': 253.3, 'pitch': 2.0, 'yaw': 183.0, 'fov': 75.0})]
bench.launch(); bench.all_on()
g = cs.feat('get', 'LightLimitFix'); S0 = g.get('settings', g)
if 'IgnoreLightLODDimmer' not in S0: sys.exit('this DLL has no KeepShadowlessSpots setting')
report = {}
def tally(): return cs.call('communityshaders.inspect', {'kind': 'lights'})
def snap(place, name):
    time.sleep(5); t = tally(); report.setdefault(place, {})[name] = {'tally': t}
    src = cs.shot('tally-%s-%s-%s' % (TAG, place, name)); time.sleep(0.5)
    dst = os.path.join(OUT, '%s__%s.png' % (place, name))
    if src and os.path.exists(src): shutil.move(src, dst); report[place][name]['stats'] = cs.stats(dst)
    print(place, name, json.dumps(report[place][name]), flush=True)
try:
    for place, cell, tp, cam in PLACES:
        bench.goto(cell); time.sleep(10)
        cs.world(action='teleport', **tp); time.sleep(8); cs.world(action='hour', value=13.0); time.sleep(4)
        cs.world(action='freeze', on=True); time.sleep(1)
        cs.call('communityshaders.testbed', {'action': 'camera', **cam}); time.sleep(3)
        snap(place, 'a_as_is')
        print('set', cs.feat('set', 'LightLimitFix', dict(S0, KeepShadowlessSpots=True)), flush=True); snap(place, 'b_keep_shadowless_spots')
        print('set', cs.feat('set', 'LightLimitFix', dict(S0, IgnoreLightLODDimmer=True)), flush=True); snap(place, 'c_ignore_lod_dimmer')
        cs.feat('set', 'LightLimitFix', S0)
        cs.world(action='freeze', on=False)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.feat('set', 'LightLimitFix', S0)
    except Exception: pass
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump(report, open(os.path.join(OUT, 'tally.json'), 'w'), indent=1)
bench.finish()

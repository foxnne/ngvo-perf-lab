"""Queue job: are Light Limit Fix local shadows blocking shadow-casting lights (window lights) indoors?
Dragonsreach + Bleak Falls, same cameras as interior_ab: as is, EnableLocalShadows off, LLF off. Live only.
usage: python llf_shadow_ab.py TAG   Output results/interior_ab/TAG/<place>__<variant>.png + llf_settings.json"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [('dragonsreach', 'WhiterunDragonsreach', {'x': -448.0, 'y': -128.0, 'z': -318.0}, {'x': -448.0, 'y': -128.0, 'z': -133.0, 'pitch': 2.0, 'yaw': 359.0, 'fov': 75.0}),
          ('bleakfalls', 'BleakFallsBarrow01', {'x': -7411.0, 'y': 1082.0, 'z': 573.5}, {'x': -7411.0, 'y': 1082.0, 'z': 758.5, 'pitch': -4.0, 'yaw': 90.0, 'fov': 75.0})]
bench.launch(); bench.all_on()
g = cs.feat('get', 'LightLimitFix'); S0 = g.get('settings', g)
json.dump(S0, open(os.path.join(OUT, 'llf_settings.json'), 'w'), indent=1); print('LLF settings', json.dumps(S0)[:1500], flush=True)
def snap(place, name):
    time.sleep(5); src = cs.shot('llf-%s-%s-%s' % (TAG, place, name)); time.sleep(0.5)
    dst = os.path.join(OUT, '%s__%s.png' % (place, name))
    if src and os.path.exists(src): shutil.move(src, dst); print(place, name, cs.stats(dst), flush=True)
try:
    for place, cell, tp, cam in PLACES:
        bench.goto(cell); time.sleep(10)
        cs.world(action='teleport', **tp); time.sleep(8); cs.world(action='hour', value=13.0); time.sleep(4)
        cs.world(action='freeze', on=True); time.sleep(1)
        cs.call('communityshaders.testbed', {'action': 'camera', **cam}); time.sleep(3)
        snap(place, 'a_as_is')
        if 'EnableLocalShadows' in S0:
            print('set', cs.feat('set', 'LightLimitFix', dict(S0, EnableLocalShadows=not S0.get('EnableLocalShadows'))), flush=True); snap(place, 'b_local_shadows_flipped')
            cs.feat('set', 'LightLimitFix', S0)
        cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'LightLimitFix', 'enabled': False}); snap(place, 'c_llf_off')
        cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'LightLimitFix', 'enabled': True}); time.sleep(3)
        cs.world(action='freeze', on=False)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.feat('set', 'LightLimitFix', S0); cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'LightLimitFix', 'enabled': True})
    except Exception: pass
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

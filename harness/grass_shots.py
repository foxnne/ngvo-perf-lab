"""Queue job: individual full-resolution grass confirmation shots, one biome at a time (13:00, clear), eye height looking
slightly down, four directions each. The morning haze (type 1, loading 0.2) is set live for the shots and the saved
Physical Sky state restored afterwards (nothing is saved). Output results/grass_shots/TAG/<place>__<yaw>.png"""
import copy, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'grass_shots', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [('tundra_whiterun', 'coc WhiterunExterior04'), ('pine_forest_riverwood', 'coc Riverwood'), ('pine_forest_falkreath', 'cow Tamriel -5 -19'),
          ('rift_fall_forest', 'cow Tamriel 40 -24'), ('rift_fields', 'cow Tamriel 36 -20'), ('reach', 'cow Tamriel -36 2'),
          ('marsh', 'cow Tamriel -8 17'), ('volcanic_tundra', 'cow Tamriel 28 -2'), ('coast', 'cow Tamriel 8 26'), ('snow_edge', 'cow Tamriel 20 14')]
bench.launch(); bench.console('tgm'); bench.all_on()
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); orig = g.get('settings', g)
s = copy.deepcopy(orig); s.update({'aerosolLoading': 0.2, 'aerosolHumidity': 50.0}); s0 = copy.deepcopy(s); s0['aerosolType'] = 0; s['aerosolType'] = 1
cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s0}); time.sleep(1)
print('haze set', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s}).get('applied'), flush=True)
try:
    for label, cmd in PLACES:
        try:
            bench.console(cmd); time.sleep(8)
            if not bench.settle(): raise RuntimeError('did not settle')
            time.sleep(5)
        except Exception as e:
            print(label, 'failed', str(e)[:80], flush=True); continue
        cs.world(action='weather', name='SunnyTU', instant=True, lock=True); cs.world(action='timescale', value=1); cs.world(action='hour', value=13.0); time.sleep(12)
        p = bench.state_()['position']; n = 0
        for yaw in (0, 90, 180, 270):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 150, 'pitch': 14.0, 'yaw': float(yaw), 'fov': 70.0}); time.sleep(5)
            src = cs.shot('grass-%s-%s-%d' % (TAG, label, yaw)); time.sleep(1)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, '%s__%03d.png' % (label, yaw))); n += 1
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
        print(label, cmd, round(p['x']), round(p['y']), round(p['z']), n, 'shots', flush=True)
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': orig})
    try: bench.console('tgm')
    except Exception: pass
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

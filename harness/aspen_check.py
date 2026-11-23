"""Queue job: near vs LOD aspen colour check outside Riften (cow Tamriel 40 -24), 13:00 clear. Shots with the LOD crown
lighting as saved, with LODTreeBrightness 1.0, and with LODTreeLighting off. Output results/aspen_check/TAG/."""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'aspen_check', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.console('tgm'); bench.all_on()
bench.console('cow Tamriel 40 -24'); time.sleep(8); bench.settle(); time.sleep(5)
cs.world(action='weather', name='SunnyTU', instant=True, lock=True); cs.world(action='timescale', value=1); cs.world(action='hour', value=13.0); time.sleep(10)
p = bench.state_()['position']
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'TreeWind'}); orig = g.get('settings', g)
try:
    for name, ch in (('0_saved', {}), ('1_lod_brightness_1.0', {'LODTreeBrightness': 1.0}), ('2_lod_lighting_off', {'LODTreeLighting': False}), ('3_lod_brightness_1.0_variation_0', {'LODTreeBrightness': 1.0, 'LODTreeVariation': 0.0})):
        s = dict(orig); s.update(ch); cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'TreeWind', 'settings': s}); time.sleep(4)
        for yaw in (180, 270):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 200, 'pitch': -4.0, 'yaw': float(yaw), 'fov': 70.0}); time.sleep(4)
            src = cs.shot('aspen-%s-%s-%d' % (TAG, name, yaw)); time.sleep(1)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, '%s__%03d.png' % (name, yaw)))
        print(name, 'done', flush=True)
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'TreeWind', 'settings': orig})
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    try: bench.console('tgm')
    except Exception: pass
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

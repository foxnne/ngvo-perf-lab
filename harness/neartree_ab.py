"""Queue job: why do near trees look filmed/desaturated? Outside Riften (cow Tamriel 40 -24), 13:00 clear, level camera at
the trees. One feature switched per shot: Ground Cover off, Light Shafts off, Ground Fog off, SSGI off, Skylighting off,
Neural Rendering off. Morning haze set live (not saved). Output results/neartree_ab/TAG/."""
import copy, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'neartree_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.console('tgm'); bench.all_on()
def get(short):
    g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return g.get('settings', g)
def put(short, s): return cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
ps0 = get('PhysicalSky'); s = copy.deepcopy(ps0); s.update({'aerosolLoading': 0.2, 'aerosolHumidity': 50.0}); z = copy.deepcopy(s); z['aerosolType'] = 0; s['aerosolType'] = 1
put('PhysicalSky', z); time.sleep(1); put('PhysicalSky', s)
bench.console('cow Tamriel 40 -24'); time.sleep(8); bench.settle(); time.sleep(5)
cs.world(action='weather', name='SunnyTU', instant=True, lock=True); cs.world(action='timescale', value=1); cs.world(action='hour', value=13.0); time.sleep(12)
p = bench.state_()['position']
TESTS = [('0_now', None, None), ('1_ground_cover_off', 'GroundCover', {'Enabled': False}), ('2_light_shafts_off', 'LightShafts', {'Enabled': False}),
         ('3_ground_fog_off', 'GroundFog', {'Enabled': False}), ('4_ssgi_off', 'ScreenSpaceGI', {'Enabled': False}),
         ('5_skylighting_off', 'Skylighting', {'Enabled': False}), ('6_neural_rendering_off', 'NeuralRendering', {'enabled': False}),
         ('7_heavy_haze_as_saved', 'PhysicalSky', None)]
try:
    for name, short, ch in TESTS:
        o = None
        if name.startswith('7_'):
            put('PhysicalSky', ps0); time.sleep(3)
        elif short:
            o = get(short); n = copy.deepcopy(o); n.update(ch); print(name, put(short, n).get('applied'), flush=True); time.sleep(4)
        for yaw, pitch in ((0, 0.0), (180, 0.0), (270, 10.0)):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 180, 'pitch': pitch, 'yaw': float(yaw), 'fov': 65.0}); time.sleep(4)
            src = cs.shot('ntab-%s-%s-%d' % (TAG, name, yaw)); time.sleep(1)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, '%s__%03d.png' % (name, yaw)))
        if o is not None: put(short, o); time.sleep(2)
finally:
    put('PhysicalSky', ps0)
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    try: bench.console('tgm')
    except Exception: pass
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

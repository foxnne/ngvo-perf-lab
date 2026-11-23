"""Queue job: same-pose character close-ups under setting variants (pose frozen, light frozen).
usage: python face_ab.py TAG   -> results/face_ab/TAG/*.png + a labelled sheet"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'face_ab', TAG); os.makedirs(OUT, exist_ok=True)
VARIANTS = [('0_as_now', {}),
            ('1_lighting_thickness_0.1_as_before_today', {'ScreenSpaceGI': {'Thickness': 0.1}}),
            ('2_ground_fog_off', {'GroundFog': {'Enabled': False}}),
            ('3_thickness_0.1_and_ground_fog_off', {'ScreenSpaceGI': {'Thickness': 0.1}, 'GroundFog': {'Enabled': False}}),
            ('4_sky_light_full_colour_no_weather_ambient', {'ImageBasedLighting': {'SkyIBLSaturation': 1.0, 'EnvIBLSaturation': 1.0, 'DALCAmount': 0.0}}),
            ('5_haze_as_before_0.4_loading', {'PhysicalSky': {'aerosolScatter': [5.0442, 6.8378, 9.1504], 'aerosolAbsorption': [0.2654, 0.29312, 0.32081]}}),
            ('6_as_now_again', {})]
bench.launch(); bench.all_on(); bench.console('tgm'); bench.goto('WhiterunExterior04'); bench.exterior_setup()
cs.world(action='teleport', x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=0.0, rz=160.0); time.sleep(10)
cs.world(action='weather', name='SunnyPF', instant=True, lock=True); bench.console('set gamehour to 15'); time.sleep(6)
cs.world(action='timescale', value=0); cs.world(action='freeze', on=True); time.sleep(1)
shots = []
try:
    for framing, kw in (('bust', dict(distance=95.0, height=105.0, pitch=-2.0, fov=40.0)), ('body', dict(distance=230.0, height=85.0, pitch=-2.0, fov=45.0))):
        bench.face_camera(True, **kw); time.sleep(4)
        for name, change in VARIANTS:
            orig = {}
            for short, ch in change.items():
                g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); orig[short] = g.get('settings', g)
                s = copy.deepcopy(orig[short]); s.update(ch); cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
            time.sleep(8)
            src = cs.shot(f'faceab-{framing}-{name}'); time.sleep(1.0)
            dst = os.path.join(OUT, f'{framing}_{name}' + os.path.splitext(src)[1]); shutil.copy2(src, dst); shots.append(dst); print(dst, flush=True)
            for short, o in orig.items(): cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': o})
            time.sleep(2)
finally:
    try: bench.face_camera(False)
    except Exception: pass
    cs.world(action='freeze', on=False); cs.world(action='timescale', value=1)
    try: cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
    except Exception: pass
json.dump(shots, open(os.path.join(OUT, 'shots.json'), 'w'), indent=1)
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

"""Queue job: why do the player's hands look dark red / muddy? Free camera in front of the player looking back at
the hands, in the Bannered Mare and on the Whiterun plains at 13:00. One change per shot, live only (nothing saved):
as is, Neural Rendering skin colour strength 0.6 (its default), NR skin colour 0, NR off, Skin feature off.
usage: python hands_ab.py TAG   Output results/hands_ab/TAG/<place>__<variant>.png"""
import copy, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'hands_ab', TAG); os.makedirs(OUT, exist_ok=True)
def get(short): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return g.get('settings', g)
def put(short, s): return cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
bench.launch(); bench.all_on()
NR0 = get('NeuralRendering'); SK0 = get('Skin')
def nr(**skin):
    s = copy.deepcopy(NR0); s.setdefault('skinStrengths', {}).update(skin); return s
VARIANTS = [('0_as_is', None, None), ('1_nr_skin_colour_0.6', 'NeuralRendering', nr(colorStrength=0.6)),
            ('2_nr_skin_colour_0', 'NeuralRendering', nr(colorStrength=0.0)), ('3_nr_off', 'NeuralRendering', dict(NR0, enabled=False)),
            ('4_skin_feature_off', 'Skin', dict(SK0, EnableSkin=False))]
PLACES = [('inn', 'WhiterunBanneredMare', None), ('plains', 'WhiterunExterior04', {'x': 19157.0, 'y': -7419.0, 'z': -3612.0, 'rx': 0.0, 'rz': 160.0})]
try:
    for place, cell, tp in PLACES:
        bench.goto(cell)
        if tp: cs.world(action='teleport', **tp)
        time.sleep(12)
        if place != 'inn': cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0)
        st = bench.state_(); p = st['position']; h = (st.get('angleDeg') or {}).get('z', 0.0)
        cs.world(action='freeze', on=True); time.sleep(1)
        fx, fy = math.sin(math.radians(h)), math.cos(math.radians(h))
        for shortv, (name, short, s) in enumerate(VARIANTS):
            if short: print(name, put(short, s).get('applied'), flush=True)
            time.sleep(5)
            for k, (dist, dz, pitch) in enumerate(((95.0, 105.0, 28.0), (150.0, 120.0, 18.0))):
                cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + fx * dist, 'y': p['y'] + fy * dist, 'z': p['z'] + dz,
                                                    'pitch': pitch, 'yaw': (h + 180.0) % 360.0, 'fov': 45.0}); time.sleep(2.5)
                src = cs.shot('hands-%s-%s-%s-%d' % (TAG, place, name, k)); time.sleep(0.5)
                if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, '%s__%s__%d.png' % (place, name, k)))
            if short: put(short, NR0 if short == 'NeuralRendering' else SK0); time.sleep(2)
        cs.world(action='freeze', on=False)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
        print(place, 'done', flush=True)
finally:
    put('NeuralRendering', NR0); put('Skin', SK0)
    try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

"""Queue job: why is Dragonsreach slow? Hour 13 outside (Helios-safe), enter, player camera, slow turn in place.
12 s frame-time records: as is, LLF local-shadow cache off (live), NR off (reference), both back on. Also the light tally.
usage: python interior_perf_ab.py TAG   Output results/interior_perf/TAG/"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_perf', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
getf = lambda s: (lambda g: g.get('settings', g))(cs.feat('get', s))
LLF0 = getf('LightLimitFix'); NR0 = getf('NeuralRendering'); rep = {}
def turn(t): cs.call('input', {'action': 'tap', 'device': 'keyboard', 'key': 'Right'}) if False else None
def rec(name):
    time.sleep(4)
    try: tally = cs.call('communityshaders.inspect', {'kind': 'lights'})
    except Exception as e: tally = str(e)
    m = bench.record(os.path.join(OUT, name), 12)
    rep[name] = {'render': m.get('render'), 'presented': m.get('presented'), 'tally': {k: tally.get(k) for k in ('pushed', 'shadowLights', 'keptLocalShadow', 'localShadowCacheActive')} if isinstance(tally, dict) else tally}
    print(name, json.dumps(rep[name]), flush=True)
try:
    bench.goto('WhiterunExterior04'); time.sleep(8); cs.world(action='weather', lock=False); cs.world(action='hour', value=13.0); time.sleep(6)
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); time.sleep(10)
    print('weather', cs.world(action='state').get('weather'), flush=True)
    rec('0_as_is')
    cs.feat('set', 'LightLimitFix', dict(LLF0, EnableLocalShadows=False)); rec('1_local_shadows_off')
    cs.feat('set', 'LightLimitFix', LLF0); n = dict(NR0); n['enabled'] = False; cs.feat('set', 'NeuralRendering', n); rec('2_nr_off')
    cs.feat('set', 'LightLimitFix', dict(LLF0, EnableLocalShadows=False)); rec('3_nr_off_and_local_shadows_off')
finally:
    try: cs.feat('set', 'LightLimitFix', LLF0); cs.feat('set', 'NeuralRendering', NR0)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

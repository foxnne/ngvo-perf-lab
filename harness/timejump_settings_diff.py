"""Queue job: do live CS settings change when the hour jumps indoors (Scene Manager / baseline re-apply)?
Dragonsreach: dump live settings of key features + exposure readout on arrival, after a bridge hour jump, after a console
'set gamehour', and after a bridge settings no-op save; write the diffs. usage: python timejump_settings_diff.py TAG"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
FEATS = ['LinearLighting', 'LightLimitFix', 'ImageBasedLighting', 'Skylighting', 'ScreenSpaceGI', 'SkySync', 'PostProcessing', 'VolumetricLighting', 'LightShafts', 'InteriorSun']
bench.launch(); bench.all_on()
def dump():
    d = {}
    for f in FEATS:
        try: g = cs.feat('get', f); d[f] = g.get('settings', g)
        except Exception as e: d[f] = {'error': str(e)}
    d['_exposure'] = cs.call('communityshaders.inspect', {'kind': 'exposure'}); d['_hour'] = cs.world(action='state').get('gameHour')
    return d
def flat(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from flat(v, p + '/' + k)
    elif isinstance(o, list): yield p, json.dumps(o)
    else: yield p, o
snaps = {}
try:
    bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); time.sleep(10)
    snaps['0_arrival'] = dump()
    cs.world(action='hour', value=13.0); time.sleep(8); snaps['1_bridge_hour13'] = dump()
    cs.world(action='console', command='set gamehour to 16'); time.sleep(8); snaps['2_console_h16'] = dump()
    g = cs.feat('get', 'SkySync'); s = g.get('settings', g); cs.feat('set', 'SkySync', s); time.sleep(6); snaps['3_after_noop_set'] = dump()
finally:
    json.dump(snaps, open(os.path.join(OUT, 'snaps.json'), 'w'), indent=1)
    base = dict(flat({k: v for k, v in snaps.get('0_arrival', {}).items() if not k.startswith('_')}))
    for name, sn in snaps.items():
        if name == '0_arrival': continue
        cur = dict(flat({k: v for k, v in sn.items() if not k.startswith('_')}))
        diff = {k: (base.get(k), cur.get(k)) for k in set(base) | set(cur) if base.get(k) != cur.get(k)}
        print(name, 'changed keys:', len(diff), flush=True)
        for k, v in sorted(diff.items())[:40]: print('   ', k, v, flush=True)
    for name, sn in snaps.items(): print(name, 'hour', sn.get('_hour'), 'exposure', {k: sn.get('_exposure', {}).get(k) for k in ('compensationEV', 'meteredEV100', 'preExposure')}, flush=True)
bench.finish()

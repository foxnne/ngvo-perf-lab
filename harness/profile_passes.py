"""Queue job: per-pass GPU/CPU timings and draw calls at fixed poses, everything on. usage: python profile_passes.py TAG [scenes]"""
import json, os, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; SCENES = (sys.argv[2] if len(sys.argv) > 2 else 'forest,plains').split(',')
POSES = {'plains': ('WhiterunExterior04', dict(x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=4.0, rz=247.0)), 'forest': ('HalfMoonMillExterior', None), 'city': ('WhiterunOrigin', None), 'riften': ('RiftenOrigin', None), 'rift': ('ShorsStone', None)}
def rows(o):
    if isinstance(o, dict):
        if 'gpuAvgMs' in o: yield o
        for v in o.values(): yield from rows(v)
    elif isinstance(o, list):
        for v in o: yield from rows(v)
bench.launch(); bench.all_on(); bench.console('tgm'); out = {}
for sc in SCENES:
    cell, pose = POSES[sc]; bench.goto(cell); bench.exterior_setup()
    if pose: cs.world(action='teleport', **pose)
    time.sleep(25)
    cs.call('communityshaders.frames', {'action': 'start'}); time.sleep(12); cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(1)
    c = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {})
    fr = {k: round(statistics.median(v), 2) for k, v in c.items() if v and isinstance(v[0], (int, float))}
    R = sorted(rows(cs.call('communityshaders.inspect', {'kind': 'profiler'})), key=lambda r: -r.get('gpuAvgMs', 0))
    try: dc = cs.call('communityshaders.inspect', {'kind': 'drawcalls'})
    except Exception as e: dc = {'error': str(e)[:100]}
    out[sc] = {'frames': fr, 'passes': [{'name': r.get('name'), 'gpu': round(r['gpuAvgMs'], 3), 'cpu': round(r.get('cpuAvgMs', 0), 3)} for r in R], 'drawcalls': dc}
    print(sc, fr, 'gpu passes total %.1f ms' % sum(r['gpuAvgMs'] for r in R), flush=True)
    for r in R[:22]: print('  %6.2f gpu %5.2f cpu  %s' % (r['gpuAvgMs'], r.get('cpuAvgMs', 0), r.get('name')), flush=True)
    print('  drawcalls', json.dumps(dc)[:500], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(HERE), 'results', f'profile-{TAG}.json'), 'w'), indent=1)
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

"""Queue job: apply an exported Looks Lab base grade (apply_save_look_grade.json) to the game and save it.
Deep-merges into the live Post Processing blob (a partial set resets other stages), reads back, reports unknown keys.
usage: python apply_lookgrade.py TAG FILE"""
import atexit, json, sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
NEW = json.load(open(sys.argv[2]))['PostProcessing']            # {stage: {enabled, settings}} for Look Grade and optionally LUT
bench.launch(); DONE = []; atexit.register(lambda: (not DONE) and bench.running() and bench.quit_game())
get = lambda: (lambda g: g.get('settings', g))(cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PostProcessing'}))
pp = get()
for st in NEW:
    if not isinstance(pp.get(st), dict): raise SystemExit('no %s stage in Post Processing: %s' % (st, str(pp)[:200]))
    print(st, 'live stage:', json.dumps(pp[st])[:300], flush=True)
unknown = []
def merge(dst, src, path=''):
    for k, v in src.items():
        if k not in dst: unknown.append(path + k)
        if isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v, path + k + '/')
        else: dst[k] = v
for st in NEW: merge(pp[st], NEW[st], st + '/')
print('keys not present before:', unknown, flush=True)
if unknown: raise SystemExit('exported keys do not match the live stage; nothing applied')
print('set', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PostProcessing', 'settings': pp}).get('applied'), flush=True); time.sleep(1)
full = get(); rb = full.get('Look Grade', {}); flat = rb.get('settings', rb)
if 'LUT' in NEW: print('readback LUT', json.dumps(full.get('LUT'))[:300], flush=True)
print('readback enabled', rb.get('enabled'), {k: flat.get(k) for k in ('Exposure', 'Highlights', 'Midtones', 'ShadowsLift', 'Saturation', 'Vibrance')}, flush=True)
print('save', cs.call('communityshaders.settings', {'action': 'save'}), flush=True); time.sleep(8)
DONE.append(1); bench.finish()

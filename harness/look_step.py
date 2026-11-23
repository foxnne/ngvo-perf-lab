"""Try post-processing variants live on a fixed view and report tone statistics. Base = the live Post Processing settings at start;
the base is put back at the end unless --keep NAME names a variant to leave applied (never saved).
usage: python look_step.py TAG VARIANTS.json [--weather SunnyPF] [--hour 12] [--yaw 250] [--fov 55] [--dz 900] [--keep NAME]
VARIANTS.json: [{"name": .., "pp": {nested Post Processing changes}, "features": {short: changes}}]"""
import copy, json, os, shutil, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs


def opt(n, d): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


TAG = sys.argv[1]; VARS = json.load(open(sys.argv[2])); OUT = os.path.join(os.path.dirname(HERE), 'results', 'look_step', TAG); os.makedirs(OUT, exist_ok=True)
st = bench.state_()
if st['cell']['interior']: sys.exit('player is indoors: go outside first (no hour or weather changes indoors)')
get = lambda n: (lambda r: r.get('settings', r))(cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}))
put = lambda n, s: cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})


def merge(d, s):
    for k, v in s.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict): merge(d[k], v)
        else: d[k] = v


def stats(f):
    a = np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255; h, w = a.shape[:2]; Y = a @ np.array([.2126, .7152, .0722], np.float32)
    mx = a.max(2); mn = a.min(2); S = np.where(mx > 0.05, (mx - mn) / np.maximum(mx, 1e-4), 0)
    sky = a[:int(h * .1), int(w * .55):int(w * .7)].reshape(-1, 3).mean(0); sh = a[Y < np.percentile(Y, 10)].mean(0)
    import colorsys
    hh, ss, vv = colorsys.rgb_to_hsv(*sky)
    far = a[int(h * .03):int(h * .28)]; FAR = ' | far band: clip %.1f%% mean %.2f' % (100 * float((far.max(2) > 0.995).mean()), float((far @ np.array([.2126, .7152, .0722], np.float32)).mean()))
    return FAR[3:] + ' || ' + 'p1 %.3f p50 %.3f p99 %.3f clip %.1f%% | sat50 %.2f sat90 %.2f | sky hue %3.0f sat %.2f val %.2f | shadow R/B %.2f' % (
        *np.percentile(Y, [1, 50, 99]), 100 * float((a.max(2) > 0.995).mean()), *np.percentile(S, [50, 90]), hh * 360, ss, vv, sh[0] / max(sh[2], 1e-3))


cs.world(action='weather', name=opt('--weather', 'SunnyPF'), instant=True, lock=True); cs.world(action='hour', value=float(opt('--hour', '12'))); time.sleep(8)
p = st['position']
cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + float(opt('--dz', '900')), 'pitch': float(opt('--pitch', '6')), 'yaw': float(opt('--yaw', '250')), 'fov': float(opt('--fov', '55'))})
base = get('PostProcessing'); OTHER = {}; keep = opt('--keep', None); kept = None; time.sleep(8)
try:
    for v in VARS:
        s = copy.deepcopy(base); merge(s, v.get('pp', {})); put('PostProcessing', s)
        for short, ch in v.get('features', {}).items():
            OTHER.setdefault(short, get(short)); s2 = copy.deepcopy(OTHER[short]); merge(s2, ch); put(short, s2)
        cs.world(action='hour', value=float(opt('--hour', '12'))); time.sleep(float(v.get('settle', 9)))
        f = cs.shot('look-%s-%s' % (TAG, v['name'])); d = os.path.join(OUT, v['name'] + os.path.splitext(f)[1]); shutil.move(f, d); print('%-26s %s' % (v['name'], stats(d)), flush=True)
        for short in v.get('features', {}): put(short, OTHER[short])
        if v['name'] == keep: kept = v
finally:
    put('PostProcessing', base)
    if kept:
        s = copy.deepcopy(base); merge(s, kept.get('pp', {})); put('PostProcessing', s)
        for short, ch in kept.get('features', {}).items(): s2 = copy.deepcopy(OTHER[short]); merge(s2, ch); put(short, s2)
        print('left live:', kept['name'])
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    cs.world(action='weather', name=opt('--weather', 'SunnyPF'), instant=False, lock=False)

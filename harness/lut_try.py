"""Load LUT files live one after another on a fixed plains view and capture each; leaves the LAST one applied (not saved).
usage: python lut_try.py TAG lutfile [lutfile ...]   (file names inside the 'foxnne - NAT LUTs' LUT folder; 'none' = LUT off)"""
import copy, json, os, shutil, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; LUTS = sys.argv[2:]
OUT = os.path.join(os.path.dirname(HERE), 'results', 'look_grade', TAG); os.makedirs(OUT, exist_ok=True)
D = os.path.join('C:' + os.sep, 'Modlists', 'NGVO 8.0 Beta', 'mods', 'foxnne - NAT LUTs', 'SKSE', 'Plugins', 'CommunityShaders', 'LUTs')
P = json.load(open(os.path.join(os.path.dirname(HERE), 'results', 'look_grade', 'a', 'pp_before.json')))   # baseline post processing


def st(f):
    a = np.asarray(Image.open(f).convert('RGB')).astype(np.float32) / 255; Y = a @ np.array([.2126, .7152, .0722], np.float32)
    mx = a.max(2); mn = a.min(2); S = np.where(mx > 0.02, (mx - mn) / np.maximum(mx, 1e-4), 0)
    return 'p1 %.3f p50 %.3f p99 %.3f | sat50 %.2f sat90 %.2f' % (*np.percentile(Y, [1, 50, 99]), *np.percentile(S[Y > 0.05], [50, 90]))


cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0)
p = bench.state_()['position']
cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 900, 'pitch': 6.0, 'yaw': 250.0, 'fov': 40.0}); time.sleep(8)
for i, lut in enumerate(LUTS):
    Q = copy.deepcopy(P); Q['Look Grade']['enabled'] = False
    if lut != 'none': Q['LUT']['enabled'] = True; Q['LUT']['settings']['LutPath'] = os.path.join(D, lut)
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PostProcessing', 'settings': Q}); time.sleep(8)
    f = cs.shot('lut-%s-%d' % (TAG, i)); d = os.path.join(OUT, '%d_%s.png' % (i, os.path.splitext(lut)[0])); shutil.move(f, d); print('%-36s' % lut, st(d), flush=True)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); print('left live:', LUTS[-1])

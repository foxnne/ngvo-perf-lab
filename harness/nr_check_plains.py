"""1) Is Neural Rendering really evaluating? Frozen face close-up: frame time and image with NR on / off / on.
2) Whiterun plains framing candidates with the raised free camera (8 headings x 2 heights).
output: results/nr_check/ and results/viewfinder_plains/"""
import copy, json, os, shutil, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
import numpy as np
from PIL import Image, ImageDraw
RES = os.path.join(os.path.dirname(HERE), 'results')
O1 = os.path.join(RES, 'nr_check'); O2 = os.path.join(RES, 'viewfinder_plains'); os.makedirs(O1, exist_ok=True); os.makedirs(O2, exist_ok=True)
def lum(p): return np.asarray(Image.open(p).convert('RGB').resize((860, 360))).astype(np.float32).mean(axis=2) / 255
def measure(sec=8):
    cs.call('communityshaders.frames', {'action': 'start'}); time.sleep(sec)
    cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(1)
    f = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {}).get('frameMs', [])
    return round(statistics.median(f), 2) if f else None
bench.launch(); bench.console('tgm')
bench.goto('WhiterunExterior04'); bench.exterior_setup()
cs.world(action='teleport', x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=0.0, rz=160.0); time.sleep(12)
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'NeuralRendering'}); orig = g.get('settings', g)
out = {'settings': orig, 'steps': []}
cs.world(action='timescale', value=0); cs.world(action='freeze', on=True); time.sleep(1)
try:
    bench.face_camera(True); time.sleep(4)
    imgs = {}
    for name, en in (('on1', True), ('off', False), ('on2', True)):
        s = copy.deepcopy(orig); s['enabled'] = en
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': s}); time.sleep(8)
        ms = measure(); src = cs.shot(f'nrcheck-{name}'); time.sleep(1)
        dst = os.path.join(O1, f'face_{name}' + os.path.splitext(src)[1]); shutil.copy2(src, dst); imgs[name] = lum(dst)
        out['steps'].append({'state': name, 'frame_ms': ms}); print(name, 'frame', ms, 'ms', flush=True)
    out['diff_on_vs_off'] = round(float(np.abs(imgs['on1'] - imgs['off']).mean()), 5)
    out['diff_on_vs_on'] = round(float(np.abs(imgs['on1'] - imgs['on2']).mean()), 5)
    print('image diff on-vs-off', out['diff_on_vs_off'], ' on-vs-on (noise floor)', out['diff_on_vs_on'], flush=True)
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': orig})
    try: bench.face_camera(False)
    except Exception: pass
    cs.world(action='freeze', on=False); cs.world(action='timescale', value=1)
    json.dump(out, open(os.path.join(O1, 'nr_check.json'), 'w'), indent=1)
# plains framings
time.sleep(4); p = bench.state_()['position']; print('player at', p, flush=True)
tiles = []
try:
    for up in (700.0, 2000.0):
        for yaw in range(0, 360, 45):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + up, 'pitch': -3.0, 'yaw': float(yaw), 'fov': 65.0}); time.sleep(4)
            src = cs.shot(f'plains-{int(up)}-{yaw}'); time.sleep(1)
            dst = os.path.join(O2, f'plains_up{int(up):04d}_yaw{yaw:03d}' + os.path.splitext(src)[1]); shutil.copy2(src, dst)
            tiles.append((dst, f'height +{int(up)}  heading {yaw} (0 north, 90 east)'))
finally:
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
w, h = 860, 360; sheet = Image.new('RGB', (w * 4, (h + 26) * 4), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, (path, label) in enumerate(tiles):
    sheet.paste(Image.open(path).convert('RGB').resize((w, h)), ((i % 4) * w, (i // 4) * (h + 26) + 26)); d.text(((i % 4) * w + 8, (i // 4) * (h + 26) + 6), label, fill=(240, 240, 240))
sheet.save(os.path.join(O2, 'sheet_plains.jpg'), quality=90); print('sheet', len(tiles), flush=True)
time.sleep(10); L = os.path.expanduser('~/Documents/My Games/Skyrim Special Edition/SKSE/BottledShaders.log')
bench.quit_game(); time.sleep(8)
if os.path.exists(L): shutil.copy2(L, os.path.join(O1, 'BottledShaders.log'))

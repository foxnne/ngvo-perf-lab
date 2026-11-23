"""Wide landscape shots in several regions at noon, clear weather. At each stop the player stands at the place, the camera is raised
above them and turns through 8 directions; the directions that look like a long view (a clear band of sky above land) are kept.
usage: python region_shots.py TAG [place ...]"""
import os, shutil, sys, time
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'region_shots', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = {'ilinalta': ['coc GuardianStones'], 'rift': ['coc ShorsStone', 'cow Tamriel 40 -22'], 'riften_lake': ['coc RiftenStables', 'cow Tamriel 41 -28'],
          'dragonbridge': ['coc DragonBridgeExterior01', 'coc DragonBridge', 'cow Tamriel -23 20'], 'reach': ['coc Karthwasten', 'cow Tamriel -32 8'],
          'pale': ['coc DawnstarExterior01', 'cow Tamriel 9 22'], 'winterhold_nw': ['cow Tamriel 24 27', 'coc WinterholdExterior01'], 'plains': ['coc WhiterunExterior04'],
          'eastmarch': ['cow Tamriel 30 2'], 'falkreath': ['coc FalkreathExterior01', 'cow Tamriel -7 -22']}
want = sys.argv[2:] or list(PLACES)


def score(path):
    a = np.asarray(Image.open(path).convert('RGB').resize((430, 180))).astype(np.float32) / 255; Y = a @ np.array([.2126, .7152, .0722], np.float32)
    gy = np.abs(np.diff(Y, axis=0)); gx = np.abs(np.diff(Y, axis=1)); tex = np.zeros_like(Y); tex[1:, :] += gy; tex[:, 1:] += gx
    sky = ((a[..., 2] > a[..., 0] * 1.03) | (Y > 0.8)) & (tex < 0.03)
    top = sky[:70].mean(); low = sky[110:].mean(); far = float(tex[60:110].mean())
    return float(top), float(low), far


for place in want:
    last = None
    for cmd in PLACES[place]:
        bench.console(cmd); time.sleep(36)
        try:
            s = bench.state_()
            if not s['cell']['interior']: last = s; break
        except Exception:
            time.sleep(8)
    if not last: print(place, 'could not travel'); continue
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=12.0); time.sleep(12)
    p = bench.state_()['position']; res = []
    for yaw in range(0, 360, 45):
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 700, 'pitch': 4, 'yaw': yaw, 'fov': 55}); time.sleep(7)
        f = cs.shot('rg-%s-%d' % (place, yaw)); d = os.path.join(OUT, '%s_yaw%03d.png' % (place, yaw)); shutil.move(f, d)
        top, low, far = score(d); res.append((top, low, far, d))
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    good = sorted([r for r in res if 0.25 <= r[0] <= 0.95 and r[1] < 0.15], key=lambda r: -r[2])[:2]
    for r in res:
        if r not in good: os.remove(r[3])
    print('%-14s cell %-22s kept %s' % (place, last['cell']['editorID'], [os.path.basename(r[3]) + ' sky %.2f' % r[0] for r in good] or 'NONE (no direction looked like a long view)'), flush=True)
s = bench.state_(); cs.world(action='weather', name=s['weather']['editorID'], instant=False, lock=False)

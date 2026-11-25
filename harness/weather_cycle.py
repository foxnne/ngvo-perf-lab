"""The high Ilinalta view cycled through weathers, tilted up to show the sky; each frame is labelled with the metered scene
light against the first weather. usage: python weather_cycle.py TAG [hour] [--view NAME] [weather=LABEL ...]
Default camera: views.json ilinalta_backlit position, dz 3500, pitch -5, yaw 270, fov 60 (the framing the user asked for
2026-11-23). --view NAME uses any view from views.json as saved."""
import json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
import numpy as np
from PIL import Image, ImageDraw, ImageFont
VIEW = None
if '--view' in sys.argv:
    i = sys.argv.index('--view'); VIEW = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'views.json')))[sys.argv[i + 1]]; VNAME = sys.argv[i + 1]; del sys.argv[i:i + 2]
TAG = sys.argv[1]; HOUR = float(sys.argv[2]) if len(sys.argv) > 2 and '=' not in sys.argv[2] else 13.0
N = [a.split('=', 1) for a in sys.argv[2:] if '=' in a] or [('SunnyPF', 'CLEAR'), ('CloudyPF', 'PARTLY CLOUDY'), ('OvercastPF', 'OVERCAST'), ('FogPF', 'FOG'),
                                                             ('RainPF', 'RAIN'), ('StormPF', 'STORM'), ('Snow', 'SNOW (cloudy)')]
OUT = os.path.join(os.path.dirname(HERE), 'results', 'views', TAG); os.makedirs(OUT, exist_ok=True)
if bench.menus().get('messageBoxOpen'): sys.exit('a message box is open in game')
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name=N[0][0], instant=True, lock=True)
bench.console(VIEW['travel'] if VIEW else 'cow Tamriel -2 -14'); time.sleep(45)
for _ in range(10):
    a = bench.state_(); time.sleep(4); b = bench.state_()
    if not b['cell']['interior'] and a['position'] == b['position']: break
P = bench.state_()['position']; rows = []
try:
    for w, label in N:
        cs.world(action='hour', value=HOUR); cs.world(action='weather', name=w, instant=True, lock=True)
        C = VIEW['camera'] if VIEW else {'dz': 3500, 'pitch': -5, 'yaw': 270, 'fov': 60}
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': P['x'], 'y': P['y'], 'z': P['z'] + C['dz'], 'pitch': C['pitch'], 'yaw': C['yaw'], 'fov': C['fov']})
        time.sleep(34); cs.world(action='hour', value=HOUR); time.sleep(5)
        e = cs.call('communityshaders.inspect', {'kind': 'exposure'})
        f = cs.shot('wc') or cs.shot('wc2'); d = os.path.join(OUT, w + '.png'); shutil.move(f, d)
        a = np.asarray(Image.open(d).convert('RGB').resize((430, 180))).astype(float) / 255; rows.append((w, label, e['meteredLuminance']))
        print('%-11s metered %.4f | image %.3f sky %.3f land %.3f' % (w, e['meteredLuminance'], a.mean(), a[:60].mean(), a[100:].mean()), flush=True)
    for w, label, L in rows:
        st = math.log2(L / rows[0][2]); print('%-11s %+.1f stops vs %s' % (w, st, rows[0][1]))
        im = Image.open(os.path.join(OUT, w + '.png')).convert('RGB'); W, H = im.size; fs = int(H * 0.045); font = ImageFont.truetype('arialbd.ttf', fs)
        dr = ImageDraw.Draw(im); dr.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0))
        dr.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  %s %02d:%02d  -  scene light %+.1f stops vs %s' % (label, VNAME.replace('_', ' ') if VIEW else 'Ilinalta', int(HOUR), round(HOUR % 1 * 60), st, rows[0][1].lower()), fill=(255, 230, 0), font=font)
        im.save(os.path.join(OUT, 'labelled_' + w + '.png'))
finally:
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=False, lock=False); cs.world(action='hour', value=13.0)

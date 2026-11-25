"""Sky-type prototypes (reference sheet https://claude.ai/artifact/DFFWtX5H6d2pH9PFT1mGhi): each recipe builds one real closed
sky from layers (middle sheet, low layer, cirrus) on a clear weather the scene pack does not drive, and is shot from the high
Ilinalta view. Nothing is saved. usage: python sky_types.py TAG [hour] [name ...]"""
import copy, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, saved_fix
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; rest = sys.argv[2:]
HOUR = float(rest.pop(0)) if rest and rest[0].replace('.', '').isdigit() else 13.0
OUT = os.path.join(os.path.dirname(HERE), 'results', 'sky_types', TAG); os.makedirs(OUT, exist_ok=True)
from sky_recipes import R
want = rest or [r[0] for r in R]
if bench.menus().get('messageBoxOpen'): sys.exit('a message box is open in game')
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
bench.console('cow Tamriel -2 -14'); time.sleep(45)
for _ in range(10):
    a = bench.state_(); time.sleep(4); b = bench.state_()
    if not b['cell']['interior'] and a['position'] == b['position']: break
P = bench.state_()['position']
try:
    for name, label, fn in R:
        if name not in want: continue
        saved_fix.fix(); cs.call('communityshaders.settings', {'action': 'load'}); time.sleep(2.5)
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); s = copy.deepcopy(g.get('settings', g)); fn(s)
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s})
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PostProcessing'}); pp = copy.deepcopy(g.get('settings', g)); pp['cinematic_camera']['Exposure']['MaxISO'] = 12800.0
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PostProcessing', 'settings': pp})
        cs.world(action='hour', value=HOUR); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': P['x'], 'y': P['y'], 'z': P['z'] + 3500, 'pitch': -5, 'yaw': 270, 'fov': 60})
        time.sleep(34); cs.world(action='hour', value=HOUR); time.sleep(4)
        f = cs.shot('st') or cs.shot('st2'); d = os.path.join(OUT, name + '.png'); shutil.move(f, d)
        im = Image.open(d).convert('RGB'); W, H = im.size; fs = int(H * 0.045); font = ImageFont.truetype('arialbd.ttf', fs)
        dr = ImageDraw.Draw(im); dr.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0)); dr.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  first prototype  -  Ilinalta %02d:%02d' % (label, int(HOUR), round(HOUR % 1 * 60)), fill=(255, 230, 0), font=font)
        im.save(os.path.join(OUT, 'labelled_' + name + '.png')); print(name, cs.stats(d)['mean'], flush=True)
finally:
    saved_fix.fix(); cs.call('communityshaders.settings', {'action': 'load'})
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=False, lock=False); cs.world(action='hour', value=13.0)

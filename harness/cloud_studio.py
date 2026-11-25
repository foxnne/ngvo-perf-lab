"""Cloud studio: look at one sky from all sides. The camera rises above the Whiterun plains and looks round: from the
ground, level with the cloud in four directions, from above in four directions, and straight down. Recipes come from sky_recipes.py
('saved' = the saved fair-weather sky). Nothing is saved. usage: python cloud_studio.py TAG RECIPE [hour] [view ...]"""
import copy, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, saved_fix
from sky_recipes import R
from PIL import Image, ImageDraw, ImageFont
TAG, RECIPE = sys.argv[1], sys.argv[2]; rest = sys.argv[3:]
HOUR = float(rest.pop(0)) if rest and rest[0].replace('.', '').isdigit() else 13.0
OUT = os.path.join(os.path.dirname(HERE), 'results', 'cloud_studio', TAG); os.makedirs(OUT, exist_ok=True)
U = 70.03   # game units per metre
# NEVER move the camera far sideways: on 2026-11-23 a camera 630,000 units from the player crashed the game in cell loading
# (BGSQueuedObjectInitialLoad, null cell). The camera stays above the player and only changes height and direction.
# name: (camera height above ground in metres, yaw: 0 north / 90 east / 180 south / 270 west, pitch: negative looks up, field of view)
VIEWS = {'from_ground_west': (10, 270, -30, 70), 'cloud_level_north': (1500, 0, 0, 60), 'cloud_level_east': (1500, 90, 0, 60), 'cloud_level_south': (1500, 180, 0, 60),
         'cloud_level_west': (1500, 270, 0, 60), 'above_north': (3500, 0, 18, 60), 'above_east': (3500, 90, 18, 60), 'above_south': (3500, 180, 18, 60), 'above_west': (3500, 270, 18, 60),
         'top_down': (6000, 0, 85, 70)}
want = rest or list(VIEWS)
if bench.menus().get('messageBoxOpen'): sys.exit('a message box is open in game')
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
s = bench.state_()
if s['cell']['interior'] or s['cell']['editorID'] != 'WhiterunExterior04': bench.console('coc WhiterunExterior04'); time.sleep(48)
P = bench.state_()['position']
label = dict((r[0], r[1]) for r in R).get(RECIPE, 'SAVED FAIR SKY')
try:
    saved_fix.fix(); cs.call('communityshaders.settings', {'action': 'load'}); time.sleep(2.5)
    if RECIPE != 'saved':
        fn = [r[2] for r in R if r[0] == RECIPE][0]
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); st = copy.deepcopy(g.get('settings', g)); fn(st)
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': st})
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PostProcessing'}); pp = copy.deepcopy(g.get('settings', g)); pp['cinematic_camera']['Exposure']['MaxISO'] = 12800.0
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PostProcessing', 'settings': pp})
    cs.world(action='hour', value=HOUR); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
    first = True
    for name in want:
        height, yaw, pitch, fov = VIEWS[name]
        cam = dict(x=P['x'], y=P['y'], z=P['z'] + max(height, 10) * U, pitch=pitch, yaw=yaw, fov=fov)
        cs.call('communityshaders.testbed', dict(cam, action='camera')); time.sleep(30 if first else 14); first = False
        cs.world(action='hour', value=HOUR); time.sleep(3)
        f = cs.shot('cs') or cs.shot('cs2'); d = os.path.join(OUT, '%s_%s.png' % (RECIPE, name)); shutil.move(f, d)
        im = Image.open(d).convert('RGB'); W, H = im.size; fs = int(H * 0.045); font = ImageFont.truetype('arialbd.ttf', fs)
        dr = ImageDraw.Draw(im); dr.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0))
        dr.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  %s  -  %02d:%02d' % (label, name.replace('_', ' '), int(HOUR), round(HOUR % 1 * 60)), fill=(255, 230, 0), font=font)
        im.save(os.path.join(OUT, 'labelled_%s_%s.png' % (RECIPE, name))); print(name, cs.stats(d)['mean'], flush=True)
finally:
    saved_fix.fix(); cs.call('communityshaders.settings', {'action': 'load'})
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=False, lock=False); cs.world(action='hour', value=13.0)

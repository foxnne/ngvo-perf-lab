"""A/B a deployed SSGI composite shader change: neck under hair + Riverwood forest floor (canopy look must hold).
usage: python ssgi_ab.py NEW_FILE OLD_FILE"""
import math, os, shutil, subprocess, sys, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
NEW, OLD = sys.argv[1], sys.argv[2]
DEPLOYED = r'C:\Modlists\NGVO 8.0 Beta\mods\Bottled Shaders - foxnne\Shaders\ScreenSpaceGI\composite.cs.hlsl'
OUT = os.path.join(shots.ROOT, 'results', 'ssgi_ab'); os.makedirs(OUT, exist_ok=True)
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24')
def use(path):
    shutil.copy(path, DEPLOYED)
    cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'ScreenSpaceGI', 'enabled': False}); time.sleep(2)
    cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': 'ScreenSpaceGI', 'enabled': True}); time.sleep(5)
def grab(name):
    p = os.path.join(OUT, name + '.png')
    subprocess.run([r'C:\Users\foxnn\dev\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', p]); return p
res = {}
bench.console('tm')
try:
    cs.world(action='timescale', value=0)
    v = cs.call('communityshaders.testbed', {'action': 'view_get'}); hd = v['head']; yaw = hd['yaw']; a = math.radians(yaw + 215)
    neck = {'action': 'camera', 'mode': 'free', 'x': hd['x'] + math.sin(a) * 45, 'y': hd['y'] + math.cos(a) * 45, 'z': hd['z'] - 6, 'yaw': (yaw + 35) % 360, 'pitch': -8.0, 'fov': 35}
    bench.console('tai')
    for tag, path in (('old', OLD), ('new', NEW)):
        use(path); cs.call('communityshaders.testbed', neck); time.sleep(4); res['neck_' + tag] = grab('neck_' + tag)
    bench.console('tai')
    view = json.load(open(os.path.join(HERE, 'views.json')))['riverwood_floor']; c = view['camera']
    cs.world(action='timescale', value=20); bench.console('coc Riverwood'); time.sleep(10); bench.settle(maxwait=120)
    cs.world(action='hour', value=13.0); time.sleep(12); cs.world(action='timescale', value=0)
    for tag, path in (('old', OLD), ('new', NEW)):
        use(path); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'free', 'x': c['x'], 'y': c['y'], 'z': c['z'], 'yaw': c['yaw'], 'pitch': c['pitch'], 'fov': c['fov']})
        time.sleep(8); res['forest_' + tag] = grab('forest_' + tag)
finally:
    shutil.copy(NEW, DEPLOYED)
    bench.console('tm'); cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 40)
for scene, crop in (('neck', (1020, 140, 2420, 1300)), ('forest', (0, 0, 3440, 1440))):
    ims = [Image.open(res['%s_%s' % (scene, t)]).crop(crop) for t in ('old', 'new')]
    if scene == 'forest': ims = [im.resize((1720, 720)) for im in ims]
    w, h = ims[0].size; out = Image.new('RGB', (w * 2, h))
    for i, (im, t) in enumerate(zip(ims, ('before', 'contact occlusion'))): out.paste(im, (i * w, 0)); ImageDraw.Draw(out).text((i * w + 12, 8), t, fill='red', font=font)
    out.save(os.path.join(OUT, scene + '_ab.png')); print(os.path.join(OUT, scene + '_ab.png'))

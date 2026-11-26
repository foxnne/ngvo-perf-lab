"""Why does hair glow (user 2026-11-25)? Same pose, one suspect off at a time. usage: python hair_glow.py"""
import math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(shots.ROOT, 'results', 'hair_glow'); os.makedirs(OUT, exist_ok=True)
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24')
tog = lambda f, on: cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': f, 'enabled': on})
SUS = ['none', 'HairSpecular', 'NeuralRendering', 'ScreenSpaceGI', 'LightLimitFix', 'Skylighting', 'ImageBasedLighting', 'none']
cs.world(action='weather', name='SunnyPF'); cs.world(action='hour', value=13.0); time.sleep(25); cs.world(action='timescale', value=0)
v = cs.call('communityshaders.testbed', {'action': 'view_get'}); hd = v['head']; yaw = hd['yaw']; a = math.radians(yaw + 25)
cam = {'action': 'camera', 'mode': 'free', 'x': hd['x'] + math.sin(a) * 60, 'y': hd['y'] + math.cos(a) * 60, 'z': hd['z'] + 2, 'yaw': (yaw + 205) % 360, 'pitch': 0.0, 'fov': 32}
bench.console('tai'); bench.console('tm'); rows = []
try:
    for s in SUS:
        if s != 'none': tog(s, False)
        cs.call('communityshaders.testbed', cam); time.sleep(4)
        p = os.path.join(OUT, '%s.png' % s)
        subprocess.run([r'C:\Users\foxnn\dev\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', p])
        rows.append((s, p))
        if s != 'none': tog(s, True); time.sleep(2)
finally:
    bench.console('tai'); bench.console('tm'); cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 34)
ims = [Image.open(p).crop((1120, 160, 2320, 1240)) for _, p in rows]; w, h = ims[0].size; cols = 4
out = Image.new('RGB', (w * cols, h * 2))
for i, (im, (s, _)) in enumerate(zip(ims, rows)):
    x, y = (i % cols) * w, (i // cols) * h; out.paste(im, (x, y)); ImageDraw.Draw(out).text((x + 10, y + 8), 'all on' if s == 'none' else s + ' off', fill='red', font=font)
out.save(os.path.join(OUT, 'hair_grid.png')); print(os.path.join(OUT, 'hair_grid.png'))

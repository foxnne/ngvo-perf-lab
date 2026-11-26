"""Black hands caught live (user 2026-11-25): shoot the hands, then each suspect off, then a shader cache clear.
usage: python hands_black.py"""
import json, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(shots.ROOT, 'results', 'hands_black_%s' % time.strftime('%H%M')); os.makedirs(OUT, exist_ok=True)
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24')
tog = lambda f, on: cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': f, 'enabled': on})
json.dump(cs.call('communityshaders.testbed', {'action': 'inspect_actor', 'actor': 'player'}), open(os.path.join(OUT, 'inspect.json'), 'w'), indent=1)
cs.world(action='timescale', value=0)
p = cs.call('communityshaders.testbed', {'action': 'view_get'})['player']; y = math.radians(p['yaw'])
cam = {'action': 'camera', 'mode': 'free', 'x': p['x'] + math.sin(y) * 120, 'y': p['y'] + math.cos(y) * 120, 'z': p['z'] + 85, 'yaw': (p['yaw'] + 180) % 360, 'pitch': 8.0, 'fov': 40}
SUS = ['none', 'Skin', 'SubsurfaceScattering', 'ScreenSpaceGI', 'NeuralRendering', 'TruePBR', 'WetnessEffects', 'LightLimitFix', 'Skylighting', 'ImageBasedLighting']
bench.console('tai'); bench.console('tm'); rows = []
def shot(tag):
    cs.call('communityshaders.testbed', cam); time.sleep(3)
    path = os.path.join(OUT, '%02d_%s.png' % (len(rows), tag))
    subprocess.run([r'C:\Users\foxnn\dev\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', path])
    rows.append((tag, path)); print('shot', tag, flush=True)
try:
    for s in SUS:
        if s != 'none': tog(s, False)
        shot('all on' if s == 'none' else s + ' off')
        if s != 'none': tog(s, True); time.sleep(2)
    cs.call('communityshaders.shadercache', {'action': 'clear'}); time.sleep(20)
    shot('after shader cache clear')
finally:
    bench.console('tai'); bench.console('tm'); cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 34)
ims = [Image.open(p).crop((1020, 200, 2420, 1300)).resize((700, 550)) for _, p in rows]; w, h = ims[0].size; cols = 4
out = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)))
for i, (im, (t, _)) in enumerate(zip(ims, rows)):
    x, yy = (i % cols) * w, (i // cols) * h; out.paste(im, (x, yy)); ImageDraw.Draw(out).text((x + 8, yy + 6), t, fill='red', font=font)
out.save(os.path.join(OUT, 'grid.png')); print(os.path.join(OUT, 'grid.png'))

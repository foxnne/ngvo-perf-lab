"""Hair should shade the back of the neck (user 2026-11-25: 'AO seems very wide and loose'). Same pose, several SSGI/AO setups,
with their GPU cost. usage: python neck_ao.py"""
import copy, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(shots.ROOT, 'results', 'neck_ao'); os.makedirs(OUT, exist_ok=True)
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24')
get = lambda f: cs.call('communityshaders.feature', {'action': 'get', 'shortName': f})
put = lambda f, s: cs.call('communityshaders.feature', {'action': 'set', 'shortName': f, 'settings': s})
tog = lambda f, on: cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': f, 'enabled': on})
gi0 = get('ScreenSpaceGI')
CONFIGS = [
    ('A now (half res)', None),
    ('B full res, thinner, AO 3', dict(HalfRes=False, Thickness=0.03, AOPower=3.0)),
    ('C AO only (no bounce light)', dict(EnableGI=False)),
    ('D vanilla SSAO instead', dict(EnableGI=False, EnableVanillaSSAO=True)),
    ('E SSGI off', 'off'),
]
cs.world(action='timescale', value=0)
v = cs.call('communityshaders.testbed', {'action': 'view_get'}); hd = v['head']; yaw = hd['yaw']
a = math.radians(yaw + 180 + 35)                       # behind, a little to the side
cam = {'action': 'camera', 'mode': 'free', 'x': hd['x'] + math.sin(a) * 45, 'y': hd['y'] + math.cos(a) * 45, 'z': hd['z'] - 6,
       'yaw': (yaw + 35) % 360, 'pitch': -8.0, 'fov': 35}
bench.console('tai'); bench.console('tm'); rows = []
try:
    for label, cfg in CONFIGS:
        if cfg == 'off': tog('ScreenSpaceGI', False)
        else:
            tog('ScreenSpaceGI', True); s = copy.deepcopy(gi0)
            if cfg: s.update(cfg)
            put('ScreenSpaceGI', s)
        cs.call('communityshaders.testbed', cam); time.sleep(6)
        prof = cs.call('communityshaders.inspect', {'kind': 'profiler'})
        ms = sum(p.get('gpuAvgMs', 0) for p in prof['passes'] if p.get('name', '').startswith('ScreenSpaceGI'))
        path = os.path.join(OUT, '%s.png' % label[0])
        subprocess.run([r'C:\Users\foxnn\dev\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', path])
        rows.append((label, ms, prof['frame']['avgMs'], path)); print('%-30s SSGI %.2f ms, frame %.1f ms' % (label, ms, prof['frame']['avgMs']), flush=True)
finally:
    tog('ScreenSpaceGI', True); put('ScreenSpaceGI', gi0)
    bench.console('tai'); bench.console('tm'); cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 36)
ims = [Image.open(p).crop((1020, 140, 2420, 1300)) for *_, p in rows]; w, h = ims[0].size
out = Image.new('RGB', (w * 3, h * 2))
for i, (im, (label, ms, fr, _)) in enumerate(zip(ims, rows)):
    x, y = (i % 3) * w, (i // 3) * h; out.paste(im, (x, y)); ImageDraw.Draw(out).text((x + 12, y + 8), '%s  (SSGI %.2f ms)' % (label, ms), fill='red', font=font)
out.save(os.path.join(OUT, 'neck_grid.png')); print(os.path.join(OUT, 'neck_grid.png'))

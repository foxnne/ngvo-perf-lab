"""Blue sky-lit shadows A/B (user 2026-11-25): PhysicalSkyFill off vs on (+ SkyFillScale steps) at clear 13:00.
Road: player's own shadow ratio at Whiterun Stables. Forest: Riverwood floor view (must hold). Snow: Winterhold street, shadow hue.
usage: python skyfill_ab.py"""
import copy, json, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(shots.ROOT, 'results', 'skyfill'); os.makedirs(OUT, exist_ok=True)
FF = r'C:\Users\foxnn\dev\ffmpeg.exe'
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24')
gi0 = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'ScreenSpaceGI'})
CFG = [('off (now)', None), ('on, scale 1.0', dict(PhysicalSkyFill=True, SkyFillSaturation=1.0, SkyFillEnvWeight=0.0, SkyFillScale=1.0, BounceSkyLimit=4.0)),
       ('on, scale 0.65', dict(PhysicalSkyFill=True, SkyFillSaturation=1.0, SkyFillEnvWeight=0.0, SkyFillScale=0.65, BounceSkyLimit=4.0))]
lin = lambda v: ((v / 255 + 0.055) / 1.055) ** 2.4 if v > 10 else v / 255 / 12.92
def grab(path):
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', path]); return path
def clear_noon():
    cs.world(action='weather', name='SunnyPF'); cs.world(action='timescale', value=20); cs.world(action='hour', value=13.0); time.sleep(20); cs.world(action='timescale', value=0)
SCENES = []
def scene_road():
    bench.console('coc WhiterunExterior01'); time.sleep(10); bench.settle(maxwait=120)
    bench.console('player.setpos x 17378'); bench.console('player.setpos y -11253'); time.sleep(3); clear_noon()
    p = cs.call('communityshaders.testbed', {'action': 'view_get'})['player']; a = math.radians(p['yaw'] + 60)
    return {'action': 'camera', 'mode': 'free', 'x': p['x'] + math.sin(a) * 330, 'y': p['y'] + math.cos(a) * 330, 'z': p['z'] + 230, 'yaw': (p['yaw'] + 240) % 360, 'pitch': 30.0, 'fov': 55}
def scene_forest():
    c = json.load(open(os.path.join(HERE, 'views.json')))['riverwood_floor']['camera']
    bench.console('coc Riverwood'); time.sleep(10); bench.settle(maxwait=120); clear_noon()
    return {'action': 'camera', 'mode': 'free', 'x': c['x'], 'y': c['y'], 'z': c['z'], 'yaw': c['yaw'], 'pitch': c['pitch'], 'fov': c['fov']}
def scene_snow():
    bench.console('coc Winterhold'); time.sleep(12); bench.settle(maxwait=120); clear_noon()
    p = cs.call('communityshaders.testbed', {'action': 'view_get'})['player']; a = math.radians(p['yaw'] + 180)
    return {'action': 'camera', 'mode': 'free', 'x': p['x'] + math.sin(a) * 400, 'y': p['y'] + math.cos(a) * 400, 'z': p['z'] + 300, 'yaw': p['yaw'] % 360, 'pitch': 18.0, 'fov': 65}
res = {}
bench.console('tm')
try:
    for name, setup in (('road', scene_road), ('forest', scene_forest), ('snow', scene_snow)):
        cam = setup()
        for label, cfg in CFG:
            s = copy.deepcopy(gi0)
            if cfg: s.update(cfg)
            cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'ScreenSpaceGI', 'settings': s})
            cs.call('communityshaders.testbed', cam); time.sleep(7)
            path = grab(os.path.join(OUT, '%s_%s.png' % (name, label.split(',')[0].replace(' ', '') + label.split('scale')[-1].strip().replace('.', '') if 'scale' in label else name + '_off')))
            im = Image.open(path).convert('RGB'); px = sorted(im.convert('L').crop((600, 500, 2800, 1300)).getdata()); n = len(px)
            sh = sum(lin(v) for v in px[:n // 8]) / (n // 8); lit = sum(lin(v) for v in px[-n // 3:]) / (n // 3)
            dark = [q for q in im.crop((600, 500, 2800, 1300)).resize((550, 200)).getdata() if sum(q) < 240]
            hue = tuple(round(sum(c[i] for c in dark) / max(len(dark), 1)) for i in range(3))
            res.setdefault(name, []).append({'cfg': label, 'shadow_ratio': round(sh / lit, 3), 'stops': round(math.log2(lit / max(sh, 1e-6)), 2), 'shadow_rgb': hue, 'mean': round(sum(px) / n, 1), 'img': path})
            print(name, res[name][-1], flush=True)
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'ScreenSpaceGI', 'settings': gi0})
    bench.console('tm'); cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
json.dump(res, open(os.path.join(OUT, 'skyfill_%s.json' % time.strftime('%H%M')), 'w'), indent=1)
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 34)
rows = [r for r in res.values()]; w, h = 1146, 480
out = Image.new('RGB', (w * 3, h * len(rows)))
for y, r in enumerate(rows):
    for x, e in enumerate(r):
        im = Image.open(e['img']).resize((w, h)); out.paste(im, (x * w, y * h))
        ImageDraw.Draw(out).text((x * w + 10, y * h + 8), '%s  %.2f stops  shadow rgb %s' % (e['cfg'], e['stops'], e['shadow_rgb']), fill='red', font=font)
out.save(os.path.join(OUT, 'skyfill_grid.jpg'), quality=90); print(os.path.join(OUT, 'skyfill_grid.jpg'))

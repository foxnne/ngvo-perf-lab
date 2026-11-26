"""Shadow depth vs forest shade (user 2026-11-25): sweep LinearLighting.ambientMult at clear 13:00, time frozen.
Road: sun-shadow / sunlit ratio next to the player at Whiterun Stables. Forest: Riverwood pine floor (views.json riverwood_floor),
mean brightness and shade detail. usage: python ambient_sweep.py [0.85,0.7,0.55,0.45]"""
import json, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageStat
VALUES = [float(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '0.85,0.7,0.55,0.45').split(',')]
OUT = os.path.join(shots.ROOT, 'results', 'ambient'); os.makedirs(OUT, exist_ok=True)
FF = r'C:\Users\foxnn\dev\ffmpeg.exe'
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24,crop=3000:1250:220:100,scale=1500:-2')
lin = lambda v: ((v / 255 + 0.055) / 1.055) ** 2.4 if v > 10 else v / 255 / 12.92
def grab(path):
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', path])
    return Image.open(path).convert('L')
def setamb(v):
    r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'LinearLighting'})
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'LinearLighting', 'settings': dict(r, ambientMult=v)})
orig = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'LinearLighting'})['ambientMult']
WEATHER = os.environ.get('SWEEP_WEATHER', 'Helios_SClearSkyPF')
def clear_noon():
    print(cs.world(action='weather', name=WEATHER)); cs.world(action='timescale', value=20); cs.world(action='hour', value=13.0); time.sleep(15); cs.world(action='timescale', value=0)
res = {}
bench.console('tm')
try:
    # Road: player's own shadow. Camera on the shadow side found earlier (yaw offset 150).
    bench.console('coc WhiterunExterior01'); time.sleep(10); bench.settle(maxwait=120)
    bench.console('player.setpos x 17378'); bench.console('player.setpos y -11253'); time.sleep(4); clear_noon()
    p = cs.call('communityshaders.testbed', {'action': 'view_get'})['player']
    # put the camera opposite the sun direction is unknown: take 4 sides, keep the one with the biggest dark area near the feet
    for v in VALUES:
        setamb(v); time.sleep(5)
        best = None
        for off in (60, 150, 240, 330):
            a = math.radians(p['yaw'] + off)
            cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'free', 'x': p['x'] + math.sin(a) * 330, 'y': p['y'] + math.cos(a) * 330,
                                                 'z': p['z'] + 230, 'yaw': (p['yaw'] + off + 180) % 360, 'pitch': 30.0, 'fov': 55}); time.sleep(2.5)
            im = grab(os.path.join(OUT, 'road_%.2f_%d.png' % (v, off)))
            px = sorted(im.crop((300, 350, 1200, 620)).getdata())        # ground band around the feet
            sh, lit = sum(lin(x) for x in px[:len(px) // 8]) / (len(px) // 8), sum(lin(x) for x in px[-len(px) // 3:]) / (len(px) // 3)
            if best is None or sh / lit < best[0]: best = (sh / lit, off)
        res.setdefault(v, {})['road_ratio'] = round(best[0], 3); res[v]['road_stops'] = round(math.log2(1 / best[0]), 2); res[v]['road_side'] = best[1]
        print(v, res[v], flush=True)
    view = json.load(open(os.path.join(HERE, 'views.json')))['riverwood_floor']; c = view['camera']
    bench.console('coc Riverwood'); time.sleep(10); bench.settle(maxwait=120); clear_noon()
    for v in VALUES:
        setamb(v); time.sleep(5)
        cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'free', 'x': c['x'], 'y': c['y'], 'z': c['z'], 'yaw': c['yaw'], 'pitch': c['pitch'], 'fov': c['fov']}); time.sleep(8)
        im = grab(os.path.join(OUT, 'forest_%.2f.png' % v)); px = sorted(im.getdata()); n = len(px)
        res[v].update(forest_mean=round(ImageStat.Stat(im).mean[0], 1), forest_p10=px[n // 10], forest_p50=px[n // 2], forest_p90=px[n * 9 // 10])
        print(v, res[v], flush=True)
finally:
    setamb(orig); cs.world(action='timescale', value=20); bench.console('tm'); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
json.dump(res, open(os.path.join(OUT, 'sweep_%s.json' % time.strftime('%H%M%S')), 'w'), indent=1)
print('restored ambientMult', orig)

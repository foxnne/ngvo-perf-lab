"""Sun shadow softness comparison (close-range work, 2026-11-24): contact-hardening penumbra on all near shadows.
usage: python shadow_soft.py TAG"""
import html, math, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; tb = shots.tb; OUT = os.path.join(shots.ROOT, 'results', 'shadowsoft', TAG); GAL = os.path.join(shots.ROOT, 'gallery', 'shadowsoft'); os.makedirs(OUT, exist_ok=True); os.makedirs(GAL, exist_ok=True)
VAR = [('A', 'AS NOW (FIXED EDGE)', (0, 1.0, 1024)), ('B', 'REAL SUN PENUMBRA', (1, 1.0, 1024)), ('C', 'REAL SUN, CASTERS TO 60 M', (1, 1.0, 4096)),
       ('D', 'SUN x2, CASTERS TO 60 M', (1, 2.0, 4096)), ('E', 'SUN x3, CASTERS TO 60 M', (1, 3.0, 4096))]
def setv(a, sc, md):
    for k, v in (('SUN_PCSS_ALL', a), ('SUN_SOFT_SCALE', '%.1f' % sc), ('SUN_PCSS_MAXDIST', '%.1f' % md)):
        r = subprocess.run([sys.executable, os.path.join(HERE, 'hot.py'), 'define', 'Utility.hlsl', k, str(v)], capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1][:110], flush=True)
PLACES = [('cow Tamriel -2 -14', [('forest_into_shade', 270, 125, 2, 75), ('forest_sunlit_floor', 0, 125, 4, 75)]),
          ('coc WhiterunExterior01', [('stables_house', 300, 140, 0, 70), ('stables_road', 200, 140, 4, 70)])]
frames = {}
try:
    for travel, views in PLACES:
        tb(action='camera', mode='player'); bench.console(travel); time.sleep(8); shots.ready(25, 150)
        cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(8)
        p = tb(action='view_get')['player']; fps = {}
        for key, label, v in VAR:
            setv(*v); time.sleep(4)
            for name, yaw, h, pitch, fov in views:
                a = math.radians(yaw); tb(action='camera', mode='override', x=p['x'] + math.sin(a) * 70, y=p['y'] + math.cos(a) * 70, z=p['z'] + h, pitch=pitch, yaw=yaw, fov=fov)
                shots.ready(10, 80); cs.world(action='hour', value=13.0); time.sleep(2.5)
                f = shots.grab('ss'); d = os.path.join(OUT, '%s_%s.png' % (name, key)); shutil.move(f, d); frames.setdefault(name, []).append((key, label, d))
            try:
                pr = cs.call('communityshaders.inspect', {'kind': 'profiler'}); print(travel.split()[0], key, label, 'frame ms', pr.get('frameMs') or pr.get('frame_ms') or str(pr)[:80], flush=True)
            except Exception as e: print(key, label, flush=True)
finally:
    setv(0, 1.0, 1024); tb(action='camera', mode='player'); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
body = []
for name, lst in frames.items():
    for key, label, d in lst:
        im = Image.open(d).convert('RGB'); W, H = im.size; fs = int(H * 0.05); dr = ImageDraw.Draw(im); dr.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0)); dr.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  %s' % (key, label), fill=(255, 230, 0), font=ImageFont.truetype('arialbd.ttf', fs))
        im.save(os.path.join(GAL, '%s_%s_%s.png' % (TAG, name, key))); th = im.copy(); th.thumbnail((900, 900)); th.save(os.path.join(GAL, '%s_%s_%s.jpg' % (TAG, name, key)), quality=84)
    body.append('<h2>%s</h2><div class="g">%s</div>' % (html.escape(name.replace('_', ' ')), ''.join('<a href="shadowsoft/%s_%s_%s.png"><img src="shadowsoft/%s_%s_%s.jpg?v=%d"><span>%s - %s</span></a>' % (TAG, name, k, TAG, name, k, int(time.time()), k, html.escape(l)) for k, l, _ in lst)))
page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shadow softness</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}h1{font-size:20px}h2{font-size:16px;margin:22px 0 8px}small{color:#888;font-weight:400}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}a{color:#ddd;text-decoration:none;background:#1c1c1c;border-radius:8px;overflow:hidden;display:block}
img{width:100%%;height:auto;display:block}span{display:block;padding:6px 8px;font-size:13px}</style>
<h1>Sun shadow softness <small>%s, clear sky 13:00. Only the shadow edge filter changes; nothing saved. Tap for the uncompressed frame.</small></h1>%s''' % (time.strftime('%Y-%m-%d %H:%M'), '\n'.join(body))
open(os.path.join(shots.ROOT, 'gallery', 'shadowsoft.html'), 'w', encoding='utf-8').write(page); print('page written')

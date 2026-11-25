"""Softness comparison (user 2026-11-23, RDR2 reference): one change at a time, live and not saved, on first-person views
under forest canopy and by the Whiterun stables. Writes full-size frames, a labelled sheet per view, and a small web page
gallery/sharpness.html so they can be flipped through on the phone.  usage: python softness_test.py TAG"""
import copy, html, json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; tb = shots.tb; OUT = os.path.join(shots.ROOT, 'results', 'sharpness', TAG); os.makedirs(OUT, exist_ok=True)
GAL = os.path.join(shots.ROOT, 'gallery', 'sharpness'); os.makedirs(GAL, exist_ok=True)
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings', g)
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
VAR = [('A', 'AS NOW (OFFSET 0)', 0.0), ('B', 'SOFTER +0.25', 0.25), ('C', 'SOFTER +0.5', 0.5), ('D', 'SOFTER +0.75', 0.75), ('E', 'NEUTRAL +1.0', 1.0)]
FEATS = ()
def apply(off): print(tb(action='mipbias', offset=off), flush=True); time.sleep(1.0)
# (travel, name, yaw, extra height, pitch, fov)
PLACES = [('cow Tamriel -2 -14', [('forest_into_shade', 270, 125, 2, 75), ('forest_sunlit_floor', 0, 125, 4, 75), ('forest_canopy_up', 90, 125, -22, 75)]),
          ('coc WhiterunExterior01', [('stables_house', 300, 140, 0, 70), ('stables_road', 200, 140, 4, 70)])]
frames = {}
try:
    for travel, views in PLACES:
        tb(action='camera', mode='player'); bench.console(travel); time.sleep(8); shots.ready(25, 150)
        cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True)
        p = tb(action='view_get')['player']
        for key, label, fns in VAR:
            apply(fns)
            for name, yaw, h, pitch, fov in views:
                a = math.radians(yaw); tb(action='camera', mode='override', x=p['x'] + math.sin(a) * 70, y=p['y'] + math.cos(a) * 70, z=p['z'] + h, pitch=pitch, yaw=yaw, fov=fov)
                shots.ready(10, 80); time.sleep(2.0 if key == 'A' else 0.5); cs.world(action='hour', value=13.0); time.sleep(0.8)
                f = shots.grab('so'); d = os.path.join(OUT, '%s_%s.png' % (name, key)); shutil.move(f, d); frames.setdefault(name, []).append((key, label, d))
            print(travel, key, label, flush=True)
        apply(0.0); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
finally:
    apply(0.0)
    tb(action='camera', mode='player'); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
# sheets and page
font = None; body = []
for name, lst in frames.items():
    ims = []
    for key, label, d in lst:
        im = Image.open(d).convert('RGB'); W, H = im.size; fs = int(H * 0.05); font = ImageFont.truetype('arialbd.ttf', fs)
        dr = ImageDraw.Draw(im); dr.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0)); dr.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  %s' % (key, label), fill=(255, 230, 0), font=font)
        lab = os.path.join(GAL, '%s_%s.png' % (name, key)); im.save(lab); ims.append(im)
        th = im.copy(); th.thumbnail((900, 900)); th.save(os.path.join(GAL, '%s_%s.jpg' % (name, key)), quality=84)
    W, H = ims[0].size; cols = 2; rows = (len(ims) + 1) // 2; sh = Image.new('RGB', (W * cols // 2, H * rows // 2))
    for i, im in enumerate(ims): sh.paste(im.resize((W // 2, H // 2)), ((i % cols) * (W // 2), (i // cols) * (H // 2)))
    sh.save(os.path.join(OUT, 'sheet_%s.png' % name))
    body.append('<h2>%s</h2><div class="g">%s</div>' % (html.escape(name.replace('_', ' ')), ''.join(
        '<a href="sharpness/%s_%s.png"><img src="sharpness/%s_%s.jpg?v=%d"><span>%s - %s</span></a>' % (name, k, name, k, int(time.time()), k, html.escape(l)) for k, l, _ in lst)))
page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Texture sharpness test</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}h1{font-size:20px}h2{font-size:16px;margin:22px 0 8px}small{color:#888;font-weight:400}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}a{color:#ddd;text-decoration:none;background:#1c1c1c;border-radius:8px;overflow:hidden;display:block}
img{width:100%%;height:auto;display:block}span{display:block;padding:6px 8px;font-size:13px}</style>
<h1>Texture sharpness test <small>%s, clear sky 13:00. Only texture sharpness changes between frames; nothing saved. Tap for the uncompressed frame.</small></h1>%s''' % (time.strftime('%Y-%m-%d %H:%M'), '\n'.join(body))
open(os.path.join(shots.ROOT, 'gallery', 'sharpness.html'), 'w', encoding='utf-8').write(page); print('page written')

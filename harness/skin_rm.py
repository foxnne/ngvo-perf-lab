"""Skin detail comparison on the player's face (user 2026-11-23): where does pore-level detail go, and which control brings
it back most naturally? One change per frame, live, nothing saved. Camera in front of the character's face.
usage: python skin_test.py TAG [travel command...]   (no travel = where the character stands)"""
import copy, html, json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
import numpy as np
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; TRAVEL = sys.argv[2:]; tb = shots.tb
OUT = os.path.join(shots.ROOT, 'results', 'skin', TAG); os.makedirs(OUT, exist_ok=True); GAL = os.path.join(shots.ROOT, 'gallery', 'skin'); os.makedirs(GAL, exist_ok=True)
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings', g)
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
FEATS = ('SubsurfaceScattering', 'Skin', 'NeuralRendering'); BASE = {n: get(n) for n in FEATS}
def sss_radius(r):
    def f(s):
        for k in ('BaseProfile', 'HumanProfile'): s['SubsurfaceScattering'][k]['BlurRadius'] = r
    return f
def sss_off(s):
    s['Skin']['DefaultProfile']['UseSSS'] = False
    for k in ('BaseProfile', 'HumanProfile'): s['SubsurfaceScattering'][k]['Strength'] = [0.0, 0.0, 0.0]
def detail(v):
    def f(s): s['Skin']['DefaultProfile']['SkinDetailStrength'] = v; s['Skin']['DefaultProfile']['EnableSkinDetail'] = v > 0
    return f
def nr_off(s): s['NeuralRendering']['enabled'] = False
def nr_full(s): s['NeuralRendering']['resolutionScale'] = 1.0
def nr_structure(s): s['NeuralRendering']['localStructureStrength'] = 1.41
VAR = [('A', 'AS NOW', []), ('B', 'SUBSURFACE OFF', [sss_off]), ('C', 'SUBSURFACE RADIUS HALF', [sss_radius(0.5)]), ('D', 'SUBSURFACE RADIUS QUARTER', [sss_radius(0.25)]),
       ('E', 'SKIN DETAIL LAYER 0.5', [detail(0.5)]), ('F', 'SKIN DETAIL LAYER OFF', [detail(0.0)]), ('G', 'NEURAL RENDERING OFF', [nr_off]),
       ('H', 'NEURAL AT FULL SIZE', [nr_full]), ('I', 'NEURAL STRUCTURE 1.41', [nr_structure]), ('J', 'RADIUS HALF + DETAIL 0.5', [sss_radius(0.5), detail(0.5)])]
if TRAVEL:
    tb(action='camera', mode='player'); bench.console(' '.join(TRAVEL)); time.sleep(8); shots.ready(25, 150)
    cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True)
def cam_at(ang, dist, fov):
    h = tb(action='view_get')['head']; a = math.radians(ang)
    cx, cy = h['x'] + math.sin(a) * dist, h['y'] + math.cos(a) * dist
    return dict(x=cx, y=cy, z=h['z'] + 2, pitch=0, yaw=(math.degrees(math.atan2(h['x'] - cx, h['y'] - cy))) % 360, fov=fov)
def skin_score(f):      # share of skin-coloured pixels in the middle of the frame
    a = np.asarray(Image.open(f).convert('RGB')).astype(float); H, W, _ = a.shape; c = a[H // 4:3 * H // 4, 3 * W // 8:5 * W // 8]
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    return float(((r > 90) & (r > g * 1.12) & (g > b * 1.05) & (r - b < 110) & (r - b > 25)).mean())
def find_face():        # the body's facing is not readable (the player angle follows the orbiting camera), so look from all round
    best = (-1, 0)
    for step, cands in ((45, range(0, 360, 45)), (15, None)):
        if cands is None: cands = [best[1] - 30, best[1] - 15, best[1] + 15, best[1] + 30]
        for ang in cands:
            tb(action='camera', mode='override', **cam_at(ang, 90, 30)); time.sleep(1.2); f = shots.grab('ff'); sc = skin_score(f); os.remove(f)
            print('  look from %d: skin %.3f' % (ang % 360, sc), flush=True)
            if sc > best[0]: best = (sc, ang)
    return best[1] % 360
def sharp(im):          # mean local contrast at the finest scale in the middle of the frame (the face)
    a = np.asarray(im.convert('L')).astype(float); H, W = a.shape; c = a[int(H * .17):int(H * .47), int(W * .50):int(W * .62)]
    return float(np.abs(c - (np.roll(c, 1, 0) + np.roll(c, -1, 0) + np.roll(c, 1, 1) + np.roll(c, -1, 1)) / 4).mean())
rows = []; frames = []
try:
    for key, label, fns in VAR:
        s = copy.deepcopy(BASE)
        for f in fns: f(s)
        for n in FEATS: put(n, s[n])
        time.sleep(4.0)
        f = shots.grab('sk'); d = os.path.join(OUT, 'face_%s.png' % key); shutil.move(f, d); im = Image.open(d).convert('RGB'); sp = sharp(im)
        rows.append((key, label, sp)); frames.append((key, label, d)); print('%s  %-28s fine detail measure %.3f' % (key, label, sp), flush=True)
finally:
    for n in FEATS: put(n, BASE[n])
    if TRAVEL: cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
body = []
for key, label, d in frames:
    im = Image.open(d).convert('RGB'); W, H = im.size; fs = int(H * 0.05); dr = ImageDraw.Draw(im); dr.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0))
    dr.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  %s' % (key, label), fill=(255, 230, 0), font=ImageFont.truetype('arialbd.ttf', fs))
    im.save(os.path.join(GAL, '%s_%s.png' % (TAG, key))); th = im.crop((int(W * .40), 0, int(W * .72), int(H * .62))); th.thumbnail((900, 900)); th.save(os.path.join(GAL, '%s_%s.jpg' % (TAG, key)), quality=88)
    body.append('<a href="skin/%s_%s.png"><img src="skin/%s_%s.jpg?v=%d"><span>%s - %s</span></a>' % (TAG, key, TAG, key, int(time.time()), key, html.escape(label)))
old = ''
pp = os.path.join(shots.ROOT, 'gallery', 'skin.html')
page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Skin test</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}h1{font-size:20px}h2{font-size:16px;margin:22px 0 8px}small{color:#888;font-weight:400}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}a{color:#ddd;text-decoration:none;background:#1c1c1c;border-radius:8px;overflow:hidden;display:block}
img{width:100%%;height:auto;display:block}span{display:block;padding:6px 8px;font-size:13px}</style>
<h1>Skin test <small>%s, set "%s". One change per frame, none saved. Framed by RaceMenu, clear sky 13:00. Thumbnails are the face; tap for the full uncompressed frame.</small></h1><div class="g">%s</div>''' % (time.strftime('%Y-%m-%d %H:%M'), TAG, '\n'.join(body))
open(pp, 'w', encoding='utf-8').write(page); json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w')); print('page written')

"""Green cast hunt on the After Upscaling placement (RaceMenu framing). usage: python nr_cast.py TAG HOUR"""
import copy, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs, shots, bench
import numpy as np
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; HOUR = float(sys.argv[2])
D = r'C:\Modlists\NGVO 8.0 Beta\Stock Game\Data\SKSE\Plugins\CommunityShaders'; F = os.path.join(D, 'NRModelPreset.txt')
OUT = os.path.join(shots.ROOT, 'results', 'nrface', TAG); os.makedirs(OUT, exist_ok=True)
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings', g)
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
NR = get('NeuralRendering'); cur = {'preset': None}
def setup(preset, skin=None, **kw):
    s = copy.deepcopy(NR); s.update(kw); s['resolutionScale'] = 1.0
    if skin is not None: s['skinStrengths'].update(skin)
    if preset != cur['preset']:
        os.makedirs(D, exist_ok=True); open(F, 'w').write(str(preset)); t = copy.deepcopy(s); t['resolutionScale'] = 0.9; put('NeuralRendering', t); time.sleep(5); cur['preset'] = preset
    put('NeuralRendering', s)
P = dict(preset=1, placement=1)
VAR = [('a', 'OURS (FINISHED, P0)', dict(preset=0, placement=3)), ('c', 'AFTER P1', dict(P)),
       ('j', 'AFTER P1 + SKIN HUE GUARD', dict(P, skin={'hueGuard': True})),
       ('k', 'AFTER P1 + SKIN BROAD 0.6', dict(P, skin={'broadLuminosity': 0.6})),
       ('l', 'AFTER P1 + HUE GUARD + COL 1.0', dict(P, skin={'hueGuard': True, 'colorStrength': 1.0})),
       ('m', 'AFTER P1 + RATIO GUARD 1.5', dict(P, ratioGuardEnabled=True, maxRatio=1.5))]
print([x for x in bench.menus()['openMenus'] if 'ace' in x]); cs.world(action='hour', value=HOUR); time.sleep(10)
W, H = 3440, 1440; box = (int(W * .41) - 280, int(H * .27) - 270, int(W * .41) + 280, int(H * .27) + 250); tiles = []
try:
    for key, label, kw in VAR:
        setup(**kw); time.sleep(13); f = shots.grab('nc'); d = os.path.join(OUT, key + '.png'); shutil.move(f, d)
        im = Image.open(d).convert('RGB'); a = np.asarray(im).astype(float)
        ck = a[int(H * .27) + 20:int(H * .27) + 80, int(W * .41) + 30:int(W * .41) + 80].reshape(-1, 3).mean(0)   # cheek under the eye, beside the nose
        c = im.crop(box); dr = ImageDraw.Draw(c); dr.rectangle((0, 0, 560, 40), fill=(0, 0, 0)); dr.text((8, 6), '%s  %s' % (key.upper(), label), fill=(255, 230, 0), font=ImageFont.truetype('arialbd.ttf', 22)); tiles.append(c)
        print('%s %-36s cheek rgb %3.0f %3.0f %3.0f  g/r %.3f' % (key, label, ck[0], ck[1], ck[2], ck[1] / ck[0]), flush=True)
finally:
    if os.path.exists(F): os.remove(F); os.rmdir(D)
    put('NeuralRendering', NR)
sh = Image.new('RGB', (560 * 3, 520 * 2))
for i, c in enumerate(tiles): sh.paste(c, ((i % 3) * 560, (i // 3) * 520))
sh.save(os.path.join(OUT, 'cmp.png'))

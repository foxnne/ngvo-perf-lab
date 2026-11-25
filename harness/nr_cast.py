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
VAR = [('a', 'FINISHED IMAGE (OURS), PRESET 0', dict(preset=0, placement=3)),
       ('b', 'AFTER UPSCALING, PRESET 0', dict(preset=0, placement=1)),
       ('c', 'AFTER UPSCALING, PRESET 1', dict(preset=1, placement=1)),
       ('d', 'AFTER, P1, SKIN COLOUR 1.0', dict(preset=1, placement=1, skin={'colorStrength': 1.0, 'detailLuminosity': 1.0})),
       ('e', 'AFTER, P1, SKIN COLOUR 0.5', dict(preset=1, placement=1, skin={'colorStrength': 0.5, 'detailLuminosity': 1.0})),
       ('f', 'AFTER, P1, NEUTWO CURVE', dict(preset=1, placement=1, proxyCurve=1)),
       ('g', 'AFTER, P1, LEGACY CURVE', dict(preset=1, placement=1, proxyCurve=2)),
       ('h', 'AFTER, P1, COLOUR STRENGTH 0 (ALL)', dict(preset=1, placement=1, colorStrength=0.0)),
       ('i', 'FINISHED IMAGE, PRESET 1', dict(preset=1, placement=3))]
print([x for x in bench.menus()['openMenus'] if 'ace' in x]); cs.world(action='hour', value=HOUR); time.sleep(10)
W, H = 3440, 1440; box = (int(W * .49), int(H * .14), int(W * .49) + 560, int(H * .14) + 520); tiles = []
try:
    for key, label, kw in VAR:
        setup(**kw); time.sleep(13); f = shots.grab('nc'); d = os.path.join(OUT, key + '.png'); shutil.move(f, d)
        im = Image.open(d).convert('RGB'); a = np.asarray(im).astype(float)
        ck = a[int(H * .36):int(H * .44), int(W * .545):int(W * .575)].reshape(-1, 3).mean(0)   # cheek under the eye, beside the nose
        c = im.crop(box); dr = ImageDraw.Draw(c); dr.rectangle((0, 0, 560, 40), fill=(0, 0, 0)); dr.text((8, 6), '%s  %s' % (key.upper(), label), fill=(255, 230, 0), font=ImageFont.truetype('arialbd.ttf', 22)); tiles.append(c)
        print('%s %-36s cheek rgb %3.0f %3.0f %3.0f  g/r %.3f' % (key, label, ck[0], ck[1], ck[2], ck[1] / ck[0]), flush=True)
finally:
    if os.path.exists(F): os.remove(F); os.rmdir(D)
    put('NeuralRendering', NR)
sh = Image.new('RGB', (560 * 3, 520 * 3))
for i, c in enumerate(tiles): sh.paste(c, ((i % 3) * 560, (i // 3) * 520))
sh.save(os.path.join(OUT, 'cmp.png'))

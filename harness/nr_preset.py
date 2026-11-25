"""Model preset sweep on the face (RaceMenu open): NRModelPreset.txt in the real Data folder, model recreated per value."""
import copy, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs, shots
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; EXTRA = dict(a.split('=') for a in sys.argv[2:])
D = r'C:\Modlists\NGVO 8.0 Beta\Stock Game\Data\SKSE\Plugins\CommunityShaders'; F = os.path.join(D, 'NRModelPreset.txt'); os.makedirs(D, exist_ok=True)
OUT = os.path.join(shots.ROOT, 'results', 'nrface', TAG); os.makedirs(OUT, exist_ok=True)
def get(): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'NeuralRendering'}); return g.get('settings', g)
def put(s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': s})
BASE = get(); W, H = 3440, 1440; box = (int(W * .49), int(H * .14), int(W * .49) + 560, int(H * .14) + 520); tiles = []
try:
    for p in (0, 1, 2, 3, 4):
        open(F, 'w').write(str(p))
        s = copy.deepcopy(BASE); s['resolutionScale'] = 0.9
        for k_, v in EXTRA.items(): s[k_] = type(BASE.get(k_, 0))(float(v)) if not isinstance(BASE.get(k_), bool) else v == '1'
        put(s); time.sleep(5); s['resolutionScale'] = 1.0; put(s); time.sleep(14)
        f = shots.grab('np'); d = os.path.join(OUT, 'preset_%d.png' % p); shutil.move(f, d)
        c = Image.open(d).convert('RGB').crop(box); dr = ImageDraw.Draw(c); dr.rectangle((0, 0, 250, 46), fill=(0, 0, 0)); dr.text((10, 4), 'PRESET %d' % p, fill=(255, 230, 0), font=ImageFont.truetype('arialbd.ttf', 34)); tiles.append(c); print('preset', p, flush=True)
finally:
    os.remove(F); os.rmdir(D); put(BASE)
sh = Image.new('RGB', (560 * 3, 520 * 2))
for i, c in enumerate(tiles): sh.paste(c, ((i % 3) * 560, (i // 3) * 520))
sh.save(os.path.join(OUT, 'cmp.png'))

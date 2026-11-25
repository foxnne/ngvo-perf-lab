"""NPC face set: spawn named NPCs one at a time in the sun at the stables, shoot neural off / as saved / full size.
usage: python npc_faces.py TAG [hour]"""
import copy, html, json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs, shots, bench
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; HOUR = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0; tb = shots.tb
OUT = os.path.join(shots.ROOT, 'results', 'npcfaces', TAG); GAL = os.path.join(shots.ROOT, 'gallery', 'npcfaces'); os.makedirs(OUT, exist_ok=True); os.makedirs(GAL, exist_ok=True)
NPCS = ['Ysolda', 'Heimskr', 'Irileth', 'Belethor', 'Carlotta Valentia', 'Farengar Secret-Fire', 'Adrianne Avenicci', 'Amren', 'Arcadia', 'Saadia', 'Eorlund Gray-Mane']
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings', g)
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
NR = get('NeuralRendering')
def nr(**kw): s = copy.deepcopy(NR); s.update(kw); put('NeuralRendering', s)
X, Y, Z, RZ = 18322.2, -10992.1, -4624.35, 200.0
cs.world(action='hour', value=HOUR); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(8)
tb(action='pin', x=X + 100, y=Y + 500, z=Z + 30)
W, H = 3440, 1440; box = (W // 2 - 520, H // 2 - 520, W // 2 + 520, H // 2 + 520); f24 = ImageFont.truetype('arialbd.ttf', 30); body = []
try:
    for name in NPCS:
        r = tb(action='spawn', npc=name, x=X, y=Y, z=Z, rz=RZ, ai=False)
        if 'eye' not in r: print('skip', name, json.dumps(r)[:120], flush=True); continue
        time.sleep(6); e = r['eye']
        if e['z'] - Z < 95: print('skip (not standing)', name, flush=True); tb(action='remove', id=r['id']); continue
        e = dict(e); e['z'] += 2; a = math.radians(RZ + 12); cx, cy = e['x'] + math.sin(a) * 80, e['y'] + math.cos(a) * 80
        tb(action='camera', mode='override', x=cx, y=cy, z=e['z'], pitch=0, yaw=math.degrees(math.atan2(e['x'] - cx, e['y'] - cy)) % 360, fov=36)
        key = name.split()[0].lower(); tiles = []
        for tag, label, kw, wait in (('off', 'NEURAL OFF', dict(enabled=False), 6), ('now', 'AS SAVED (0.75 SIZE)', dict(), 9), ('full', 'FULL SIZE', dict(resolutionScale=1.0), 15)):
            nr(**kw); time.sleep(wait); f = shots.grab('nf'); d = os.path.join(OUT, '%s_%s.png' % (key, tag)); shutil.move(f, d)
            c = Image.open(d).convert('RGB').crop(box); dr = ImageDraw.Draw(c); dr.rectangle((0, 0, 1040, 44), fill=(0, 0, 0)); dr.text((10, 5), '%s  -  %s' % (name.upper(), label), fill=(255, 230, 0), font=f24); tiles.append(c)
        sh = Image.new('RGB', (1040 * 3, 1040))
        for i, c in enumerate(tiles): sh.paste(c, (i * 1040, 0))
        sh.save(os.path.join(GAL, '%s_%s.png' % (TAG, key))); t = sh.copy(); t.thumbnail((1800, 600)); t.save(os.path.join(GAL, '%s_%s.jpg' % (TAG, key)), quality=88)
        body.append('<a href="npcfaces/%s_%s.png"><img src="npcfaces/%s_%s.jpg?v=%d"><span>%s: neural off / as saved / full size</span></a>' % (TAG, key, TAG, key, int(time.time()), html.escape(name)))
        tb(action='remove', id=r['id']); print('done', name, flush=True); time.sleep(1)
finally:
    put('NeuralRendering', NR); tb(action='clear'); tb(action='camera', mode='player'); p = tb(action='view_get')['player']; tb(action='unpin', x=X - 60, y=Y + 280, z=Z + 8)
    cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NPC faces</title>
<style>body{margin:0;padding:16px;background:#111;color:#ddd;font:15px system-ui}h1{font-size:20px}small{color:#888;font-weight:400}
a{color:#ddd;text-decoration:none;background:#1c1c1c;border-radius:8px;overflow:hidden;display:block;margin:0 0 12px}img{width:100%%;height:auto;display:block}span{display:block;padding:6px 8px;font-size:13px}</style>
<h1>NPC faces <small>%s, clear sky %g:00, set "%s". Each row: neural off, as saved, full size. Tap for native pixels.</small></h1>%s''' % (time.strftime('%Y-%m-%d %H:%M'), HOUR, TAG, '\n'.join(body))
open(os.path.join(shots.ROOT, 'gallery', 'npcfaces.html'), 'w', encoding='utf-8').write(page); print('page written')

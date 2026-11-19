"""NPC portrait set for Neural Rendering / skin tuning: spawns each named NPC in front of the player, starts a conversation
(the cinematic dialogue camera frames the face), freezes the frame and takes shots; also a fixed free-camera close-up.
usage: python npc_portraits.py TAG [--npcs "Ysolda,Camilla Valerius,..."] [--cell WhiterunExterior04] [--hour 12]
output: results/npc_portraits/TAG/<npc>_<n>.png and sheet.jpg     needs the bridge actions testbed spawn{npc} and talk."""
import json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image, ImageDraw
def opt(name, default=None): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'npc_portraits', TAG); os.makedirs(OUT, exist_ok=True)
NPCS = opt('--npcs', 'Ysolda,Camilla Valerius,Jenassa,Mjoll the Lioness,Serana,Hadvar,Balgruuf the Greater').split(',')
bench.launch(); bench.console('tgm'); bench.console('tcai')          # no combat while people are spawned
bench.goto(opt('--cell', 'WhiterunExterior04')); cs.world(action='hour', value=float(opt('--hour', '12'))); cs.world(action='weather', name='SunnyTU', instant=True, lock=True)
cs.world(action='teleport', x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=0.0, rz=160.0); time.sleep(10)
tiles = []; log = {}
TRACK = '--track' in sys.argv        # default: the static framing (routine off, frozen frame); --track keeps AI on so they look at the player
nr = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'NeuralRendering'}); nr = nr.get('settings', nr)
log['_neural_rendering'] = {k: nr.get(k) for k in ('enabled', 'resolutionScale', 'alternateFrames')}; print('Neural Rendering live:', log['_neural_rendering'], flush=True)
if not nr.get('enabled'): bench.quit_game(); sys.exit('Neural Rendering is OFF in this session: not taking shots')
# Neural Rendering resolution variants requested by the user (2026-11-18): 100% and 75%, never off. --scales 1.0,0.75
SCALES = [float(x) for x in opt('--scales', open(os.path.join(HERE, 'portrait_scales.txt')).read().strip() if os.path.exists(os.path.join(HERE, 'portrait_scales.txt')) else '1.0').split(',')]
def set_scale(sc):
    s2 = dict(nr); s2.update({'enabled': True, 'resolutionScale': sc, 'resolutionScaleX': sc, 'resolutionScaleY': sc})
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': s2}); time.sleep(7)
def shot(name):
    src = cs.shot('npc-' + name); time.sleep(1); dst = os.path.join(OUT, name + os.path.splitext(src)[1]); shutil.copy2(src, dst); return dst
VIEWS3 = [('front', 0, 62, 0, 30), ('three_quarter_left', -38, 66, 2, 30)]   # two views per NPC (user, 2026-11-18); was four, with three_quarter_right (38, 66, 2, 30) and low_wide (18, 95, -6, 38)
VIEWS3_UNUSED = [('placeholder', 0, 0, 0, 0)]   # name, angle around the face (deg), distance, pitch, fov
for npc in NPCS:
    key = npc.split()[0].lower()
    try:
        cs.world(action='teleport', x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=0.0, rz=160.0); time.sleep(2)
        s = bench.state_(); p = s['position']; hd = s['angleDeg']['z']; h = math.radians(hd)
        x, y = p['x'] + math.sin(h) * 130, p['y'] + math.cos(h) * 130
        r = cs.call('communityshaders.testbed', dict({'action': 'spawn', 'npc': npc, 'x': x, 'y': y, 'z': p['z'], 'rz': (hd + 180) % 360}, **({} if TRACK else {'ai': False})))
        if TRACK and 'refFormID' in r:                                      # AI stays on so they turn and look at the player; restrained so they do not walk home
            bench.console('prid ' + r['refFormID'][2:]); bench.console('setrestrained 1')
        if 'error' in r: print(npc, 'spawn failed', r, flush=True); log[npc] = r; continue
        info = None
        for _ in range(12):                                       # wait for the body, hair and face to load
            time.sleep(2)
            refs = cs.call('communityshaders.testbed', {'action': 'list'}).get('refs', [])
            info = next((q for q in refs if q['id'] == r['id']), None)
            if info and info.get('loaded3D') and info.get('eye'): break
        if not info or not info.get('eye'): print(npc, 'never loaded', info, flush=True); log[npc] = {'spawn': r, 'error': 'not loaded'}; continue
        time.sleep(7)                                             # time to notice the player and turn the head
        refs = cs.call('communityshaders.testbed', {'action': 'list'}).get('refs', []); info = next((q for q in refs if q['id'] == r['id']), info)
        e = info['eye']
        if TRACK: facing = math.atan2(p['x'] - e['x'], p['y'] - e['y'])                 # camera sits on the line to the player, so they look into it
        else: facing = math.radians(info['rz']); cs.world(action='freeze', on=True); time.sleep(1.0)   # the framing the user approved: still pose, frozen frame
        for sc in SCALES:
            if len(SCALES) > 1 or sc != 1.0: set_scale(sc)
            tagsc = '' if sc == 1.0 else '_nr%d' % round(sc * 100)
            for vname, ang, dist, pitch, fov in VIEWS3:
                a = facing + math.radians(ang)
                cx, cy = e['x'] + math.sin(a) * dist, e['y'] + math.cos(a) * dist
                cs.call('communityshaders.testbed', {'action': 'camera', 'x': cx, 'y': cy, 'z': e['z'] - 2 + (dist * math.tan(math.radians(pitch))), 'pitch': pitch, 'yaw': (math.degrees(a) + 180) % 360, 'fov': fov}); time.sleep(3)
                tiles.append((shot(f'{key}_{vname}{tagsc}'), f'{npc}: {vname}' + ('' if sc == 1.0 else '  NR %d%%' % round(sc * 100))))
        if len(SCALES) > 1 or SCALES[0] != 1.0: set_scale(1.0)
        cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        log[npc] = {'spawn': r, 'eye': e}
        cs.call('communityshaders.testbed', {'action': 'remove', 'id': r['id']}); time.sleep(2)
        print(npc, 'ok', r.get('baseFormID'), flush=True)
    except Exception as ex:
        print(npc, 'FAILED', str(ex)[:160], flush=True)
        try: cs.world(action='freeze', on=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
json.dump(log, open(os.path.join(OUT, 'log.json'), 'w'), indent=1)
if tiles:
    w, h = 860, 360; sheet = Image.new('RGB', (w * 4, (h + 26) * ((len(tiles) + 3) // 4)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    for i, (path, label) in enumerate(tiles):
        sheet.paste(Image.open(path).convert('RGB').resize((w, h)), ((i % 4) * w, (i // 4) * (h + 26) + 26)); d.text(((i % 4) * w + 8, (i // 4) * (h + 26) + 6), label, fill=(240, 240, 240))
    sheet.save(os.path.join(OUT, 'sheet.jpg'), quality=88)
try: cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': nr})
except Exception: pass
try: cs.call('communityshaders.testbed', {'action': 'clear'})
except Exception: pass
bench.quit_game()

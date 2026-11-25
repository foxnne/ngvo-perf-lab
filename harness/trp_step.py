"""One step of the Theo's Render Pipeline trial: write its user ini, restart, measure, shoot faces.
usage: python trp_step.py TAG Key=Value [Key=Value ...]     (keys go to [SourceDLSSG] of TheosRenderPipeline.User.ini)"""
import math, os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('NGVO_MENU_WAIT', '2400')
import bench, cs, shots
from PIL import Image
TAG = sys.argv[1]; KV = [a.split('=', 1) for a in sys.argv[2:]]; tb = shots.tb
INI = r'C:\Modlists\NGVO 8.0 Beta\overwrite\SKSE\Plugins\TheosRenderPipeline.User.ini'
LOG = os.path.expanduser(r'~\Documents\My Games\Skyrim Special Edition\SKSE\TheosRenderPipeline.log')
OUT = os.path.join(shots.ROOT, 'results', 'trp', TAG); os.makedirs(OUT, exist_ok=True)
if bench.running(): bench.quit_game(); time.sleep(8)
os.makedirs(os.path.dirname(INI), exist_ok=True)
open(INI, 'w', encoding='utf-8').write('[SourceDLSSG]\n' + ''.join('%s=%s\n' % (k, v) for k, v in KV)); print(open(INI).read(), flush=True)
bench.launch()
for i in range(40):
    m = bench.menus()
    if m.get('messageBoxOpen') and 'Main Menu' not in m.get('openMenus', []):
        bench.tap('right'); time.sleep(.6); bench.tap('enter'); time.sleep(3); continue
    s = bench.state_()
    if s.get('cell') and 'Loading Menu' not in m.get('openMenus', []) and i > 4: break
    time.sleep(3)
print('running', bench.running(), flush=True)
bench.console('coc WhiterunExterior01'); time.sleep(10); shots.ready(25, 150)
cs.world(action='hour', value=14.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(25)
pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']; print('stables frame avg %.1f ms p95 %.1f' % (pr['avgMs'], pr['p95Ms']), flush=True)
lines = [l for l in open(LOG, encoding='utf-8', errors='replace') if 'SourceDLSSG/SL' not in l and 'ngxLog' not in l]
for pat in (r'Performance NR\]', r'Performance D3D12\]', r'rolling percentiles'):
    hit = [l for l in lines if re.search(pat, l)]; print(hit[-1].strip()[:330] if hit else 'no line ' + pat, flush=True)
for l in lines:
    if re.search(r'(?i)\bNR\b|neural', l) and 'Performance' not in l and 'shortcuts' not in l: print('  ', l.strip()[:260])
    if re.search(r'(?i)reduced|refus|\[E\]|\[W\]', l): print(' !', l.strip()[:260])
# faces: two NPCs, then the character in RaceMenu
X, Y, Z, RZ = 18322.2, -10992.1, -4624.35, 200.0; W, H = 3440, 1440
tb(action='pin', x=X + 100, y=Y + 500, z=Z + 30)
for name in ('Adrianne Avenicci', 'Belethor'):
    r = tb(action='spawn', npc=name, x=X, y=Y, z=Z, rz=RZ, ai=False); time.sleep(6); e = r['eye']; a = math.radians(RZ + 12); cx, cy = e['x'] + math.sin(a) * 80, e['y'] + math.cos(a) * 80
    tb(action='camera', mode='override', x=cx, y=cy, z=e['z'] + 2, pitch=0, yaw=math.degrees(math.atan2(e['x'] - cx, e['y'] - cy)) % 360, fov=36); time.sleep(12)
    f = shots.grab('tr'); shutil.move(f, os.path.join(OUT, name.split()[0].lower() + '.png')); tb(action='remove', id=r['id'])
tb(action='clear'); tb(action='camera', mode='player'); tb(action='unpin', x=X - 60, y=Y + 280, z=Z + 8); time.sleep(3)
cs.world(action='console', command='showracemenu'); time.sleep(14); f = shots.grab('tr'); shutil.move(f, os.path.join(OUT, 'player.png'))
bench.tap('r'); time.sleep(2.5); bench.tap('enter'); time.sleep(4)
cs.world(action='weather', name='SunnyPF', instant=False, lock=False); print('shots done', OUT)

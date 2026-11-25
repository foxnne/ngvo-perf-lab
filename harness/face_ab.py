"""Exact face comparison across neural rendering stacks: fixed spot, fixed hour (time frozen), fixed camera maths.
Player via RaceMenu first (character teleported to an exact pose), then two NPCs spawned at the same spot.
usage: python face_ab.py TAG [ours|theo]     ours = also shoots the old-NGVO recipe as a second variant, live"""
import copy, json, math, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
TAG = sys.argv[1]; MODE = sys.argv[2] if len(sys.argv) > 2 else 'theo'; tb = shots.tb
OUT = os.path.join(shots.ROOT, 'results', 'faceab', TAG); os.makedirs(OUT, exist_ok=True)
X, Y, Z, RZ = 18322.2, -10992.1, -4624.35, 200.0
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings', g)
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
VARS = [('main', None)]
if MODE == 'ours':
    NR = get('NeuralRendering'); old = copy.deepcopy(NR); old.update(placement=3, style=1, automaticMask=False, rawModelOutput=True, resolutionScale=1.0)
    VARS = [('saved', NR), ('oldngvo', old)]
def shoot(name):
    for key, s in VARS:
        if s is not None: put('NeuralRendering', s); time.sleep(14)
        f = shots.grab('fa'); shutil.move(f, os.path.join(OUT, '%s_%s.png' % (name, key))); print('shot', name, key, flush=True)
    if MODE == 'ours': put('NeuralRendering', VARS[0][1]); time.sleep(8)
tb(action='camera', mode='player'); bench.console('coc WhiterunExterior01'); time.sleep(10); shots.ready(25, 150)
cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); cs.world(action='timescale', value=0)
cs.world(action='teleport', x=X, y=Y, z=Z, rz=RZ); time.sleep(45)
pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']; card = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader'], capture_output=True, text=True).stdout.strip()
print('stables frame avg %.1f ms p95 %.1f | card %s | box %s' % (pr['avgMs'], pr['p95Ms'], card, bench.menus().get('messageBoxOpen')), flush=True)
vt = r'C:\Modlists\NGVO 8.0 Beta\overwrite\SKSE\Plugins\CommunityShaders\VramTrack.jsonl'
if os.path.exists(vt):
    for r in [json.loads(x) for x in open(vt, encoding='utf-8') if x.strip()][-3:]:
        print('  tracker: proc %5.0f MB | created %5.0f MB/s freed %5.0f MB/s | %s' % (r['procMB'], r['newMB'] / max(r['dt'], .1), r['freedMB'] / max(r['dt'], .1), [(s['cat'], round(s['mb']), s['n']) for s in r.get('sites', [])[:3]]), flush=True)
cs.world(action='console', command='showracemenu'); time.sleep(14); print([x for x in bench.menus()['openMenus'] if 'ace' in x]); shoot('player')
bench.tap('r'); time.sleep(2.5); bench.tap('enter'); time.sleep(4)
tb(action='pin', x=X + 100, y=Y + 500, z=Z + 30)
for name in ('Adrianne Avenicci', 'Belethor'):
    r = tb(action='spawn', npc=name, x=X, y=Y, z=Z, rz=RZ, ai=False); time.sleep(6); e = r['eye']; a = math.radians(RZ + 12); cx, cy = e['x'] + math.sin(a) * 80, e['y'] + math.cos(a) * 80
    tb(action='camera', mode='override', x=cx, y=cy, z=e['z'] + 2, pitch=0, yaw=math.degrees(math.atan2(e['x'] - cx, e['y'] - cy)) % 360, fov=36); time.sleep(12)
    shoot(name.split()[0].lower()); tb(action='remove', id=r['id'])
tb(action='clear'); tb(action='camera', mode='player'); tb(action='unpin', x=X, y=Y, z=Z + 8)
cs.world(action='timescale', value=20); cs.world(action='weather', name='SunnyPF', instant=False, lock=False); print('done', OUT)

"""One view, one weather, a list of setting variants x hours: which setting fixes what. Variants are merged onto the cloud draft for that weather.
usage: python sky_sweep.py TAG VARIANTS.json [--view plains_west] [--group cloudy] [--hours 18.2]
VARIANTS.json: [{"name": "...", "set": {PhysicalSky keys, nested like the live settings}}, ...]   output: results/sky_sweep/TAG/"""
import atexit, copy, json, os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, hot
LAST = {}; SHADER_TOUCHED = set(); FAST = '--fast' in sys.argv
from PIL import Image, ImageDraw
DRAFT = 'C:/Users/foxnn/dev/nat3-volclouds'
def opt(name, default=None): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
TAG = sys.argv[1]; VARIANTS = json.load(open(sys.argv[2])); OUT = os.path.join(os.path.dirname(HERE), 'results', 'sky_sweep', TAG); os.makedirs(OUT, exist_ok=True)
VN = opt('--view', 'plains_west'); GRP = opt('--group', 'cloudy'); HOURS = [float(h) for h in opt('--hours', '18.2').split(',')]
V = json.load(open(os.path.join(HERE, 'views.json')))[VN]
rows = [[c.strip() for c in l.strip('|\n').split('|')] for l in open(DRAFT + '/notes/weather-table.md', encoding='utf-8') if re.match(r'\| \w+ \| `0x', l)]
REP = {}
for r in rows:
    if r[3] not in REP or (r[0].endswith(('TU', 'PF')) and not REP[r[3]][0].endswith(('TU', 'PF'))): REP[r[3]] = (r[0], r[1].strip('`'))
WNAME, KEY = REP[GRP]
PERIOD = lambda h: 'Day' if 8 <= h < 17 else 'Sunset' if 17 <= h < 19.5 else 'Dusk' if 19.5 <= h < 21 else 'Sunrise' if 6 <= h < 8 else 'Dawn' if 4.5 <= h < 6 else 'Night'
def merge(dst, src):
    for k, v in src.items():
        if k.startswith('_'): continue
        if isinstance(v, dict) and isinstance(dst.get(k), list) and set(v) <= set('xyzw'):
            for a, i in zip('xyzw', range(4)):
                if a in v and i < len(dst[k]): dst[k][i] = v[a]
        elif isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        else: dst[k] = v
VIEW_SAVE = 'harness_view_' + VN      # a save made at this view the first time it is visited: later runs load straight into it
bench.launch(save=VIEW_SAVE); bench.console('tgm'); bench.all_on()
DONE = []
atexit.register(lambda: (not DONE) and bench.running() and bench.quit_game())      # a failed run must not leave the game open: it stalls the job queue
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); orig = g.get('settings', g)
base = json.load(open(DRAFT + '/draft/foxnne-nat3-clouds/Baseline/PhysicalSky.json'))
if bench.LOADED_SAVE != VIEW_SAVE:
    bench.goto(V['cell']); cs.world(action='teleport', **V['player']); time.sleep(V.get('settle_seconds', 12))
    if '--no-view-save' not in sys.argv:
        try: print('view save', cs.call('game', {'action': 'save', 'name': VIEW_SAVE}), flush=True); time.sleep(6)
        except Exception as e: print('view save failed', str(e)[:120], flush=True)
else: time.sleep(8)
p = bench.state_()['position']; c = V['camera']
cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c['dx'], 'y': p['y'] + c['dy'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']})
cs.world(action='timescale', value=1); tiles = []; log = {}; OTHER = {}; READBACK = {}
try:
    for h in HOURS:
        cs.world(action='hour', value=h); cs.world(action='weather', name=WNAME, instant=True, lock=True); time.sleep(10)
        for var in VARIANTS:
            s = copy.deepcopy(orig)
            if '--stock' not in sys.argv: merge(s, base)       # --stock: no cloud draft, variants apply to the saved settings only
            f = f'{DRAFT}/draft/foxnne-nat3-clouds/Weather/{KEY}/{PERIOD(h)}/foxnne-nat3-clouds_PhysicalSky.json'
            if os.path.exists(f) and '--stock' not in sys.argv: merge(s, json.load(open(f)))
            merge(s, var.get('set', {}))
            hz = (s.get('aerosolType'), s.get('aerosolLoading'), s.get('aerosolHumidity'))
            if s.get('aerosolType') and hz != LAST.get('hz'):      # haze presets are only re-derived when the type CHANGES: force that, but only when the haze inputs differ
                s0 = copy.deepcopy(s); s0['aerosolType'] = 0
                cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s0}); time.sleep(1.0)
            LAST['hz'] = hz
            r = cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s})
            if var.get('shader'):                                   # shader constants: edit #defines in the deployed copy and hot reload (no restart)
                hot.set_defines(var['shader']['file'], var['shader']['defines']); hot.reload(); SHADER_TOUCHED.add(var['shader']['file'])
            for short, changes in var.get('features', {}).items():      # other features (e.g. PostProcessing, VolumetricLighting): set for this variant, restored after the shot
                gg = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); o2 = gg.get('settings', gg); OTHER.setdefault(short, o2)
                s2 = copy.deepcopy(OTHER[short]); merge(s2, changes); cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s2})
            for c in var.get('console', []): bench.console(c)          # console toggles (e.g. ts): switched for the shot, switched back after
            if var.get('weather'): cs.world(action='weather', name=var['weather'], instant=True, lock=True)
            cs.world(action='hour', value=h); time.sleep(float(var.get('settle', 12)))
            src = cs.shot(f'sweep-{TAG}-{var["name"]}-{h}'); time.sleep(1)
            name = re.sub(r'[^A-Za-z0-9_.+-]', '_', f'{var["name"]}__h{h:g}'); dst = os.path.join(OUT, name + os.path.splitext(src)[1]); shutil.move(src, dst)   # move, not copy: the game's Screenshots folder was filling with duplicates
            rb = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); rb = rb.get('settings', rb)
            READBACK[name] = {k: rb.get(k) for k in ('aerosolType', 'aerosolLoading', 'aerosolScatter', 'aerosolAbsorption', 'aerosolPhaseG', 'aerosolHumidity')}
            st = cs.stats(dst); log[name] = {'applied': r.get('applied', str(r)[:60]), 'mean': round(st['mean'], 3), 'sat': round(st['sat'], 3)}
            try:
                if FAST: raise RuntimeError('fast')                                                  # cost of this variant: median frame time over 4 s
                cs.call('communityshaders.frames', {'action': 'start'}); time.sleep(4); cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(0.6)
                fm = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {}).get('frameMs', [])
                if fm: log[name]['frame_ms'] = round(sorted(fm)[len(fm) // 2], 2)
            except Exception: pass
            tiles.append((dst, f'{var["name"]}  {h:g}h')); print(name, log[name], flush=True)
            for c in var.get('console', []): bench.console(c)
            if var.get('weather'): cs.world(action='weather', name=WNAME, instant=True, lock=True); time.sleep(8)
            for short in var.get('features', {}): cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': OTHER[short]})
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': orig})
    if SHADER_TOUCHED:
        hot.restore()
        try: hot.reload()
        except Exception: pass
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump({'view': VN, 'group': GRP, 'weather': WNAME, 'variants': VARIANTS, 'shots': log, 'haze_readback': READBACK}, open(os.path.join(OUT, 'log.json'), 'w'), indent=1)
cols = 4; w, hh = 860, 360
sheet = Image.new('RGB', (w * cols, (hh + 26) * ((len(tiles) + cols - 1) // cols)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, (path, label) in enumerate(tiles):
    sheet.paste(Image.open(path).convert('RGB').resize((w, hh)), ((i % cols) * w, (i // cols) * (hh + 26) + 26)); d.text(((i % cols) * w + 8, (i // cols) * (hh + 26) + 6), label, fill=(240, 240, 240))
sheet.save(os.path.join(OUT, 'sheet.jpg'), quality=88); print('sheet', len(tiles), flush=True)
DONE.append(1); bench.finish()

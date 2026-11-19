"""Sky lab: apply a cloud preset LIVE (no pack install) for one weather per group and shoot the reference views.
Preset source: the nat3-volclouds draft (Baseline + that weather's per-period file), deep-merged onto the live Physical Sky settings.
usage: python sky_lab.py TAG [--groups clear_sky,clear,cloudy,overcast,rain,storm,snow,fog] [--hours 12,18.2] [--views plains_west,ilinalta_west]
       [--override FILE.json]   (extra PhysicalSky values merged last, for tuning passes)   [--stock]  (skip the draft: shoot current settings)
output: results/sky_preset/TAG/<group>__<view>__h<hour>.png and sheet.jpg"""
import copy, json, os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image, ImageDraw
DRAFT = 'C:/Users/foxnn/dev/nat3-volclouds'
def opt(name, default=None): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'sky_preset', TAG); os.makedirs(OUT, exist_ok=True)
GROUPS = opt('--groups', 'clear_sky,clear,cloudy,overcast,rain,storm,snow,fog').split(',')
HOURS = [float(h) for h in opt('--hours', '12,18.2').split(',')]
VIEWS = json.load(open(os.path.join(HERE, 'views.json'))); VNAMES = opt('--views', 'plains_west,ilinalta_west').split(',')
OVERRIDE = json.load(open(opt('--override'))) if opt('--override') else {}
# one representative weather per group, first row of that group in the table that is a Tundra/Pine Forest variant if possible
rows = [[c.strip() for c in l.strip('|\n').split('|')] for l in open(DRAFT + '/notes/weather-table.md', encoding='utf-8') if re.match(r'\| \w+ \| `0x', l)]
REP = {}
for r in rows:
    g = r[3]; name = r[0]; key = r[1].strip('`')
    if g not in REP or (name.endswith(('TU', 'PF')) and not REP[g][0].endswith(('TU', 'PF'))): REP[g] = (name, key)
for r in rows:                                        # hand picks where the automatic one is a quest weather
    if r[0] in ('Snow',): REP.setdefault('_snowpick', (r[0], r[1].strip('`')))
if '_snowpick' in REP: REP['snow'] = REP.pop('_snowpick')
PERIOD = lambda h: 'Day' if 8 <= h < 17 else 'Sunset' if 17 <= h < 19.5 else 'Dusk' if 19.5 <= h < 21 else 'Sunrise' if 6 <= h < 8 else 'Dawn' if 4.5 <= h < 6 else 'Night'

def merge(dst, src):
    for k, v in src.items():
        if k.startswith('_'): continue
        if isinstance(v, dict) and isinstance(dst.get(k), list) and set(v) <= set('xyzw'):      # scene files write vectors as {x,y,z,w}
            for a, i in zip('xyzw', range(4)):
                if a in v and i < len(dst[k]): dst[k][i] = v[a]
        elif isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        elif k in dst or not dst: dst[k] = v
        else: MISSING.add(k); dst[k] = v
MISSING = set()

bench.launch(); bench.console('tgm')
bench.all_on()
pp = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PostProcessing'}); pp = pp.get('settings', pp)
LOOKSTATE = {k: (v.get('enabled') if isinstance(v, dict) else None) for k, v in pp.items() if k in ('LUT', 'Look Grade', 'Vignette', 'Local Exposure', 'Histogram Auto Exposure', 'Motion Blur', 'Depth of Field')}
print('look effects live:', LOOKSTATE, flush=True)
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); orig = g.get('settings', g)
json.dump(orig, open(os.path.join(OUT, 'physicalsky_before.json'), 'w'), indent=1)
base = json.load(open(DRAFT + '/draft/foxnne-nat3-clouds/Baseline/PhysicalSky.json'))
tiles = []; log = {}
try:
    for vn in VNAMES:
        v = VIEWS[vn]; bench.goto(v['cell']); cs.world(action='teleport', **v['player']); time.sleep(v.get('settle_seconds', 12))
        p = bench.state_()['position']; c = v['camera']
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + c['dx'], 'y': p['y'] + c['dy'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']})
        cs.world(action='timescale', value=1)
        for grp in GROUPS:
            if grp not in REP: print('no weather for group', grp, flush=True); continue
            wname, key = REP[grp]
            for h in HOURS:
                s = copy.deepcopy(orig)
                if '--stock' not in sys.argv:
                    merge(s, base)
                    f = f'{DRAFT}/draft/foxnne-nat3-clouds/Weather/{key}/{PERIOD(h)}/foxnne-nat3-clouds_PhysicalSky.json'
                    if os.path.exists(f): merge(s, json.load(open(f)))
                    else: print('no draft file', f, flush=True)
                merge(s, OVERRIDE)
                r = cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s})
                cs.world(action='hour', value=h); w = cs.world(action='weather', name=wname, instant=True, lock=True); time.sleep(14)
                src = cs.shot(f'sky-{TAG}-{grp}-{vn}-{h}'); time.sleep(1)
                name = f'{grp}__{vn}__h{h:g}'; dst = os.path.join(OUT, name + os.path.splitext(src)[1]); shutil.copy2(src, dst)
                st = cs.stats(src); log[name] = {'weather': wname, 'set_ok': r.get('ok', str(r)[:80]), 'weather_ok': w.get('ok'), 'mean': round(st['mean'], 3), 'p99': round(st['p99'], 3), 'clip%': round(st['clip%'], 2)}
                tiles.append((dst, f'{grp} ({wname})  {vn}  {h:g}h')); print(name, log[name], flush=True)
        cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': orig})
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    json.dump({'shots': log, 'keys_not_in_live_settings': sorted(MISSING)}, open(os.path.join(OUT, 'log.json'), 'w'), indent=1)
cols = len(HOURS) * len(VNAMES); w, h = 860, 360
order = sorted(tiles, key=lambda t: (GROUPS.index(os.path.basename(t[0]).split('__')[0]), t[0]))
sheet = Image.new('RGB', (w * cols, (h + 26) * ((len(order) + cols - 1) // cols)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, (path, label) in enumerate(order):
    sheet.paste(Image.open(path).convert('RGB').resize((w, h)), ((i % cols) * w, (i // cols) * (h + 26) + 26)); d.text(((i % cols) * w + 8, (i // cols) * (h + 26) + 6), label, fill=(240, 240, 240))
sheet.save(os.path.join(OUT, 'sheet.jpg'), quality=88); print('sheet', len(order), 'missing keys', sorted(MISSING), flush=True)
bench.quit_game()

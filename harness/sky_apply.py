"""Apply one sky candidate LIVE (nothing saved, camera untouched): saved settings + cloud draft base + the draft for GROUP + a variant.
usage: python sky_apply.py VARIANTS.json NAME [--shot TAG]
variant: {"name", "group": draft group whose cloud structure to start from, "weather": weather to force, "hour", "set": PhysicalSky, "features": {short: changes}}
'python sky_apply.py restore' reloads the saved settings."""
import copy, json, os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs, saved_fix
DRAFT = 'C:/Users/foxnn/dev/nat3-volclouds'
if sys.argv[1] == 'restore':
    print('saved file restored:', saved_fix.fix() or 'clean'); print(cs.call('communityshaders.settings', {'action': 'load'})); sys.exit()
var = [v for v in json.load(open(sys.argv[1])) if v['name'] == sys.argv[2]][0]
rows = [[c.strip() for c in l.strip('|\n').split('|')] for l in open(DRAFT + '/notes/weather-table.md', encoding='utf-8') if re.match(r'\| \w+ \| `0x', l)]
REP = {}
for r in rows:
    if r[3] not in REP or (r[0].endswith(('TU', 'PF')) and not REP[r[3]][0].endswith(('TU', 'PF'))): REP[r[3]] = (r[0], r[1].strip('`'))


def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), list) and set(v) <= set('xyzw'):
            for a, i in zip('xyzw', range(4)):
                if a in v and i < len(dst[k]): dst[k][i] = v[a]
        elif isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        else: dst[k] = v


print('saved file restored:', saved_fix.fix() or 'clean'); cs.call('communityshaders.settings', {'action': 'load'}); time.sleep(2.5)       # start from the saved settings every time
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); s = copy.deepcopy(g.get('settings', g))
if var.get('group'):
    merge(s, json.load(open(DRAFT + '/draft/foxnne-nat3-clouds/Baseline/PhysicalSky.json')))
    f = f'{DRAFT}/draft/foxnne-nat3-clouds/Weather/{REP[var["group"]][1]}/Day/foxnne-nat3-clouds_PhysicalSky.json'
    print('draft', var['group'], os.path.exists(f)); merge(s, json.load(open(f)))
merge(s, var.get('set', {}))
print('sky', str(cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s}))[:70])
for short, ch in var.get('features', {}).items():
    gg = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); s2 = copy.deepcopy(gg.get('settings', gg)); merge(s2, ch)
    print(short, str(cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s2}))[:60])
if var.get('weather'): cs.world(action='weather', name=var['weather'], instant=True, lock=True)
if var.get('hour'): cs.world(action='hour', value=var['hour'])
if '--shot' in sys.argv:
    time.sleep(16); src = cs.shot('apply-' + var['name']); d = os.path.join(os.path.dirname(HERE), 'results', 'sky_apply'); os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, var['name'] + os.path.splitext(src)[1]); shutil.move(src, dst); print('shot', dst, cs.stats(dst))

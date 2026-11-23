"""Baseline reference shots for the Looks Lab: views x time of day x sky type, with the Look Grade stage and the LUT OFF
(the lab applies the grade to these). Resumable: a shot whose PNG and manifest entry exist is skipped.

usage: python baseline_shoot.py TAG [--stage 1|2|all] [--plan baseline_plan.json] [--dry-run]
                                [--only-sky clear,rain] [--only-view plains_west,face_tight] [--only-time Day,Sunset]
                                [--limit N] [--redo] [--no-everything-on-check] [--period-model sun|clock]
  TAG        output folder name: results/baseline/TAG/  (PNG files, manifest.json, settings_snapshot.json, sheet.jpg)
  --period-model  sun (default): the plan's 'period_model' and 'times' (periods follow the sun, fork branch
             foxnne/scene-periods-sun). clock: 'period_model_clock' and 'times_clock', the model and hours used before
             (a game build without that branch, or with Periods Follow the Sun switched off).
  --dry-run  print the matrix, the count, the time estimate and the offline checks; touches neither game nor bridge
Queue:  python queue_runner.py add baseline_shoot.py TAG --stage 1
Lab set (compact: outdoors, interiors, dungeons):  baseline_shoot.py lab-baseline-02 --plan baseline_plan_lab.json
Like sky_sweep.py it attaches to a running game when the queue runner says so (NGVO_ATTACH / NGVO_KEEP_OPEN) and
otherwise launches one; on failure it closes the game so the queue is not stalled. Everything it changes live
(Physical Sky, fog, ambient, Post Processing toggles, camera, time scale, weather lock, god mode) is put back at the end; nothing is saved.

Places: every shot carries 'category' (exterior / interior / dungeon), 'place_layers' (the Scene Manager place layers it
belongs to) and 'period' / 'period_weights'. Indoor views (kind interior or dungeon, at a site marked "interior": true) are
shot once per time row and never get a weather: the script sets and locks a weather only outdoors, and releases any weather
lock (its own or one an earlier job left) before it travels indoors, so the cell shows its own interior weather.
A site is reached with 'coc <cell>' or, for places without a cell name, its 'travel' console command (cow Tamriel x y).
A views.json view marked "needs_camera_check": true has no checked framing yet: the camera then looks where the player
faces after arriving, the shot is flagged, and the camera used is written to the manifest so it can be copied to views.json.
"""
import atexit, copy, hashlib, json, math, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
LAB = os.path.dirname(HERE)


def opt(name, default=None): return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
def flag(name): return name in sys.argv
def csv(name): return [x for x in (opt(name) or '').split(',') if x]


# ------------------------------------------------------------------ plan
def load_plan(path):
    plan = json.load(open(path, encoding='utf-8'))
    plan['_hash'] = hashlib.sha1(open(path, 'rb').read()).hexdigest()[:12]
    kind = opt('--period-model', 'sun')
    if kind not in ('sun', 'clock'): raise SystemExit('--period-model must be sun or clock')
    if kind == 'clock':      # the earlier model and its hours table, kept in the plan as named alternatives
        if 'period_model_clock' not in plan or 'times_clock' not in plan: raise SystemExit('this plan has no clock model (period_model_clock / times_clock)')
        plan['period_model'], plan['times'] = plan['period_model_clock'], plan['times_clock']
    return plan


def category(kind):
    """The place tag of a shot: exterior, interior or dungeon (a face close-up is an exterior shot)."""
    return kind if kind in ('interior', 'dungeon') else 'exterior'


PLACE_LAYERS = {'exterior': [], 'interior': ['Interior'], 'dungeon': ['Interior', 'Dungeon']}     # Scene Manager / lab place layers per category


def period_factors_clock(hour, model):
    """Scene Manager CLOCK period weights for a game hour (the fork's model without periodsFollowSun, see the plan's
    period_model_clock note)."""
    names, starts, off = model['names'], model['starts'], model['blend_offsets']; n = len(names)
    end = lambda s, i: s[i + 1] if i + 1 < n else s[0] + 24.0
    blend = float(model.get('blend_hours', 1.0))
    for i in range(n):
        need = 1.0 + off[i] - off[(i + 1) % n]
        if need > 0: blend = min(blend, (end(starts, i) - starts[i]) / need)
    s = [starts[i] + off[i] * blend for i in range(n)]
    h = hour - blend * 0.5
    if h < 0: h += 24.0
    idx, ph = -1, h
    for i in range(n):
        e = end(s, i); x = h + 24.0 if (e > 24.0 and h < s[i]) else h
        if s[i] <= x < e: idx, ph = i, x; break
    f = {}
    if idx < 0: return {'Day': 1.0}
    to_end = end(s, idx) - ph
    if blend <= 0 or to_end >= blend: return {names[idx]: 1.0}
    p = max(0.0, min(1.0, to_end / blend)); smooth = p * p * p * (p * (p * 6.0 - 15.0) + 10.0)
    w = p + (smooth - p) * float(model.get('ease', 1.0))
    f[names[idx]] = round(w, 4); f[names[(idx + 1) % n]] = round(1.0 - w, 4)
    return {k: v for k, v in f.items() if v > 0}


def sun_clock(hour, sun):
    """Sky Sync's sun at a game hour: (elevation in degrees, hour of the highest point). Same maths as SkySync.cpp
    GetSunHorizonHours + CalculateAlternateSunDirection / CalculateVanillaSunDirection; sun: {path, timing, tilt_deg}."""
    t = sun['timing']; alt = sun['path'] == 'alternate'
    half = 0.25 if alt else float(sun.get('sun_alpha_trans_time', 2.0)) / 2.0
    sunrise, sunset = (t[0] + t[1]) / 12.0 - half, (t[2] + t[3]) / 12.0 + half; day = sunset - sunrise
    since = hour - sunrise if hour >= sunrise else hour + 24.0 - sunrise
    if alt:
        phase = math.pi * since / day if since < day else math.pi * (1.0 + (since - day) / (24.0 - day))
        z = math.sin(phase) * math.sin(math.radians(float(sun.get('tilt_deg', 55.0))))
    else:
        is_day = since < day
        x = (1.0 - 2.0 * since / day) * 400.0 if is_day else (2.0 * (since - day) / (24.0 - day) - 1.0) * 400.0
        zz = 400.0 - abs(x) if is_day else abs(x) - 400.0
        z = zz / math.sqrt(x * x + 25.0 * 25.0 + zz * zz)
    return math.degrees(math.asin(max(-1.0, min(1.0, z)))), (sunrise + sunset) / 2.0


def period_factors_sun(hour, model):
    """Sun-driven period weights (the fork's ScenePeriodSun.h): Night below night_elevation, Dawn / Dusk up to the horizon,
    Sunrise / Sunset up to day_elevation, Day above, each boundary blended over blend_degrees of sun elevation."""
    elevation, noon = sun_clock(hour, model['sun'])
    room = min(model['day_elevation'] - model['horizon_elevation'], model['horizon_elevation'] - model['night_elevation'])
    blend = min(max(float(model.get('blend_degrees', 3.0)), 0.0), max(room, 0.0)); ease = max(0.0, min(1.0, float(model.get('ease', 1.0))))
    def above(b):
        if blend <= 0: return 1.0 if elevation >= b else 0.0
        p = max(0.0, min(1.0, (elevation - b) / blend + 0.5)); smooth = p * p * p * (p * (p * 6.0 - 15.0) + 10.0)
        return p + (smooth - p) * ease
    a_n, a_h, a_d = above(model['night_elevation']), above(model['horizon_elevation']), above(model['day_elevation'])
    since = math.fmod(hour - noon, 24.0)
    if since < -12.0: since += 24.0
    elif since >= 12.0: since -= 24.0
    h = 0.25; to_midnight = 12.0 - abs(since)
    if abs(since) < h: rising = 0.5 - since / (2 * h)
    elif to_midnight < h: rising = 0.5 + to_midnight / (2 * h) if since < 0 else 0.5 - to_midnight / (2 * h)
    else: rising = 1.0 if since < 0 else 0.0
    twilight, low = max(a_n - a_h, 0.0), max(a_h - a_d, 0.0)
    w = [twilight * rising, low * rising, a_d, low * (1.0 - rising), twilight * (1.0 - rising), 1.0 - a_n]
    return {k: v for k, v in ((n, round(x, 4)) for n, x in zip(model['names'], w)) if v > 0}


def period_factors(hour, model):
    """Period weights for a game hour: model kind 'sun' (periods follow the sun) or the clock model (no kind / 'clock')."""
    return period_factors_sun(hour, model) if model.get('kind') == 'sun' else period_factors_clock(hour, model)


def dominant(f): return max(f.items(), key=lambda kv: kv[1])[0]


def nest(flat):
    """{'a.b.x': 1} -> {'a': {'b': {'x': 1}}} (the pass-3 types file uses flat dotted keys; whole-object values pass through)."""
    out = {}
    for k, v in flat.items():
        d = out; parts = k.split('.')
        for p in parts[:-1]: d = d.setdefault(p, {})
        d[parts[-1]] = v
    return out


def merge(dst, src):
    """Same rules as sky_sweep.merge: {'x':..,'y':..} onto a list sets components; dicts recurse; the rest replaces."""
    for k, v in src.items():
        if k.startswith('_'): continue
        if isinstance(v, dict) and isinstance(dst.get(k), list) and set(v) <= set('xyzw'):
            for a, i in zip('xyzw', range(4)):
                if a in v and i < len(dst[k]): dst[k][i] = v[a]
        elif isinstance(v, dict) and isinstance(dst.get(k), dict): merge(dst[k], v)
        else: dst[k] = v


_TYPES = {}
def sky_for(plan, sky_type, period):
    """Physical Sky 'set' (nested) and other-feature changes for a sky type in a period, from the pass-3 types file."""
    sky = plan['sky']; conf = sky['types'][sky_type]
    out = {'weather': conf['weather'], 'set': {}, 'features': {}, 'form_key': None, 'source': sky['mode']}
    if sky['mode'] != 'types_json': return out
    f = sky['types_file']
    if f not in _TYPES: _TYPES[f] = json.load(open(f, encoding='utf-8'))
    doc = _TYPES[f]; rep = doc['types'][sky_type]['representative']
    if rep['editorId'] != conf['weather']:
        raise SystemExit(f"plan weather {conf['weather']} for '{sky_type}' is not the representative in the types file ({rep['editorId']}): its values would not belong to that weather")
    flat = dict(rep['PhysicalSky.Day'])
    flat.update((rep.get('PhysicalSky.periodOverrides') or {}).get(period, {}))
    for k, v in (doc.get('globalOnly', {}).get('PhysicalSky') or {}).items(): flat[k] = v
    out['set'] = nest(flat); out['form_key'] = rep['formKey']
    slot = 'Night' if period == 'Night' else 'DawnDusk' if period in ('Dawn', 'Dusk') else 'Day'
    for feat in ('ExponentialHeightFog', 'ImageBasedLighting'):
        ch = {}
        for k, v in (rep.get(feat) or {}).items():
            name, _, suffix = k.partition('.')
            if suffix == slot and isinstance(v, (int, float)): ch[name] = v
        if ch: out['features'][feat] = ch
    return out


def check_plan(plan, vj):
    """Offline consistency of sites and views (run before anything is launched): a mistake here would otherwise show up as a
    wrong place, or as an outdoor weather forced inside a cell, minutes into a run."""
    times = {k for k in plan['times'] if not k.startswith('_')}
    sites = {k: v for k, v in plan['sites'].items() if not k.startswith('_')}
    warnings = plan.setdefault('_warnings', []); del warnings[:]
    for sid, site in sites.items():
        if bool(site.get('cell')) == bool(site.get('travel')): raise SystemExit('site %s needs either a cell or a travel command' % sid)
    for v in plan['views']:
        if v['site'] not in sites: raise SystemExit('view %s: unknown site %s' % (v['id'], v['site']))
        site = sites[v['site']]
        if (category(v['kind']) != 'exterior') != bool(site.get('interior')):
            raise SystemExit('view %s is kind %s but site %s is %s' % (v['id'], v['kind'], v['site'], 'marked interior' if site.get('interior') else 'not marked interior'))
        bad = [t for t in v.get('times', []) if t not in times]
        if bad: raise SystemExit('view %s: times %s are not rows of the plan (%s)' % (v['id'], bad, sorted(times)))
        if v.get('views_json'):
            if v['views_json'] not in vj: raise SystemExit('view %s is not in views.json' % v['views_json'])
            src = vj[v['views_json']]
            for k in ('cell', 'travel'):
                if src.get(k) != site.get(k): raise SystemExit('view %s: views.json %s %r differs from site %s %r' % (v['id'], k, src.get(k), v['site'], site.get(k)))
            if src.get('player') != site.get('player'):      # not fatal: the camera is relative to wherever the player stands, but the frame differs from sky_sweep's
                warnings.append('view %s: views.json player %s differs from site %s player %s' % (v['id'], src.get('player'), v['site'], site.get('player')))
        elif v['kind'] != 'face' and 'camera' not in v: raise SystemExit('view %s has neither views_json nor a camera' % v['id'])


def unchecked_camera(view, vj):
    """True while the view's framing has not been checked in game (views.json or plan "needs_camera_check": true)."""
    return bool(view.get('needs_camera_check') or (view.get('views_json') and vj[view['views_json']].get('needs_camera_check')))


def expand(plan, stage):
    """The ordered shot list: site -> sky type -> time -> view (fewest cell loads and weather changes).
    A view may list its own 'times' (row names); without it an outdoor view gets every row and an indoor view the rows of
    'interior_matrix'. Indoor views are shot once per time row, not per sky type: no weather is set for them."""
    stages = sorted(plan['stages']) if stage == 'all' else [stage]
    only_sky, only_view, only_time = csv('--only-sky'), csv('--only-view'), csv('--only-time')
    times = {k: v for k, v in plan['times'].items() if not k.startswith('_')}
    vj = json.load(open(os.path.join(HERE, 'views.json'), encoding='utf-8'))
    check_plan(plan, vj)
    shots = []
    for site_id, site in plan['sites'].items():
        if site_id.startswith('_'): continue
        views = [v for v in plan['views'] if v['site'] == site_id and (not only_view or v['id'] in only_view)]
        if not views: continue
        for st in stages:
            skies = [s for s in plan['stages'][st]['sky_types'] if not only_sky or s in only_sky]
            for si, sky in enumerate(skies):
                for tname, trow in times.items():
                    if only_time and tname not in only_time: continue
                    for v in views:
                        cat = category(v['kind']); indoor = cat != 'exterior'
                        rows = v.get('times') or (plan['interior_matrix'].get(v['kind'], []) if indoor else None)
                        if rows is not None and tname not in rows: continue
                        if indoor and si != 0: continue
                        if not indoor and 'skies' in v and sky not in v['skies']: continue   # per-view weather list (lab plan)
                        hour = float(trow['hour']); pf = period_factors(hour, plan['period_model'])
                        sky_label = 'indoor' if indoor else sky          # an indoor shot belongs to no sky type: its weather is the cell's own
                        name = re.sub(r'[^A-Za-z0-9_.+-]', '_', f"{v['id']}__{sky_label}__{tname.lower()}_h{hour:g}")
                        shot = {'id': name, 'file': name + '.png', 'view': v['id'], 'site': site_id, 'kind': v['kind'], 'category': cat, 'place_layers': PLACE_LAYERS[cat],
                                'cell': site.get('cell') or site['travel'], 'stage': st, 'sky_type': None if indoor else sky, 'sky_label': sky_label,
                                'weather': None if indoor else plan['sky']['types'][sky]['weather'], 'time_row': tname, 'hour': hour,
                                'period': dominant(pf), 'period_weights': pf}
                        if unchecked_camera(v, vj): shot['needs_camera_check'] = True
                        shots.append(shot)
    return shots


# ------------------------------------------------------------------ offline checks
def static_neutral_check(plan):
    """Reads the saved settings (never writes): can anything outside this script switch the grade or the LUT back on?"""
    notes, problems = [], []
    n = plan['neutral']; off = set(n['post_processing_off'])
    try:
        sm = json.load(open(n['scene_manager_file'], encoding='utf-8-sig'))
        def entries():
            for e in sm.get('interiorOnly', []): yield 'interior', e
            for e in sm.get('timeOfDay', []): yield 'timeOfDay', e
            for k, v in (sm.get('weather') or {}).items():
                for e in v.get('entries', []): yield 'weather ' + k, e
            for grp in (sm.get('location') or {}).values():
                for k, v in (grp or {}).items():
                    for e in v.get('entries', []): yield 'location ' + k, e
        total = active = toggles = 0
        for where, e in entries():
            if e.get('feature') != 'PostProcessing' or not e.get('path') or e['path'][0] not in off: continue
            total += 1
            if not e.get('paused'): active += 1
            if e.get('setting') == 'enabled' and not e.get('paused'): toggles += 1; problems.append(f'Scene Manager entry switches {e["path"][0]} on/off ({where})')
        notes.append(f'Scene Manager user file: {total} entries on {sorted(off)}, {active} not paused')
        if active: notes.append('  note: un-paused entries only change slider values; with the stage disabled they do not reach the image')
    except Exception as e:
        notes.append('Scene Manager file not read: %s' % str(e)[:100])
    try:
        su = json.load(open(n['settings_user_file'], encoding='utf-8-sig')); pp = su.get('Post Processing') or su.get('PostProcessing') or {}
        for k in sorted(off): notes.append(f'saved user setting  Post Processing / {k} / enabled = {pp.get(k, {}).get("enabled", "(not saved: pack or default value applies)")}')
        notes.append('saved presets: %s' % json.dumps(su.get('Presets')))
        hd = su.get('HDR Display') or {}
        notes.append('saved HDR Display: %s' % json.dumps(hd))
    except Exception as e:
        notes.append('user settings file not read: %s' % str(e)[:100])
    return notes, problems


def build_info(plan):
    b = plan['build']; out = {}
    try:
        st = os.stat(b['dll']); h = hashlib.sha1()
        with open(b['dll'], 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
        out.update(dll=b['dll'], dll_date=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)), dll_size=st.st_size, dll_sha1=h.hexdigest()[:16])
    except OSError as e: out['dll_error'] = str(e)[:100]
    try:
        g = lambda *a: subprocess.run(['git', '-C', b['fork'], *a], capture_output=True, text=True).stdout.strip()
        out.update(fork_head=g('rev-parse', '--short', 'HEAD'), fork_branch=g('branch', '--show-current'), fork_head_date=g('log', '-1', '--format=%cI'),
                   fork_dirty=bool(g('status', '--porcelain', '--untracked-files=no')))
    except Exception as e: out['fork_error'] = str(e)[:100]
    return out


# ------------------------------------------------------------------ image statistics
def image_stats(path, view, pcts):
    """Luminance statistics on the display-encoded (sRGB) values, 0..1: the same numbers the grade's Black Point works on.
    near / far are fixed regions of the frame per view (no depth buffer needed): foreground strip and distance band."""
    import numpy as np
    from PIL import Image
    im = Image.open(path); mode, size = im.mode, im.size
    a = np.asarray(im.convert('RGB')).astype(np.float32) / 255.0
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    H, W = lum.shape
    def region(r):
        x0, y0, x1, y1 = r; return lum[int(y0 * H):max(int(y1 * H), int(y0 * H) + 1), int(x0 * W):max(int(x1 * W), int(x0 * W) + 1)]
    def dark(v):
        d = {('p%g' % p): round(float(np.percentile(v, p)), 4) for p in pcts}
        d['min'] = round(float(v.min()), 4); d['mean'] = round(float(v.mean()), 4); d['crushed_pct'] = round(float((v <= 2.0 / 255.0).mean() * 100), 3)
        return d
    return {'resolution': [size[0], size[1]], 'mode': mode,
            'mean': round(float(lum.mean()), 4), 'p1': round(float(np.percentile(lum, 1)), 4), 'p50': round(float(np.percentile(lum, 50)), 4),
            'p99': round(float(np.percentile(lum, 99)), 4), 'clip_pct': round(float((mx > 0.98).mean() * 100), 3), 'sat': round(float(sat.mean()), 4),
            'mean_rgb': [round(float(a[..., i].mean()), 4) for i in range(3)],
            'dark': {'all': dark(lum), 'near': dark(region(view['near'])), 'far': dark(region(view['far']))},
            'regions': {'near': view['near'], 'far': view['far']}}


def jhash(o): return hashlib.sha1(json.dumps(o, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:12]


def save_json(path, o):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(o, f, indent=1)
    os.replace(tmp, path)


# ------------------------------------------------------------------ dry run
def dry_run(plan, shots, out_dir, manifest):
    have = {s['id'] for s in manifest.get('shots', []) if os.path.exists(os.path.join(out_dir, s['file']))}
    todo = [s for s in shots if s['id'] not in have or flag('--redo')]
    print('PLAN', plan['_hash'], '| output', out_dir)
    print('\nTimes (hour -> Scene Manager period weights):')
    for k, v in plan['times'].items():
        if not k.startswith('_'): print('  %-8s %5.2f  %s' % (k, v['hour'], period_factors(float(v['hour']), plan['period_model'])))
    print('\nSky types (outdoor shots; mode %s):' % plan['sky']['mode'])
    seen = []
    for s in shots:
        if s['sky_type'] and s['sky_type'] not in seen:
            seen.append(s['sky_type']); sk = sky_for(plan, s['sky_type'], 'Day')
            print('  %-9s stage %s  weather %-12s %-22s Physical Sky keys %d, other features %s' % (s['sky_type'], s['stage'], sk['weather'], sk['form_key'], len(json.dumps(sk['set'])), list(sk['features'])))
    cols = seen + (['indoor'] if any(s['sky_label'] == 'indoor' for s in shots) else [])
    print('\nMatrix (rows: view; columns: sky type, or indoor = no weather set; cell: number of times):')
    views = []; [views.append(s['view']) for s in shots if s['view'] not in views]
    print('  %-22s%-10s' % ('view', 'category') + ''.join('%-10s' % k for k in cols) + 'total')
    for v in views:
        row = [sum(1 for s in shots if s['view'] == v and s['sky_label'] == k) for k in cols]
        print('  %-22s%-10s' % (v, next(s['category'] for s in shots if s['view'] == v)) + ''.join('%-10d' % c for c in row) + str(sum(row)))
    print('\nShot list (order of shooting%s):' % ('' if len(shots) <= 40 or flag('--list') else '; first 40, --list for all'))
    for s in (shots if len(shots) <= 40 or flag('--list') else shots[:40]): print('  %-46s %-9s %-7s %-10s %s%s' % (s['id'], s['category'], s['period'], s['weather'] or '(cell\'s own)', s['cell'], '   CAMERA NOT CHECKED' if s.get('needs_camera_check') else ''))
    combos = {(s['site'], s['sky_label'], s['time_row']) for s in todo}; sites = {s['site'] for s in todo}; wchg = {(s['site'], s['sky_type']) for s in todo if s['sky_type']}
    sk = plan['sky']; cap = plan['capture']
    est = sum(30 + plan['sites'][x].get('settle_seconds', 12) for x in sites) + len(wchg) * sk['weather_settle_seconds'] + (len(combos) - len(wchg)) * (sk['hour_settle_seconds'] + 3) \
        + len(todo) * (cap['camera_settle_seconds'] + 5) + sum(9 for s in todo if s['kind'] == 'face' and cap.get('face_pose_check'))
    print('\nShots in plan: %d | already on disk: %d | to shoot: %d' % (len(shots), len(shots) - len(todo), len(todo)))
    print('Estimate from the plan\'s settle times: %.0f min attached to a running game (sites %d, weather changes %d, time changes %d); a fresh launch adds about 5-10 min'
          % (est / 60, len(sites), len(wchg), len(combos)))
    unchecked = sorted({s['view'] for s in shots if s.get('needs_camera_check')})
    if unchecked: print('Camera not checked in game (framed along the player\'s facing, flagged in the manifest): %s' % ', '.join(unchecked))
    for w in plan.get('_warnings', []): print('WARNING: ' + w)
    notes, problems = static_neutral_check(plan)
    print('\nNeutral check (offline part; the live part reads Post Processing back before every shot):')
    for n in notes: print('  ' + n)
    for p in problems: print('  PROBLEM: ' + p)
    print('\nBuild:', json.dumps(build_info(plan)))
    if flag('--list'):
        for s in todo: print(' ', s['file'], s['period_weights'])
    print('\nDRY RUN: nothing was launched, the bridge was not contacted, no file was written.')


# ------------------------------------------------------------------ live run
def live(plan, shots, out_dir, manifest):
    import bench, cs
    from PIL import Image, ImageDraw
    import numpy as np
    vj = json.load(open(os.path.join(HERE, 'views.json'), encoding='utf-8'))
    by_id = {s['id']: s for s in manifest.get('shots', [])}
    done = lambda s: (not flag('--redo')) and s['id'] in by_id and os.path.exists(os.path.join(out_dir, s['file']))
    todo = [s for s in shots if not done(s)]
    lim = int(opt('--limit', '0'))
    if lim: todo = todo[:lim]
    print('baseline %s: %d shots in plan, %d to shoot' % (TAG, len(shots), len(todo)), flush=True)
    if not todo: print('nothing to do'); return
    notes, problems = static_neutral_check(plan)
    for n in notes: print('neutral(offline):', n, flush=True)
    if problems: raise SystemExit('neutral check failed before launch: %s' % problems)
    for w in plan.get('_warnings', []): print('WARNING:', w, flush=True)

    # God mode ON for the run (falls after travel, hostiles in the dungeon cells). tgm is a toggle and the bridge has no
    # read-back for it, so it is switched back OFF in the restore steps at the end (a failed run closes the game instead).
    bench.launch(); bench.console('tgm')
    FINISHED = []
    atexit.register(lambda: (not FINISHED) and bench.running() and bench.quit_game())     # a failed run must not leave the game open: it stalls the queue
    everything = bench.all_on(strict=not flag('--no-everything-on-check'))
    get = lambda short: (lambda g: g.get('settings', g))(cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}))
    put = lambda short, s: cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
    ps0 = get('PhysicalSky'); pp0 = get('PostProcessing'); world0 = bench.state_(); OTHER = {}
    if not isinstance(pp0, dict) or 'Look Grade' not in pp0 or 'LUT' not in pp0: raise SystemExit('Post Processing settings do not hold Look Grade / LUT: %s' % str(pp0)[:200])
    neutral = plan['neutral']
    pp_n = copy.deepcopy(pp0)                                    # always the FULL blob: a partial set resets the stages left out
    for k in neutral['post_processing_off']: pp_n[k]['enabled'] = False
    def verify_neutral():
        rb = get('PostProcessing'); bad = [k for k in neutral['post_processing_off'] if rb.get(k, {}).get('enabled') is not False]
        if bad: raise SystemExit('NOT NEUTRAL: %s still enabled on read-back' % bad)
        return rb
    put('PostProcessing', pp_n); time.sleep(1.0); rb = verify_neutral()
    pp_enabled = {k: v.get('enabled') for k, v in rb.items() if isinstance(v, dict) and 'enabled' in v}
    warn_on = [k for k in neutral.get('post_processing_warn_if_on', []) if pp_enabled.get(k)]
    hdr = None
    try: hdr = get('HDRDisplay').get('enableHDR')
    except Exception: pass
    if neutral.get('hdr_must_be_off') and hdr is True: raise SystemExit('HDR output is on: the lab works on SDR frames')
    print('neutral(live): Look Grade and LUT read back disabled; stages enabled: %s; after-grade stages on: %s; HDR %s' % (pp_enabled, warn_on or 'none', hdr), flush=True)

    manifest.update({'schema': 'ngvo-baseline-manifest/1', 'tag': TAG, 'plan_file': os.path.abspath(PLAN_PATH), 'plan_hash': plan['_hash'],
                     'updated': time.strftime('%Y-%m-%d %H:%M:%S'), 'build': build_info(plan), 'period_model': {k: v for k, v in plan['period_model'].items() if not k.startswith('_')},
                     'times': {k: v for k, v in plan['times'].items() if not k.startswith('_')},
                     'views': {v['id']: dict({k: v[k] for k in ('site', 'kind', 'near', 'far')}, category=category(v['kind']), place_layers=PLACE_LAYERS[category(v['kind'])],
                                             **({'needs_camera_check': True} if unchecked_camera(v, vj) else {})) for v in plan['views']},
                     'sky_mode': plan['sky']['mode'],
                     'neutral': {'definition': 'Post Processing stages %s disabled live, not saved (read back before every shot); everything else as saved' % neutral['post_processing_off'],
                                 'post_processing_enabled': pp_enabled, 'after_grade_stages_on': warn_on, 'hdr': hdr, 'offline_notes': notes},
                     'everything_on': everything})
    manifest.setdefault('created', manifest['updated']); manifest.setdefault('shots', [])
    save_json(os.path.join(out_dir, 'settings_snapshot.json'), {'PhysicalSky': ps0, 'PostProcessing': pp0, 'PostProcessing_neutral': pp_n, 'world': world0})
    MAN = os.path.join(out_dir, 'manifest.json')
    views = {v['id']: v for v in plan['views']}
    sk = plan['sky']; cap = plan['capture']; LAST = {}

    def camera(view):
        """Places the free camera for a view; returns the camera used (absolute), for the manifest."""
        st = bench.state_(); p = st['position']
        if view['kind'] == 'face': bench.face_camera(True, **view['face']); return {'face': view['face']}
        c = vj[view['views_json']]['camera'] if view.get('views_json') else view['camera']
        facing = unchecked_camera(view, vj) or c.get('yaw') == 'player'      # no checked framing: look where the player faces after arriving (the yaw in views.json is a placeholder)
        cam = {'x': p['x'] + c['dx'], 'y': p['y'] + c['dy'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': float(st['angleDeg']['z'] if facing else c['yaw']), 'fov': c['fov']}
        cs.call('communityshaders.testbed', dict(cam, action='camera'))
        return dict(cam, yaw_from='player facing' if facing else 'view', player={'x': p['x'], 'y': p['y'], 'z': p['z'], 'rz': st['angleDeg']['z']})

    def travel(site):
        if site.get('travel'):                                               # a place without a cell name (cow Tamriel x y), as aspen_check.py / grass_shots.py do it
            bench.console(site['travel']); time.sleep(8)
            if not bench.settle(): raise RuntimeError('could not reach ' + site['travel'])
            last = None
            for _ in range(15):                                              # far travel: wait until the player has stopped moving (landed)
                p = bench.pos()
                if last and max(abs(a - b) for a, b in zip(p, last)) < 5: break
                last = p; time.sleep(2)
            time.sleep(3)
        else: bench.goto(site['cell'])

    def weather_ref(w):
        """Bridge arguments naming a weather from a state read-back ({editorID, formID})."""
        w = w or {}
        return {'name': w['editorID']} if w.get('editorID') else {'id': w['formID']} if w.get('formID') else None

    def release_weather_lock():
        """Releases a weather lock (this job's, or one an earlier job left) and keeps the current weather. A lock re-forces
        its weather on every sky update, also after a cell change, so an interior entered while locked shows that outdoor weather.
        instant=True is the bridge's ForceWeather without override: it cannot leave the weather pinned once the lock is gone."""
        st = bench.state_(); ref = weather_ref(st.get('weather'))
        locked = st['weatherLocked'] if 'weatherLocked' in st else LAST.get('locked')
        if locked and ref: cs.world(action='weather', instant=True, lock=False, **ref); time.sleep(1.0)
        LAST['locked'] = False

    def restore_saved_sky():
        """Physical Sky and the other features a sky type changed go back to the values found at the start (types_json mode)."""
        if not LAST.get('sky_applied'): return
        put('PhysicalSky', ps0); [put(k, v) for k, v in OTHER.items()]
        LAST['sky_applied'] = False; LAST.pop('hz', None)

    def apply_sky(s):
        skyset = sky_for(plan, s['sky_type'], s['period']); applied = {'PhysicalSky': None, 'features': {}}
        if sk['mode'] == 'types_json':
            v = copy.deepcopy(ps0); merge(v, skyset['set'])
            hz = (v.get('aerosolType'), v.get('aerosolLoading'), v.get('aerosolHumidity'))
            if v.get('aerosolType') and hz != LAST.get('hz'):          # haze presets are only re-derived when the type changes (see sky_sweep.py)
                v0 = copy.deepcopy(v); v0['aerosolType'] = 0; put('PhysicalSky', v0); time.sleep(1.0)
            LAST['hz'] = hz; put('PhysicalSky', v); applied['PhysicalSky'] = skyset['set']; LAST['sky_applied'] = True
            for short in set(OTHER) | set(skyset['features']):         # every feature touched so far goes back to saved + this type's changes
                OTHER.setdefault(short, get(short)); v2 = copy.deepcopy(OTHER[short]); merge(v2, skyset['features'].get(short, {})); put(short, v2)
                applied['features'][short] = skyset['features'].get(short, {})
        return skyset, applied

    cur_site = None; cur_combo = None; cur_weather = None; skyset = applied = None; tiles = []; failed_restores = []
    try:
        cs.world(action='timescale', value=1)
        for s in todo:
            site = plan['sites'][s['site']]; view = views[s['view']]; indoor = bool(site.get('interior'))
            combo = (s['sky_label'], s['time_row'])
            # Indoors the hour is set BEFORE the cell loads and never inside it: Helios swaps an interior copy of the outside
            # weather into windowed cells on entry, and an hour change inside rolls a new weather it does not resync until
            # re-entry (window light and sun patches vanish). A new hour at the same indoor site therefore re-enters the cell.
            if s['site'] != cur_site or (indoor and combo != cur_combo):
                try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
                except Exception: pass
                if indoor:
                    release_weather_lock(); restore_saved_sky()      # the interior must come up with its own (Helios) weather and the saved sky
                    cs.world(action='hour', value=s['hour']); time.sleep(sk['hour_settle_seconds'])
                travel(site)
                if site.get('player'): cs.world(action='teleport', **site['player'])
                time.sleep(site.get('settle_seconds', 12)); cur_site = s['site']; cur_weather = None
                cur_combo = combo if indoor else None
                if indoor:
                    skyset = {'form_key': None, 'source': 'cell (Helios interior weather, hour set before entry)'}; applied = {'PhysicalSky': None, 'features': {}}
            if not indoor and combo != cur_combo:
                wchg = s['weather'] != cur_weather
                cs.world(action='hour', value=s['hour'])
                if wchg: cs.world(action='weather', name=s['weather'], instant=True, lock=True); cur_weather = s['weather']; LAST['locked'] = True
                skyset, applied = apply_sky(s)
                cs.world(action='hour', value=s['hour'])
                time.sleep(sk['weather_settle_seconds'] if wchg else sk['hour_settle_seconds']); cur_combo = combo
            flags = []
            frozen = False
            try:
                cam = camera(view); time.sleep(cap['camera_settle_seconds'])
                if s.get('needs_camera_check'): flags.append('camera not checked: framed along the player facing')
                if view['kind'] == 'face':
                    cs.world(action='freeze', on=True); frozen = True; time.sleep(1.0)
                    if cap.get('face_pose_check'):
                        lum = lambda p: np.asarray(Image.open(p).convert('RGB').resize((860, 360))).astype(np.float32).mean(axis=2) / 255
                        pa = cs.shot('baseline-posecheck1'); a = lum(pa); time.sleep(3); pb = cs.shot('baseline-posecheck2'); b = lum(pb)
                        d = float(np.abs(a - b).mean())
                        for p in (pa, pb):
                            try: os.remove(p)
                            except OSError: pass
                        if d > cap['face_pose_max_diff']: flags.append('pose_moving %.4f' % d)
                rb = verify_neutral()
                src = cs.shot('baseline-' + s['id']); time.sleep(1.0)
                dst = os.path.join(out_dir, s['file']); shutil.move(src, dst)       # move: keep the game's Screenshots folder from filling
            finally:
                if frozen: cs.world(action='freeze', on=False)
                if view['kind'] == 'face':
                    try: bench.face_camera(False)
                    except Exception: pass
            st = image_stats(dst, view, cap['dark_percentiles'])
            if cap.get('expect_resolution') and st['resolution'] != cap['expect_resolution']: flags.append('resolution %s' % st['resolution'])
            if st['mode'] not in ('RGB', 'RGBA'): flags.append('image mode %s' % st['mode'])
            w = bench.state_()
            wrb = (w.get('weather') or {}); crb = (w.get('cell') or {})
            if not indoor and str(wrb.get('editorID', wrb.get('editorId', ''))).lower() not in ('', s['weather'].lower()): flags.append('weather read back %s' % wrb.get('editorID', wrb.get('editorId')))
            if indoor and w.get('weatherLocked'): flags.append('weather locked indoors (%s)' % wrb.get('editorID'))
            if 'interior' in crb and bool(crb['interior']) != indoor: flags.append('cell %s is %s' % (crb.get('editorID'), 'an interior' if crb['interior'] else 'not an interior'))
            rec = dict(s); rec.update({'weather_form_key': skyset['form_key'], 'sky_source': skyset['source'], 'sky_period_used': s['period'],
                                       'hour_readback': w.get('gameHour'), 'weather_readback': wrb, 'weather_locked': w.get('weatherLocked'), 'cell_readback': crb, 'camera': cam,
                                       'taken': time.strftime('%Y-%m-%d %H:%M:%S'),
                                       'settings_hash': jhash({'sky': applied, 'pp': rb, 'base': jhash(ps0)}), 'stats': st, 'flags': flags})
            manifest['shots'] = [x for x in manifest['shots'] if x['id'] != s['id']] + [rec]
            manifest['updated'] = rec['taken']; save_json(MAN, manifest)
            tiles.append((dst, '%s  %s  %s %gh' % (s['view'], s['sky_label'], s['time_row'], s['hour'])))
            print(s['id'], 'mean %.3f' % st['mean'], 'near p1 %.3f' % st['dark']['near']['p1'], 'far p1 %.3f' % st['dark']['far']['p1'], flags or '', flush=True)
    finally:
        def weather_back():
            """Outdoors at the start and at the end: back to the weather the job found, unlocked (as before). Otherwise (the job
            started or ended inside a cell) only the lock is released: an interior's weather is not forced outdoors or the reverse."""
            now = bench.state_(); w0 = weather_ref(world0.get('weather'))
            if w0 and not (world0.get('cell') or {}).get('interior') and not (now.get('cell') or {}).get('interior'):
                cs.world(action='weather', instant=True, lock=False, **w0); LAST['locked'] = False
            else: release_weather_lock()
        for fn in (lambda: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}), lambda: cs.world(action='freeze', on=False),
                   lambda: put('PhysicalSky', ps0), lambda: [put(k, v) for k, v in OTHER.items()], lambda: put('PostProcessing', pp0),
                   lambda: cs.world(action='timescale', value=world0.get('timeScale', 1)), weather_back,
                   lambda: bench.console('tgm')):                            # god mode OFF again (it was toggled on at the start): a kept-open game may be played next
            try: fn()
            except Exception as e: failed_restores.append(str(e)[:100]); print('restore step failed:', str(e)[:100], flush=True)
        print('restore steps run (player camera, Physical Sky and Post Processing as found, time scale, weather lock released, god mode toggled back off): %s'
              % ('all ok' if not failed_restores else '%d FAILED' % len(failed_restores)), flush=True)
    if tiles:
        cols = 6; w, hh = 573, 240
        sheet = Image.new('RGB', (w * cols, (hh + 22) * ((len(tiles) + cols - 1) // cols)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
        for i, (path, label) in enumerate(tiles):
            sheet.paste(Image.open(path).convert('RGB').resize((w, hh)), ((i % cols) * w, (i // cols) * (hh + 22) + 22)); d.text(((i % cols) * w + 6, (i // cols) * (hh + 22) + 5), label, fill=(240, 240, 240))
        sheet.save(os.path.join(out_dir, 'sheet-%s.jpg' % time.strftime('%m%d-%H%M')), quality=85)
    print('done: %d shots this run, %d in the manifest' % (len(tiles), len(manifest['shots'])), flush=True)
    FINISHED.append(1); bench.finish()


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'): sys.exit(__doc__)
    TAG = sys.argv[1]; PLAN_PATH = opt('--plan', os.path.join(HERE, 'baseline_plan.json'))
    if not os.path.exists(PLAN_PATH) and os.path.exists(os.path.join(HERE, PLAN_PATH)): PLAN_PATH = os.path.join(HERE, PLAN_PATH)      # a plan named relative to harness/
    plan = load_plan(PLAN_PATH); stage = opt('--stage', '1')
    if stage != 'all' and stage not in plan['stages']: sys.exit('unknown stage %s (plan has %s, or all)' % (stage, sorted(plan['stages'])))
    out_dir = os.path.join(LAB, 'results', 'baseline', TAG)
    mpath = os.path.join(out_dir, 'manifest.json')
    manifest = json.load(open(mpath, encoding='utf-8')) if os.path.exists(mpath) else {}
    shots = expand(plan, stage)
    if flag('--dry-run'): dry_run(plan, shots, out_dir, manifest)
    else:
        os.makedirs(out_dir, exist_ok=True); live(plan, shots, out_dir, manifest)

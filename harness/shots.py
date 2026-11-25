"""Views framework. Since 2026-11-23 the camera is placed with the bridge's OVERRIDE mode (the Sky Above fast travel
method: the game stays in its normal camera state and the rendered camera is moved after the game's own update). That
draws all the land wherever the character is; the free-camera state was what made far land go missing. The character
just stays where it arrives. Anchors are kept in views.json but only used when a view sets "pin": true.

Older text: every view is an ANCHOR (where the character is held, so the game draws the right land) plus a CAMERA
(absolute position, direction, field of view). Needs the bridge build with testbed view_get / pin / unpin (2026-11-23).

  python shots.py save NAME [note words...]       save what is on screen right now (any camera: first person, tfc, a camera mod)
  python shots.py shoot TAG NAME [NAME ...] [--hour 12,17.5] [--weather SunnyPF,OvercastPF] [--compare]
  python shots.py anchor NAME [NAME ...]          convert old views: fix the character spot and the camera position for good
  python shots.py snap common|all|NAME ...        reshoot and overwrite the pictures on the phone page (clear noon unless --hour/--weather)
  python shots.py restore NAME [STAMP]            make a shot's recorded settings live again (undo); nothing is saved to disk
  python shots.py fix flagged|NAME ...            views with missing land: try character spots near the camera, keep the best
  python shots.py list [text]                     names, what each is good for, known flaws

shoot: travels if the anchor is far, pins the character at the anchor, frames the camera, waits until the game is ready
(no loading, frame time steady), shoots, labels, and puts the character back where it arrived. --compare puts each frame
beside the view's reference frame. A frame with large flat sky-coloured areas below the horizon is reported as 'HOLES?'.
Old views without an anchor are shot the old way (camera straight above the arrival point) and marked legacy."""
import json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, views_page
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(HERE); VPATH = os.path.join(HERE, 'views.json')
tb = lambda **k: cs.call('communityshaders.testbed', k)


def label(path, text, dst=None):
    im = Image.open(path).convert('RGB'); W, H = im.size; fs = int(H * 0.045); font = ImageFont.truetype('arialbd.ttf', fs)
    d = ImageDraw.Draw(im); d.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0)); d.text((int(fs * 0.6), int(fs * 0.3)), text, fill=(255, 230, 0), font=font)
    im.save(dst or path); return im


def holes(path):
    """Share of the lower part of the frame that is bright sky blue: sky showing through land that was not drawn."""
    a = np.asarray(Image.open(path).convert('RGB').resize((430, 180))).astype(np.float32) / 255; low = a[70:]
    return float(((low[..., 2] > low[..., 0] * 1.3) & (low[..., 2] > 0.6)).mean())


def grab(tag):
    """Screenshot with retries; returns the file path or raises."""
    for k in range(4):
        try:
            r = cs.call('communityshaders.capture', {'kind': 'screenshot', 'tag': '%s%d' % (tag, k), 'timeoutMs': 40000}, timeout=60)
        except Exception as e:
            r = {'error': repr(e)}
        if r.get('path') and os.path.exists(r['path']): return r['path']
        print('  screenshot try %d failed: %s' % (k + 1, json.dumps(r)[:200]), flush=True); time.sleep(4)
    raise RuntimeError('screenshot failed four times')


def ready(min_wait, max_wait=90):
    """Wait until nothing is loading and the frame time has settled; returns seconds waited."""
    t0 = time.time(); last = []
    while time.time() - t0 < max_wait:
        try:
            v = tb(action='view_get'); ms = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']['ms']; sc = cs.call('communityshaders.inspect', {'kind': 'shadercache'})
        except Exception:
            time.sleep(1.5); continue
        last = (last + [ms])[-5:]
        if int(time.time() - t0) % 8 == 0: awake()
        steady = len(last) == 5 and max(last) < 1.35 * (sum(last) / 5) + 3
        if time.time() - t0 >= min_wait and not v.get('loading') and steady and not sc.get('compiling') and not sc.get('standalonePending'): break
        time.sleep(1.2)
    return round(time.time() - t0, 1)


WEATHER_SETTLE = 30
REF_SECONDS = 600.0      # the fixed clock every reference shot is taken at (clouds, tree sway, shader timer)


def world_pin(h, w):
    """Same time, same weather, same clouds: stop the game clock at the hour, lock the weather, and put our own clocks
    on the fixed reference value. Returns the list of things that could NOT be pinned (older build without refclock)."""
    miss = []
    cs.world(action='timescale', value=0)
    if h is not None: cs.world(action='hour', value=h)
    if w is not None:
        was = (cs.world(action='state').get('weather') or {}).get('editorID')
        cs.world(action='weather', name=w, instant=True, lock=True)
        if was != w: time.sleep(WEATHER_SETTLE)     # the sky settings blend over to the new weather
    try:
        r = cs.world(action='refclock', on=True, seconds=REF_SECONDS)
        if not r.get('on'): miss.append('clouds and tree sway (this build has no reference clock)')
    except Exception: miss.append('clouds and tree sway (this build has no reference clock)')
    return miss


def world_release():
    try: cs.world(action='refclock', on=False)
    except Exception: pass
    cs.world(action='timescale', value=20)


def settle_exposure(max_wait=45):
    """Wait until the automatic exposure has stopped moving (under 0.3 % over three seconds). Returns the final value."""
    t0 = time.time(); last = []
    while time.time() - t0 < max_wait:
        try: e = cs.call('communityshaders.inspect', {'kind': 'exposure'}).get('preExposure')
        except Exception: e = None
        if e:
            last = (last + [e])[-7:]
            if len(last) == 7 and (max(last) - min(last)) / max(last) < 0.003: return e
        time.sleep(0.5)
    return last[-1] if last else None


def awake():
    """The idle (vanity) camera starts after a while without input and zooms on whatever moves; it wrecked repeat shots
    (2026-11-24). A tap on a key that does nothing keeps it away; camera state 1 means it is already running."""
    try:
        bench.tap('RightControl')
        if tb(action='view_get')['camera'].get('state') == 1: time.sleep(2.5); bench.tap('RightControl'); time.sleep(2.5)
    except Exception: pass


def pose_error(cam, pose):
    """How far the camera on screen is from the one asked for: (units, degrees). Checked before every reference shot."""
    c = tb(action='view_get')['camera']
    if c.get('state') == 1: return 1e6, 180.0      # idle camera running
    d = math.dist([c['x'], c['y'], c['z']], [pose['x'], pose['y'], pose['z']])
    dy = abs((c['yaw'] - cam['yaw'] + 180) % 360 - 180); dp = abs(c['pitch'] - cam['pitch'])
    return d, max(dy, dp, abs(c['fov'] - cam['fov']))


def save(name, note):
    v = tb(action='view_get'); c, p = v['camera'], v['player']; V = json.load(open(VPATH))
    travel = None
    if v.get('worldspace') == 'Tamriel' and not v['cell']['interior']: travel = 'cow Tamriel %d %d' % (math.floor(p['x'] / 4096), math.floor(p['y'] / 4096))
    elif v['cell']['editorID']: travel = 'coc ' + v['cell']['editorID']
    old = V.get(name, {})
    V[name] = {'note': note or old.get('note', ''), 'travel': travel, 'worldspace': v.get('worldspace'), 'cell': v['cell']['editorID'],
               'anchor': {k: round(p[k], 1) for k in ('x', 'y', 'z', 'yaw')},
               'camera': {'absolute': True, **{k: round(c[k], 2) for k in ('x', 'y', 'z', 'pitch', 'yaw', 'fov')}},
               'saved': time.strftime('%Y-%m-%d %H:%M'), 'good_for': old.get('good_for'), 'sample': old.get('sample')}
    json.dump(V, open(VPATH, 'w'), indent=1)
    d = math.dist([c['x'], c['y'], c['z']], [p['x'], p['y'], p['z']])
    print('saved %s: character at (%.0f, %.0f, %.0f) in %s, camera %.0f units from it, fov %.0f, %s' % (name, p['x'], p['y'], p['z'], v['cell']['editorID'] or '?', d, c['fov'], 'first person' if c.get('firstPerson') else 'free camera' if c.get('free') else 'third person'))
    if d > 6000: print('  note: the camera is far from the character; the game may not draw all the land for this view')


def anchor(names):
    """Turn old views (camera above wherever the character arrived) into anchored ones: travel, take the arrival
    spot as the fixed anchor and make the camera position absolute, so every later shot is the same frame."""
    V = json.load(open(VPATH)); done = {}
    for name in names:
        v = V[name]; c = v['camera']
        if v.get('anchor'): print(name, 'already anchored'); continue
        # Oldest views have no travel command, only a cell and sometimes a saved character spot (2026-11-25)
        if not v.get('travel'): v['travel'] = 'coc ' + v['cell']
        place = v.get('player') if isinstance(v.get('player'), dict) and 'x' in v['player'] else None
        key = v['travel'] + (' @%.0f,%.0f' % (place['x'], place['y']) if place else '')
        if key not in done:
            tb(action='camera', mode='player')
            if not done or list(done)[-1].split(' @')[0] != v['travel']: bench.console(v['travel']); time.sleep(8); ready(25, 150)
            if place:
                cs.world(action='teleport', x=place['x'], y=place['y'], z=place['z'], rz=place.get('rz', 0)); time.sleep(4); ready(15, 90)
            done[key] = tb(action='view_get')
        g = done[key]; p = g['player']
        v['anchor'] = {'x': round(p['x'], 1), 'y': round(p['y'], 1), 'z': round(p['z'] + 4, 1), 'yaw': round(p['yaw'], 1)}
        v['camera'] = {'absolute': True, 'x': round(p['x'] + c.get('dx', 0), 1), 'y': round(p['y'] + c.get('dy', 0), 1), 'z': round(p['z'] + c.get('dz', 0), 1), 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']}
        v['cell'] = g['cell']['editorID']; v['worldspace'] = g.get('worldspace'); v['saved'] = time.strftime('%Y-%m-%d %H:%M'); v.pop('player', None)
        json.dump(V, open(VPATH, 'w'), indent=1); print('anchored', name, v['anchor'], flush=True)


def fix(names):
    """For views with missing land: try character spots around the camera (in the air at camera height, hidden) and keep
    the one where the least sky shows through the land. The game culls far land by the cell the CHARACTER is in."""
    V = json.load(open(VPATH)); tmp = os.path.join(ROOT, 'results', 'shots', '_fix'); os.makedirs(tmp, exist_ok=True)
    names = sorted(names, key=lambda n: V[n].get('travel') or ''); where = None; ground = None
    cs.world(action='hour', value=12.0); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
    try:
        for name in names:
            v = V[name]; cam = v['camera']; a0 = v['anchor']
            if v['travel'] != where:
                tb(action='camera', mode='player')
                if tb(action='view_get').get('pinned') and ground: tb(action='unpin', x=ground['x'], y=ground['y'], z=ground['z'] + 20)
                bench.console(v['travel']); time.sleep(8); ready(25, 150); where = v['travel']; ground = tb(action='view_get')['player']
            yaw = math.radians(cam['yaw']); fx, fy = math.sin(yaw), math.cos(yaw); C = 4096
            cand = [('saved', a0['x'], a0['y'], a0['z'])] + [(k, cam['x'] + dx, cam['y'] + dy, cam['z']) for k, dx, dy in (
                ('at camera', 0, 0), ('1 ahead', fx * C, fy * C), ('2 ahead', fx * 2 * C, fy * 2 * C), ('3 ahead', fx * 3 * C, fy * 3 * C), ('1 back', -fx * C, -fy * C),
                ('1 left', -fy * C, fx * C), ('1 right', fy * C, -fx * C), ('2 ahead left', fx * 2 * C - fy * C, fy * 2 * C + fx * C), ('2 ahead right', fx * 2 * C + fy * C, fy * 2 * C - fx * C))]
            best = None; log = []
            for k, x, y, z in cand:
                tb(action='pin', x=x, y=y, z=z, yaw=a0.get('yaw', 0)); tb(action='camera', pitch=cam['pitch'], yaw=cam['yaw'], fov=cam['fov'], x=cam['x'], y=cam['y'], z=cam['z'])
                ready(7, 40); f = grab('fx'); hs = holes(f); log.append('%s %.1f%%' % (k, hs * 100))
                if best is None or hs < best[0] - 0.002: best = (hs, k, x, y, z); shutil.copy2(f, os.path.join(tmp, name + '.png'))
                os.remove(f)
                if hs < 0.003: break
            hs, k, x, y, z = best
            v['anchor'] = {'x': round(x, 1), 'y': round(y, 1), 'z': round(z, 1), 'yaw': a0.get('yaw', 0)}; v['anchor_note'] = 'chosen by fix: %s (%.1f%% sky through land)' % (k, hs * 100)
            v['flaw'] = None if hs < 0.01 else 'land still missing (%.0f%% of the lower frame) from every character spot tried' % (hs * 100)
            json.dump(V, open(VPATH, 'w'), indent=1); print('%-34s -> %-14s | %s' % (name, k, ', '.join(log)), flush=True)
    finally:
        try:
            tb(action='camera', mode='player')
            if ground: tb(action='unpin', x=ground['x'], y=ground['y'], z=ground['z'] + 20)
        except Exception: pass
        cs.world(action='weather', name='SunnyPF', instant=False, lock=False)


def shoot(tag, names, hours, weathers, compare, publish=True, strict=False):
    V = json.load(open(VPATH)); out = os.path.join(ROOT, 'results', 'shots', tag); os.makedirs(out, exist_ok=True)
    if bench.menus().get('messageBoxOpen'): sys.exit('a message box is open in game')
    locked = None; back = None
    try:
        for name in names:
            v = V[name]; cam = v['camera']; anchor = v.get('anchor')
            tb(action='camera', mode='player'); here = tb(action='view_get')['player']
            target = anchor or v.get('player_place') or None
            far = target is None or math.dist([here['x'], here['y']], [target['x'], target['y']]) > 12000
            if far and v.get('travel'):
                bench.console(v['travel']); time.sleep(8); ready(25, 150)
            ground = tb(action='view_get')['player']
            pose = dict(x=cam['x'], y=cam['y'], z=cam['z']) if cam.get('absolute') else dict(x=ground['x'] + cam.get('dx', 0), y=ground['y'] + cam.get('dy', 0), z=ground['z'] + cam.get('dz', 0))
            # The character is held just behind and below the camera: out of the picture whatever the hide flag does,
            # and the game loads its full-detail land around the camera instead of around the arrival spot.
            yw, pt = math.radians(cam['yaw']), math.radians(cam['pitch'])
            fwd = (math.sin(yw) * math.cos(pt), math.cos(yw) * math.cos(pt), -math.sin(pt))
            if not v.get('nopin'): tb(action='pin', x=pose['x'] - fwd[0] * 260, y=pose['y'] - fwd[1] * 260, z=pose['z'] - fwd[2] * 260 - 140, yaw=cam['yaw'])
            back = ground
            first = True
            for w in weathers:
                for h in hours:
                    miss = world_pin(h, w) if (h is not None and w is not None) else ['time and weather (none given)']; locked = True
                    if not cam.get('absolute'): miss.append('camera (legacy view: placed from the arrival spot)')
                    tb(action='camera', mode='override', pitch=cam['pitch'], yaw=cam['yaw'], fov=cam['fov'], **pose)
                    waited = ready(14 if (first or w is not None) else 6); first = False
                    for attempt in range(3):
                        dpos, dang = pose_error(cam, pose)
                        if dpos < 6 and dang < 0.2: break
                        awake()
                        tb(action='camera', mode='override', pitch=cam['pitch'], yaw=cam['yaw'], fov=cam['fov'], **pose); time.sleep(2)
                    else: miss.append('camera (off by %.0f units, %.1f degrees)' % (dpos, dang))
                    awake(); ev = settle_exposure(); awake(); time.sleep(1.0)
                    if pose_error(cam, pose)[0] > 6: miss.append('camera (idle camera took over)')
                    if miss: print('  NOT PINNED: ' + '; '.join(miss), flush=True)
                    if strict and miss: raise RuntimeError(name + ' is not repeatable: ' + '; '.join(miss))
                    f = grab('sh'); stem = name + ('_%s' % w if w else '') + ('_h%04d' % round(h * 100) if h is not None else '')
                    d = os.path.join(out, stem + '.png'); shutil.move(f, d); hs = 0.0 if v.get('set') == 'sky' else holes(d)
                    text = name.replace('_', ' ').upper() + ('  -  ' + w if w else '') + ('  -  %02d:%02d' % (int(h), round(h % 1 * 60)) if h is not None else '') + ('' if anchor else '  -  legacy view')
                    label(d, text, os.path.join(out, 'labelled_' + stem + '.png'))
                    if publish: views_page.publish(name, d, {'weather': w or '', 'hour': '%02d:%02d' % (int(h), round(h % 1 * 60)) if h is not None else '', 'holes': hs > 0.02}, views_page.snapshot())
                    print('%-44s waited %4.1fs  %s' % (stem, waited, 'HOLES? %.0f%% of the lower frame is sky blue' % (hs * 100) if hs > 0.02 else 'ok'), flush=True)
                    if compare and v.get('sample') and os.path.exists(os.path.join(ROOT, v['sample'])):
                        A = label(os.path.join(ROOT, v['sample']), 'REFERENCE  -  ' + name.replace('_', ' '), os.path.join(out, '_ref.png')); B = Image.open(os.path.join(out, 'labelled_' + stem + '.png'))
                        sh = Image.new('RGB', (B.width, B.height * 2 + 8)); sh.paste(A.resize(B.size), (0, 0)); sh.paste(B, (0, B.height + 8)); sh.save(os.path.join(out, 'compare_' + stem + '.png')); os.remove(os.path.join(out, '_ref.png'))
            tb(action='camera', mode='player')
            if not v.get('nopin'): tb(action='unpin', x=back['x'], y=back['y'], z=back['z'] + 20)
            back = None
    finally:
        try:
            tb(action='camera', mode='player')
            if tb(action='view_get').get('pinned'):
                if back: tb(action='unpin', x=back['x'], y=back['y'], z=back['z'] + 20)
                else: tb(action='unpin')
        except Exception: pass
        if locked: world_release(); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)


def compare_frames(a, b, out):
    """Mean difference (0-255), share of pixels more than 8 apart, and a picture of where they differ (x8)."""
    A = np.asarray(Image.open(a).convert('RGB')).astype(np.int16); B = np.asarray(Image.open(b).convert('RGB')).astype(np.int16)
    d = np.abs(A - B).max(axis=2); Image.fromarray(np.clip(d * 8, 0, 255).astype(np.uint8)).save(out)
    # Coarse measure: 16x16 pixel blocks averaged first, so leaf flutter and water ripples cancel and only real
    # differences (cloud shadows, exposure, a moved camera, something in the picture) remain.
    H, W = d.shape; h, w = H // 16, W // 16
    blk = lambda X: X[:h * 16, :w * 16].reshape(h, 16, w, 16, 3).mean(axis=(1, 3))
    c = np.abs(blk(A) - blk(B)).max(axis=2)
    return float(d.mean()), float((c > 6).mean()), float(abs(A.mean() - B.mean()))


def repeat(tag, names, hour, weather, away=None):
    """Proof of repeatability: shoot every view twice with a full reset in between (camera released, character put down,
    clocks released; with away = a travel command, a trip there and back as well) and measure how much the pair differs."""
    rows = []
    for name in names:
        fs = []
        for run in ('a', 'b'):
            shoot('%s/%s' % (tag, run), [name], [hour], [weather], False, publish=False, strict=False)
            fs.append(os.path.join(ROOT, 'results', 'shots', tag, run, '%s_%s_h%04d.png' % (name, weather, round(hour * 100))))
            if run == 'a':
                time.sleep(6)
                if away: bench.console(away); time.sleep(8); ready(25, 150)
        m, share, lum = compare_frames(fs[0], fs[1], os.path.join(ROOT, 'results', 'shots', tag, name + '_diff.png'))
        rows.append((name, m, share, lum)); print('REPEAT %-34s pixel difference %.2f of 255, %.1f%% of the picture differs at block scale, brightness apart %.2f' % (name, m, share * 100, lum), flush=True)
    json.dump(rows, open(os.path.join(ROOT, 'results', 'shots', tag, 'repeat.json'), 'w'))
    return rows


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'list':
        V = json.load(open(VPATH)); q = (a[1] if len(a) > 1 else '').lower()
        for k, v in V.items():
            line = '%-32s %-8s %s%s' % (k, 'anchored' if v.get('anchor') else 'legacy', v.get('good_for') or v.get('note', '')[:90], '   FLAW: ' + v['flaw'] if v.get('flaw') else '')
            if q in line.lower(): print(line)
    elif a[0] == 'save': save(a[1], ' '.join(a[2:]))
    elif a[0] == 'anchor': anchor(a[1:])
    elif a[0] == 'fix': fix(a[1:] if a[1:] != ['flagged'] else [n for n, m in json.load(open(views_page.META)).items() if m.get('holes')])
    elif a[0] == 'snap':      # update the phone page: python shots.py snap common | all | NAME ... [--hour 12] [--weather SunnyPF]
        def opt(flag, cast, default):
            if flag in a:
                i = a.index(flag); val = [cast(x) for x in a[i + 1].split(',')]; del a[i:i + 2]; return val
            return default
        hours = opt('--hour', float, [12.0]); weathers = opt('--weather', str, ['SunnyPF']); V = json.load(open(VPATH))
        names = views_page.COMMON if a[1:] == ['common'] else [k for k, v in V.items() if v.get('set') == 'sky'] if a[1:] == ['sky'] else [k for k, v in V.items() if v.get('anchor')] if a[1:] == ['all'] else a[1:]
        names = sorted(names, key=lambda n: V[n].get('travel') or '')      # one trip per region
        shoot('live', names, hours, weathers, False)
    elif a[0] == 'repeat':    # python shots.py repeat TAG NAME ... [--hour 12] [--weather SunnyPF] [--away "cow Tamriel 4 -3"]
        away = None
        if '--away' in a: i = a.index('--away'); away = a[i + 1]; del a[i:i + 2]
        hour = 12.0; weather = 'SunnyPF'
        if '--hour' in a: i = a.index('--hour'); hour = float(a[i + 1]); del a[i:i + 2]
        if '--weather' in a: i = a.index('--weather'); weather = a[i + 1]; del a[i:i + 2]
        repeat(a[1], a[2:], hour, weather, away)
    elif a[0] == 'restore': views_page.restore(a[1], a[2] if len(a) > 2 else None)
    elif a[0] == 'shoot':
        def opt(flag, cast):
            if flag in a:
                i = a.index(flag); val = [cast(x) for x in a[i + 1].split(',')]; del a[i:i + 2]; return val
            return [None]
        hours = opt('--hour', float); weathers = opt('--weather', str); compare = '--compare' in a
        if compare: a.remove('--compare')
        shoot(a[1], a[2:], hours, weathers, compare)

"""NGVO performance lab harness.

usage:
  python bench.py run LABEL [--scenarios plains,sprint,flight] [--reps 1] [--tracy] [--no-launch] [--keep-open]
                            [--cs-disable TreeWind,PhysicalSky] [--cs-set '{"Upscaling":{"frameGenerationMode":0}}']
  python bench.py compare LABEL_A LABEL_B
  python bench.py show LABEL

Each rep is a fresh launch (unless --no-launch): launch through MO2, load the last save, run the scenarios, quit.
Per scenario it records: CS frame recorder (render frames), PresentMon (presented frames incl. frame generation, if it can
start), VramTracker rows (if the marker is on), a position track, and optionally a Tracy capture.
Results: results/LABEL/repN/SCENARIO/*.json and one line per scenario in results/results.jsonl (stamped with the config id).

Rules (see docs/PROTOCOL.md): only one thing drives the game at a time; never benchmark while a build is running;
never use the suspend-based stack sampler unattended.
"""
import json, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cs, state

ROOT = 'C:/Modlists/NGVO 8.0 Beta'
VT = ROOT + '/overwrite/SKSE/Plugins/CommunityShaders/VramTrack.jsonl'
PRESENTMON = LAB + '/ext/presentmon/PresentMon-2.6.0-x64.exe'
TRACY_CAPTURE = LAB + '/ext/tracy/tracy-capture.exe'
RESULTS = LAB + '/results'
START = (19157.0, -7419.0, -3612.0)          # coc WhiterunExterior04 spawn
FLY_TARGET = (-28000.0, -27000.0); FLY_Z = -2300.0


# ---------------------------------------------------------------- game control
def tap(k): cs.call('input', {'action': 'tap', 'device': 'keyboard', 'key': k})
def down(k, hold_ms=None):
    try: cs.call('input', {'action': 'down', 'device': 'keyboard', 'key': k, **({'maxHoldMs': hold_ms} if hold_ms else {})})
    except Exception: pass
def release():
    try: cs.call('input', {'action': 'releaseAll'})
    except Exception: pass
def console(c): cs.world(action='console', command=c)
def state_():
    try: return cs.world(action='state')
    except Exception: return {}
def menus():
    try: return cs.call('menu', {'action': 'list'})
    except Exception: return {'messageBoxOpen': False, 'openMenus': ['?']}
def pos():
    p = state_().get('position') or {}
    return p.get('x', 0.0), p.get('y', 0.0), p.get('z', 0.0)
def running():
    return 'SkyrimSE.exe' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SkyrimSE.exe'], capture_output=True, text=True).stdout


def settle(cell=None, maxwait=180):
    """Wait until a cell is loaded; answers the SkyrimNet 'older save' prompt with Delete History (user's standing choice)."""
    t0 = time.time()
    while time.time() - t0 < maxwait:
        m = menus()
        if m.get('messageBoxOpen'):
            time.sleep(1)
            if 'Main Menu' in m.get('openMenus', []):
                # Still on the main menu: this is the game's "save relies on missing content" Yes/No prompt.
                # Yes is the default button; pressing right first would pick No and cancel the load.
                tap('enter')
            else:
                # In the world: SkyrimNet's "older save" prompt; the right-hand button is Delete History (user's standing choice).
                tap('right'); time.sleep(.6); tap('enter')
            time.sleep(3); continue
        s = state_()
        if s.get('cell') and s.get('position') and 'Loading Menu' not in m.get('openMenus', []) and (cell is None or s['cell']['editorID'] == cell):
            return s
        time.sleep(3)
    return None


LOADED_SAVE = None
BASE_SAVE = 'preRestart_auri'    # the harness's fixed starting save; named explicitly so view saves made later don't change what a run loads


def saves():
    try: return [s['name'] for s in cs.call('game', {'action': 'list'}).get('saves', [])]
    except Exception: return []


def launch(save=None):
    """save: name of a save to load (e.g. a per-view save); falls back to BASE_SAVE, then to the most recent save."""
    global LOADED_SAVE
    if running():
        # Session mode: the queue runner left the game open for the next job. Attach instead of relaunching,
        # and switch place by loading the wanted save from inside the game (seconds, not minutes).
        if os.environ.get('NGVO_KEEP_OPEN') != '1' and os.environ.get('NGVO_ATTACH') != '1':
            raise SystemExit('game already running; quit it first or pass --no-launch')
        try: cs.call('menu', {'action': 'list'})
        except Exception: raise SystemExit('game is running but the bridge does not answer')
        release()
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
        have = saves()
        if save in have:
            print('attached: loading save', save, flush=True)
            cs.call('game', {'action': 'load', 'name': save}); time.sleep(12)
            if not settle(): raise SystemExit('save did not load')
            LOADED_SAVE = save; time.sleep(4)
        else:
            print('attached: staying in the current game (no save named %s)' % save, flush=True); LOADED_SAVE = None
        return
    if mo2_running(): close_mo2()
    for attempt in range(3):                      # the MO2 shortcut sometimes does not start the game: send it again
        # Tool shells run inside a Windows job object; an MO2 started from here inherits it and then gets
        # ERROR_ACCESS_DENIED starting skse64_loader.exe. Going through Explorer starts MO2 outside the job.
        subprocess.Popen(['explorer.exe', os.path.join(HERE, 'launch-ngvo.lnk').replace('/', chr(92))])
        t0 = time.time()
        while time.time() - t0 < 75 and not running(): time.sleep(5)
        if running(): break
    else: raise SystemExit('game did not start')
    t0 = time.time()
    while time.time() - t0 < 420:
        try:
            if 'Main Menu' in cs.call('menu', {'action': 'list'})['openMenus']: break
        except Exception: pass
        time.sleep(5)
    else: raise SystemExit('main menu not reached')
    have = saves(); pick = save if save in have else BASE_SAVE if BASE_SAVE in have else None
    print('loading save:', pick or '(most recent)', flush=True)
    cs.call('game', {'action': 'load', 'name': pick} if pick else {'action': 'loadLast'}); time.sleep(15)
    LOADED_SAVE = pick
    if not settle(): raise SystemExit('save did not load')
    time.sleep(5)


NR_SCALE = 0.75          # user decision 2026-11-18: Neural Rendering at 75% resolution going forward


def all_on(strict=True):
    """Everything-on check (user rule): Neural Rendering on at NR_SCALE every frame, frame generation on, volumetric clouds on.
    Returns the live state; with strict, quits the game and exits when something is off, so nothing is measured or shot that way."""
    def g(short):
        r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return r.get('settings', r)
    nr, up, ps = g('NeuralRendering'), g('Upscaling'), g('PhysicalSky')
    state = {'nr_enabled': nr.get('enabled'), 'nr_scale': nr.get('resolutionScale'), 'nr_alternate': nr.get('alternateFrames'),
             'frame_generation': up.get('frameGenerationMode'), 'volumetric_clouds': ps.get('enableVolumetricClouds'), 'physical_sky': ps.get('enabled')}
    bad = [k for k, ok in (('nr_enabled', state['nr_enabled'] is True), ('nr_scale', abs((state['nr_scale'] or 0) - NR_SCALE) < 0.01), ('nr_alternate', state['nr_alternate'] is False),
                           ('frame_generation', bool(state['frame_generation'])), ('volumetric_clouds', state['volumetric_clouds'] is True), ('physical_sky', state['physical_sky'] is True)) if not ok]
    print('everything-on check:', state, 'NOT ON: %s' % bad if bad else 'ok', flush=True)
    if bad and strict:
        quit_game(); sys.exit('everything-on check failed: %s' % bad)
    return state


def finish():
    """End of a job: leave the game open when the queue runner says another game job follows."""
    if os.environ.get('NGVO_KEEP_OPEN') == '1' and running():
        release()
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
        print('session kept open for the next job', flush=True); return
    quit_game()


def quit_game():
    release()
    try: cs.world(action='quit', confirm=True)
    except Exception: pass
    t0 = time.time()
    while running() and time.time() - t0 < 90: time.sleep(3)
    close_mo2()


def mo2_running():
    return 'ModOrganizer.exe' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ModOrganizer.exe'], capture_output=True, text=True).stdout


def close_mo2():
    """MO2 stays open after the game exits (Root Builder cleans up). A second shortcut launch is then forwarded to it and
    fails ('failed to receive data from secondary process' / 'Cannot start skse64_loader.exe'), so close it between runs."""
    time.sleep(12)                                   # let Root Builder finish clearing the game folder
    ps = "$m=Get-Process ModOrganizer -ErrorAction SilentlyContinue; if($m){ [void]$m.CloseMainWindow() }"
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True)
    t0 = time.time()
    while mo2_running() and time.time() - t0 < 25: time.sleep(2)
    if mo2_running():
        subprocess.run(['powershell', '-NoProfile', '-Command', 'Get-Process ModOrganizer -ErrorAction SilentlyContinue | Stop-Process -Force'], capture_output=True)
    time.sleep(4)


def goto(cell):
    console('coc ' + cell); time.sleep(6)
    s = settle(cell)
    if not s: raise RuntimeError('could not reach ' + cell)
    time.sleep(4); return s


def exterior_setup():
    cs.world(action='hour', value=12.0); cs.world(action='timescale', value=1)
    cs.world(action='weather', name='SunnyTU', instant=True, lock=True)


def collision(on):
    """tcl is a toggle: probe by lifting the player and seeing whether they fall."""
    x, y, z = pos()
    cs.world(action='teleport', x=x, y=y, z=z + 400); time.sleep(1.5)
    falls = pos()[2] < z + 250
    if falls != on: console('tcl'); time.sleep(.5)
    cs.world(action='teleport', x=x, y=y, z=z + (5 if on else 0)); time.sleep(1.5)


# ---------------------------------------------------------------- recording
def stats(f):
    if not f: return {}
    sf = sorted(f); n = len(f); q = lambda p: round(sf[min(n - 1, int(n * p))], 2)
    return dict(frames=n, mean=round(sum(f) / n, 2), fps=round(1000 * n / sum(f), 1), p50=q(.5), p95=q(.95), p99=q(.99), max=round(sf[-1], 1),
                over50=sum(1 for x in f if x > 50), over100=sum(1 for x in f if x > 100), over250=sum(1 for x in f if x > 250), stall_ms=round(sum(x for x in f if x > 100)))


def record(out, seconds, tick=None, tracy=False, interval=0.2):
    """Records `seconds` of gameplay; tick(t) is called about 4x a second and drives the player."""
    os.makedirs(out, exist_ok=True)
    pm_csv = os.path.join(out, 'presentmon.csv'); pm = None
    pm_agent = False
    try:
        # A helper started under a fresh sign-in (pm_agent.py) has the permission PresentMon needs; ask it when it is alive
        alive = LAB + '/results/pm/agent.alive'
        if os.path.exists(alive) and time.time() - os.path.getmtime(alive) < 10:
            json.dump({'out': pm_csv.replace('/', chr(92)), 'seconds': int(seconds) + 2}, open(LAB + '/results/pm/requests/%d.json' % int(time.time() * 1000), 'w')); pm_agent = True
            time.sleep(1.0)
        else:
            pm = subprocess.Popen([PRESENTMON, '--process_name', 'SkyrimSE.exe', '--output_file', pm_csv, '--timed', str(int(seconds) + 2), '--terminate_after_timed',
                                   '--no_console_stats', '--stop_existing_session', '--track_frame_type'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception: pm = None
    tr = None
    if tracy:
        tr = subprocess.Popen([TRACY_CAPTURE, '-o', os.path.join(out, 'capture.tracy'), '-f', '-s', str(int(seconds))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    vt0 = os.path.getsize(VT) if os.path.exists(VT) else 0
    cs.call('communityshaders.frames', {'action': 'start'}); t0 = time.time()
    track = []; n = 0; every = max(1, round(0.2 / interval))
    while time.time() - t0 < seconds:
        t = time.time() - t0
        if tick: tick(t)
        if n % every == 0:                       # position track about 5x a second
            tq = time.time(); s = state_(); api = time.time() - tq
            p = s.get('position') or {}
            track.append({'t': round(t, 2), 'ts': int(time.time() * 1000), 'cell': (s.get('cell') or {}).get('editorID', 'ERR'), 'x': round(p.get('x', 0)), 'y': round(p.get('y', 0)), 'z': round(p.get('z', 0)), 'api': round(api, 3)})
        n += 1; time.sleep(interval)
    release()
    cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(1.5)
    fr = cs.call('communityshaders.frames', {'action': 'read'}); cols = fr.get('columns', {})
    json.dump({'t_start': t0, 'frames': fr}, open(os.path.join(out, 'frames.json'), 'w'))
    json.dump(track, open(os.path.join(out, 'track.json'), 'w'))
    m = {'render': stats(cols.get('frameMs', []))}
    if cols.get('presentThreadCpuMs'): m['main_cpu_ms'] = round(sum(cols['presentThreadCpuMs']) / len(cols['presentThreadCpuMs']), 2)
    if cols.get('frameGeneration'): m['fg_share'] = round(sum(1 for x in cols['frameGeneration'] if x) / len(cols['frameGeneration']), 2)
    if track:
        m['distance'] = round(math.hypot(track[-1]['x'] - track[0]['x'], track[-1]['y'] - track[0]['y']))
        m['cells'] = len({t['cell'] for t in track})
    if os.path.exists(VT):
        rows = []
        with open(VT) as fh:
            fh.seek(vt0)
            for l in fh:
                try: rows.append(json.loads(l))
                except Exception: pass
        if rows:
            g = 'SkyrimSE.exe|buf_geom'
            m['vram'] = dict(proc_max=round(max(r.get('procMB', 0) for r in rows)), proc_min=round(min(r.get('procMB', 0) for r in rows)),
                             new_top=sorted([round(r.get('newMB', 0)) for r in rows], reverse=True)[:4], geom_live_max=round(max(r['live'].get(g, 0) for r in rows)))
            json.dump(rows, open(os.path.join(out, 'vram.json'), 'w'))
    if pm_agent:
        time.sleep(6)                                  # the helper's PresentMon stops by itself after the timed capture
        m['presented'] = presentmon_stats(pm_csv)
    elif pm is not None:
        try: pm.wait(timeout=20)
        except Exception: pm.kill()
        m['presented'] = presentmon_stats(pm_csv)
    if tr is not None:
        try: tr.wait(timeout=30)
        except Exception: tr.kill()
    return m


def presentmon_stats(path):
    if not os.path.exists(path) or os.path.getsize(path) < 200: return {'error': 'no data (PresentMon needs admin or Performance Log Users)'}
    import csv
    rows = list(csv.DictReader(open(path, newline='')))
    if not rows: return {'error': 'empty'}
    col = next((c for c in ('FrameTime', 'MsBetweenPresents') if c in rows[0]), None)
    disp = next((c for c in ('DisplayedTime', 'MsBetweenDisplayChange') if c in rows[0]), None)
    out = {}
    def nums(c):
        v = []
        for r in rows:
            try: v.append(float(r[c]))
            except Exception: pass
        return v
    if col: out['present'] = stats(nums(col))
    if disp: out['displayed'] = stats([x for x in nums(disp) if x > 0])
    if 'FrameType' in rows[0]:
        import collections
        out['frame_types'] = dict(collections.Counter(r['FrameType'] for r in rows))
    return out


# ---------------------------------------------------------------- scenarios
def sc_static(cell, pose=None, seconds=15, interior=False):
    def run(out, tracy):
        s = goto(cell)
        if not interior: exterior_setup()
        if pose: cs.world(action='teleport', **pose)
        time.sleep(10)
        return record(out, seconds, tracy=tracy)
    return run


def face_camera(on, distance=60.0, height=112.0, pitch=-2.0, fov=35.0):
    """Free camera in front of the player's face (close-up), or back to the player camera."""
    if not on:
        cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); return
    s = state_(); p = s['position']; h = math.radians(s['angleDeg']['z'])
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'] + math.sin(h) * distance, 'y': p['y'] + math.cos(h) * distance, 'z': p['z'] + height,
                                         'pitch': pitch, 'yaw': math.degrees(h) + 180.0, 'fov': fov})


def sc_face(cell, pose, seconds=15):
    """Close-up of the player's face: the view Neural Rendering quality is judged on."""
    def run(out, tracy):
        goto(cell); exterior_setup(); cs.world(action='teleport', **pose); time.sleep(8)
        try:
            face_camera(True); time.sleep(4)
            return record(out, seconds, tracy=tracy)
        finally:
            face_camera(False)
    return run


def sc_flight(seconds=100):
    heading = math.degrees(math.atan2(FLY_TARGET[0] - START[0], FLY_TARGET[1] - START[1])) % 360
    def run(out, tracy):
        goto('WhiterunExterior04'); exterior_setup(); console('tgm') if False else None
        collision(False)
        cs.world(action='teleport', x=START[0], y=START[1], z=FLY_Z, rx=0.0, rz=heading); time.sleep(10)
        # CapsLock (walk/run) is a toggle that other scenarios may have flipped: measure and fix before recording
        down('w'); time.sleep(1.0); p0 = pos(); time.sleep(3.0); p1 = pos()
        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 3.0 < 250: tap('capsLock')
        release(); cs.world(action='teleport', x=START[0], y=START[1], z=FLY_Z, rx=0.0, rz=heading); time.sleep(4)
        last = [0.0]
        def tick(t):
            if t - last[0] > 2.5 or t < 0.3: down('w'); last[0] = t
        m = record(out, seconds, tick, tracy)
        collision(True); return m
    return run


def sc_sprint(route_file, seconds=100):
    pts = json.load(open(os.path.join(HERE, 'routes', route_file)))['points']
    def run(out, tracy):
        goto('WhiterunExterior04'); exterior_setup(); collision(True)
        cs.world(action='teleport', x=pts[0][0], y=pts[0][1]); time.sleep(6)
        st = {'i': 1, 'keys': -9.0, 'stuck_t': 0.0, 'last': pos(), 'last_t': 0.0, 'skips': 0}
        def tick(t):
            x, y, z = pos()
            while st['i'] < len(pts) - 1 and math.hypot(pts[st['i']][0] - x, pts[st['i']][1] - y) < 350: st['i'] += 1
            tx, ty = pts[min(st['i'] + 1, len(pts) - 1)]
            cs.world(action='teleport', rz=math.degrees(math.atan2(tx - x, ty - y)) % 360)
            if t - st['keys'] > 2.5: down('w'); down('leftShift'); st['keys'] = t
            if t - st['last_t'] > 3.0:
                if math.hypot(x - st['last'][0], y - st['last'][1]) < 150:      # stuck: hop to the next waypoint, keep height
                    cs.world(action='teleport', x=pts[st['i']][0], y=pts[st['i']][1], z=z + 60); st['skips'] += 1
                st['last'] = (x, y, z); st['last_t'] = t
        m = record(out, seconds, tick, tracy); m['route_progress'] = round(st['i'] / len(pts), 2); m['stuck_hops'] = st['skips']
        return m
    return run


def sc_onward(route_file, seconds=100, start_index=6, steady=False, cell='WhiterunExterior04'):
    """Ground sprint with the Onward mod: placed on a road, C starts auto-move along it (no marker needed),
    CapsLock switches walk to run, holding Shift sprints. Its cinematic camera also moves, which exercises occlusion."""
    pts = json.load(open(os.path.join(HERE, 'routes', route_file)))['points']
    def run(out, tracy):
        goto(cell); exterior_setup(); collision(True)
        x, y = pts[start_index][:2]; tx, ty = pts[start_index + 3][:2]
        where = dict(x=x, y=y, rz=math.degrees(math.atan2(tx - x, ty - y)) % 360)
        if len(pts[start_index]) > 2: where['z'] = pts[start_index][2] + 40      # routes with heights: start just above the ground
        cs.world(action='teleport', **where); time.sleep(8 if 'z' in where else 6)
        p0 = pos(); tap('c'); time.sleep(5); p1 = pos()
        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 5 < 200: tap('capsLock'); time.sleep(3)
        st = {'keys': -9.0, 'last': pos(), 'last_t': 0.0, 'restarts': 0}
        def tick(t):
            # Sprint toggles on each key-down event: re-sending 'down' every 2.5 s (the old behaviour, kept for results
            # comparable with suites B-D) makes the player stop and restart the sprint. steady=True holds Shift for the
            # bridge's 60 s maximum and re-presses once, so the sprint is continuous.
            if steady:
                if t - st['keys'] > 58.0: down('leftShift', 60000); st['keys'] = t
            elif t - st['keys'] > 2.5: down('leftShift'); st['keys'] = t
            if t - st['last_t'] > 4.0:
                x, y, z = pos()
                if math.hypot(x - st['last'][0], y - st['last'][1]) < 200: tap('c'); st['restarts'] += 1   # auto-move stopped: start it again
                st['last'] = (x, y, z); st['last_t'] = t
        m = record(out, seconds, tick, tracy); m['onward_restarts'] = st['restarts']
        end = pos(); m['offroute'] = round(min(math.hypot(end[0] - q[0], end[1] - q[1]) for q in pts))
        tap('c'); release()
        return m
    return run


def sc_spin(cell, pose, seconds=40, rev_seconds=3.0):
    """Stands still and turns the camera through full circles (one revolution every rev_seconds), to expose
    stutter from culling, shadow and texture streaming when the view changes quickly."""
    def run(out, tracy):
        goto(cell); exterior_setup(); collision(True)
        cs.world(action='teleport', **pose); time.sleep(10)
        def tick(t):
            cs.world(action='teleport', rz=(pose.get('rz', 0.0) + 360.0 * t / rev_seconds) % 360)
        return record(out, seconds, tick, tracy, interval=0.03)
    return run


SCENARIOS = {
    'plains': sc_static('WhiterunExterior04', dict(x=START[0], y=START[1], z=START[2], rx=4.0, rz=247.0)),
    'forest': sc_static('HalfMoonMillExterior'),
    'city': sc_static('WhiterunOrigin'),
    'interior': sc_static('WhiterunBanneredMare', interior=True),
    'flight': sc_flight(),
    # player facing south-east into the noon sun on the plains
    'face': sc_face('WhiterunExterior04', dict(x=START[0], y=START[1], z=START[2], rx=0.0, rz=160.0)),
    'spin': sc_spin('WhiterunExterior04', dict(x=START[0], y=START[1], z=START[2], rx=4.0, rz=247.0)),
    'sprint': sc_onward('whiterun_south.json'),
    'sprint2': sc_onward('whiterun_south.json', steady=True),
    # Riverwood -> Guardian Stones: ~24,500 units, about 55 s at a steady sprint, so the run ends at the stones
    'forest_run': sc_onward('riverwood_guardian.json', seconds=58, start_index=23, steady=True, cell='Riverwood'),
    # the long view west over Lake Ilinalta from the Guardian Stones (pose from the devbench recording's anchor): distant LOD, water, sky
    'vista': sc_static('GuardianStones', dict(x=662.0, y=-59220.0, z=612.0, rx=-2.0, rz=278.5)),
    'sprint_steer': sc_sprint('whiterun_south.json'),
}


# ---------------------------------------------------------------- temporary config variants
CS_SETTINGS = ROOT + '/mods/CS Settings/SKSE/Plugins/CommunityShaders/SettingsUser.json'


class Variant:
    """Applies a temporary change for a run and restores the files afterwards (game must be closed).
    cs_disable: CS feature short names to disable at boot. cs_set: dict merged into SettingsUser.json."""
    def __init__(self, cs_disable=(), cs_set=None):
        self.cs_disable = [x for x in cs_disable if x]; self.cs_set = cs_set or {}; self.backup = None

    def __enter__(self):
        if not (self.cs_disable or self.cs_set): return self
        if running(): raise SystemExit('close the game before applying a variant')
        self.backup = open(CS_SETTINGS, 'rb').read()
        d = json.loads(self.backup)
        dab = d.setdefault('Disable at Boot', {})
        for n in self.cs_disable: dab[n] = True
        def merge(a, b):
            for k, v in b.items():
                if isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)
                else: a[k] = v
        merge(d, self.cs_set)
        json.dump(d, open(CS_SETTINGS, 'w'), indent=4)
        return self

    def __exit__(self, *a):
        if self.backup is not None:
            t0 = time.time()
            while running() and time.time() - t0 < 60: time.sleep(2)
            open(CS_SETTINGS, 'wb').write(self.backup)


# ---------------------------------------------------------------- commands
def cmd_run(label, scenarios, reps, tracy, do_launch, keep_open):
    man = state.manifest()
    for rep in range(1, reps + 1):
        if do_launch: launch()
        try: all_on(strict=False)                      # printed into the suite log: which of NR / frame generation / clouds were really on
        except Exception as e: print('everything-on check failed to run:', str(e)[:100], flush=True)
        console('tgm')
        for name in scenarios:
            out = os.path.join(RESULTS, label, 'rep%d' % rep, name)
            try:
                m = SCENARIOS[name](out, tracy)
            except Exception as e:
                m = {'error': str(e)[:200]}
            rec = {'label': label, 'rep': rep, 'scenario': name, 'config': man['id'], 'time': time.strftime('%Y-%m-%d %H:%M:%S'), **m}
            os.makedirs(out, exist_ok=True); json.dump(rec, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
            with open(os.path.join(RESULTS, 'results.jsonl'), 'a') as fh: fh.write(json.dumps(rec) + '\n')
            r = m.get('render', {})
            print('%s rep%d %-8s fps %-5s p99 %-6s max %-6s >100ms %-3s stall %sms vram %s' % (label, rep, name, r.get('fps'), r.get('p99'), r.get('max'), r.get('over100'), r.get('stall_ms'),
                  (m.get('vram') or {}).get('proc_max')), m.get('error', ''), flush=True)
        try: cs.world(action='weather', name='SunnyTU', instant=False, lock=False)
        except Exception: pass
        if do_launch and not keep_open: quit_game()
    json.dump(man, open(os.path.join(RESULTS, label, 'manifest.json'), 'w'), indent=1)


def load(label):
    rows = [json.loads(l) for l in open(os.path.join(RESULTS, 'results.jsonl'))]
    return [r for r in rows if r['label'] == label]


def agg(rows):
    out = {}
    for sc in sorted({r['scenario'] for r in rows}):
        rr = [r for r in rows if r['scenario'] == sc and 'render' in r and r['render']]
        if not rr: continue
        f = lambda k: [r['render'][k] for r in rr]
        mean = lambda v: sum(v) / len(v)
        out[sc] = dict(n=len(rr), fps=round(mean(f('fps')), 1), fps_spread=round(max(f('fps')) - min(f('fps')), 1), p99=round(mean(f('p99')), 1), max=round(max(f('max'))),
                       over100=round(mean(f('over100')), 1), stall_ms=round(mean(f('stall_ms'))), vram=round(mean([(r.get('vram') or {}).get('proc_max', 0) for r in rr])))
    return out


def cmd_show(label):
    for sc, a in agg(load(label)).items(): print('%-9s' % sc, a)


def cmd_compare(a, b):
    A, B = agg(load(a)), agg(load(b))
    print('%-9s %-22s %-22s %s' % ('scenario', a, b, 'delta'))
    for sc in A:
        if sc not in B: continue
        for k in ('fps', 'p99', 'over100', 'stall_ms', 'vram'):
            print('%-9s %-9s %-12s %-12s %+.1f%s' % (sc, k, A[sc][k], B[sc][k], B[sc][k] - A[sc][k], '   (run-to-run spread %.1f)' % max(A[sc]['fps_spread'], B[sc]['fps_spread']) if k == 'fps' else ''))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'run':
        opt = lambda k, d: a[a.index(k) + 1] if k in a else d
        with Variant(opt('--cs-disable', '').split(','), json.loads(opt('--cs-set', '{}'))):
            cmd_run(a[1], opt('--scenarios', 'plains,sprint,flight').split(','), int(opt('--reps', '1')), '--tracy' in a, '--no-launch' not in a, '--keep-open' in a)
    elif a[0] == 'show': cmd_show(a[1])
    elif a[0] == 'compare': cmd_compare(a[1], a[2])

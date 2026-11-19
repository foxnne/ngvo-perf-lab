"""Repeatable cell-load benchmark: no-clip flight from Whiterun west-southwest at fixed height and heading.

usage: python flybench.py LABEL [seconds=140]
Writes look/edits/flybench/LABEL/{frames.json,track.jsonl,stacks.csv,summary.json} and prints a summary.
Needs the game loaded in any exterior/interior; handles the SkyrimNet prompt (Delete). Uses the CS frame recorder,
the VramTracker log (if its marker is on) and scratchpad/stacksamp.ps1 for main-thread stacks.
"""
import json, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs

NOSTACKS = '--nostacks' in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
LABEL = ARGS[0]; SECS = int(ARGS[1]) if len(ARGS) > 1 else 140
OUT = os.path.join(os.path.dirname(HERE), 'edits', 'flybench', LABEL); os.makedirs(OUT, exist_ok=True)
SCR = 'C:/Users/foxnn/AppData/Local/Temp/claude/3faf89cbf3e7ed47/f00ecae3-865a-43f6-bdb9-8828c99c0a95/scratchpad'
VT = 'C:/Modlists/NGVO 8.0 Beta/overwrite/SKSE/Plugins/CommunityShaders/VramTrack.jsonl'
START = (19157.0, -7419.0, -2300.0); TARGET = (-28000.0, -27000.0)
HEADING = math.degrees(math.atan2(TARGET[0] - START[0], TARGET[1] - START[1])) % 360


def tap(k):
    cs.call('input', {'action': 'tap', 'device': 'keyboard', 'key': k})


def state():
    try: return cs.world(action='state')
    except Exception: return {}


def menus():
    try: return cs.call('menu', {'action': 'list'})
    except Exception: return {'messageBoxOpen': False, 'openMenus': ['?']}


def settle(cell=None, maxwait=150):
    t0 = time.time()
    while time.time() - t0 < maxwait:
        m = menus()
        if m.get('messageBoxOpen'):
            time.sleep(1); tap('right'); time.sleep(.6); tap('enter'); time.sleep(3); continue
        s = state()
        if s.get('cell') and s.get('position') and 'Loading Menu' not in m.get('openMenus', []) and (cell is None or s['cell']['editorID'] == cell):
            return s
        time.sleep(3)
    return None


def pos():
    p = state().get('position') or {}
    return p.get('x', 0.0), p.get('y', 0.0), p.get('z', 0.0)


s = settle()
if not s: sys.exit('game not ready')
if s['cell']['editorID'] != 'WhiterunExterior04':
    cs.world(action='console', command='coc WhiterunExterior04'); time.sleep(6)
    if not settle('WhiterunExterior04'): sys.exit('could not reach start cell')
time.sleep(4)
cs.world(action='hour', value=12.0); cs.world(action='timescale', value=20)
cs.world(action='weather', name='SunnyTU', instant=True, lock=True)
cs.world(action='console', command='tgm')
# collision off only if we still collide: probe by teleporting up and seeing whether we fall
cs.world(action='teleport', x=START[0], y=START[1], z=START[2], rx=0.0, rz=HEADING); time.sleep(2.0)
if pos()[2] < START[2] - 150:
    cs.world(action='console', command='tcl'); time.sleep(0.5)
    cs.world(action='teleport', x=START[0], y=START[1], z=START[2], rx=0.0, rz=HEADING); time.sleep(2.0)
print('start', [round(v) for v in pos()], 'heading %.1f' % HEADING, flush=True)
time.sleep(8)  # let the start area finish loading

for f in ('stacks.csv', 'stacks.csv.info', 'track.jsonl'):
    try: os.remove(os.path.join(OUT, f))
    except FileNotFoundError: pass
# The sampler suspends the game's main thread for each sample: it must never be killed mid-sample, so it runs detached
# from this script (an interrupted tool call would otherwise leave the game frozen).
samp = None
if not NOSTACKS:
    samp = subprocess.Popen(['powershell', '-NoProfile', '-File', SCR + '/stacksamp.ps1', '-Out', os.path.join(OUT, 'stacks.csv').replace('/', chr(92)),
                             '-Seconds', str(SECS + 6)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                            creationflags=0x00000008 | 0x00000200)
time.sleep(5)
vt0 = os.path.getsize(VT) if os.path.exists(VT) else 0
cs.call('communityshaders.frames', {'action': 'start'}); t_start = time.time()
track = open(os.path.join(OUT, 'track.jsonl'), 'w'); last_down = 0; caps_checked = False; p_prev = pos(); t_prev = time.time()
while time.time() - t_start < SECS:
    now = time.time()
    if now - last_down > 2.5:
        try: cs.call('input', {'action': 'down', 'device': 'keyboard', 'key': 'w'})
        except Exception: pass
        last_down = now
    time.sleep(0.5)
    t = time.time(); tq = t
    st = state(); dt = time.time() - tq
    p = st.get('position') or {}; c = (st.get('cell') or {}).get('editorID', 'ERR')
    track.write(json.dumps({'ts': int(t * 1000), 't': round(t - t_start, 2), 'cell': c, 'x': round(p.get('x', 0)), 'y': round(p.get('y', 0)), 'z': round(p.get('z', 0)), 'api': round(dt, 3)}) + '\n'); track.flush()
    if not caps_checked and t - t_start > 5:
        sp = math.hypot(p.get('x', 0) - p_prev[0], p.get('y', 0) - p_prev[1]) / max(t - t_prev, 1e-3)
        if sp < 200: tap('capsLock')
        caps_checked = True; print('speed %.0f u/s%s' % (sp, ' -> toggled run' if sp < 200 else ''), flush=True)
    if not caps_checked and t - t_start <= 1.0: p_prev = (p.get('x', 0), p.get('y', 0), p.get('z', 0)); t_prev = t
cs.call('input', {'action': 'releaseAll'})
cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(1.5)
fr = cs.call('communityshaders.frames', {'action': 'read'})
json.dump({'t_start': t_start, 'frames': fr}, open(os.path.join(OUT, 'frames.json'), 'w'))
track.close()
if samp is not None:
    try: samp.wait(timeout=40)
    except Exception: pass
cs.world(action='weather', name='SunnyTU', instant=False, lock=False)

f = fr.get('columns', {}).get('frameMs', [])
end = pos(); dist = math.hypot(end[0] - START[0], end[1] - START[1])
summ = {'label': LABEL, 'seconds': SECS, 'distance': round(dist), 'frames': len(f)}
if f:
    sf = sorted(f)
    summ.update(mean=round(sum(f) / len(f), 2), p50=round(sf[len(f) // 2], 2), p99=round(sf[int(len(f) * .99) - 1], 2), max=round(sf[-1], 1),
                over50=sum(1 for x in f if x > 50), over100=sum(1 for x in f if x > 100), over250=sum(1 for x in f if x > 250), over500=sum(1 for x in f if x > 500),
                stall_ms=round(sum(x for x in f if x > 100)))
if os.path.exists(VT):
    rows = []
    with open(VT) as fh:
        fh.seek(vt0)
        for l in fh:
            try: rows.append(json.loads(l))
            except Exception: pass
    if rows:
        g = 'SkyrimSE.exe|buf_geom'
        summ.update(vram_proc_max=round(max(r.get('procMB', 0) for r in rows)), vram_proc_min=round(min(r.get('procMB', 0) for r in rows)),
                    geom_burst_top=sorted([round(r['created'].get(g, 0)) for r in rows], reverse=True)[:5],
                    new_total_top=sorted([round(r.get('newMB', 0)) for r in rows], reverse=True)[:5], geom_live_max=round(max(r['live'].get(g, 0) for r in rows)))
        json.dump(rows, open(os.path.join(OUT, 'vram.json'), 'w'))
json.dump(summ, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
print(json.dumps(summ), flush=True)

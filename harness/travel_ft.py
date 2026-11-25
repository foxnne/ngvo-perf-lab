"""Travel memory test with REAL fast travel (user 2026-11-25: simulate the goal, not forced jumps). Each trip goes through
the map like a player (m, f, type the name, Enter, e, Enter) so Sky Above flies its arc; frame times are recorded during
the flight, and after landing the same readings as travel_leak.py are logged (RAM, video memory, tracker, frame, NR).
usage: python travel_ft.py TAG [--rounds 4] [--dests Riften,Solitude,...]      output: results/travel_ft/TAG.json"""
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
TAG = sys.argv[1]
ROUNDS = int(sys.argv[sys.argv.index('--rounds') + 1]) if '--rounds' in sys.argv else 4
DESTS = (sys.argv[sys.argv.index('--dests') + 1] if '--dests' in sys.argv else 'Riften Stables,Solitude Sawmill,Markarth Stables,Windhelm Stables,Falkreath,Dawnstar').split(',')
OUT = os.path.join(shots.ROOT, 'results', 'travel_ft'); os.makedirs(OUT, exist_ok=True)
MAP_UI = '--map-ui' in sys.argv          # default: the bridge's fasttravel action (the map UI path stalled at the confirm box)
sys.argv = [sys.argv[0], '_unused']          # travel_leak reads argv at import; only its helpers are wanted
src = open(os.path.join(HERE, 'travel_leak.py'), encoding='utf-8').read().split("\nrows = []")[0]
tl = {'__file__': os.path.join(HERE, 'travel_leak.py')}; exec(compile(src, 'travel_leak_helpers', 'exec'), tl)
mem = tl['mem']

rows = []
def save(): json.dump(rows, open(os.path.join(OUT, TAG + '.json'), 'w'), indent=1)


SFT_LOG = os.path.expanduser('~/Documents/My Games/Skyrim Special Edition/SKSE/SeamlessFastTravel.log')
def flights_ended():
    try: return open(SFT_LOG, encoding='utf-8', errors='replace').read().count('Flight ended')
    except Exception: return 0


def typ(s):
    for ch in s.lower():
        bench.tap('space' if ch == ' ' else ch); time.sleep(0.08)


def trip(dest):
    p0 = bench.pos(); t0 = time.time(); n0 = flights_ended()
    if MAP_UI:
        bench.tap('m'); time.sleep(3.0)
        bench.tap('f'); time.sleep(1.2); typ(dest); time.sleep(0.8); bench.tap('enter'); time.sleep(2.0)
        bench.tap('e'); time.sleep(1.2); bench.tap('enter'); time.sleep(0.5)
    else:      # bridge: Game.FastTravel(marker), flown by Sky Above when bScriptedFastTravel=1 (2026-11-25)
        r = cs.world(action='fasttravel', name=dest); print('  ->', r.get('name'), r.get('marker'), 'queued' if r.get('queued') else r, flush=True)
    try: cs.call('communityshaders.frames', {'action': 'start'})
    except Exception: pass
    last = None; still = 0; ended = False
    while time.time() - t0 < 180:
        if not MAP_UI and flights_ended() > n0:
            ended = True; time.sleep(1.0)
            try: last = bench.pos()
            except Exception: pass
            break
        time.sleep(2.0)
        try: p = bench.pos()
        except Exception: p = None
        if p and last and math.hypot(p[0] - last[0], p[1] - last[1]) < 50: still += 1
        else: still = 0
        last = p or last
        if still >= 4 and last and math.hypot(last[0] - p0[0], last[1] - p0[1]) > 5000: break
    try:
        cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(0.6)
        fm = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {}).get('frameMs', [])
    except Exception: fm = []
    moved = math.hypot(last[0] - p0[0], last[1] - p0[1]) if last else 0
    fs = sorted(fm)
    return {'ended': ended, 'moved': round(moved), 'flightSeconds': round(time.time() - t0, 1), 'frames': len(fm),
            'flightMedianMs': round(fs[len(fs) // 2], 1) if fs else None, 'flightP99Ms': round(fs[int(len(fs) * 0.99)], 1) if fs else None,
            'flightMaxMs': round(fs[-1], 1) if fs else None, 'over100': sum(1 for x in fm if x > 100), 'over250': sum(1 for x in fm if x > 250)}


def log(label, extra=None):
    m = mem(); m['step'] = label; m.update(extra or {}); rows.append(m); save()
    f = extra or {}
    print('%-22s RAM %6d  video %6d  tex %5s geom %5s  frame %6.1f ms  NR %-5s | flight %s s, median %s, p99 %s, max %s, >250ms %s' % (
        label, m['privateMB'], m['gpuMB'], m.get('textures'), m.get('geometry'), m['frameMs'], m['nrMs'],
        f.get('flightSeconds'), f.get('flightMedianMs'), f.get('flightP99Ms'), f.get('flightMaxMs'), f.get('over250')), flush=True)


if bench.pos() is None: sys.exit('no player position')
v = cs.call('communityshaders.testbed', {'action': 'view_get'})
if v['cell'].get('interior'):
    bench.console('cow Tamriel 4 -3'); time.sleep(8); shots.ready(25, 150)
bench.console('tgm'); time.sleep(1)
log('start')
for r in range(ROUNDS):
    for d in DESTS:
        if not bench.running(): print('GAME DIED'); sys.exit(1)
        res = trip(d); shots.ready(10, 90)
        if res['moved'] < 5000: print('  fast travel to %s did not happen (moved %d)' % (d, res['moved']), flush=True)
        log('r%d %s' % (r + 1, d), res)
time.sleep(60); log('after 60 s standing')

"""Road run for performance: Onward auto-move (key C) along the road from the Whiterun stables, running (CapsLock), no sprint.
Samples position and frame timing every 2 s. usage: python road_run.py TAG [start_yaw] [max_seconds]"""
import json, math, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
TAG = sys.argv[1]; YAW = float(sys.argv[2]) if len(sys.argv) > 2 else 110.0; MAXS = float(sys.argv[3]) if len(sys.argv) > 3 else 600.0
OUT = os.path.join(shots.ROOT, 'results', 'roadrun'); os.makedirs(OUT, exist_ok=True); tb = shots.tb
TARGET = tuple(float(v) for v in os.environ.get('RUN_TARGET', '18400,-47000').split(','))   # default Riverwood, cell 4,-12
START = os.environ.get('RUN_START', 'coc WhiterunExterior01')
LOG = os.path.expanduser(r'~\Documents\My Games\Skyrim Special Edition\SKSE\TheosRenderPipeline.log')
if '--here' not in sys.argv:
    tb(action='camera', mode='player'); bench.console(START); time.sleep(10); shots.ready(25, 150)
    cs.world(action='hour', value=10.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=False); time.sleep(6)
    if os.environ.get('RUN_TOGGLES'): bench.console('tgm'); bench.console('tdetect')
s = bench.state_(); p = s['position']; cs.world(action='teleport', x=p['x'], y=p['y'], z=p['z'], rz=YAW); time.sleep(2)
log0 = sum(1 for _ in open(LOG, encoding='utf-8', errors='replace'))
bench.tap('c'); time.sleep(1.5); bench.tap('capslock'); t0 = time.time(); rows = []; last = None; still = 0
while time.time() - t0 < MAXS:
    time.sleep(2.0); s = bench.state_(); p = s.get('position') or {}; pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']
    x, y = p.get('x', 0), p.get('y', 0); d = math.hypot(x - TARGET[0], y - TARGET[1]); sp = math.hypot(x - last[0], y - last[1]) / 2.0 if last else 0.0; last = (x, y)
    rows.append(dict(t=round(time.time() - t0, 1), x=round(x), y=round(y), z=round(p.get('z', 0)), dist=round(d), speed=round(sp), ms=round(pr['ms'], 1), avg=round(pr['avgMs'], 1), p99=round(pr['p99Ms'], 1), cell=(s.get('cell') or {}).get('editorID')))
    if len(rows) % 10 == 0: print(json.dumps(rows[-1]), flush=True)
    still = still + 1 if sp < 20 else 0
    if still >= 5: print('stopped at', round(x), round(y), 'dist', round(d), flush=True); break
    if d < 2500: print('arrived near target', flush=True); break
bench.tap('c'); bench.release()
json.dump(rows, open(os.path.join(OUT, TAG + '.json'), 'w'))
ms = sorted(r['ms'] for r in rows); n = len(ms)
print('samples %d  seconds %.0f  distance left %d' % (n, rows[-1]['t'], rows[-1]['dist']))
print('frame ms: median %.1f  p90 %.1f  max %.1f   worst rolling p99 %.1f' % (ms[n // 2], ms[int(n * .9)], ms[-1], max(r['p99'] for r in rows)))
lines = [l for i, l in enumerate(open(LOG, encoding='utf-8', errors='replace')) if i >= log0]
cad = [float(m.group(1)) for l in lines for m in [re.search(r'cadence p50=([\d.]+)', l)] if m]; p99 = [float(m.group(1)) for l in lines for m in [re.search(r'cadence p50=[\d.]+ p95=[\d.]+ p99=([\d.]+)', l)] if m]
slow = [l for l in lines if 'slow host Present' in l]
if cad: print('Theo log: cadence p50 median %.1f ms, worst window p99 %.1f ms, slow presents %d' % (sorted(cad)[len(cad) // 2], max(p99), len(slow)))
for l in slow[:6]: print('  ', re.search(r'total=[\d.]+ ms', l).group())

"""Queue job: real map fast travels (Sky Above flies the camera), recorded. For each destination: open the map (m), open
the find list (f), type the name, Enter (cursor goes to the marker), e (select) and Enter (Yes, iYesButton=1); then
shoot every 2 s and record frame times until the position settles at the far end. Check by distance that it moved.
usage: python fast_travel_job.py TAG [Dest,Dest,...]   output: results/fast_travel/TAG/"""
import json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]
DESTS = (sys.argv[2] if len(sys.argv) > 2 else 'Solitude,Riften,Markarth,Windhelm').split(',')
OUT = os.path.join(os.path.dirname(HERE), 'results', 'fast_travel', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.goto('WhiterunExterior04'); bench.exterior_setup()
cs.world(action='weather', name='SunnyTU', instant=True, lock=False); cs.world(action='hour', value=15.0); cs.world(action='timescale', value=1)
log = []
def typ(s):
    for ch in s.lower():
        bench.tap('space' if ch == ' ' else ch); time.sleep(0.08)
for d in DESTS:
    p0 = bench.pos(); t0 = time.time(); rec = {'dest': d, 'from': [round(v) for v in p0[:2]]}
    bench.tap('m'); time.sleep(3.0)
    shot = cs.shot('ft-%s-%s-map' % (TAG, d)); time.sleep(0.5)
    if shot and os.path.exists(shot): shutil.move(shot, os.path.join(OUT, '%s_00_map.png' % d))
    bench.tap('f'); time.sleep(1.2); typ(d); time.sleep(0.8); bench.tap('enter'); time.sleep(2.0)
    s2 = cs.shot('ft-%s-%s-pick' % (TAG, d)); time.sleep(0.3)
    if s2 and os.path.exists(s2): shutil.move(s2, os.path.join(OUT, '%s_01_picked.png' % d))
    bench.tap('e'); time.sleep(1.2); bench.tap('enter'); time.sleep(0.5)
    try: cs.call('communityshaders.frames', {'action': 'start'})
    except Exception: pass
    shots = 0; last = None; still = 0; tstart = time.time()
    while time.time() - tstart < 150:
        time.sleep(2.0)
        try:
            s = cs.shot('ft-%s-%s-%02d' % (TAG, d, shots))
            if s and os.path.exists(s): shutil.move(s, os.path.join(OUT, '%s_%02d.png' % (d, shots + 2))); shots += 1
            p = bench.pos()
        except Exception as e:
            p = None
        if p and last and math.hypot(p[0] - last[0], p[1] - last[1]) < 50: still += 1
        else: still = 0
        last = p or last
        if still >= 4 and last and math.hypot(last[0] - p0[0], last[1] - p0[1]) > 5000: break
    try:
        cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(0.6)
        fm = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {}).get('frameMs', [])
    except Exception: fm = []
    p1 = last or bench.pos(); moved = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    fs = sorted(fm)
    rec.update({'to': [round(v) for v in p1[:2]], 'moved': round(moved), 'seconds': round(time.time() - t0, 1), 'shots': shots,
                'frames': len(fm), 'median_ms': round(fs[len(fs) // 2], 1) if fs else None,
                'p99_ms': round(fs[int(len(fs) * 0.99)], 1) if fs else None, 'max_ms': round(fs[-1], 1) if fs else None,
                'over_100ms': sum(1 for x in fm if x > 100), 'over_250ms': sum(1 for x in fm if x > 250)})
    print(json.dumps(rec), flush=True); log.append(rec)
    if moved < 5000: print('fast travel to %s did not happen (map UI path failed?)' % d, flush=True)
    time.sleep(8)
json.dump(log, open(os.path.join(OUT, 'log.json'), 'w'), indent=1)
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

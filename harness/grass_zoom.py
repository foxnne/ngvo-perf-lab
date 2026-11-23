"""Queue job: how far does grass draw on the Whiterun plains? From a low camera (250 units above the player) at 13:00 SunnyPF,
four headings, each at fov 70 (as played), 25 and 10 (zoomed onto the distance). Note: zooming enlarges distant grass on screen,
so CS Grass Optimizations culls less of it than at fov 70; the fov 70 frames are the as-played truth.
usage: python grass_zoom.py TAG   Output results/grass_zoom/TAG/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'grass_zoom', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
try:
    bench.goto('WhiterunExterior04')
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(20)
    for a in [sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == '--live']:      # --live Short:Key=value  (live feature setting)
        short, kv = a.split(':', 1); k, v = kv.split('=', 1)
        s = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); s = s.get('settings', s)
        old = s.get(k); s[k] = type(old)(float(v)) if isinstance(old, (int, float)) and not isinstance(old, bool) else (v.lower() in ('1', 'true')) if isinstance(old, bool) else v
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s}); time.sleep(4)
        print('live set', short, k, old, '->', s[k], flush=True)
    p = bench.state_()['position']
    try:
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'GrassOptimizations'})
        print('live Grass Optimizations settings:', g.get('settings', g), flush=True)
    except Exception as e:
        print('could not read live grass settings:', str(e)[:120], flush=True)
    for yaw in (250.0,):          # straight down the plains; the other headings mostly showed walls
        for fov in (70.0, 25.0, 10.0):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 250.0, 'pitch': -2.0 if fov < 70 else -5.0, 'yaw': yaw, 'fov': fov}); time.sleep(7)
            src = cs.shot('gz-%s-%d-%d' % (TAG, int(yaw), int(fov))); time.sleep(0.4)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'plains__yaw%03d__fov%02d.png' % (int(yaw), int(fov)))); print('shot', yaw, fov, flush=True)
    # high views straight above the player (same x,y, so the loaded grid does not move): looks down onto the far plains
    for yaw in (250.0,):
        for dz, pitch, fov in ((4000.0, 18.0, 50.0), (4000.0, 12.0, 20.0), (8000.0, 30.0, 50.0)):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + dz, 'pitch': pitch, 'yaw': yaw, 'fov': fov}); time.sleep(7)
            src = cs.shot('gz-%s-high-%d-%d-%d' % (TAG, int(yaw), int(dz), int(fov))); time.sleep(0.4)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'high__yaw%03d__z%04d__fov%02d.png' % (int(yaw), int(dz), int(fov)))); print('shot high', yaw, dz, fov, flush=True)
    # straight-down probes over cell centres west of the player: is there grass k cells out?
    cx = int(p['x'] // 4096); cy = int(p['y'] // 4096)
    for k in (4, 8, 10, 12, 14, 16, 18):
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': (cx - k) * 4096 + 2048, 'y': cy * 4096 + 2048, 'z': p['z'] + 3000.0, 'pitch': 89.0, 'yaw': 0.0, 'fov': 60.0}); time.sleep(5)
        src = cs.shot('gz-%s-probe-w%02d' % (TAG, k)); time.sleep(0.4)
        if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'probe__west%02d.png' % k)); print('shot probe west', k, flush=True)
finally:
    try: cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

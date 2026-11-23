"""Queue job: distant tree LOD check (Rift aspens, Whiterun plains). Camera raised above the player, 4 headings, 13:00 SunnyPF.
usage: python lod_overlook.py TAG   Output results/lod_overlook/TAG/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'lod_overlook', TAG); os.makedirs(OUT, exist_ok=True)
SITES = [('rift', 'cow Tamriel 40 -24', 2000.0), ('plains', 'cow Tamriel 0 -2', 1200.0)]
bench.launch(); bench.all_on()
try:
    for name, where, up in SITES:
        bench.console(where); time.sleep(8); bench.settle()
        cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(15)
        p = bench.state_()['position']
        for yaw in (0.0, 90.0, 180.0, 270.0):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + up, 'pitch': -8.0, 'yaw': yaw, 'fov': 70.0}); time.sleep(6)
            src = cs.shot('lo-%s-%s-%d' % (TAG, name, int(yaw))); time.sleep(0.4)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, '%s__yaw%03d.png' % (name, int(yaw)))); print('shot', name, yaw, flush=True)
        if name == 'plains':
            g = cs.feat('get', 'ViewAtmosphere'); VA0 = g.get('settings', g)
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + up, 'pitch': -8.0, 'yaw': 270.0, 'fov': 70.0}); time.sleep(4)
            for ex in (12.0, 6.0, 3.0):
                cs.feat('set', 'ViewAtmosphere', dict(VA0, distanceExaggeration=ex)); time.sleep(5)
                src = cs.shot('lo-%s-ex%d' % (TAG, int(ex))); time.sleep(0.4)
                if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'plains__yaw270__exaggeration%02d.png' % int(ex))); print('shot exaggeration', ex, flush=True)
            cs.feat('set', 'ViewAtmosphere', VA0)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
finally:
    try: cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

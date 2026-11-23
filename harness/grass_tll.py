"""Job: does far grass exist but sit hidden (under LOD terrain), or is it not created at all?
Whiterun plains, 13:00 SunnyPF. Shots: normal, then with `tll` (all LOD off: far grass would float in the void),
then the free camera parked far from the player looking down (grass under the camera = created out there).
usage: python grass_tll.py TAG   Output results/grass_tll/TAG/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'grass_tll', TAG); os.makedirs(OUT, exist_ok=True)


def cam(x, y, z, pitch, yaw, fov):
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': x, 'y': y, 'z': z, 'pitch': pitch, 'yaw': yaw, 'fov': fov}); time.sleep(7)


def shot(name):
    src = cs.shot('gt-%s-%s' % (TAG, name)); time.sleep(0.4)
    if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, name + '.png')); print('shot', name, flush=True)


bench.launch(); bench.all_on()
try:
    bench.goto('WhiterunExterior04')
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(20)
    p = bench.state_()['position']; print('player', p, flush=True)
    for fov, pitch in ((70.0, -5.0), (25.0, -2.0)):
        cam(p['x'], p['y'], p['z'] + 250.0, pitch, 250.0, fov); shot('a_normal_fov%02d' % fov)
    bench.console('tll'); time.sleep(4)
    for fov, pitch in ((70.0, -5.0), (25.0, -2.0)):
        cam(p['x'], p['y'], p['z'] + 250.0, pitch, 250.0, fov); shot('b_tll_fov%02d' % fov)
    for i, (dx, dy) in enumerate(((-12000, 0), (0, -12000), (-20000, -8000), (-6000, -6000))):
        cam(p['x'] + dx, p['y'] + dy, p['z'] + 2500.0, -60.0, 250.0, 70.0); shot('c_tll_far%d_%d_%d' % (i, dx, dy))
    bench.console('tll'); time.sleep(4)
    for i, (dx, dy) in enumerate(((-12000, 0), (0, -12000), (-20000, -8000), (-6000, -6000))):
        cam(p['x'] + dx, p['y'] + dy, p['z'] + 2500.0, -60.0, 250.0, 70.0); shot('d_lod_far%d_%d_%d' % (i, dx, dy))
finally:
    try: cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

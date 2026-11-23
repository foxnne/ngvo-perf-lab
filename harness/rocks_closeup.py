"""Queue job: close-up of Rugged Ground stones on the Whiterun plain (plains_ground player pose), 13:00 SunnyPF.
Camera 120 units up, looking down 30 degrees, 3 headings; one wide shot. usage: python rocks_closeup.py TAG"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'rocks', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
try:
    bench.console('cow Tamriel 0 -2'); time.sleep(8); bench.settle(); time.sleep(6)
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(15)
    p = bench.state_()['position']; cs.world(action='freeze', on=True); time.sleep(1)
    for name, dz, pitch, yaw, fov in (('close_a', 130, 35, 270, 60), ('close_b', 130, 35, 90, 60), ('close_c', 90, 45, 0, 50), ('wide', 170, 10, 270, 80)):
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + dz, 'pitch': pitch, 'yaw': yaw, 'fov': fov}); time.sleep(5)
        src = cs.shot('rk-%s-%s' % (TAG, name)); time.sleep(0.4)
        if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, name + '.png')); print('shot', name, flush=True)
finally:
    try: cs.world(action='freeze', on=False); cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

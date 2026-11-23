"""High bird's-eye shots: the player (collision off, god mode) is lifted high above a spot so LOD culling stays valid, and the camera
at the player looks down across the land in a few directions. Noon, clear. usage: python birdseye_shots.py TAG [spot ...]
Also: python birdseye_shots.py TAG --backlit  -> Ilinalta and plains views toward a low sun (hour 17.5 and 18.5)."""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'region_shots', TAG); os.makedirs(OUT, exist_ok=True)
# cell x, y of the spot the player hovers over; views = (yaw, pitch)
SPOTS = {'whiterun_hold': (4, -3), 'falkreath_ilinalta': (-2, -14), 'rift': (40, -22), 'reach': (-30, 4), 'haafingar': (-18, 22),
         'pale': (10, 20), 'winterhold': (26, 24), 'eastmarch': (30, 2), 'hjaalmarch': (-8, 18), 'centre': (8, 4)}
args = [a for a in sys.argv[2:] if not a.startswith('--')]


def cam(yaw, pitch, fov=60, dz=None):
    # the player drops back to the ground when the free camera starts, so the camera height is kept here, not read from the player
    global DZ
    if dz is not None: DZ = dz
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': P['x'], 'y': P['y'], 'z': P['z'] + DZ, 'pitch': pitch, 'yaw': yaw, 'fov': fov})


def shot(name, wait=8):
    time.sleep(wait); f = cs.shot('be-' + name) or cs.shot('be2-' + name); d = os.path.join(OUT, name + os.path.splitext(f)[1]); shutil.move(f, d); print(name, flush=True)


def hover(cx, cy, z):
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    bench.console('cow Tamriel %d %d' % (cx, cy)); time.sleep(30)
    for _ in range(12):
        try:
            a = bench.state_(); time.sleep(4); b = bench.state_()
            if not b['cell']['interior'] and a['position'] == b['position'] and abs(b['position']['x'] - (cx * 4096 + 2048)) < 6000: break
        except Exception: time.sleep(5)
    global P, DZ
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); time.sleep(3); P = bench.state_()['position']; DZ = z   # z is camera height above the player


st = bench.state_()
if st['cell']['interior']: bench.console('cow Tamriel 4 -3'); time.sleep(34)
# collision off and god mode are switched on by the caller before this runs (they are toggles)
try:
    if '--backlit' in sys.argv:
        for name, (cx, cy), z, yaws in (('ilinalta', (-2, -14), 3500, (225, 270, 315)), ('plains', (4, -3), 1500, (240, 270, 300))):
            hover(cx, cy, z)
            for hour in (17.5, 18.75):
                cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=hour); time.sleep(10)
                for yaw in yaws:
                    cs.world(action='hour', value=hour); cam(yaw, 8, 45); shot('backlit_%s_h%s_yaw%d' % (name, str(hour).replace('.', ''), yaw))
    else:
        cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=12.0)
        for name in (args or list(SPOTS)):
            cx, cy = SPOTS[name]; hover(cx, cy, 5000); cs.world(action='hour', value=12.0)
            for yaw in (0, 90, 180, 270):
                cam(yaw, 10, 55); shot('wide_%s_yaw%03d' % (name, yaw))
            cam(0, 80, 75, dz=18000); shot('bird_%s_down' % name, 10)
            for yaw in (0, 90, 180, 270):
                cam(yaw, 30, 65); shot('bird_%s_yaw%03d' % (name, yaw))
finally:
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    s = bench.state_(); cs.world(action='weather', name=s['weather']['editorID'], instant=False, lock=False)

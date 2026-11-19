"""Walk across snow near Winterhold and shoot the trail from above. output: results/footprint_check/"""
import math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
OUT = os.path.join(os.path.dirname(HERE), 'results', 'footprint_check'); os.makedirs(OUT, exist_ok=True)
def keep(tag):
    src = cs.shot(tag); time.sleep(1.0); shutil.move(src, os.path.join(OUT, tag + os.path.splitext(src)[1])); print('shot', tag, flush=True)
bench.launch(); bench.console('tgm'); bench.all_on()
for cell in ('WinterholdExterior01', 'DawnstarExterior01'):
    bench.goto(cell); bench.exterior_setup(); cs.world(action='weather', name='SunnyTU', instant=True, lock=True); time.sleep(8)
    a = bench.state_()['position']
    bench.down('w', 7000)
    time.sleep(8); bench.release(); time.sleep(2)
    b = bench.state_()['position']; print(cell, 'walked', round(math.dist((a['x'], a['y']), (b['x'], b['y']))), a, b, flush=True)
    mx, my, mz = (a['x'] + b['x']) / 2, (a['y'] + b['y']) / 2, max(a['z'], b['z'])
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': mx, 'y': my, 'z': mz + 420, 'pitch': 89.0, 'yaw': 0.0, 'fov': 60.0}); time.sleep(5); keep(f'prints_{cell}_top')
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': b['x'], 'y': b['y'], 'z': b['z'] + 170, 'pitch': 35.0, 'yaw': math.degrees(math.atan2(a['x'] - b['x'], a['y'] - b['y'])) % 360, 'fov': 65.0}); time.sleep(5); keep(f'prints_{cell}_back')
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); time.sleep(2)
bench.quit_game()

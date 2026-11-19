"""Ground fog trial: same views, hours and weather with and without the GroundFog mod (run once before installing, once after).
usage: python fog_trial.py TAG      output: results/fog_trial/TAG/*.png, log.json"""
import json, os, shutil, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'fog_trial', TAG); os.makedirs(OUT, exist_ok=True)
def measure(sec=8):
    cs.call('communityshaders.frames', {'action': 'start'}); time.sleep(sec)
    cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(1)
    f = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {}).get('frameMs', [])
    return round(statistics.median(f), 2) if f else None
bench.launch(); bench.console('tgm')
bench.all_on()
bench.goto('GuardianStones'); cs.world(action='teleport', x=662.0, y=-59220.0, z=612.0, rx=0.0, rz=270.0); time.sleep(14)
p = bench.state_()['position']; log = {}
CAMS = {'shore': dict(dz=150.0, yaw=270.0, pitch=-2.0), 'vista': dict(dz=1100.0, yaw=252.0, pitch=-3.0)}
for hour in (6.5, 12.0, 18.2, 22.0):
    cs.world(action='timescale', value=1); cs.world(action='hour', value=hour); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(20)
    for cname, c in CAMS.items():
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': 65.0}); time.sleep(6)
        ms = measure(); src = cs.shot(f'fog-{TAG}-{cname}-{hour}'); time.sleep(1)
        name = f'{cname}_h{hour:g}'; shutil.copy2(src, os.path.join(OUT, name + os.path.splitext(src)[1])); log[name] = ms; print(name, 'frame', ms, 'ms', flush=True)
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); time.sleep(3)
    ms = measure(); src = cs.shot(f'fog-{TAG}-player-{hour}'); time.sleep(1)
    name = f'player_h{hour:g}'; shutil.copy2(src, os.path.join(OUT, name + os.path.splitext(src)[1])); log[name] = ms; print(name, 'frame', ms, 'ms', flush=True)
json.dump(log, open(os.path.join(OUT, 'log.json'), 'w'), indent=1)
bench.quit_game()

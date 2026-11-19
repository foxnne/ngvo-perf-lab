"""Launch, go to the first Right Whale pod in the Sea of Ghosts and take shots. output: results/whale_check/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
OUT = os.path.join(os.path.dirname(HERE), 'results', 'whale_check'); os.makedirs(OUT, exist_ok=True)
def keep(tag):
    src = cs.shot(tag); time.sleep(1.0); dst = os.path.join(OUT, tag + os.path.splitext(src)[1]); shutil.move(src, dst); print('shot', tag, flush=True)
bench.launch(); bench.console('tgm'); bench.all_on()
bench.goto('WhiterunExterior04'); bench.exterior_setup()
cs.world(action='weather', name='SunnyTU', instant=True, lock=True)
W = (63305.0, 135807.0, -14173.0)
cs.world(action='teleport', x=W[0] - 900, y=W[1] - 400, z=-13900.0, rx=0.0, rz=60.0); time.sleep(25)
print('state', bench.state_().get('position'), flush=True)
try: print('actors', str(cs.call('communityshaders.testbed', {'action': 'list'}))[:300], flush=True)
except Exception as e: print('list', str(e)[:100])
for name, cam in (('above_water', dict(x=W[0] - 1500, y=W[1] - 900, z=-13500.0, pitch=12.0, yaw=55.0, fov=70.0)),
                  ('under_water_side', dict(x=W[0] - 1100, y=W[1] - 300, z=-14350.0, pitch=0.0, yaw=75.0, fov=75.0)),
                  ('under_water_pod', dict(x=W[0] + 200, y=W[1] - 1500, z=-14400.0, pitch=-5.0, yaw=10.0, fov=80.0))):
    cs.call('communityshaders.testbed', {'action': 'camera', **cam}); time.sleep(8); keep('whale_' + name)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
import subprocess
print(subprocess.run(['powershell', '-NoProfile', '-Command', "(Get-Process SkyrimSE | % { '{0:N1} GB working set' -f ($_.WorkingSet64/1GB) })"], capture_output=True, text=True).stdout.strip(), flush=True)
bench.quit_game()

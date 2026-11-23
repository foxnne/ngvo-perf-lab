"""Queue job: build the fork (PR-Tracy), deploy it, stage cloud map assets, then do the first launch that recompiles shaders.
Game and MO2 must be closed (the queue runner guarantees it). Stops at the first failing step."""
import os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
LOG = 'C:/Users/foxnn/AppData/Local/Temp/claude/3faf89cbf3e7ed47/f00ecae3-865a-43f6-bdb9-8828c99c0a95/scratchpad/cs-prtracy-build.log'
os.makedirs(os.path.dirname(LOG), exist_ok=True)
t0 = time.time(); print('build start', time.strftime('%H:%M:%S'), flush=True)
subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'build_tracy.ps1')], cwd=HERE)
log = open(LOG, encoding='ascii', errors='replace').read()
print('build took %d s' % (time.time() - t0)); print('\n'.join(l for l in log.splitlines() if 'EXIT' in l or ' error ' in l.lower())[-3000:], flush=True)
if 'BUILD_EXIT 0' not in log: sys.exit('build failed: see ' + LOG)
p = subprocess.run([sys.executable, 'deploy.py', 'PR-Tracy'], cwd=HERE, capture_output=True, text=True); print(p.stdout[-2500:], p.stderr[-800:], flush=True)
if p.returncode: sys.exit('deploy failed')
dst = 'C:/Modlists/NGVO 8.0 Beta/mods/foxnne - Cloud Weather Map/textures/PhysicalSky/LocalNdf/tamriel-mist-separate'; os.makedirs(dst, exist_ok=True)
for f in ('Height.dds', 'Modeling.dds'): shutil.copy2('C:/Users/foxnn/dev/cloud-weather-map/out/tamriel-mist-separate/' + f, dst)
print('asset staged', flush=True)
env = dict(os.environ, NGVO_MENU_WAIT='2400')        # the first launch after a build recompiles every shader before the main menu appears
p = subprocess.run([sys.executable, 'first_launch.py'], cwd=HERE, capture_output=True, text=True, env=env); print(p.stdout[-1500:], p.stderr[-500:], flush=True)
if p.returncode: sys.exit('first launch after the build failed')

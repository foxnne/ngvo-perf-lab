"""Queue job: test shader-only Ground Fog commits one after another in ONE game session by hot reload.
For each commit: write its GroundFog shader files into the deployed mod, recompile (hot.reload), shoot a sweep.
At the end the LAST commit's shaders stay deployed (they are shader-only and match the deployed DLL).
usage: python fog_commits_job.py TAG SWEEP VIEW HOURS COMMIT[,COMMIT...] [FILE;FILE...]   (FILE paths relative to the fork; default: the Ground Fog shaders)"""
import os, subprocess, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, hot
TAG, SWEEP, VIEW, HOURS, COMMITS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(',')
FILES_ARG = sys.argv[6].split(';') if len(sys.argv) > 6 else None
FORK = 'C:/Users/foxnn/dev/skyrim-community-shaders'
FILES = ['features/Ground Fog/Shaders/GroundFog/FlowSim.cs.hlsl', 'features/Ground Fog/Shaders/GroundFog/GroundFog.hlsli', 'features/Ground Fog/Shaders/GroundFog/GroundFogPixel.cs.hlsl', 'features/Ground Fog/Shaders/GroundFog/Pool.hlsli']
if FILES_ARG: FILES = FILES_ARG
bench.launch()
env = dict(os.environ, NGVO_ATTACH='1', NGVO_KEEP_OPEN='1')
for i, c in enumerate(COMMITS):
    for f in FILES:
        data = subprocess.run(['git', '-C', FORK, 'show', '%s:%s' % (c, f)], capture_output=True).stdout
        if not data: sys.exit('could not read %s at %s' % (f, c))
        open(hot.deployed(f), 'wb').write(data)
    r = hot.reload(); print(c, 'reload', json.dumps(r)[:300], flush=True)
    if r.get('errors'): print('COMPILE ERRORS at', c, flush=True); continue
    sub = '%s-%d-%s' % (TAG, i, c[:7])
    p = subprocess.run([sys.executable, 'sky_sweep.py', sub, SWEEP, '--stock', '--view', VIEW, '--group', 'clear', '--hours', HOURS, '--fast'], cwd=HERE, env=env, capture_output=True, text=True)
    print(sub, 'rc', p.returncode, p.stdout[-600:], p.stderr[-300:], flush=True)
print('deployed now:', COMMITS[-1], flush=True)
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

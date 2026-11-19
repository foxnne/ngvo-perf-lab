"""VSync A/B with frame generation on: the same scenarios with SSE Display Tweaks EnableVSync true (as shipped) and false.
With VSync on, our DX12 swap chain presents with SyncInterval 1 and the frame limiter never runs, so any pacing wait
is inside Present. The ini is restored afterwards. Each side also keeps the Community Shaders log (hitch sampler lines).
usage: python vsync_ab.py TAG"""
import os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
TAG = sys.argv[1]
INI = 'C:/Modlists/NGVO 8.0 Beta/mods/NGVO - MCM and INI Settings/SKSE/Plugins/SSEDisplayTweaks.ini'
LOG = os.path.expanduser('~/Documents/My Games/Skyrim Special Edition/SKSE/BottledShaders.log')
MARK = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/HitchSample.on'
RES = os.path.join(os.path.dirname(HERE), 'results')
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
orig = open(INI, 'rb').read()
shutil.copy2(INI, INI + '.bak-pre-vsync-ab')
open(MARK, 'w').close()
try:
    for side, value in (('off', b'false'), ('on', b'true')):
        new, n = re.subn(rb'(?m)^(EnableVSync\s*=\s*)\w+', lambda m: m.group(1) + value, orig)
        if n != 1: sys.exit('EnableVSync line not found exactly once')
        open(INI, 'wb').write(new)
        label = f'{TAG}-vsync-{side}'
        p = subprocess.run([sys.executable, 'bench.py', 'run', label, '--scenarios', 'plains,forest_run,sprint2', '--tracy'], cwd=HERE, capture_output=True, text=True)
        open(os.path.join(RES, f'suite-{label}.log'), 'w').write(p.stdout + '\n' + p.stderr)
        for line in p.stdout.splitlines():
            if label in line: print(line, flush=True)
        time.sleep(15)
        if os.path.exists(LOG): shutil.copy2(LOG, os.path.join(RES, f'cslog-{label}.log'))
        time.sleep(25)
finally:
    open(INI, 'wb').write(orig)
    if os.path.exists(MARK): os.remove(MARK)
    print('ini restored, sampler marker removed', flush=True)

"""Waits for run_d.py to finish, then runs, each as its own game session:
1. Neural Rendering face shots at 100 / 75 / 50 % and off (user asked for these first)
2. elimination attribution on the plains and forest poses
3. forest standing shot, Riverwood -> Guardian Stones run, vista, steady Whiterun sprint, plains and face, 2 repetitions
4. candidate framings for the tuning views
Logs go to results/<name>.log."""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), 'results')


def busy():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'run_d.py' }).Count"], capture_output=True, text=True).stdout.strip()
    return out not in ('', '0')


def step(log, *cmd):
    p = subprocess.run([sys.executable, *cmd], cwd=HERE, capture_output=True, text=True)
    with open(os.path.join(RES, log), 'w') as f: f.write(p.stdout + '\n' + p.stderr)
    time.sleep(40)


while busy(): time.sleep(30)
time.sleep(60)
import json
MARK = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/'


def marker(name, on):
    p = MARK + name
    if on: open(p, 'w').close()
    elif os.path.exists(p): os.remove(p)


# Build with the hitch sampler and the Neural Rendering hand-off markers (diagnostics only; both idle unless switched on)
step('deploy-sampler.log', 'deploy.py', 'PR-Tracy')
step('nr_face.log', 'nr_face_shots.py')
# Does alternate-frame Neural Rendering gain anything once frame generation is off? (it gains nothing with it on, at 100%)
FG0 = {'Upscaling': {'frameGenerationMode': 0}}
step('suite-D2a.log', 'bench.py', 'run', 'D2-fgoff-nr-alt', '--scenarios', 'plains,spin', '--cs-set', json.dumps({**FG0, 'Neural Rendering': {'alternateFrames': True}}))
step('suite-D2b.log', 'bench.py', 'run', 'D2-fgoff-nr-everyframe', '--scenarios', 'plains,spin', '--cs-set', json.dumps({**FG0, 'Neural Rendering': {'alternateFrames': False}}))
step('attribution-E1.log', 'attribute.py', 'E1', '--scenes', 'plains,forest', '--shots')
step('suite-F.log', 'bench.py', 'run', 'F-routes', '--scenarios', 'forest,forest_run,vista,sprint2,plains,face', '--reps', '2')
# Small-hitch hunt on the steady routes: first with our VRAM tracking diagnostic off, then with the sampler on and a Tracy capture
marker('VramTrack.on', False)
step('suite-G1.log', 'bench.py', 'run', 'G1-vramtrack-off', '--scenarios', 'sprint2,forest_run', '--reps', '2')
marker('HitchSample.on', True)
step('suite-G2.log', 'bench.py', 'run', 'G2-sampler', '--scenarios', 'sprint2,forest_run,plains', '--tracy')
marker('HitchSample.on', False)
step('viewfinder.log', 'viewfinder.py')

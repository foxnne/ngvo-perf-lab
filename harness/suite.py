"""Full benchmark suite on the current configuration, as ONE process (kill this process to stop the whole suite).

usage: python suite.py TAG [--wait-shaders]      results labels are TAG-*
--wait-shaders: first launch the game and wait on the loading screen until the shader cache has finished compiling.
"""
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
tag = sys.argv[1]
LOG = os.path.join(os.path.dirname(HERE), 'results', f'suite-{tag}.log')
CSLOG = 'C:/Users/foxnn/Documents/My Games/Skyrim Special Edition/SKSE/BottledShaders.log'


def log(s):
    with open(LOG, 'a') as f: f.write(time.strftime('%H:%M:%S ') + s + '\n')


def run(label, *args):
    t0 = time.time()
    p = subprocess.run([sys.executable, 'bench.py', 'run', f'{tag}-{label}', *args], cwd=HERE, capture_output=True, text=True)
    log(f'=== {label} {" ".join(args)} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-1500:]}')


def wait_shaders(max_minutes=180):
    import bench, cs
    if bench.running(): bench.quit_game()
    if bench.mo2_running(): bench.close_mo2()
    for attempt in range(3):
        subprocess.Popen(['explorer.exe', os.path.join(HERE, 'launch-ngvo.lnk').replace('/', chr(92))])
        t0 = time.time()
        while time.time() - t0 < 75 and not bench.running(): time.sleep(5)
        if bench.running(): break
    t0 = time.time(); last = -1; quiet = 0; menu = False
    while time.time() - t0 < max_minutes * 60:
        try: menu = 'Main Menu' in cs.call('menu', {'action': 'list'})['openMenus']
        except Exception: menu = False
        sz = os.path.getsize(CSLOG) if os.path.exists(CSLOG) else 0
        quiet = quiet + 1 if sz == last else 0; last = sz
        if menu and quiet >= 6: break                     # menu up and the shader log quiet for 90 s
        if not bench.running(): log('game exited during shader compile'); return False
        time.sleep(15)
    txt = open(CSLOG, encoding='utf-8', errors='ignore').read()
    rem = re.findall(r'remaining=(\d+)', txt[-6000:])
    log('shader wait %.0f min, main menu=%s, last remaining=%s' % ((time.time() - t0) / 60, menu, rem[-1] if rem else '?'))
    for l in [x for x in txt.splitlines() if re.search(r'Neural|\[error\]', x)][-10:]: log('  cs: ' + l[27:230])
    bench.quit_game()
    return menu


if '--wait-shaders' in sys.argv and not wait_shaders():
    log('SUITE ABORTED: shader wait failed'); sys.exit(1)

core = ['--scenarios', 'plains,spin,sprint,flight']
run('warmup', *core)                                   # runtime shader compiles / first-visit bakes: discarded
run('base', *core, '--reps', '3')
run('scenes', '--scenarios', 'forest,city,interior')
run('tracy', *core, '--tracy')
quick = ['--scenarios', 'plains,spin,sprint']
NR = 'Neural Rendering'
run('nr-altframes', *quick, '--cs-set', json.dumps({NR: {'alternateFrames': True}}))
run('nr-off', *quick, '--cs-set', json.dumps({NR: {'enabled': False}}))
run('fg-off', *quick, '--cs-set', json.dumps({'Upscaling': {'frameGenerationMode': 0}}))
run('fg-nr-off', *quick, '--cs-set', json.dumps({'Upscaling': {'frameGenerationMode': 0}, NR: {'enabled': False}}))
run('treewind-off', *quick, '--cs-disable', 'TreeWind')
run('psky-off', *quick, '--cs-disable', 'PhysicalSky')
run('ssgi-ssr-off', *quick, '--cs-disable', 'ScreenSpaceGI,ScreenSpaceReflections')
log('SUITE DONE')

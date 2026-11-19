"""Phase D, one process: deploy the Tree Wind build-budget fix, wait for the shader cache, then measure.
D-base x3 (same scenarios as C-base), Tracy, then the NR / frame-generation / Physical Sky variants (settings only:
no Disable-at-Boot variants, those invalidate the shader cache), then the staged mods (apply_queue) and an E pass.
usage: python run_d.py   log: results/suite-D.log"""
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
LOG = os.path.join(os.path.dirname(HERE), 'results', 'suite-D.log')
CSLOG = 'C:/Users/foxnn/Documents/My Games/Skyrim Special Edition/SKSE/BottledShaders.log'


def log(s):
    with open(LOG, 'a') as f: f.write(time.strftime('%H:%M:%S ') + s + '\n')


def step(name, *cmd):
    p = subprocess.run([sys.executable, *cmd], cwd=HERE, capture_output=True, text=True)
    log('=== %s exit %d\n%s\n%s' % (name, p.returncode, p.stdout[-2500:], p.stderr[-1000:]))
    return p.returncode


def run(label, *args):
    t0 = time.time()
    p = subprocess.run([sys.executable, 'bench.py', 'run', label, *args], cwd=HERE, capture_output=True, text=True)
    log(f'=== {label} {" ".join(args)} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-1500:]}')
    return p.returncode


def close_all():
    if bench.running(): bench.quit_game()
    time.sleep(5)
    if bench.mo2_running(): bench.close_mo2()
    time.sleep(5)


def wait_shaders(max_minutes=150):
    close_all()
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
        if menu and quiet >= 6: break
        if not bench.running(): log('game exited during shader wait'); return False
        time.sleep(15)
    txt = open(CSLOG, encoding='utf-8', errors='ignore').read()
    rem = re.findall(r'remaining=(\d+)', txt)
    log('shader wait %.0f min, main menu=%s, compiles logged=%d, last remaining=%s' % ((time.time() - t0) / 60, menu, len(rem), rem[-1] if rem else 'none'))
    close_all()
    return menu


close_all()
if step('deploy treewind fix', 'deploy.py', 'PR-Tracy') != 0: log('ABORT: deploy failed'); sys.exit(1)
if not wait_shaders(): log('ABORT: shader wait failed'); sys.exit(1)
core = ['--scenarios', 'plains,spin,sprint,flight']; quick = ['--scenarios', 'plains,spin,sprint']
NR = 'Neural Rendering'; PS = 'Physical Sky'
run('D-warmup', *core)
run('D-base', *core, '--reps', '3')
run('D-tracy', '--scenarios', 'spin,sprint,flight', '--tracy')
run('D-scenes', '--scenarios', 'forest,city,interior')
for label, setting in (('nr-everyframe', {NR: {'alternateFrames': False}}),
                       ('nr-res75', {NR: {'resolutionScale': 0.75}}),
                       ('nr-res75-everyframe', {NR: {'resolutionScale': 0.75, 'alternateFrames': False}}),
                       ('nr-res50', {NR: {'resolutionScale': 0.5}}),
                       ('nr-off', {NR: {'enabled': False}}),
                       ('fg-off', {'Upscaling': {'frameGenerationMode': 0}}),
                       ('fg-nr-off', {'Upscaling': {'frameGenerationMode': 0}, NR: {'enabled': False}}),
                       ('psky-on', {PS: {'enabled': True, 'enableVolumetricClouds': False}}),
                       ('psky-volclouds', {PS: {'enabled': True, 'enableVolumetricClouds': True}})):
    run('D-' + label, *quick, '--cs-set', json.dumps(setting))
log('D DONE')
close_all(); time.sleep(20)
if step('apply_queue', 'apply_queue.py') == 0:
    run('E-warmup', '--scenarios', 'plains,sprint,city')
    run('E-newmods', '--scenarios', 'plains,spin,sprint,flight,forest,city,interior')
log('ALL DONE')

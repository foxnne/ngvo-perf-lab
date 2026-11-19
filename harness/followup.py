"""Queued behind suite.py and suite_extra.py: NR every-frame comparisons (the user's saved setting has alternateFrames on,
so every C-* run uses alternate frames), then applies the install queue. usage: python followup.py TAG"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); tag = sys.argv[1]
LOG = os.path.join(os.path.dirname(HERE), 'results', f'suite-{tag}.log')
def log(s):
    with open(LOG, 'a') as f: f.write(time.strftime('%H:%M:%S ') + s + '\n')
def suite_running():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'suite(_extra)?\.py' }).Count"], capture_output=True, text=True).stdout.strip()
    return out not in ('', '0')
time.sleep(5)
while suite_running(): time.sleep(30)
time.sleep(40)
while suite_running(): time.sleep(30)
def run(label, *args):
    t0 = time.time()
    p = subprocess.run([sys.executable, 'bench.py', 'run', f'{tag}-{label}', *args], cwd=HERE, capture_output=True, text=True)
    log(f'=== {label} {" ".join(args)} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-1500:]}')
quick = ['--scenarios', 'plains,spin,sprint']; NR = 'Neural Rendering'
run('nr-everyframe', *quick, '--cs-set', json.dumps({NR: {'alternateFrames': False}}))
run('nr-res75-everyframe', *quick, '--cs-set', json.dumps({NR: {'resolutionScale': 0.75, 'alternateFrames': False}}))
log('FOLLOWUP BENCH DONE')
def step(name, *cmd):
    p = subprocess.run([sys.executable, *cmd], cwd=HERE, capture_output=True, text=True)
    log('=== %s exit %d\n%s\n%s' % (name, p.returncode, p.stdout[-2000:], p.stderr[-1000:]))
    return p.returncode
# Tree Wind build-budget fix (built 14:16, PR-Tracy): deploy, then the same core scenarios as C-base, plus a Tracy capture
time.sleep(45)
if step('deploy treewind fix', 'deploy.py', 'PR-Tracy') == 0:
    core = ['--scenarios', 'plains,spin,sprint,flight']
    run2 = lambda label, *args: (lambda t0, p: log(f'=== {label} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-1500:]}'))(time.time(), subprocess.run([sys.executable, 'bench.py', 'run', f'D-{label}', *args], cwd=HERE, capture_output=True, text=True))
    run2('warmup', *core)
    run2('base', *core, '--reps', '3')
    run2('tracy', '--scenarios', 'sprint,flight', '--tracy')
    run2('scenes', '--scenarios', 'forest,city,interior')
# staged mods + OmniSight on, then one pass to see their effect (city scene for the overlay helper)
time.sleep(45)
if step('apply_queue', 'apply_queue.py') == 0:
    run2 = lambda label, *args: (lambda t0, p: log(f'=== {label} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-1500:]}'))(time.time(), subprocess.run([sys.executable, 'bench.py', 'run', f'E-{label}', *args], cwd=HERE, capture_output=True, text=True))
    run2('warmup', '--scenarios', 'plains,sprint,city')
    run2('newmods', '--scenarios', 'plains,spin,sprint,flight,forest,city,interior')
log('FOLLOWUP ALL DONE')

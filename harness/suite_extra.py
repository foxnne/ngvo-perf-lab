"""Extra comparisons queued behind suite C: waits for suite.py to finish, then runs. usage: python suite_extra.py TAG"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); tag = sys.argv[1]
LOG = os.path.join(os.path.dirname(HERE), 'results', f'suite-{tag}.log')
def log(s):
    with open(LOG, 'a') as f: f.write(time.strftime('%H:%M:%S ') + s + '\n')
def suite_running():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'suite.py' }).Count"], capture_output=True, text=True).stdout.strip()
    return out not in ('', '0')
while suite_running(): time.sleep(30)
def run(label, *args):
    t0 = time.time()
    p = subprocess.run([sys.executable, 'bench.py', 'run', f'{tag}-{label}', *args], cwd=HERE, capture_output=True, text=True)
    log(f'=== {label} {" ".join(args)} ({time.time() - t0:.0f}s, exit {p.returncode})\n{p.stdout[-3000:]}\n{p.stderr[-1500:]}')
quick = ['--scenarios', 'plains,spin,sprint']
NR = 'Neural Rendering'; PS = 'Physical Sky'
run('nr-res75', *quick, '--cs-set', json.dumps({NR: {'resolutionScale': 0.75}}))
run('nr-res75-alt', *quick, '--cs-set', json.dumps({NR: {'resolutionScale': 0.75, 'alternateFrames': True}}))
run('nr-res50', *quick, '--cs-set', json.dumps({NR: {'resolutionScale': 0.5}}))
run('psky-on', *quick, '--cs-set', json.dumps({PS: {'enabled': True, 'enableVolumetricClouds': False}}))
run('psky-volclouds', *quick, '--cs-set', json.dumps({PS: {'enabled': True, 'enableVolumetricClouds': True}}))
log('EXTRA DONE')

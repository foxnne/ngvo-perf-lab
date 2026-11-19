"""One-at-a-time job queue for the game (the game is a single resource; separately queued waiters collided).
Jobs are lines in harness/queue.txt: a python script and its arguments, relative to harness/. The runner takes the first line,
waits until the game is closed and no other harness script is running, runs it, logs to results/queue.log, and repeats.
Add a job:  python queue_runner.py add sky_sweep.py TAG sweeps/x.json --stock --view plains_west ...
Start it:   python queue_runner.py run        (keeps running; exits after 30 idle minutes with an empty queue)
A line starting with '!' is run with the game allowed to be closed-only edits (plain python script too); '#' lines are skipped."""
import os, subprocess, sys, time, shlex
HERE = os.path.dirname(os.path.abspath(__file__)); Q = os.path.join(HERE, 'queue.txt'); LOG = os.path.join(os.path.dirname(HERE), 'results', 'queue.log')
def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f: f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
def busy():
    ps = "(@(Get-Process SkyrimSE,ModOrganizer -ErrorAction SilentlyContinue).Count) + (@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'sky_sweep.py|load_shot.py|whale_check.py|footprint_check.py|save_sky_base.py|map_shot.py|bench.py|attribute.py' -and $_.CommandLine -notmatch 'queue_runner' }).Count)"
    out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.strip()
    return out not in ('0', '')
def pop():
    if not os.path.exists(Q): return None
    lines = [l for l in open(Q, encoding='utf-8').read().splitlines()]
    for i, l in enumerate(lines):
        if l.strip() and not l.startswith('#'):
            open(Q, 'w', encoding='utf-8').write('\n'.join(lines[:i] + lines[i + 1:]) + ('\n' if len(lines) > 1 else ''))
            return l.strip()
    return None
if sys.argv[1] == 'add':
    with open(Q, 'a', encoding='utf-8') as f: f.write(' '.join(shlex.quote(a) if ' ' in a else a for a in sys.argv[2:]) + '\n')
    print('queued:', ' '.join(sys.argv[2:]))
elif sys.argv[1] == 'run':
    idle_since = time.time(); log('runner started')
    while True:
        if busy(): time.sleep(20); idle_since = time.time(); continue
        time.sleep(25)
        if busy(): continue
        job = pop()
        if not job:
            if time.time() - idle_since > 1800: log('runner idle 30 min: exit'); break
            time.sleep(30); continue
        args = shlex.split(job); tag = args[1] if len(args) > 1 else args[0]
        log('start: ' + job)
        with open(os.path.join(os.path.dirname(HERE), 'results', f'job-{os.path.splitext(args[0])[0]}-{tag}.log'), 'w', encoding='utf-8') as out:
            rc = subprocess.run([sys.executable] + args, cwd=HERE, stdout=out, stderr=subprocess.STDOUT).returncode
        log(f'done rc={rc}: ' + job); idle_since = time.time(); time.sleep(30)
elif sys.argv[1] == 'list':
    print(open(Q, encoding='utf-8').read() if os.path.exists(Q) else '(empty)')

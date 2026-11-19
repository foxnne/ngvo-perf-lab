"""One job queue for the lab (replaces chained waiter scripts). usage: python jobq.py
Reads harness/queue.jsonl; each line: {"name": ..., "cmd": [args after python], "log": "results/x.log"} or {"name":..., "marker": ["File.on", true|false]}.
Takes the first line when nothing else of ours is running, removes it from the file, runs it, appends to results/jobq.log.
Edit queue.jsonl at any time to add, remove or reorder jobs (the running job is no longer in the file). Stop: create harness/queue.stop."""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); LAB = os.path.dirname(HERE)
Q = os.path.join(HERE, 'queue.jsonl'); STOP = os.path.join(HERE, 'queue.stop'); LOG = os.path.join(LAB, 'results', 'jobq.log')
MARK = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/'
OURS = ('bench.py', 'attribute.py', 'viewfinder.py', 'flicker.py', 'nr_face_shots.py', 'run_d.py', 'after_d.py', 'after_after.py', 'apply_queue.py', 'deploy.py')


def log(s):
    with open(LOG, 'a') as f: f.write(time.strftime('%H:%M:%S ') + s + '\n')


def busy():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\").CommandLine"], capture_output=True, text=True).stdout
    return any(n in out for n in OURS)


def game_or_mo2():
    t = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    return 'skyrimse.exe' in t or 'modorganizer.exe' in t


log('queue runner started')
while not os.path.exists(STOP):
    if busy(): time.sleep(15); continue
    try: lines = [l for l in open(Q, encoding='utf-8').read().splitlines() if l.strip()]
    except OSError: lines = []
    if not lines: time.sleep(20); continue
    try: job = json.loads(lines[0])
    except Exception as e:
        log('bad queue line dropped: %s' % lines[0][:120]); open(Q, 'w', encoding='utf-8').write('\n'.join(lines[1:]) + '\n'); continue
    open(Q, 'w', encoding='utf-8').write('\n'.join(lines[1:]) + ('\n' if len(lines) > 1 else ''))
    if 'marker' in job:
        name, on = job['marker']; p = MARK + name
        if on: open(p, 'w').close()
        elif os.path.exists(p): os.remove(p)
        log('marker %s -> %s' % (name, on)); continue
    # jobs launch the game themselves: give a previous game / Mod Organizer time to close
    # Never start over a running game: after a job it closes within a minute or two; if it stays open the user is
    # playing (or a quit failed), so wait for it however long that takes, and say so once in the log.
    t0 = time.time(); said = False
    while game_or_mo2():
        if time.time() - t0 > 180 and not said: log('waiting: the game or Mod Organizer is still open (user playing?)'); said = True
        if os.path.exists(STOP): break
        time.sleep(10)
    time.sleep(20)
    log('START %s: %s' % (job.get('name'), ' '.join(job['cmd'])[:200])); t0 = time.time()
    p = subprocess.run([sys.executable, *job['cmd']], cwd=HERE, capture_output=True, text=True)
    if job.get('log'):
        with open(os.path.join(LAB, job['log']), 'w') as f: f.write(p.stdout + '\n' + p.stderr)
    log('END   %s (%.0f s, exit %d) %s' % (job.get('name'), time.time() - t0, p.returncode, (p.stdout.strip().splitlines() or [''])[-1][:160]))
log('queue runner stopped (queue.stop)')

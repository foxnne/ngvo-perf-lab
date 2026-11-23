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
GAME_JOBS = ('look_proposal.py', 'look_layers.py', 'grass_slider.py', 'grass_zoom.py', 'rift_fog_ab.py', 'vram_breakdown.py', 'rift_weather.py', 'mem_probe.py', 'sky_sweep.py', 'rocks_closeup.py', 'haze_ab.py', 'lod_overlook.py', 'bloom_ext_ab.py', 'memory_walk.py', 'forest_views.py', 'interior_perf_ab.py', 'helios_verify.py', 'bloom_ab.py', 'beams_ab.py', 'interior_natural_time.py', 'interior_sun_weather.py', 'timejump_settings_diff.py', 'interior_sun_recovery.py', 'interior_sun_rotation.py', 'interior_sun_skysync.py', 'interior_sun_hours.py', 'freeze_lights_check.py', 'interior_exposure_ab.py', 'light_tally_ab.py', 'llf_shadow_ab.py', 'interior_ab.py', 'hands_ab.py', 'apply_save.py', 'lightning_demo.py', 'load_shot.py', 'map_shot.py', 'whale_check.py', 'footprint_check.py', 'baseline_shoot.py', 'profile_passes.py')
def is_game_job(line): return bool(line) and line.split()[0] in GAME_JOBS and '--fresh' not in line
def other_scripts():
    ps = "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'sky_sweep.py|lightning_demo.py|build_deploy_job.py|first_launch.py|load_shot.py|whale_check.py|footprint_check.py|baseline_shoot.py|profile_passes.py|save_sky_base.py|map_shot.py|bench.py|attribute.py' -and $_.CommandLine -notmatch 'queue_runner' }).Count"
    out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.strip()
    return out not in ('0', '')
def game_open():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-Process SkyrimSE,ModOrganizer -ErrorAction SilentlyContinue).Count"], capture_output=True, text=True).stdout.strip()
    return out not in ('0', '')
def close_game():
    subprocess.run([sys.executable, '-c', 'import bench; bench.quit_game()'], cwd=HERE); time.sleep(10)
def peek():
    if not os.path.exists(Q): return None
    for l in open(Q, encoding='utf-8').read().splitlines():
        if l.strip() and not l.startswith('#'): return l.strip()
    return None
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
    LOCK = os.path.join(HERE, 'queue_runner.lock')   # one runner only: a second one closed the game mid-job (2026-11-21)
    if os.path.exists(LOCK):
        old_pid = open(LOCK).read().strip()
        alive = old_pid and old_pid in subprocess.run(['tasklist', '/FI', 'PID eq ' + old_pid], capture_output=True, text=True).stdout
        if alive: print('another runner is active (pid %s); not starting' % old_pid); sys.exit(1)
    open(LOCK, 'w').write(str(os.getpid()))
    idle_since = time.time(); log('runner started (session mode: the game stays open between consecutive game jobs)')
    while True:
        if other_scripts(): time.sleep(15); idle_since = time.time(); continue
        job = pop()
        if not job:
            if game_open() and time.time() - idle_since > 240: log('queue empty for 4 min: closing the game'); close_game()
            if time.time() - idle_since > 1800: log('runner idle 30 min: exit'); break
            time.sleep(20); continue
        args = shlex.split(job); args[0] = args[0].lstrip('!'); tag = args[1] if len(args) > 1 else args[0]
        env = dict(os.environ)
        if is_game_job(job):
            env['NGVO_ATTACH'] = '1'
            if is_game_job(peek()): env['NGVO_KEEP_OPEN'] = '1'
        elif game_open():
            log('closing the game for: ' + job); close_game()
        log('start%s: %s' % (' (attached)' if is_game_job(job) and game_open() else '', job))
        with open(os.path.join(os.path.dirname(HERE), 'results', f'job-{os.path.splitext(args[0])[0]}-' + ''.join(c if c.isalnum() or c in '-_.' else '_' for c in str(tag))[-60:] + '.log'), 'w', encoding='utf-8') as out:
            rc = subprocess.run([sys.executable] + args, cwd=HERE, stdout=out, stderr=subprocess.STDOUT, env=env).returncode
        log(f'done rc={rc}: ' + job); idle_since = time.time(); time.sleep(8)
elif sys.argv[1] == 'list':
    print(open(Q, encoding='utf-8').read() if os.path.exists(Q) else '(empty)')

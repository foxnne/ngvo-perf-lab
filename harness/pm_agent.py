r"""PresentMon helper. Run it once under a fresh sign-in so it has the Performance Log Users permission:
    runas /user:foxnn "C:\Users\foxnn\AppData\Local\Programs\Python\Python312\python.exe C:\Users\foxnn\dev\ngvo-perf-lab\harness\pm_agent.py"
It waits for capture requests from the benchmark harness (results/pm/requests/*.json: {"out": csv path, "seconds": n}) and runs
PresentMon for each, so every test gets its own closed CSV. Leave the window open; closing it stops PresentMon captures."""
import glob, json, os, subprocess, time
LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PM = os.path.join(LAB, 'ext', 'presentmon', 'PresentMon-2.6.0-x64.exe'); REQ = os.path.join(LAB, 'results', 'pm', 'requests'); ALIVE = os.path.join(LAB, 'results', 'pm', 'agent.alive')
os.makedirs(REQ, exist_ok=True); print('PresentMon helper running. Leave this window open.', flush=True); last = 0; n = 0
while True:
    if time.time() - last > 2:
        try: open(ALIVE, 'w').write(str(time.time()))
        except OSError: pass
        last = time.time()
    for f in sorted(glob.glob(os.path.join(REQ, '*.json'))):
        try: r = json.load(open(f)); os.remove(f)
        except Exception: continue
        n += 1; print(time.strftime('%H:%M:%S'), 'capture', n, r['seconds'], 's ->', r['out'], flush=True)
        subprocess.Popen([PM, '--process_name', 'SkyrimSE.exe', '--output_file', r['out'], '--timed', str(int(r['seconds'])), '--terminate_after_timed',
                          '--no_console_stats', '--stop_existing_session', '--track_frame_type'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)

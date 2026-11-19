"""Waits for the running game to finish compiling shaders (reads the 'remaining=' count in the Community Shaders log), then quits it."""
import os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
L = os.path.expanduser('~/Documents/My Games/Skyrim Special Edition/SKSE/BottledShaders.log')
def remaining():
    try:
        with open(L, 'rb') as f:
            f.seek(max(0, os.path.getsize(L) - 200000)); t = f.read().decode('utf-8', 'replace')
        m = re.findall(r'remaining=(\d+)', t); return int(m[-1]) if m else None, os.path.getmtime(L)
    except Exception: return None, 0
t0 = time.time(); last = None
while bench.running() and time.time() - t0 < 4 * 3600:
    r, mt = remaining(); quiet = time.time() - mt
    if r != last and (last is None or r is None or abs((last or 0) - r) >= 100): print(time.strftime('%H:%M'), 'remaining', r, flush=True); last = r
    if r is not None and r <= 3 and quiet > 240: break       # nothing left and the log has been quiet for 4 minutes
    if quiet > 1500: print('log quiet for 25 min at remaining', r, flush=True); break
    time.sleep(60)
print(time.strftime('%H:%M'), 'finished waiting: remaining', remaining()[0], 'after', round((time.time() - t0) / 60), 'min', flush=True)
try: bench.quit_game()
except Exception as e: print('quit failed', str(e)[:80], flush=True)

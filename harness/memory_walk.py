"""Queue job: where does the extra ~12 GB of committed memory come from? Launch, then record SkyrimSE private bytes, working set
and system free RAM at the loaded save and after travelling to each of several exterior cells (each settled 20 s).
usage: python memory_walk.py TAG   Output results/memory/TAG.json"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'memory'); os.makedirs(OUT, exist_ok=True)
def mem():
    ps = ("$p=Get-Process SkyrimSE -ErrorAction SilentlyContinue | Select-Object -First 1; $os=Get-CimInstance Win32_OperatingSystem; "
          "'{0} {1} {2}' -f [math]::Round($p.PrivateMemorySize64/1MB), [math]::Round($p.WorkingSet64/1MB), [math]::Round($os.FreePhysicalMemory/1KB)")
    o = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.split()
    return dict(private_mb=int(o[0]), working_set_mb=int(o[1]), system_free_mb=int(o[2])) if len(o) == 3 else {'raw': o}
rep = []
def rec(name): time.sleep(20); r = dict(step=name, **mem()); rep.append(r); print(json.dumps(r), flush=True)
bench.launch(); bench.all_on(); rec('0_loaded_save')
STOPS = [('plains', 'WhiterunExterior04'), ('riverwood', 'cow Tamriel 4 -12'), ('forest_south', 'cow Tamriel 2 -14'), ('falkreath', 'cow Tamriel -6 -20'), ('rift', 'cow Tamriel 40 -24'), ('plains_again', 'WhiterunExterior04')]
try:
    for name, where in STOPS:
        if where.startswith('cow'): bench.console(where); time.sleep(8); bench.settle()
        else: bench.goto(where)
        rec(name)
finally:
    json.dump(rep, open(os.path.join(OUT, TAG + '.json'), 'w'), indent=1)
bench.finish()

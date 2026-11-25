"""Reproduce the video memory overflow: launch, jump through regions, log frame time and memory after each (60 s settle)."""
import json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('NGVO_MENU_WAIT', '2400')
import bench, cs, shots
LOG = os.path.expanduser(r'~\Documents\My Games\Skyrim Special Edition\SKSE\TheosRenderPipeline.log'); OUT = os.path.join(shots.ROOT, 'results', 'perf40', 'vram_repro.jsonl')
bench.launch()
for i in range(40):
    m = bench.menus()
    if m.get('messageBoxOpen') and 'Main Menu' not in m.get('openMenus', []):
        bench.tap('right'); time.sleep(.6); bench.tap('enter'); time.sleep(3); continue
    s = bench.state_()
    if s.get('cell') and 'Loading Menu' not in m.get('openMenus', []) and i > 4: break
    time.sleep(3)
def read(tag):
    pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']; l = [x for x in open(LOG, encoding='utf-8', errors='replace') if 'Performance NR' in x][-1]
    g = lambda k: int(re.search(k + r'=(\d+)', l).group(1))
    card = int(subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout.strip())
    r = dict(tag=tag, t=time.strftime('%H:%M:%S'), ms=round(pr['avgMs'], 1), p95=round(pr['p95Ms'], 1), card_mb=card, game_gb=round(g('vramUsageBytes') / 2**30, 2), budget_gb=round(g('vramBudgetBytes') / 2**30, 2), spilled_mb=round(g('vramProcessDemotedBytes') / 2**20))
    open(OUT, 'a').write(json.dumps(r) + '\n'); print(json.dumps(r), flush=True); return r
if os.path.exists(OUT): os.remove(OUT)
time.sleep(20); read('loaded save (inn)')
STOPS = [('stables', 'coc WhiterunExterior01'), ('falkreath forest', 'cow Tamriel -2 -14'), ('riverwood', 'coc Riverwood'), ('rift forest', 'cow Tamriel 40 -24'), ('falkreath town side', 'cow Tamriel -6 -20'),
         ('reach', 'cow Tamriel -36 4'), ('pale coast', 'cow Tamriel 10 24'), ('stables again', 'coc WhiterunExterior01'), ('falkreath forest again', 'cow Tamriel -2 -14'), ('stables third', 'coc WhiterunExterior01')]
cs.world(action='timescale', value=1)
for name, where in STOPS:
    bench.console(where); time.sleep(10); shots.ready(25, 150); cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(60)
    r = read(name)
cs.world(action='timescale', value=20); cs.world(action='weather', name='SunnyPF', instant=False, lock=False); print('done')

"""Faster Objects on/off: locked views in Riverwood and on the plains, then (off only) the nine-stop region run that crashed before."""
import json, os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('NGVO_MENU_WAIT', '2400')
import bench, cs, shots
INI = r'C:\Modlists\NGVO 8.0 Beta\mods\Faster Objects\SKSE\Plugins\SkyrimPrecombines.ini'; BAK = INI + '.bak-pre-offtest-20261124'
OUT = os.path.join(shots.ROOT, 'results', 'perf40', 'faster_objects'); os.makedirs(OUT, exist_ok=True); ROWS = os.path.join(OUT, 'rows.jsonl')
if not os.path.exists(BAK): shutil.copy(INI, BAK)
base = open(BAK, encoding='utf-8-sig').read()
def start(enabled):
    if bench.running(): bench.quit_game(); time.sleep(10)
    open(INI, 'w', encoding='utf-8').write(base if enabled else re.sub(r'(?m)^bEnabled\s*=\s*1', 'bEnabled=0', base, count=1))
    bench.launch()
    for i in range(40):
        m = bench.menus()
        if m.get('messageBoxOpen') and 'Main Menu' not in m.get('openMenus', []):
            bench.tap('right'); time.sleep(.6); bench.tap('enter'); time.sleep(3); continue
        s = bench.state_()
        if s.get('cell') and 'Loading Menu' not in m.get('openMenus', []) and i > 4: break
        time.sleep(3)
    return bench.running()
def row(label, tag):
    v = []
    for _ in range(3): v.append(cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']['avgMs']); time.sleep(8)
    d = cs.call('communityshaders.inspect', {'kind': 'drawcalls'})['shaders']; gpu = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout.strip()
    r = dict(variant=label, view=tag, ms=round(sum(v) / 3, 1), total=round(d['Total']['drawCalls']), cpu=round(d['Total']['cpuMs'], 1), utility=round(d['Utility']['drawCalls']), lighting=round(d['Lighting']['drawCalls']), gpu=gpu)
    open(ROWS, 'a').write(json.dumps(r) + '\n'); print(json.dumps(r), flush=True)
def views(label):
    cs.world(action='timescale', value=0)
    bench.console('coc Riverwood'); time.sleep(10); shots.ready(25, 150); cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True)
    cs.world(action='teleport', x=17256.0, y=-47220.9, z=-144.5, rz=58.7); time.sleep(3); shots.tb(action='camera', mode='override', x=17149.7, y=-47373.2, z=-23.5, pitch=0, yaw=58.7, fov=85); time.sleep(75); row(label, 'riverwood day')
    shots.tb(action='camera', mode='player'); bench.console('coc WhiterunExterior01'); time.sleep(10); shots.ready(25, 150); cs.world(action='hour', value=13.0)
    shots.tb(action='camera', mode='override', x=18322.0, y=-10992.0, z=-4500.0, pitch=0, yaw=276.0, fov=85); time.sleep(75); row(label, 'plains from stables')
    shots.tb(action='camera', mode='player'); cs.world(action='timescale', value=1)
try:
    if os.path.exists(ROWS): os.rename(ROWS, ROWS + '.' + time.strftime('%H%M%S'))
    if start(True): views('faster objects ON')
    if start(False):
        views('faster objects OFF')
        for name, where in [('stables', 'coc WhiterunExterior01'), ('falkreath forest', 'cow Tamriel -2 -14'), ('riverwood', 'coc Riverwood'), ('rift forest', 'cow Tamriel 40 -24'), ('falkreath town side', 'cow Tamriel -6 -20'), ('reach', 'cow Tamriel -36 4'), ('stables again', 'coc WhiterunExterior01'), ('falkreath forest again', 'cow Tamriel -2 -14'), ('riverwood again', 'coc Riverwood')]:
            if not bench.running(): print('GAME NOT RUNNING before', name, flush=True); break
            bench.console(where); time.sleep(10); shots.ready(25, 150); cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(55)
            pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']; print('jump %-24s %.1f ms (%.0f fps) p95 %.1f' % (name, pr['avgMs'], 1000 / pr['avgMs'], pr['p95Ms']), flush=True)
        print('region run finished, game running:', bench.running(), flush=True)
finally:
    shutil.copy(BAK, INI); print('ini restored (takes effect next start); game left running with Faster Objects', 'OFF' if bench.running() else '(not running)', flush=True)
    if bench.running(): cs.world(action='timescale', value=20); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)

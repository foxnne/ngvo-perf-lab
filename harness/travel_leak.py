"""Does memory come back after leaving a region? (user 2026-11-24: fast travel must be able to go everywhere smoothly.)
Jumps between far-apart exterior places, waits, and after each jump logs process RAM, video memory, the Neural Rendering
time and the video memory tracker's totals per owner and kind. With --purge the game's 'pcb' (purge cell buffers) is run
after each arrival. No camera work, no weather changes: the character just arrives and stands.
usage: python travel_leak.py TAG [--purge] [--rounds 2]"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
TAG = sys.argv[1]; PURGE = '--purge' in sys.argv; ROUNDS = int(sys.argv[sys.argv.index('--rounds') + 1]) if '--rounds' in sys.argv else 2
OUT = os.path.join(shots.ROOT, 'results', 'travel_leak'); os.makedirs(OUT, exist_ok=True)
TRACK = 'C:/Modlists/NGVO 8.0 Beta/overwrite/SKSE/Plugins/CommunityShaders/VramTrack.jsonl'
PLACES = ['cow Tamriel 40 -22', 'cow Tamriel 10 20', 'cow Tamriel -38 2', 'cow Tamriel -18 22', 'cow Tamriel 4 -3', 'cow Tamriel -2 -14']   # Rift, Pale, Reach, Haafingar, Whiterun, Ilinalta


def track():
    try:
        with open(TRACK, 'rb') as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - 20000)); line = f.read().decode('utf-8', 'replace').strip().splitlines()[-1]
        d = json.loads(line); live = d.get('live', {}); grp = {}
        for k, v in live.items():
            kind = k.split('|')[1]; g = 'textures' if kind.startswith('tex') else 'geometry' if kind == 'buf_geom' else 'render targets' if kind in ('rt', 'uav', 'cube') else 'other buffers'
            grp[g] = grp.get(g, 0) + v
        return {'trackedMB': round(d.get('totalLiveMB', 0)), 'procMB': round(d.get('procMB', 0)), 'budgetMB': round(d.get('budgetMB', 0)), **{k: round(v) for k, v in grp.items()}, 'counts': d.get('liveCount', {})}
    except Exception as e:
        return {'trackError': repr(e)[:80]}


def mem():
    g = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(['powershell', '-NoProfile', '-Command', "$p=Get-Process SkyrimSE; '{0:F0} {1:F0}' -f ($p.WorkingSet64/1MB),($p.PrivateMemorySize64/1MB)"], capture_output=True, text=True).stdout.split()
    p = cs.call('communityshaders.inspect', {'kind': 'profiler'}); nr = [x['gpuAvgMs'] for x in p['passes'] if x['name'] == 'NeuralRendering::Generate']
    return {'gpuMB': int(g), 'ramMB': int(r[0]), 'privateMB': int(r[1]), 'frameMs': round(p['frame']['avgMs'], 1), 'nrMs': round(nr[0], 1) if nr else None, **track()}


rows = []
def log(label):
    m = mem(); m['step'] = label; c = m.pop('counts', {}); rows.append({**m, 'counts': c})
    print('%-26s RAM %6d  video %6d  tracked %6s (tex %5s geom %5s rt %5s)  frame %6.1f ms  NR %s' % (label, m['privateMB'], m['gpuMB'], m.get('trackedMB'), m.get('textures'), m.get('geometry'), m.get('render targets'), m['frameMs'], m['nrMs']), flush=True)
    json.dump(rows, open(os.path.join(OUT, TAG + '.json'), 'w'))


log('start')
for r in range(ROUNDS):
    for pl in PLACES:
        if not bench.running(): print('GAME DIED'); sys.exit(1)
        bench.console(pl); time.sleep(8); shots.ready(25, 150)
        if PURGE: bench.console('pcb'); time.sleep(6)
        log('r%d %s%s' % (r + 1, pl[12:], ' +purge' if PURGE else ''))
time.sleep(60); log('after 60 s standing')

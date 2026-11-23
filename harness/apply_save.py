"""Queue job: apply feature setting changes in the game and save them to the user settings file through the bridge.
usage: python apply_save.py TAG '{"ShortName": {"Key": value, ...}, ...}'   (attaches to a running game or launches one)"""
import atexit, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
changes = json.loads(open(sys.argv[2][1:]).read()) if sys.argv[2].startswith('@') else json.loads(sys.argv[2])
bench.launch(); DONE = []; atexit.register(lambda: (not DONE) and bench.running() and bench.quit_game())
for short, ch in changes.items():
    g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); s = g.get('settings', g)
    missing = [k for k in ch if k not in s]; s.update(ch)
    r = cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s}); time.sleep(1)
    rb = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); rb = rb.get('settings', rb)
    print(short, 'applied', r.get('applied'), 'readback', {k: rb.get(k) for k in ch}, 'keys not present before:', missing, flush=True)
print('save', cs.call('communityshaders.settings', {'action': 'save'}), flush=True); time.sleep(8)
DONE.append(1); bench.finish()

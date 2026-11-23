"""Apply haze loading in a running game (forcing the preset to re-derive), check the height fog strength, save settings, take a check frame."""
import copy, json, os, shutil, sys, time, atexit
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
LOAD = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2; FOG = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
def get(short):
    g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return g.get('settings', g)
bench.launch(); DONE = []; atexit.register(lambda: (not DONE) and bench.running() and bench.quit_game())
bench.console('tgm'); bench.all_on()
s = get('PhysicalSky'); s['aerosolLoading'] = LOAD; s0 = copy.deepcopy(s); s0['aerosolType'] = 0
cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s0}); time.sleep(1.5)
print('sky', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': s}).get('applied'), flush=True); time.sleep(4)
rb = get('PhysicalSky'); print('haze readback', {k: rb.get(k) for k in ('aerosolType', 'aerosolLoading', 'aerosolScatter', 'aerosolAbsorption')}, flush=True)
f = get('ExponentialHeightFog'); print('fog as loaded', f.get('vanillaFogStrength'), flush=True)
if abs(float(f.get('vanillaFogStrength', 0)) - FOG) > 1e-3:
    f['vanillaFogStrength'] = FOG; print('fog set', cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'ExponentialHeightFog', 'settings': f}).get('applied'), flush=True)
print('save', cs.call('communityshaders.settings', {'action': 'save'}), flush=True); time.sleep(8)
DONE.append(1); bench.quit_game()

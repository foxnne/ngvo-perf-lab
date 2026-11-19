"""First launch after a fork update: wait for the shader cache to finish compiling, then record the live state and quit.
output: results/first_launch-<date>.json"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
out = {'started': time.strftime('%H:%M:%S')}
bench.launch(); bench.console('tgm'); bench.goto('WhiterunExterior04'); bench.exterior_setup()
last = None; t0 = time.time()
while time.time() - t0 < 3 * 3600:
    try: sc = cs.call('communityshaders.inspect', {'kind': 'shadercache'})
    except Exception as e: sc = {'error': str(e)[:80]}
    brief = json.dumps(sc)[:220]
    if brief != last: print(time.strftime('%H:%M:%S'), brief, flush=True); last = brief
    active = sc.get('active', sc.get('compiling')); pending = sc.get('pending', sc.get('queued', sc.get('remaining')))
    if 'error' not in sc and not active and not pending and time.time() - t0 > 120: break
    time.sleep(30)
out['shadercache'] = sc; out['compile_minutes'] = round((time.time() - t0) / 60, 1)
out['all_on'] = bench.all_on(strict=False)
for short in ('PhysicalSky', 'NeuralRendering', 'PostProcessing', 'Upscaling', 'VolumetricLighting'):
    g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); out[short] = g.get('settings', g)
json.dump(out, open(os.path.join(os.path.dirname(HERE), 'results', 'first_launch-' + time.strftime('%Y%m%d-%H%M') + '.json'), 'w'), indent=1)
print('done after', out['compile_minutes'], 'min', flush=True)
bench.quit_game()

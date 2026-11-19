"""Close-up face shots at Neural Rendering resolution 100 / 75 / 50 % (and NR off for reference), same pose and light.
usage: python nr_face_shots.py [--no-launch] [--keep-open]   output: results/nr_face/"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
OUT = os.path.join(os.path.dirname(HERE), 'results', 'nr_face'); os.makedirs(OUT, exist_ok=True)
# The player's head is driven by real-time gaze plugins (Fourth Wall eye contact, TrueGaze, Optimal Gaze): they ignore
# sgtm and tfc freezes, so a matched pose needs them off for this session. DLL-only mods, so the load order is untouched.
GAZE = []   # not needed now that the bridge has a real freeze (world action 'freeze'); kept for reference: Fourth Wall, TrueGaze, Optimal Gaze
ML = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/modlist.txt'
ml_backup = None
if '--no-launch' not in sys.argv:
    if bench.running(): bench.quit_game(); time.sleep(8)
    if bench.mo2_running(): bench.close_mo2(); time.sleep(5)
    ml_backup = open(ML, 'rb').read()
    t = ml_backup.decode('utf-8-sig')
    CR, NL = chr(13), chr(10)
    for g in GAZE: t = t.replace('+' + g + CR + NL, '-' + g + CR + NL).replace('+' + g + NL, '-' + g + NL)
    open(ML, 'wb').write(t.encode('utf-8'))
    bench.launch()
bench.console('tgm'); bench.goto('WhiterunExterior04'); bench.exterior_setup()
cs.world(action='teleport', x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=0.0, rz=160.0); time.sleep(10)
g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'NeuralRendering'}); orig = g.get('settings', g)
if not isinstance(orig, dict) or 'error' in g: sys.exit('could not read Neural Rendering settings: %s' % str(g)[:200])
log = {'original': {k: orig.get(k) for k in ('enabled', 'alternateFrames', 'resolutionScale', 'resolutionScaleX', 'resolutionScaleY')}, 'shots': []}
cs.world(action='timescale', value=0)                # freeze time of day so the light is identical
r = cs.world(action='freeze', on=True); print('freeze', r, flush=True); time.sleep(1)   # stops animation, hair and wind; rendering continues
try:
    for framing, kw in (('tight', dict(distance=60.0, height=112.0, pitch=-2.0, fov=35.0)), ('bust', dict(distance=95.0, height=105.0, pitch=-2.0, fov=40.0))):
        bench.face_camera(True, **kw); time.sleep(4)
        import numpy as np
        from PIL import Image
        def _lum(p): return np.asarray(Image.open(p).convert('RGB').resize((860, 360))).astype(np.float32).mean(axis=2) / 255
        _a = _lum(cs.shot('nrface-check1')); time.sleep(4); _b = _lum(cs.shot('nrface-check2'))
        log.setdefault('pose_check', {})[framing] = round(float(np.abs(_a - _b).mean()), 5); print(framing, 'pose check (same settings, 4 s apart) mean diff', log['pose_check'][framing], flush=True)
        if log['pose_check'][framing] > 0.012:
            print('pose still moving: not taking this set', flush=True); continue
        for name, change in (('100', {'enabled': True, 'resolutionScale': 1.0, 'resolutionScaleX': 1.0, 'resolutionScaleY': 1.0}),
                             ('075', {'enabled': True, 'resolutionScale': 0.75, 'resolutionScaleX': 0.75, 'resolutionScaleY': 0.75}),
                             ('050', {'enabled': True, 'resolutionScale': 0.5, 'resolutionScaleX': 0.5, 'resolutionScaleY': 0.5}),
                             ('off', {'enabled': False})):
            s = copy.deepcopy(orig); s.update({k: v for k, v in change.items() if k in orig or k == 'enabled'})
            cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': s}); time.sleep(8)   # let the model settle
            back = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'NeuralRendering'}); back = back.get('settings', back)
            src = cs.shot(f'nrface-{framing}-{name}'); time.sleep(1.0)
            dst = os.path.join(OUT, f'face_{framing}_nr{name}' + os.path.splitext(src)[1]); shutil.copy2(src, dst)
            log['shots'].append({'file': dst, 'framing': framing, 'wanted': change, 'readback': {k: back.get(k) for k in ('enabled', 'resolutionScale', 'alternateFrames')}})
            print(framing, name, 'read back', log['shots'][-1]['readback'], flush=True)
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'NeuralRendering', 'settings': orig})
    try: bench.face_camera(False)
    except Exception: pass
    cs.world(action='freeze', on=False)
    cs.world(action='timescale', value=1)
json.dump(log, open(os.path.join(OUT, 'shots.json'), 'w'), indent=1)
if '--no-launch' not in sys.argv and '--keep-open' not in sys.argv: bench.quit_game()
if ml_backup is not None:
    time.sleep(10)
    if bench.mo2_running(): bench.close_mo2(); time.sleep(6)
    open(ML, 'wb').write(ml_backup); print('modlist restored (gaze plugins back on)', flush=True)

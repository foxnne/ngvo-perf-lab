"""Temporal flicker measurement at a fixed standing pose: for each setting, a burst of screenshots (real frames only, never
generated ones) and the mean frame-to-frame change in brightness, split into bands (sky / distance / near ground).
Wind moves grass in every setting, so compare settings with each other, not against zero.
usage: python flicker.py TAG [--no-launch] [--keep-open]    output: results/flicker-TAG.json + results/flicker-TAG/"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
import numpy as np
from PIL import Image
TAG = [a for a in sys.argv[1:] if not a.startswith('--')][0]
OUT = os.path.join(os.path.dirname(HERE), 'results', f'flicker-{TAG}'); os.makedirs(OUT, exist_ok=True)
N = 10


def feat(short, changes):
    box = {}
    def on():
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); box['orig'] = g.get('settings', g)
        s = copy.deepcopy(box['orig']); s.update(changes); cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
    def off(): cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': box['orig']})
    return on, off


SETTINGS = [('base', 'saved settings (NR 100%, alternate frames)', (lambda: None, lambda: None)),
            ('nr-everyframe', 'Neural Rendering every frame', feat('NeuralRendering', {'alternateFrames': False})),
            ('nr-off', 'Neural Rendering off', feat('NeuralRendering', {'enabled': False})),
            ('nr-75', 'Neural Rendering 75%', feat('NeuralRendering', {'resolutionScale': 0.75, 'resolutionScaleX': 0.75, 'resolutionScaleY': 0.75})),
            ('vol-clouds', 'volumetric clouds on (untuned)', feat('PhysicalSky', {'enableVolumetricClouds': True})),
            ('base-again', 'saved settings, repeated', (lambda: None, lambda: None))]


def burst(name):
    frames = []
    for i in range(N):
        src = cs.shot(f'flick-{name}-{i}'); time.sleep(0.25)
        im = np.asarray(Image.open(src).convert('RGB')).astype(np.float32) / 255.0
        frames.append(0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2])
        if i == 0: shutil.copy2(src, os.path.join(OUT, f'{name}' + os.path.splitext(src)[1]))
        try: os.remove(src)
        except OSError: pass
    f = np.stack(frames); d = np.abs(np.diff(f, axis=0)); h = f.shape[1]
    bands = {'sky (top third)': (0, h // 3), 'distance (middle third)': (h // 3, 2 * h // 3), 'near ground (bottom third)': (2 * h // 3, h)}
    out = {k: round(float(d[:, a:b, :].mean()) * 1000, 2) for k, (a, b) in bands.items()}
    out['share of pixels changing by more than 4% (distance band)'] = round(float((d[:, h // 3:2 * h // 3, :] > 0.04).mean()) * 100, 2)
    return out


if '--no-launch' not in sys.argv: bench.launch()
bench.console('tgm'); results = {}
for place, (cell, pose) in {'plains': ('WhiterunExterior04', dict(x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=-3.0, rz=247.0)),
                            'ilinalta': ('GuardianStones', dict(x=662.0, y=-59220.0, z=612.0, rx=-3.0, rz=278.5))}.items():
    try:
        bench.goto(cell); bench.exterior_setup(); cs.world(action='teleport', **pose); time.sleep(12)
        results[place] = {}
        for name, what, (on, off) in SETTINGS:
            try:
                on(); time.sleep(8); r = burst(f'{place}-{name}'); off(); time.sleep(3)
                results[place][name] = {'what': what, **r}; print(place, name, r, flush=True)
            except Exception as e:
                print(place, name, 'ERROR', str(e)[:120], flush=True)
                try: off()
                except Exception: pass
    except Exception as e: print(place, 'ERROR', str(e)[:120], flush=True)
    json.dump(results, open(os.path.join(os.path.dirname(HERE), 'results', f'flicker-{TAG}.json'), 'w'), indent=1)
if '--no-launch' not in sys.argv and '--keep-open' not in sys.argv: bench.quit_game()

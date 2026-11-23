"""Queue job: general screenshots of each region, to see the biome grass and trees. For every place: coc there, clear
weather, a few hours, and four camera directions from 2 m above the player looking slightly down.
Places whose coc fails are skipped and logged. usage: python region_tour.py TAG [--hours 9,15]
Output: results/region_tour/TAG/<place>__h<hour>__<yaw>.png and a contact sheet per place."""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image
TAG = sys.argv[1]
HOURS = [float(h) for h in (sys.argv[sys.argv.index('--hours') + 1] if '--hours' in sys.argv else '9.5,15').split(',')]
OUT = os.path.join(os.path.dirname(HERE), 'results', 'region_tour', TAG); os.makedirs(OUT, exist_ok=True)
PLACES = [  # (label, coc target candidates, biome)
    ('whiterun_plains', ['WhiterunExterior04'], 'tundra'),
    ('riverwood_pine', ['Riverwood', 'RiverwoodExterior'], 'pine forest'),
    ('rift_ivarstead', ['Ivarstead', 'IvarsteadExterior'], 'rift edge'),
    ('rift_shorsstone', ['ShorsStone', 'ShorsStoneExterior'], 'rift'),
    ('rift_riften', ['RiftenOrigin'], 'rift'),
    ('rift_outside_riften_west', ['cow Tamriel 40 -24'], 'rift fields outside Riften'),
    ('rift_outside_riften_south', ['cow Tamriel 42 -26'], 'rift fields outside Riften'),
    ('reach_karthwasten', ['Karthwasten', 'KarthwastenExterior'], 'reach'),
    ('reach_markarth', ['MarkarthOrigin', 'Markarth'], 'reach'),
    ('marsh_morthal', ['Morthal', 'MorthalExterior'], 'marsh'),
    ('volcanic_kynesgrove', ['Kynesgrove', 'KynesgroveExterior'], 'volcanic tundra'),
    ('falkreath_forest', ['Falkreath', 'FalkreathExterior'], 'pine forest'),
]
bench.launch(); bench.console('tgm'); bench.all_on()
log = []
for label, cands, biome in PLACES:
    ok = None
    for c in cands:
        try:
            if c.startswith('cow '):
                bench.console(c); time.sleep(6)
                if not bench.settle(): raise RuntimeError('could not reach ' + c)
                time.sleep(4)
            else:
                bench.goto(c)
            ok = c; break
        except Exception as e:
            print(label, c, 'failed', str(e)[:80], flush=True)
    if not ok: log.append((label, 'skipped')); continue
    cs.world(action='weather', name='SunnyTU', instant=True, lock=True); cs.world(action='timescale', value=1)
    p = bench.state_()['position']; shots = []
    for h in HOURS:
        cs.world(action='hour', value=h); time.sleep(10)
        for yaw in (0, 90, 180, 270):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 200, 'pitch': -6.0, 'yaw': float(yaw), 'fov': 80.0})
            time.sleep(4)
            src = cs.shot('tour-%s-%s-%g-%d' % (TAG, label, h, yaw)); time.sleep(1)
            if src and os.path.exists(src):
                dst = os.path.join(OUT, '%s__h%g__%03d.png' % (label, h, yaw)); shutil.move(src, dst); shots.append(dst)
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
    if shots:
        ims = [Image.open(s).convert('RGB').resize((860, 360)) for s in shots]
        sheet = Image.new('RGB', (860 * 4, 360 * ((len(ims) + 3) // 4)))
        for i, im in enumerate(ims): sheet.paste(im, ((i % 4) * 860, (i // 4) * 360))
        sheet.save(os.path.join(OUT, label + '__sheet.jpg'), quality=85)
    log.append((label, ok, biome, round(p['x']), round(p['y']), len(shots))); print(label, ok, biome, len(shots), 'shots', flush=True)
print('done', log, flush=True)
try: cs.world(action='weather', name='SunnyTU', instant=False, lock=False)
except Exception: pass
try: bench.console('tgm')                                        # god mode off again: a kept-open game may be played next
except Exception: pass
if os.environ.get('NGVO_KEEP_OPEN') != '1': bench.quit_game()

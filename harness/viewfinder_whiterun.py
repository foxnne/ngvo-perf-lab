"""Whiterun seen from afar (camera aimed at the city). Derived from viewfinder_vantage.py.
Candidate vantage points for sky tuning: high mountain views and sea horizons. Free camera above where the player lands,
8 headings each. output: results/viewfinder_whiterun/<place>/ and a contact sheet per place."""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image, ImageDraw
OUT = os.path.join(os.path.dirname(HERE), 'results', 'viewfinder_whiterun'); os.makedirs(OUT, exist_ok=True)
PLACES = [  # name, console travel command, camera height above the player
    ('from_north', 'cow Tamriel 4 5', 2500.0),
    ('from_northeast', 'cow Tamriel 9 3', 2500.0),
    ('from_east', 'cow Tamriel 10 -2', 2500.0),
    ('from_southeast', 'cow Tamriel 8 -6', 2500.0),
    ('from_west_plains', 'cow Tamriel -2 -3', 2500.0),
]
TARGET = (17500.0, -3500.0)   # roughly Dragonsreach (stables spawn is 19157, -7419; the city rises north-west of it)
import math
bench.launch(); bench.console('tgm')
bench.goto('WhiterunExterior04'); time.sleep(5)   # enter an exterior by coc first: cow straight from the interior save leaves Physical Sky rendering a black sky
for name, travel, up in PLACES:
    try:
        bench.console(travel); time.sleep(15)
        s = {}; last = None; t0 = time.time()
        while time.time() - t0 < 180:                    # a far cell takes a while to load, and the bridge is silent meanwhile
            s = bench.state_(); cur = s.get('position')
            if cur and last and abs(cur['x'] - last['x']) < 1 and abs(cur['y'] - last['y']) < 1: break
            last = cur; time.sleep(5)
        if not s.get('position'): raise RuntimeError('did not arrive')
        if not bench.running(): raise RuntimeError('game closed')
        bench.exterior_setup(); time.sleep(10)
        s = bench.state_(); p = s['position']; print(name, 'player at', p, str(s.get('cell'))[:60], flush=True)
        d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True); tiles = []
        aim = math.degrees(math.atan2(TARGET[0] - p['x'], TARGET[1] - p['y'])) % 360
        for yaw in (aim - 25, aim, aim + 25, aim + 180):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + up, 'pitch': -2.0, 'yaw': float(yaw), 'fov': 65.0}); time.sleep(4)
            src = cs.shot(f'wr-{name}-{int(yaw) % 360}'); time.sleep(1)
            dst = os.path.join(d, f'{name}_yaw{int(yaw) % 360:03d}' + os.path.splitext(src)[1]); shutil.copy2(src, dst); tiles.append((dst, f'{name}  heading {int(yaw) % 360} (0 N, 90 E, 180 S, 270 W)'))
        cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        w, h = 860, 360; sheet = Image.new('RGB', (w * 4, (h + 26) * 1), (20, 20, 20)); dr = ImageDraw.Draw(sheet)
        for i, (path, label) in enumerate(tiles):
            sheet.paste(Image.open(path).convert('RGB').resize((w, h)), ((i % 4) * w, (i // 4) * (h + 26) + 26)); dr.text(((i % 4) * w + 8, (i // 4) * (h + 26) + 6), label, fill=(240, 240, 240))
        sheet.save(os.path.join(OUT, f'sheet_{name}.jpg'), quality=90); print('sheet', name, flush=True)
    except Exception as e:
        print(name, 'FAILED', str(e)[:150], flush=True)
        try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
        except Exception: pass
bench.quit_game()

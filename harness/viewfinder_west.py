"""Lake Ilinalta looking west at the distant mountains: free camera raised above the Guardian Stones shore,
a fan of headings around west at three heights. usage: python viewfinder_west.py   output: results/viewfinder_west/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image, ImageDraw
OUT = os.path.join(os.path.dirname(HERE), 'results', 'viewfinder_west'); os.makedirs(OUT, exist_ok=True)
X, Y, Z = 662.0, -59220.0, 612.0
bench.launch(); bench.console('tgm')
bench.goto('GuardianStones'); bench.exterior_setup()
cs.world(action='teleport', x=X, y=Y, z=Z, rx=0.0, rz=270.0); time.sleep(14)
p = bench.state_()['position']; print('player at', p, flush=True)
tiles = []
try:
    for up in (150.0, 500.0, 1100.0):
        for yaw in (235.0, 252.0, 270.0, 288.0):
            cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + up, 'pitch': -3.0, 'yaw': yaw, 'fov': 65.0}); time.sleep(4)
            src = cs.shot(f'west-{int(up)}-{int(yaw)}'); time.sleep(1)
            dst = os.path.join(OUT, f'ilinalta_up{int(up):04d}_yaw{int(yaw)}' + os.path.splitext(src)[1]); shutil.copy2(src, dst)
            tiles.append((dst, f'height +{int(up)}  heading {int(yaw)} (270 = west)'))
finally:
    try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
w, h = 860, 360; sheet = Image.new('RGB', (w * 4, (h + 26) * 3), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, (path, label) in enumerate(tiles):
    sheet.paste(Image.open(path).convert('RGB').resize((w, h)), ((i % 4) * w, (i // 4) * (h + 26) + 26)); d.text(((i % 4) * w + 8, (i // 4) * (h + 26) + 6), label, fill=(240, 240, 240))
sheet.save(os.path.join(OUT, 'sheet_ilinalta_west.jpg'), quality=90); print('sheet', len(tiles), flush=True)
bench.quit_game()

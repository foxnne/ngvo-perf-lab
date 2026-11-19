"""Candidate framings for the two tuning views (Whiterun plains, Guardian Stones over Lake Ilinalta): a screenshot every
45 degrees at two pitches, plus a contact sheet per place, so the user can pick views that show clouds and tree LOD.
usage: python viewfinder.py [--no-launch] [--keep-open]   output: results/viewfinder/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import Image, ImageDraw
OUT = os.path.join(os.path.dirname(HERE), 'results', 'viewfinder'); os.makedirs(OUT, exist_ok=True)
PLACES = {'plains': ('WhiterunExterior04', (bench.START[0], bench.START[1], bench.START[2])), 'ilinalta': ('GuardianStones', (662.0, -59220.0, 612.0))}
if '--no-launch' not in sys.argv: bench.launch()
bench.console('tgm')
for place, (cell, (x, y, z)) in PLACES.items():
    bench.goto(cell); bench.exterior_setup()
    cs.world(action='teleport', x=x, y=y, z=z, rx=0.0, rz=0.0); time.sleep(12)
    tiles = []
    for pitch in (-12.0, -3.0):                      # negative looks up: more sky in frame
        for heading in range(0, 360, 45):
            cs.world(action='teleport', x=x, y=y, z=z, rx=pitch, rz=float(heading)); time.sleep(3.5)
            try:
                src = cs.shot(f'view-{place}-{heading}-{int(pitch)}'); time.sleep(1.0)
                dst = os.path.join(OUT, f'{place}_h{heading:03d}_p{int(pitch)}' + os.path.splitext(src)[1]); shutil.copy2(src, dst)
                tiles.append((dst, f'{place}  heading {heading}  pitch {int(pitch)}'))
            except Exception as e: print('shot failed', place, heading, pitch, str(e)[:80], flush=True)
    if tiles:
        w, h = 860, 360; sheet = Image.new('RGB', (w * 4, (h + 26) * ((len(tiles) + 3) // 4)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
        for i, (path, label) in enumerate(tiles):
            try: im = Image.open(path).convert('RGB').resize((w, h))
            except Exception: continue
            sheet.paste(im, ((i % 4) * w, (i // 4) * (h + 26) + 26)); d.text(((i % 4) * w + 8, (i // 4) * (h + 26) + 6), label, fill=(240, 240, 240))
        sheet.save(os.path.join(OUT, f'sheet_{place}.jpg'), quality=90); print('sheet', place, len(tiles), flush=True)
# Face close-ups for Neural Rendering: the player turned to four headings (different sun angles), tight and bust framings
bench.goto('WhiterunExterior04'); bench.exterior_setup(); tiles = []
for heading in (160, 250, 340, 70):
    cs.world(action='teleport', x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=0.0, rz=float(heading)); time.sleep(6)
    for name, kw in (('tight', dict(distance=60.0, height=112.0, pitch=-2.0, fov=35.0)), ('bust', dict(distance=95.0, height=105.0, pitch=-2.0, fov=40.0))):
        try:
            bench.face_camera(True, **kw); time.sleep(3.5)
            src = cs.shot(f'view-face-{heading}-{name}'); time.sleep(1.0)
            dst = os.path.join(OUT, f'face_h{heading:03d}_{name}' + os.path.splitext(src)[1]); shutil.copy2(src, dst); tiles.append(dst)
        except Exception as e: print('face shot failed', heading, name, str(e)[:80], flush=True)
        finally:
            try: bench.face_camera(False)
            except Exception: pass
print('face shots', len(tiles), flush=True)
try: cs.world(action='weather', name='SunnyTU', instant=False, lock=False)
except Exception: pass
if '--no-launch' not in sys.argv and '--keep-open' not in sys.argv: bench.quit_game()

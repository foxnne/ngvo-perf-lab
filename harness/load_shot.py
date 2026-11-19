"""Desktop grabs of loading screens (the in-game capture returns nothing while loading) and a 3D map shot. output: results/load_shot/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
from PIL import ImageGrab
OUT = os.path.join(os.path.dirname(HERE), 'results', 'load_shot'); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.console('tgm'); bench.all_on()
n = 0
for dest in ('RiftenOrigin', 'WhiterunExterior04', 'SolitudeOrigin', 'WhiterunExterior04'):
    bench.console('coc ' + dest); t0 = time.time(); seen = False
    while time.time() - t0 < 40:
        time.sleep(0.5)
        try: m = bench.menus().get('openMenus', [])
        except Exception: m = []
        if 'Loading Menu' in m:
            seen = True; ImageGrab.grab(all_screens=False).save(os.path.join(OUT, f'load_{n:02d}_{dest}.png')); n += 1; print('grab', n, dest, round(time.time() - t0, 1), flush=True)
        elif seen: break
    time.sleep(12)
bench.exterior_setup(); time.sleep(6)
bench.tap('m'); time.sleep(10)
src = cs.shot('map3d'); time.sleep(1); shutil.copy2(src, os.path.join(OUT, 'map3d.png'))
ImageGrab.grab().save(os.path.join(OUT, 'map3d_desktop.png'))
bench.tap('tab'); time.sleep(3)
try:
    import subprocess
    print(subprocess.run(['powershell', '-NoProfile', '-Command', "(Get-Process SkyrimSE | % { '{0:N1} GB working set, {1:N1} GB private' -f ($_.WorkingSet64/1GB), ($_.PrivateMemorySize64/1GB) })"], capture_output=True, text=True).stdout.strip(), flush=True)
except Exception as e: print(e)
bench.quit_game()

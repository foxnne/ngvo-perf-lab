"""3D world map shot and a loading screen capture. usage: python map_shot.py   output: results/map_shot/"""
import os, shutil, sys, time, threading
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
OUT = os.path.join(os.path.dirname(HERE), 'results', 'map_shot'); os.makedirs(OUT, exist_ok=True)
def keep(tag):
    try:
        src = cs.shot(tag); time.sleep(1.0)
        if src and os.path.exists(src): shutil.copy2(src, os.path.join(OUT, tag + os.path.splitext(src)[1])); print('shot', tag, flush=True)
    except Exception as e: print('shot failed', tag, str(e)[:100], flush=True)
bench.launch(); bench.console('tgm'); bench.all_on()
bench.goto('WhiterunExterior04'); bench.exterior_setup(); time.sleep(8)
print('menus before', bench.menus(), flush=True)
bench.tap('m'); time.sleep(8); print('menus after m', bench.menus(), flush=True)
keep('map_1_open'); time.sleep(6); keep('map_2_settled')
bench.tap('m'); time.sleep(1); bench.tap('tab'); time.sleep(4); print('menus after close', bench.menus(), flush=True)
# loading screen: start a far travel and capture while the loading menu is up
bench.console('coc RiftenOrigin')
for i in range(8):
    time.sleep(1.2)
    try: m = bench.menus()
    except Exception as e: m = str(e)[:60]
    print('load', i, m, flush=True)
    if 'Loading Menu' in str(m): keep(f'loading_{i}')
time.sleep(20); bench.quit_game()

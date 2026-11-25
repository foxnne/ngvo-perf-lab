"""Riverwood draw-call test of SPS options that are off under Bottled: one restart per variant, night and day, with a flicker check."""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('NGVO_MENU_WAIT', '2400')
import numpy as np
from PIL import Image
import bench, cs, shots
INI = r'C:\Modlists\NGVO 8.0 Beta\overwrite\SKSE\Plugins\SPS_User.ini'; BASE = open(INI, encoding='utf-8-sig').read().rstrip() + '\n'
OUT = os.path.join(shots.ROOT, 'results', 'perf40', 'sps_opts_locked'); os.makedirs(OUT, exist_ok=True); ROWS = os.path.join(OUT, 'rows.jsonl')
VAR = [('A baseline', ''),
       ('B static-light shadow cache', '[LightShadowCache]\nbAllowWithBottledShaders = true\n'),
       ('C far shadow cache', '[FarShadowCache]\nbEnabled = true\nbAllowWithBottledShaders = true\n'),
       ('D shadow instancing', '[ShadowInstancing]\nbEnabled = true\n'),
       ('E main view micro culling', '[MainViewCulling]\nbEnabled = true\n'),
       ('F B+C+D together', '[LightShadowCache]\nbAllowWithBottledShaders = true\n[FarShadowCache]\nbEnabled = true\nbAllowWithBottledShaders = true\n[ShadowInstancing]\nbEnabled = true\n')]
only = sys.argv[1:] 
def measure(tag, label):
    time.sleep(50); v = []
    for _ in range(3): pr = cs.call('communityshaders.inspect', {'kind': 'profiler'})['frame']; v.append(pr['avgMs']); time.sleep(8)
    d = cs.call('communityshaders.inspect', {'kind': 'drawcalls'})['shaders']; fr = []
    for i in range(5): f = shots.grab('so'); fr.append(np.asarray(Image.open(f).convert('L').resize((860, 360))).astype(float)); (shutil.move(f, os.path.join(OUT, '%s_%s.png' % (label[0], tag))) if i == 0 else os.remove(f)); time.sleep(0.4)
    flick = max(float(np.abs(fr[i + 1] - fr[i]).mean()) for i in range(4)); hot = max(float((np.abs(fr[i + 1] - fr[i]) > 12).mean()) for i in range(4)) * 100
    r = dict(variant=label, when=tag, ms=round(sum(v) / 3, 1), total=round(d['Total']['drawCalls']), total_cpu=round(d['Total']['cpuMs'], 1), utility=round(d['Utility']['drawCalls']), lighting=round(d['Lighting']['drawCalls']), water=round(d['Water']['drawCalls']), water_cpu=round(d['Water']['cpuMs'], 1), flicker=round(flick, 2), changed_pct=round(hot, 2))
    open(ROWS, 'a').write(json.dumps(r) + '\n'); print(json.dumps(r), flush=True)
try:
    for label, extra in VAR:
        if only and label[0] not in only: continue
        if bench.running(): bench.quit_game(); time.sleep(10)
        open(INI, 'w', encoding='utf-8').write(BASE + extra)
        bench.launch()
        for i in range(40):
            m = bench.menus()
            if m.get('messageBoxOpen') and 'Main Menu' not in m.get('openMenus', []):
                bench.tap('right'); time.sleep(.6); bench.tap('enter'); time.sleep(3); continue
            s = bench.state_()
            if s.get('cell') and 'Loading Menu' not in m.get('openMenus', []) and i > 4: break
            time.sleep(3)
        if not bench.running(): print('launch failed', label, flush=True); continue
        bench.console('coc Riverwood'); time.sleep(10); shots.ready(25, 150)
        cs.world(action='hour', value=4.0); cs.world(action='weather', name='CloudyPF', instant=True, lock=True); cs.world(action='timescale', value=0)
        cs.world(action='teleport', x=17256.0, y=-47220.9, z=-144.5, rz=58.7); time.sleep(3)
        # the idle cinematic camera wanders, so lock the view: the camera pose the user had here
        shots.tb(action='camera', mode='override', x=17149.7, y=-47373.2, z=-23.5, pitch=0, yaw=58.7, fov=85); measure('night', label)
        cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); time.sleep(40); measure('day', label)
finally:
    open(INI, 'w', encoding='utf-8').write(BASE); print('ini restored to base; game left running on the last variant', flush=True)

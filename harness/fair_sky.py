"""Fair-weather coverage study: apply a cloud-map variant live (not saved), shoot two sky views, measure cloud cover.
usage: python fair_sky.py TAG name=primaryLow,primaryHighOut[,modelingHighOut] ...   (name 'saved' = as saved)"""
import copy, json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots, saved_fix
import numpy as np
from PIL import Image
TAG = sys.argv[1]; VAR = [a.split('=') for a in sys.argv[2:]]; V = json.load(open(shots.VPATH)); tb = shots.tb
OUT = os.path.join(shots.ROOT, 'results', 'fair_sky', TAG); os.makedirs(OUT, exist_ok=True)
def get(): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'PhysicalSky'}); return g.get('settings', g)
base = get(); rows = []
cs.world(action='hour', value=13.0); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
try:
    for name, spec in VAR:
        st = copy.deepcopy(base)
        if name != 'saved':
            f = [float(x) for x in spec.split(',')]; P = st['cloudMap']['procedural']['parameters']
            P['primary']['range'][0] = f[0]
            if len(f) > 1: P['primary']['range'][3] = f[1]
            if len(f) > 2: P['modeling']['range'][3] = f[2]
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': st}); time.sleep(6)
        for view in ('sky_top_down', 'sky_from_ground_south', 'sky_cloud_level_north'):
            c = V[view]['camera']; tb(action='camera', mode='override', **{k: c[k] for k in ('x', 'y', 'z', 'pitch', 'yaw', 'fov')}); shots.ready(9, 60)
            f = shots.grab('fs'); d = os.path.join(OUT, '%s_%s.png' % (name, view)); shutil.move(f, d)
            if view == 'sky_top_down':
                a = np.asarray(Image.open(d).convert('RGB').resize((430, 180))).astype(float) / 255
                cover = float(((a.min(axis=2) > 0.62) & (a.max(axis=2) - a.min(axis=2) < 0.22)).mean())
        rows.append((name, spec, cover)); print('%-10s %-18s cloud cover from above %.0f%%' % (name, spec, cover * 100), flush=True)
finally:
    cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'PhysicalSky', 'settings': base})
    tb(action='camera', mode='player'); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)

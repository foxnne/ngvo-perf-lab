"""Depth of field check: what does it soften? Two third-person-style locked views (focus on the character / focus past her),
DoF off as the reference, then variants. Sharpness = fine local contrast per region, as % of the DoF-off frame."""
import copy, json, math, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
import numpy as np
from PIL import Image
TAG = sys.argv[1]; OUT = os.path.join(shots.ROOT, 'results', 'dof', TAG); os.makedirs(OUT, exist_ok=True); tb = shots.tb
def get(n): g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': n}); return g.get('settings') or g
def put(n, s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': n, 'settings': s})
PP = get('PostProcessing'); BASE = PP['Depth of Field']['settings']
def dof(on=True, **kw):
    p = copy.deepcopy(PP); p['Depth of Field']['enabled'] = on; p['Depth of Field']['settings'].update(kw); put('PostProcessing', p)
VAR = [('off', 'DOF OFF', None), ('now', 'AS SAVED (f/8, comp 3.94)', {}), ('comp1', 'COMPENSATION 1.0', dict(NearFarDistanceCompensation=1.0)),
       ('f11', 'f/11, COMP 1.0', dict(FNumber=11.0, NearFarDistanceCompensation=1.0)), ('f16', 'f/16, COMP 1.0', dict(FNumber=16.0, NearFarDistanceCompensation=1.0)),
       ('cap', 'f/8, COMP 1.0, FAR BLUR CAP 0.4', dict(NearFarDistanceCompensation=1.0, FarPlaneMaxBlur=0.4)), ('q7', 'f/8, COMP 1.0, QUALITY 7', dict(NearFarDistanceCompensation=1.0, BlurQuality=7.0))]
def fine(l):
    return np.abs(l - (np.roll(l, 1, 0) + np.roll(l, -1, 0) + np.roll(l, 1, 1) + np.roll(l, -1, 1)) / 4)
tb(action='camera', mode='player'); bench.console('coc WhiterunExterior01'); time.sleep(10); shots.ready(25, 150)
cs.world(action='hour', value=13.0); cs.world(action='weather', name='SClearSkyPF', instant=True, lock=True); cs.world(action='timescale', value=0)
X, Y, Z, RZ = 18322.2, -10992.1, -4624.35, 110.0; cs.world(action='teleport', x=X, y=Y, z=Z, rz=RZ); time.sleep(40)
a = math.radians(RZ); fx, fy = math.sin(a), math.cos(a); rx, ry = math.cos(a), -math.sin(a)
VIEWS = {'char_centre': dict(x=X - fx * 230, y=Y - fy * 230, z=Z + 105, pitch=0, yaw=RZ, fov=85),                 # character in the middle: focus lands on her
         'char_side': dict(x=X - fx * 260 + rx * 70, y=Y - fy * 260 + ry * 70, z=Z + 125, pitch=2, yaw=RZ, fov=85)}  # over the shoulder: centre looks past her
rows = []; ref = {}
try:
    for vname, cam in VIEWS.items():
        tb(action='camera', mode='override', **cam); time.sleep(6)
        for key, label, kw in VAR:
            if kw is None: dof(False)
            else: dof(True, **kw)
            time.sleep(7); f = shots.grab('df'); d = os.path.join(OUT, '%s_%s.png' % (vname, key)); shutil.move(f, d)
            im = Image.open(d).convert('RGB'); l = np.asarray(im.convert('L')).astype(float); H, W = l.shape; e = fine(l)
            reg = {'character': e[int(H * .30):int(H * .95), int(W * .40):int(W * .60)].mean(), 'near ground': e[int(H * .75):, :].mean(), 'mid distance': e[int(H * .40):int(H * .62), :int(W * .35)].mean(), 'far': e[int(H * .15):int(H * .40), int(W * .62):].mean()}
            if key == 'off': ref[vname] = reg
            rows.append((vname, label, {k: round(100 * reg[k] / ref[vname][k]) for k in reg}))
            print('%-12s %-32s sharpness kept: %s' % (vname, label, '  '.join('%s %3d%%' % (k, 100 * reg[k] / ref[vname][k]) for k in reg)), flush=True)
finally:
    put('PostProcessing', PP); tb(action='camera', mode='player'); cs.world(action='timescale', value=20); cs.world(action='weather', name='SunnyPF', instant=False, lock=False)
json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w'))

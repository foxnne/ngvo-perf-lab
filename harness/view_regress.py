"""Realism regression: re-shoot saved views (views.json entries that have a 'sample') at clear noon and put each beside its
sample, with brightness and colour of the land for both. usage: python view_regress.py TAG view [view ...]
Views that share a travel command are shot together, so order them by region to keep cell jumps down."""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
import numpy as np
from PIL import Image, ImageDraw, ImageFont
TAG = sys.argv[1]; names = sys.argv[2:]; V = json.load(open(os.path.join(HERE, 'views.json')))
ROOT = os.path.dirname(HERE); OUT = os.path.join(ROOT, 'results', 'view_regress', TAG); os.makedirs(OUT, exist_ok=True)
if bench.menus().get('messageBoxOpen'): sys.exit('a message box is open in game')


def stats(path):
    a = np.asarray(Image.open(path).convert('RGB').resize((430, 180))).astype(float) / 255; land = a[80:]
    return land.mean(), land.mean(axis=(0, 1)), a[:50].mean()


where = None; P = None
try:
    for name in names:
        v = V[name]; c = v['camera']
        if v['travel'] != where:
            cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
            bench.console(v['travel']); time.sleep(45)
            for _ in range(10):
                a = bench.state_(); time.sleep(4); b = bench.state_()
                if not b['cell']['interior'] and a['position'] == b['position']: break
            P = bench.state_()['position']; where = v['travel']
        cs.world(action='hour', value=12.0); cs.world(action='weather', name='SunnyPF', instant=True, lock=True)
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': P['x'], 'y': P['y'], 'z': P['z'] + c['dz'], 'pitch': c['pitch'], 'yaw': c['yaw'], 'fov': c['fov']})
        time.sleep(22); cs.world(action='hour', value=12.0); time.sleep(4)
        f = cs.shot('vr') or cs.shot('vr2'); now = os.path.join(OUT, name + '.png'); shutil.move(f, now)
        old = os.path.join(ROOT, v['sample']); (m0, c0, s0), (m1, c1, s1) = stats(old), stats(now)
        print('%-28s land %.3f -> %.3f  rgb %s -> %s  sky %.3f -> %.3f' % (name, m0, m1, np.round(c0, 2), np.round(c1, 2), s0, s1), flush=True)
        A, B = Image.open(old).convert('RGB'), Image.open(now).convert('RGB'); W, H = A.size; fs = int(H * 0.045); font = ImageFont.truetype('arialbd.ttf', fs)
        sh = Image.new('RGB', (W, H * 2 + 8))
        for k, (im, t) in enumerate(((A, 'BEFORE (2026-11-22)'), (B, 'NOW'))):
            im = im.copy(); d = ImageDraw.Draw(im); d.rectangle((0, 0, W, int(fs * 1.7)), fill=(0, 0, 0)); d.text((int(fs * 0.6), int(fs * 0.3)), '%s  -  %s  -  clear 12:00' % (t, name.replace('_', ' ')), fill=(255, 230, 0), font=font)
            sh.paste(im, (0, k * (H + 8)))
        sh.save(os.path.join(OUT, 'compare_' + name + '.png'))
finally:
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'}); cs.world(action='weather', name='SunnyPF', instant=False, lock=False); cs.world(action='hour', value=13.0)

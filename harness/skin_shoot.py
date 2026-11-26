"""Skin presets on Sinna (player, fair) and Auri (Bosmer, dark), same light (user 2026-11-25).
Presets from harness/RESEARCH-skin-sss-2026-11-25.md (P0 = current). Clear 13:00, time frozen, Auri moved next to the player.
Each preset: a two-shot at face height from the sun-side-ish 3/4, NR on. usage: python skin_shoot.py [presets=P0,P1,P2,P3,P4]"""
import copy, math, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(shots.ROOT, 'results', 'skin_presets'); os.makedirs(OUT, exist_ok=True)
AURI = '5C3139C8'
NAMES = sys.argv[1].split(',') if len(sys.argv) > 1 else ['P0', 'P1', 'P2', 'P3', 'P4']
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=rgb24')
COMMON = dict(Translucency=0.1, F0=0.028, EnableSkinDetail=True, SkinDetailTiling=10.0, BodyTilingMultiplier=2.0, WetResponse=1.0, NormalShadowLength=1.5)
SKIN = {
    'P1': dict(SkinMainRoughness=0.70, SkinSpecularTexMultiplier=1.0, SkinSecondRoughness=0.35, SecondarySpecularStrength=0.10, ExtraEdgeRoughness=0.25,
               FuzzStrength=1.0, FuzzRoughness=0.35, FuzzF0=0.045, SkinDetailStrength=0.25, NormalShadowStrength=0.6, NormalShadowHardness=6.0, ContactShadowStrength=0.5, SSSAmount=1.0),
    'P2': dict(SkinMainRoughness=0.68, SkinSpecularTexMultiplier=0.4, SkinSecondRoughness=0.45, SecondarySpecularStrength=0.15, ExtraEdgeRoughness=0.15,
               FuzzStrength=0.5, FuzzRoughness=0.5, FuzzF0=0.035, SkinDetailStrength=0.35, NormalShadowStrength=0.65, NormalShadowHardness=6.0, ContactShadowStrength=0.5, SSSAmount=0.85),
    'P4': dict(SkinMainRoughness=0.66, SkinSpecularTexMultiplier=0.5, SkinSecondRoughness=0.42, SecondarySpecularStrength=0.20, ExtraEdgeRoughness=0.10,
               FuzzStrength=0.35, FuzzRoughness=0.5, FuzzF0=0.03, SkinDetailStrength=0.50, NormalShadowStrength=0.8, NormalShadowHardness=8.0, ContactShadowStrength=0.7, SSSAmount=0.7),
}
SKIN['P3'] = SKIN['P2']
SSS = {
    'P1': dict(SSMode=0, ScatterMode=2, Human=dict(BlurRadius=1.0, Thickness=1.0, Strength=[0.48, 0.41, 0.28], Falloff=[1, 0.37, 0.3])),
    'P2': dict(SSMode=0, ScatterMode=1, Human=dict(BlurRadius=0.45, Thickness=1.0, Strength=[0.48, 0.41, 0.28], Falloff=[1, 0.37, 0.2])),
    'P3': dict(SSMode=1, ScatterMode=1, MFP=[1.0, 0.37, 0.2, 1.4], BurleySamples=24),
    'P4': dict(SSMode=0, ScatterMode=1, Human=dict(BlurRadius=0.3, Thickness=1.5, Strength=[0.45, 0.30, 0.20], Falloff=[1, 0.37, 0.2])),
}
get = lambda f: cs.call('communityshaders.feature', {'action': 'get', 'shortName': f})
put = lambda f, s: cs.call('communityshaders.feature', {'action': 'set', 'shortName': f, 'settings': s})
skin0, sss0 = get('Skin'), get('SubsurfaceScattering')
def apply(name):
    sk, ss = copy.deepcopy(skin0), copy.deepcopy(sss0)
    if name != 'P0':
        sk['EnableSkin'] = True; sk['DefaultProfile'].update(COMMON); sk['DefaultProfile'].update(SKIN[name])
        p = SSS[name]; ss['SSMode'] = p['SSMode']; ss['ScatterMode'] = p['ScatterMode']; ss['EnableCharacterLighting'] = 0
        if 'Human' in p: ss['HumanProfile'].update(p['Human'])
        if 'MFP' in p: ss['MeanFreePathHuman'] = p['MFP']; ss['BurleySamples'] = p['BurleySamples']
    put('Skin', sk); put('SubsurfaceScattering', ss)
def grab(path):
    subprocess.run([r'C:\Users\foxnn\dev\ffmpeg.exe', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=5:output_fmt=16bit', '-vf', VF, '-frames:v', '1', path])
    return path
bench.console('coc WhiterunExterior01'); time.sleep(10); bench.settle(maxwait=120)
bench.console('player.setpos x 17378'); bench.console('player.setpos y -11253'); time.sleep(3)
print(cs.world(action='weather', name=os.environ.get('SHOOT_WEATHER', 'SunnyPF'))); cs.world(action='timescale', value=20); cs.world(action='hour', value=13.0); time.sleep(40)
cs.world(action='timescale', value=0)
v = cs.call('communityshaders.testbed', {'action': 'view_get'}); hd = v['head']; yaw = hd['yaw']
side = (math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)))          # to the player's right
ax, ay = hd['x'] + side[0] * 80, hd['y'] + side[1] * 80
bench.console('prid ' + AURI); bench.console('moveto player'); time.sleep(2)
bench.console('setpos x %.1f' % ax); bench.console('setpos y %.1f' % ay); bench.console('setangle z %.1f' % yaw); time.sleep(3)
bench.console('tai'); time.sleep(2)
bench.console('tm')
def face_cam(x, y, z, dist=55, off=20):
    a = math.radians(yaw + off)
    cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'free', 'x': x + math.sin(a) * dist, 'y': y + math.cos(a) * dist, 'z': z + 2,
                                         'yaw': (yaw + off + 180) % 360, 'pitch': 0.0, 'fov': 28})
shots_ = []
mid = ((hd['x'] + ax) / 2, (hd['y'] + ay) / 2)
order = NAMES + NAMES
try:
    for i, name in enumerate(order):
        apply(name); time.sleep(5)
        a = math.radians(yaw + 10)
        cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'free', 'x': mid[0] + math.sin(a) * 120, 'y': mid[1] + math.cos(a) * 120, 'z': hd['z'] - 4,
                                             'yaw': (yaw + 10 + 180) % 360, 'pitch': 0.0, 'fov': 32})
        time.sleep(3); shots_.append(('%s%s' % (name, '' if i < len(NAMES) else ' (again)'), [grab(os.path.join(OUT, '%s_two_%d.png' % (name, i)))])); print(name, i, flush=True)
finally:
    put('Skin', skin0); put('SubsurfaceScattering', sss0)
    bench.console('tai'); bench.console('tm'); cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 40)
ims = [Image.open(r[0]).crop((620, 100, 2820, 1100)) for _, r in shots_]
w, h = ims[0].size; cols = len(NAMES); out = Image.new('RGB', (w * cols, h * 2))
for i, (im, (name, _)) in enumerate(zip(ims, shots_)):
    x, y = (i % cols) * w, (i // cols) * h; out.paste(im, (x, y)); ImageDraw.Draw(out).text((x + 14, y + 10), name, fill='red', font=font)
out.save(os.path.join(OUT, 'grid_two_repeat.png')); print(os.path.join(OUT, 'grid_two_repeat.png'))

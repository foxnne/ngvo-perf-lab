"""helper: build markdown tables of lighting/atmosphere settings (global + representative weathers + ranges). usage: python -I tables.py > tables_generated.md"""
import os, re, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inidiff import parse, ROOT, G, num
TODS = ['Sunrise', 'Day', 'Sunset', 'Night', 'InteriorDay', 'InteriorNight']
ALLT = ['Dawn', 'Sunrise', 'Day', 'Sunset', 'Dusk', 'Night', 'InteriorDay', 'InteriorNight']
wl = parse(os.path.join(ROOT, 'enbseries', '_weatherlist.ini'))
FILES = []
for (s, k), v in wl.items():
    if k == 'FileName' and v and v not in FILES: FILES.append(v)
W = {f: parse(os.path.join(ROOT, 'enbseries', f)) for f in FILES}
REP = [('global', G), ('ClearTundra', W['!_ClearWeather__tundra.ini']), ('ClearPine', W['!_ClearWeather__pineforest.ini']), ('Overcast', W['!_Overcast.ini']),
       ('Foggy', W['!_FoggyWeather.ini']), ('RainStormHeavy', W['!_RainStorm_heavy.ini']), ('Dungeons', W['!_Dungeons.ini'])]
KEYS = [
 ('ENVIRONMENT', ['DirectLightingIntensity', 'DirectLightingCurve', 'DirectLightingDesaturation', 'DirectLightingColorFilterAmount', 'DirectLightingColorFilter',
                  'AmbientLightingIntensity', 'AmbientLightingCurve', 'AmbientLightingDesaturation', 'AmbientColorFilterAmount', 'AmbientColorFilterTop', 'AmbientColorFilterMiddle', 'AmbientColorFilterBottom',
                  'SpecularAmountMultiplier', 'SpecularPowerMultiplier', 'SpecularFromLight', 'PointLightingIntensity', 'PointLightingCurve', 'PointLightingDesaturation', 'ParticleLightsIntensity',
                  'FogColorMultiplier', 'FogColorCurve', 'FogColorFilterAmount', 'FogColorFilter', 'ColorPow']),
 ('SKY', ['GradientIntensity', 'GradientDesaturation', 'GradientTopIntensity', 'GradientTopCurve', 'GradientTopColorFilter', 'GradientMiddleIntensity', 'GradientMiddleCurve', 'GradientMiddleColorFilter',
          'GradientHorizonIntensity', 'GradientHorizonCurve', 'GradientHorizonColorFilter', 'SunIntensity', 'SunDesaturation', 'SunColorFilter', 'SunGlowIntensity', 'SunGlowHaziness',
          'CloudsIntensity', 'CloudsCurve', 'CloudsDesaturation', 'CloudsOpacity', 'CloudsColorFilter', 'MoonIntensity']),
 ('BLOOM', ['Amount', 'BlueShiftAmount']),
 ('SKYLIGHTING', ['AmbientMinLevel']),
 ('IMAGEBASEDLIGHTING', ['AdditiveAmount', 'MultiplicativeAmount', 'ReflectiveAmount']),
 ('AUTOAMBIENT', ['BlendingAmount', 'TopIntensity', 'BottomIntensity', 'BottomSaturation']),
 ('RAYS', ['SunRaysMultiplier']),
 ('VOLUMETRICRAYS', ['Intensity', 'Density', 'SkyColorAmount']),
 ('VOLUMETRICFOG', ['Intensity', 'Curve', 'LightingInfluence', 'Opacity']),
 ('MIST', ['SkyLightingAmount', 'SunLightingAmount', 'Desaturation', 'ColorFilter', 'VerticalOffset', 'Density', 'VerticalFade', 'BottomTop', 'ExponentialFade', 'DistanceFade']),
 ('PROCEDURALSUN', ['GlowIntensity', 'GlowCurve']),
 ('PARTICLE', ['Intensity', 'LightingInfluence']),
 ('FIRE', ['Intensity', 'Curve']),
 ('LIGHTSPRITE', ['Intensity', 'Curve']),
 ('WINDOWLIGHT', ['Intensity', 'Curve']),
 ('GRASS', ['DirectionalMultiplier', 'AmbientMultiplier']),
 ('CLOUDSHADOWS', ['Opacity']),
]
def f(v):
    if v is None: return '-'
    if ',' in v: return '(' + ','.join('%.2f' % float(x) for x in v.split(',')) + ')'
    try: return ('%.3f' % float(v)).rstrip('0').rstrip('.')
    except: return v
mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
if mode in ('all', 'rep'):
    for name, D in REP:
        print('\n### %s\n' % name)
        print('| section.key | ' + ' | '.join(TODS) + ' |'); print('|---|' + '---|' * len(TODS))
        for sec, ks in KEYS:
            for k in ks:
                print('| %s.%s | ' % (sec, k) + ' | '.join(f(D.get((sec, k + t))) for t in TODS) + ' |')
if mode in ('all', 'range'):
    print('\n### Ranges across the %d referenced weather files (min / median / max), scalar keys\n' % len(FILES))
    print('| section.key | Day | Night | InteriorDay |'); print('|---|---|---|---|')
    for sec, ks in KEYS:
        for k in ks:
            row = []
            for t in ('Day', 'Night', 'InteriorDay'):
                vals = [num(D.get((sec, k + t), 'x')) for D in W.values()]; vals = [v for v in vals if v is not None]
                row.append('%.2f / %.2f / %.2f' % (min(vals), st.median(vals), max(vals)) if vals else '-')
            if any(r != '-' for r in row): print('| %s.%s | ' % (sec, k) + ' | '.join(row) + ' |')
if mode in ('all', 'day'):
    print('\n### Day values of the key mood settings for every referenced weather file\n')
    cols = [('ENVIRONMENT', 'DirectLightingIntensity'), ('ENVIRONMENT', 'DirectLightingCurve'), ('ENVIRONMENT', 'DirectLightingDesaturation'), ('ENVIRONMENT', 'AmbientLightingIntensity'), ('ENVIRONMENT', 'AmbientLightingCurve'),
            ('ENVIRONMENT', 'AmbientLightingDesaturation'), ('ENVIRONMENT', 'AmbientColorFilterAmount'), ('ENVIRONMENT', 'FogColorMultiplier'), ('ENVIRONMENT', 'FogColorCurve'), ('ENVIRONMENT', 'ColorPow'),
            ('SKY', 'GradientIntensity'), ('SKY', 'CloudsIntensity'), ('SKY', 'SunIntensity'), ('BLOOM', 'Amount'), ('SKYLIGHTING', 'AmbientMinLevel'), ('VOLUMETRICRAYS', 'Intensity'), ('MIST', 'Density'), ('MIST', 'SkyLightingAmount')]
    short = ['DirI', 'DirCrv', 'DirDes', 'AmbI', 'AmbCrv', 'AmbDes', 'AmbFlt', 'FogMul', 'FogCrv', 'ColPow', 'SkyGrad', 'Cloud', 'Sun', 'Bloom', 'SkyLMin', 'VolRay', 'MistDen', 'MistSky']
    for t in ('Day', 'Night'):
        print('\n**%s**\n' % t)
        print('| file | ' + ' | '.join(short) + ' |'); print('|---|' + '---|' * len(short))
        for fn, D in W.items():
            print('| %s | ' % fn[2:-4] + ' | '.join(f(D.get((s, k + t))) for s, k in cols) + ' |')
if mode in ('all', 'cmp'):
    for t in ('Day', 'Night', 'Sunset'):
        print('\n### Representative weathers side by side: %s\n' % t)
        R = [r for r in REP if r[0] != 'Dungeons']
        print('| section.key | ' + ' | '.join(n for n, _ in R) + ' |'); print('|---|' + '---|' * len(R))
        for sec, ks in KEYS:
            for k in ks:
                print('| %s.%s | ' % (sec, k) + ' | '.join(f(D.get((sec, k + t))) for _, D in R) + ' |')
    print('\n### Interiors: global vs Dungeons vs Dwarven_Ruins vs Caves_Other vs ClearTundra (InteriorDay / InteriorNight)\n')
    R = [('global', G), ('Dungeons', W['!_Dungeons.ini']), ('Dungeons2', W['!_Dungeons2.ini']), ('Dwarven_Ruins', W['!_Dwarven_Ruins.ini']), ('Caves_Other', W['!_Caves_Other.ini']), ('ClearTundra', W['!_ClearWeather__tundra.ini'])]
    print('| section.key | ' + ' | '.join(n for n, _ in R) + ' |'); print('|---|' + '---|' * len(R))
    for sec, ks in KEYS:
        for k in ks:
            print('| %s.%s | ' % (sec, k) + ' | '.join(f(D.get((sec, k + 'InteriorDay'))) + ' / ' + f(D.get((sec, k + 'InteriorNight'))) for _, D in R) + ' |')

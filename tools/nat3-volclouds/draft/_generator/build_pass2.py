"""Pass 2 generator: per-weather Physical Sky + Exponential Height Fog scene files for the 111 NAT.CS III weathers.

UNTESTED IN GAME. The sky-type numbers are anchored to the in-game calibration points of 2026-11-18 (see
CALIBRATION below), everything between and beyond those points is an educated guess.

    python -I build_pass2.py

Reads (read-only):
    NAT-CS.esp + masters (through wthr_parse.py)   the weather records themselves
    scene-catalog-pass2.json                        compiled scene catalog rows (extract_catalog.py), for validation
Writes (only under ..\\ and ..\\..\\notes):
    ..\\foxnne-nat3-clouds-pass2\\                  pack: manifest, Baseline, Weather/<formkey>/<Period>/<pack>_<Feature>.json
    ..\\alt-user-overrides-pass2\\                  same values as SceneManager.json "weather" entries (route B)
    ..\\pass2-sky-types.json                        per sky type: definition, members, one representative + its settings
    nat-cs-wthr-records.json                        parsed record facts (cache / reference)
    ..\\..\\notes\\weather-table-2.md
The old generator (build_draft.py) and its output are not touched.
"""
import collections
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script directory; wthr_parse.py lives beside this file
import wthr_parse  # noqa: E402

DRAFT = os.path.dirname(HERE)
ROOT = os.path.dirname(DRAFT)
PACK = 'foxnne-nat3-clouds-pass2'
PACK_DIR = os.path.join(DRAFT, PACK)
PERIODS = ['Dawn', 'Sunrise', 'Day', 'Sunset', 'Dusk', 'Night']
DARK_PERIODS = {'Dawn', 'Dusk', 'Night'}
GAME_UNIT_M = 0.0142875

# --------------------------------------------------------------------------------------------
# CALIBRATION (in-game, 2026-11-18). These are the only tested numbers in this file.
CALIBRATION = {
    'savedBase': {
        'cloudLayer.low.ndfAltitudeOffset': 1200.0, 'cloudLayer.low.ndfAltitudeScale': 900.0,
        'cloudLayer.low.ndfScale': [24.66, 16.7], 'cloudLayer.low.densityScale': 0.75,
        'cloudLayer.lighting.brightness/sunExtinction/viewExtinction': 1.0,
        'cloudLayer.wind.lowVelocity': [5.0, 0.0], 'cloudLayer.wind.highVelocity': [10.0, 0.0],
        'aerosolType': 1, 'aerosolLoading': 0.4, 'sunlightColor': [10.0, 9.7, 9.5], 'enableVanillaClouds': False,
        'cloudLayer.cirrus.densityScale': 0.3,
        'cloudMap.procedural.parameters.primary.range': [0.1, 0.65, 0.0, 0.65],
    },
    'coverage': 'primary.range inMin is the working lever: -0.4 = full broken-to-overcast field, 0.1 = saved base, '
                '0.2 with the high layer off = liked "clear day with a few distinct cumulus". coverageGain and outMax did little.',
    'highLayer': 'cirrus densityScale 1.0 = disliked dense popcorn; 0.3-0.4 faint; 0 off.',
    'terrain': 'Whiterun plain ~155 m, Lake Ilinalta ~215 m, peaks ~700-770 m above the map floor; base below ~600 m buries terrain.',
    'haze': 'Continental loading 0.4 = clear day; 0.7 was milky.',
    'heightFog': 'baseline vanillaFogStrength 0.3 is a white-out in foggy weather.',
}
BASE_FOG_STRENGTH = 0.3   # Presets/foxnne-look/Baseline/ExponentialHeightFog.json
PRIMARY_IN_MAX = 0.65     # saved base; not varied
SECONDARY_DEFAULT_IN_MIN = -0.2

# --------------------------------------------------------------------------------------------
# Sky types. lo = lightest member of the type, hi = heaviest; a weather sits between them by its severity (0..1).
#   inMin/outMin/outMax : cloudMap.procedural.parameters.primary.range x / z / w   (y stays 0.65)
#   sec                 : secondary.range x (code default -0.2; raised only where less cloud than the liked fair sky is wanted)
#   base/thick          : cloudLayer.low.ndfAltitudeOffset / ndfAltitudeScale, metres above the map floor
#   dens                : cloudLayer.low.densityScale (0..1)
#   cirrus              : cloudLayer.cirrus.densityScale (the "high layer")
#   haze                : Continental aerosol loading at RH 50 (lo at fog far >= 150000, hi at fog far <= 5000),
#                         written as the aerosolScatter/aerosolAbsorption it resolves to
#   fogHalfM            : height fog: shortest allowed half-opacity distance in metres (None = keep baseline 0.3)
#   sun                 : sunlight multiplier. 1.0 everywhere: the cloud shadow does the dimming, so nothing is emitted.
T = collections.OrderedDict()
T['clear'] = dict(
    label='Clear', why='Fewer clouds than the liked inMin 0.2 sky: inMin pushed to 0.45 and the secondary field raised too; high layer off.',
    inMin=(0.45, 0.45), outMin=(0.0, 0.0), outMax=(0.65, 0.65), sec=(0.30, 0.30),
    base=(1400, 1400), thick=(600, 600), dens=(0.60, 0.60), cirrus=0.0, haze=(0.40, 0.50), fogHalfM=None)
T['fair'] = dict(
    label='Fair-weather cumulus', why='The liked look itself: inMin 0.2 +/- 0.05 by NAT layer alpha, high layer off, base a little above the saved 1200.',
    inMin=(0.25, 0.15), outMin=(0.0, 0.0), outMax=(0.65, 0.65), sec=(-0.2, -0.2),
    base=(1300, 1300), thick=(700, 700), dens=(0.70, 0.70), cirrus=0.0, haze=(0.40, 0.50), fogHalfM=None)
T['partly'] = dict(
    label='Partly cloudy', why='Starts at the saved global base (inMin 0.1, 1200/900, 0.75, faint high layer 0.3) and moves a third of the way toward the -0.4 broken field.',
    inMin=(0.10, -0.15), outMin=(0.0, 0.0), outMax=(0.65, 0.65), sec=(-0.2, -0.2),
    base=(1200, 1100), thick=(900, 1000), dens=(0.75, 0.75), cirrus=0.30, haze=(0.40, 0.55), fogHalfM=None)
T['overcast'] = dict(
    label='Overcast', why='Around and past the tested -0.4 full field, flat (800-1000 m) deck with its base still above the peaks; high layer off because it is hidden.',
    inMin=(-0.35, -0.60), outMin=(0.0, 0.15), outMax=(0.65, 0.70), sec=(-0.3, -0.5),
    base=(1000, 900), thick=(800, 1000), dens=(0.75, 0.85), cirrus=0.0, haze=(0.50, 0.70), fogHalfM=1200)
T['rain'] = dict(
    label='Rain', why='Showers (bright-sun rain records) are a broken field; dark rain is a closed, lower, thicker, denser deck with milky distance.',
    inMin=(-0.30, -0.70), outMin=(0.0, 0.20), outMax=(0.65, 0.72), sec=(-0.3, -0.6),
    base=(950, 800), thick=(1100, 1500), dens=(0.80, 0.95), cirrus=0.0, haze=(0.60, 0.85), fogHalfM=900)
T['storm'] = dict(
    label='Thunderstorm', why='Darkest and deepest: closed field with a coverage floor, base just above the peaks, 1.8-2.4 km deep, full density.',
    inMin=(-0.70, -0.90), outMin=(0.20, 0.30), outMax=(0.72, 0.78), sec=(-0.6, -0.8),
    base=(800, 700), thick=(1800, 2400), dens=(0.95, 1.00), cirrus=0.0, haze=(0.80, 1.00), fogHalfM=500)
T['snow'] = dict(
    label='Snow', why='From thin broken cloud with light snow to a blizzard deck; less dense than rain so the deck stays bright.',
    inMin=(-0.10, -0.70), outMin=(0.0, 0.20), outMax=(0.65, 0.72), sec=(-0.2, -0.6),
    base=(950, 750), thick=(900, 1500), dens=(0.65, 0.85), cirrus=0.0, haze=(0.55, 0.90), fogHalfM=700)
T['fog'] = dict(
    label='Fog', why='Low thin stratus that takes the peaks (base 650-700 m, never below the 600 m limit); the ground fog itself is height fog, strongly reduced.',
    inMin=(-0.30, -0.50), outMin=(0.0, 0.10), outMax=(0.65, 0.65), sec=(-0.3, -0.4),
    base=(700, 650), thick=(500, 600), dens=(0.50, 0.60), cirrus=0.0, haze=(0.80, 1.10), fogHalfM=350)
T['special'] = dict(
    label='Other realm / map', why='Worldspace is not in the Physical Sky whitelist, so the file most likely never applies; clear values so nothing surprising happens if it does.',
    inMin=(0.45, 0.45), outMin=(0.0, 0.0), outMax=(0.65, 0.65), sec=(0.30, 0.30),
    base=(1400, 1400), thick=(600, 600), dens=(0.60, 0.60), cirrus=0.0, haze=(0.40, 0.40), fogHalfM=None)
TYPE_ORDER = list(T)

AURORA_IN_MIN_SHIFT = 0.15       # dark periods of aurora weathers: less low cloud, no high layer
AURORA_TYPES = ('clear', 'fair', 'partly')
FOG_COMPRESS = 0.3               # below the type's fogHalfM, differences between weathers are kept at this power
PREFERRED_REPRESENTATIVE = {'clear': 'SClearSkyPF', 'fair': 'SunnyPF', 'partly': 'CloudyPF', 'overcast': 'OvercastPF',
                            'rain': 'RainPF', 'storm': 'StormPF', 'snow': 'Snow', 'fog': 'FogPF', 'special': 'SovngardeClear'}

SPECIAL_PREFIXES = ('sovngarde', 'soulcairn', 'dlc2apocrypha', 'blackreach', 'worldmap')
RAIN_STORM = ('RainStormParticles',)
RAIN = ('RainParticles',)
SNOW = ('SnowParticlesMed', 'SnowParticlesLite', 'NAT_SnowParticlesLite', 'SnowParticlesStorm')
ASH = ('NAT_AshParticlesSparks', 'DLC02AshParticlesLite')
NOTES = {
    'KarthspireRedoubtFog': 'named Fog, but the record has clear-day fog (3500/150000) and a bright sun: typed by the record',
    'BloatedMansGrottoFog': 'named Fog, record fog far 85000 with dark clouds: typed overcast by the record',
    'FogRain': 'rain particles in fog (far 12000): typed fog, the low stratus deck suits both',
    'FXSkyrimStormBlowingGrass': 'storm particles with fog far 12000: typed storm',
    'FXMagicStormRain': 'spell storm (the only record with frequent thunder, byte 15); bright sun, so a light storm',
    'StormDLC2': 'Solstheim ash storm (ash particles, snow flag, fog far 5000): typed overcast, haze at the top of the range',
    'StormDLC2_ALT': 'Solstheim ash storm (ash particles, snow flag): typed overcast',
    'HelgenAttackWeather': 'quest weather with ash/spark particles: typed overcast',
    'SkyrimOvercastWar': 'civil-war battle weather: overcast by fog far 50000',
    'SunnyDLC2': 'named Sunny, cloudy flag, wind 10: typed fair',
    'SunnyDLC2_ALT': 'named Sunny, cloudy flag, wind 10: typed fair',
    'SunnyFV_A': 'named Sunny but only one cloud layer has alpha by day: typed clear',
    'SClearSkyCOMA': 'four layers with alpha, but wind 5 like the other SClearSky records: typed clear',
    'SkuldafnCloudy': 'light snow particles under a bright sun: snow type at its lightest (thin broken cloud)',
    'SnowClear': 'light snow, a single cloud layer: severity halved',
    'SnowClear_Alt': 'light snow, a single cloud layer: severity halved',
    'DLC1Eclipse': 'scripted eclipse weather: overcast by fog far 85000',
    'SkyrimMQ206weather': 'quest weather: overcast by fog far 85000',
    'DLC1FalmerValley_bf': 'Forgotten Vale blizzard-fog, fog far 4000, no particles: typed fog at its heaviest',
    'DLC1FalmerValley_bfDark': 'Forgotten Vale blizzard-fog, fog far 6000, no particles: typed fog',
    'RainFF': 'rain under a bright sun (0.76): showers, broken cloud',
    'RainCloudy_DLC2': 'rain under a bright sun (0.76): showers, broken cloud',
    'RainCloudy_DLC2_ALT': 'rain under a bright sun (0.76): showers, broken cloud',
    'CloudyDLC1_Auriel': 'pleasant flag but wind 25 like the Cloudy records: typed partly',
    'CloudyFV': 'pleasant flag but wind 25 like the Cloudy records: typed partly',
    'CloudyFV_A': 'pleasant flag but wind 25 like the Cloudy records: typed partly',
}

# --------------------------------------------------------------------------------------------
# Aerosol: Continental row of src/Features/PhysicalSky/AerosolData.inl (OPAC), RH 50 = second humidity level.
# Aerosol::Evaluate multiplies scatter and absorption by the loading; the phase g does not depend on loading.
CONTINENTAL_RH50_SCATTER = (12.61057, 17.0945, 22.87603)
CONTINENTAL_RH50_ABSORPTION = (0.663498, 0.7328, 0.802034)


def aerosol(loading):
    return ([round(c * loading, 4) for c in CONTINENTAL_RH50_SCATTER],
            [round(c * loading, 5) for c in CONTINENTAL_RH50_ABSORPTION])


# --------------------------------------------------------------------------------------------
def clamp01(x):
    return max(0.0, min(1.0, x))


def lerp(pair, t):
    return pair[0] + (pair[1] - pair[0]) * t


def lum(c):
    return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255.0


def facts(w):
    """Flat record facts used by the rules and the table."""
    layers = [l for l in w['layers'] if l['enabled']]
    day = [l['alpha'][1] for l in layers]
    night = [l['alpha'][3] for l in layers]
    lit = [(min(l['alpha'][1], 1.0), lum(l['color'][1])) for l in layers if l['alpha'][1] > 0 and l['color']]
    fog = w.get('fog', {})
    d = w['data']
    return {
        'layers': len(layers),
        'layersAlphaDay': sum(1 for a in day if a > 0),
        'alphaMeanDay': sum(day) / len(day) if day else 0.0,
        'alphaSumDay': sum(min(a, 1.0) for a in day),
        'alphaMeanNight': sum(night) / len(night) if night else 0.0,
        'cloudLumDay': sum(a * c for a, c in lit) / sum(a for a, _ in lit) if lit else 0.0,
        'sunLumDay': lum(w['colors']['sunlight'][1]),
        'ambLumDay': lum(w['colors']['ambient'][1]),
        'fogNearDay': fog.get('dayNear', 0.0), 'fogFarDay': fog.get('dayFar', 150000.0),
        'fogPowerDay': fog.get('dayPower', 1.0), 'fogMaxDay': fog.get('dayMax', 1.0),
        'fogNearNight': fog.get('nightNear', 0.0), 'fogFarNight': fog.get('nightFar', 150000.0),
        'fogPowerNight': fog.get('nightPower', 1.0), 'fogMaxNight': fog.get('nightMax', 1.0),
        'wind': d['windSpeed'], 'windDir': d['windDirection'], 'thunder': d['thunderFrequency'],
        'sunGlare': d['sunGlare'], 'sunDamage': d['sunDamage'],
        'precip': w.get('precipitationName', ''), 'aurora': bool(w.get('auroraModel')),
        'class': '+'.join(w['class']) or '-',
    }


def classify(editor_id, f):
    """Record first, name only for the other-realm skies. Returns (type, severity 0..1)."""
    n = editor_id.lower()
    dark = clamp01((0.92 - f['sunLumDay']) / 0.72)                 # 0 at a full sun (0.92), 1 at 0.20
    alpha = clamp01((f['alphaSumDay'] - 3.0) / 7.0)                # NAT stacks 3..10 layers of alpha in fair/cloudy skies
    fog_far = f['fogFarDay']
    if n.startswith(SPECIAL_PREFIXES):
        return 'special', 0.0
    if f['precip'] in RAIN_STORM:
        return 'storm', clamp01(0.5 * dark + 0.5 * clamp01((f['wind'] - 100) / 110.0))
    if fog_far <= 15000 and f['precip'] not in SNOW and f['precip'] not in ASH:
        return 'fog', clamp01(math.log(15000.0 / fog_far) / math.log(15000.0 / 4000.0))
    if f['precip'] in RAIN:
        return 'rain', clamp01(0.7 * dark + 0.3 * fog_nearness(fog_far))
    if f['precip'] in SNOW:
        s = 0.5 * dark + 0.5 * clamp01((f['wind'] - 25) / 185.0)
        if f['layersAlphaDay'] <= 1:
            s *= 0.5
        return 'snow', clamp01(s)
    if fog_far <= 100000 or f['precip'] in ASH:
        return 'overcast', clamp01(0.7 * dark + 0.3 * clamp01((0.9 - f['cloudLumDay']) / 0.7))
    if 'pleasant' in f['class'] and (f['layersAlphaDay'] <= 1 or f['wind'] <= 5):
        return 'clear', 0.0
    if f['wind'] <= 10:
        return 'fair', alpha
    return 'partly', clamp01(0.5 * alpha + 0.5 * clamp01((0.92 - f['sunLumDay']) / 0.32))


def fog_nearness(fog_far):
    """0 at the clear-day fog far of 150000 units, 1 at 5000 (log scale)."""
    return clamp01(math.log(150000.0 / max(fog_far, 1.0)) / math.log(150000.0 / 5000.0))


def wind_for(wind_byte):
    """Record wind byte -> cloud drift. Saved base 5 / 10 m/s sits at byte ~33 (between Cloudy 25 and Overcast 35).
    Direction: every Tamriel record has the same wind direction byte (43), so it is not used; +X as in the saved base."""
    low = round(max(3.0, min(16.0, 3.0 + 0.06 * wind_byte)), 2)
    return [low, 0.0], [round(2.0 * low, 2), 0.0]


def half_distance_m(near, far, power, max_opacity, strength):
    """Distance at which follow-vanilla height fog is 50% opaque at eye level, ignoring the height falloff.
    Mirrors ExponentialHeightFog::GetCommonBufferData: the density is set so that opacity = 0.5 * fogClamp at
    referenceDistance when vanillaFogStrength is 1, and extinction scales linearly with the strength."""
    clampv = max(0.0, min(max_opacity, 1.0 - 0.0001))
    target = clampv * 0.5
    if target <= 0.0 or strength <= 0.0:
        return float('inf')
    power = max(power, 0.01)
    reference = max((max(far, near + 1.0) - near) * target ** (1.0 / power), 1.0)
    return reference * math.log(0.5) / math.log(1.0 - target) / strength * GAME_UNIT_M


def fog_strength(near, far, power, max_opacity, floor_m):
    raw = half_distance_m(near, far, power, max_opacity, BASE_FOG_STRENGTH)
    if floor_m is None or raw >= floor_m:
        return BASE_FOG_STRENGTH, raw, raw
    eff = floor_m * (raw / floor_m) ** FOG_COMPRESS
    return round(max(0.01, BASE_FOG_STRENGTH * raw / eff), 3), raw, eff


def settings_for(wtype, sev, f):
    """Period-independent numbers of one weather."""
    t = T[wtype]
    loading = round(lerp(t['haze'], fog_nearness(f['fogFarDay'])), 3)
    low_v, high_v = wind_for(f['wind'])
    day = fog_strength(f['fogNearDay'], f['fogFarDay'], f['fogPowerDay'], f['fogMaxDay'], t['fogHalfM'])
    night = fog_strength(f['fogNearNight'], f['fogFarNight'], f['fogPowerNight'], f['fogMaxNight'], t['fogHalfM'])
    return {
        'inMin': round(lerp(t['inMin'], sev), 3), 'outMin': round(lerp(t['outMin'], sev), 3),
        'outMax': round(lerp(t['outMax'], sev), 3), 'sec': round(lerp(t['sec'], sev), 3),
        'base': float(round(lerp(t['base'], sev) / 10.0) * 10), 'thick': float(round(lerp(t['thick'], sev) / 10.0) * 10),
        'dens': round(lerp(t['dens'], sev), 3), 'cirrus': float(t['cirrus']),
        'loading': loading, 'windLow': low_v, 'windHigh': high_v,
        'fogDay': day[0], 'fogNight': night[0], 'fogTwilight': round(math.sqrt(day[0] * night[0]), 3),
        'fogHalfRawDayM': day[1], 'fogHalfDayM': day[2], 'fogHalfRawNightM': night[1], 'fogHalfNightM': night[2],
    }


def xyzw(v):
    return dict(zip('xyzw', [float(x) for x in v]))


def sky_tree(s, wtype, aurora, period):
    in_min, cirrus = s['inMin'], s['cirrus']
    if aurora and wtype in AURORA_TYPES and period in DARK_PERIODS:
        in_min = round(min(0.5, in_min + AURORA_IN_MIN_SHIFT), 3)
        cirrus = 0.0
    scatter, absorption = aerosol(s['loading'])
    return {
        'aerosolScatter': dict(zip('xyz', scatter)),
        'aerosolAbsorption': dict(zip('xyz', absorption)),
        'cloudMap': {'procedural': {'parameters': {
            'primary': {'range': xyzw([in_min, PRIMARY_IN_MAX, s['outMin'], s['outMax']])},
            'secondary': {'range': {'x': float(s['sec'])}},
        }}},
        'cloudLayer': {
            'low': {'ndfAltitudeOffset': s['base'], 'ndfAltitudeScale': s['thick'], 'densityScale': float(s['dens'])},
            'wind': {'lowVelocity': dict(zip('xy', s['windLow'])), 'highVelocity': dict(zip('xy', s['windHigh']))},
            'cirrus': {'densityScale': float(cirrus)},
        },
    }


def fog_tree(s, period):
    if period == 'Night':
        v = s['fogNight']
    elif period in ('Dawn', 'Dusk'):
        v = s['fogTwilight']
    else:
        v = s['fogDay']
    return {'vanillaFogStrength': float(v)}


def leaves(tree, path=()):
    for k, v in tree.items():
        if isinstance(v, dict):
            yield from leaves(v, path + (k,))
        else:
            yield path, k, v


SCENE_BLACKLIST = {  # src/CSEditor/SceneManager/SceneSettingsPolicy.h, PhysicalSky rows (prefix match)
    'PhysicalSky': [('aerosolType',), ('aerosolLoading',), ('aerosolHumidity',), ('rayMarchRange',), ('shadowVolumeRange',),
                    ('marchStepScale',), ('cloudNoise',), ('cloudLayer', 'cirrus', 'uvSize'), ('cloudRelightMix',),
                    ('cloudOriginalMix',), ('silverLiningMix',), ('silverLiningSpread',), ('cloudShadowRemapRange',),
                    ('halfResApShadow',), ('planetRadius',), ('atmosphereRadius',), ('fallbackZBottom',),
                    ('cloudMap', 'type'), ('cloudMap', 'localTexelSize'), ('cloudMap', 'texture'),
                    ('cloudMap', 'procedural', 'noise'), ('cloudMap', 'procedural', 'local'),
                    ('cloudMap', 'procedural', 'localMaskPath'),
                    ('cloudMap', 'procedural', 'parameters', 'heightFromCoverage'),
                    ('cloudMap', 'procedural', 'parameters', 'localBlendMode'),
                    ('cloudMap', 'procedural', 'parameters', 'primary', 'noise'),
                    ('cloudMap', 'procedural', 'parameters', 'secondary', 'noise'),
                    ('cloudMap', 'procedural', 'parameters', 'coverageGain', 'noise'),
                    ('cloudMap', 'procedural', 'parameters', 'coverageGain', 'exponent')],
    'ExponentialHeightFog': [],
}


def validate(feature, tree, catalog, where):
    problems = []
    for path, key, value in leaves(tree):
        full = path + (key,)
        if any(full[:len(b)] == b for b in SCENE_BLACKLIST[feature]):
            problems.append('%s: %s %s is blacklisted for scenes' % (where, feature, '/'.join(full)))
            continue
        entry = catalog.get((feature, '/'.join(path), key))
        if not entry:
            problems.append('%s: %s %s not in catalog' % (where, feature, '/'.join(full)))
            continue
        if entry['vtype'] != 'Float' or 'Trans' not in entry['flags']:
            problems.append('%s: %s %s is not a transitionable float' % (where, feature, '/'.join(full)))
        if not isinstance(value, float):
            problems.append('%s: %s %s is not written as a float' % (where, feature, '/'.join(full)))
        elif entry['bounds'] == 'true' and not (float(entry['mn']) <= value <= float(entry['mx'])):
            problems.append('%s: %s %s = %s outside %s..%s' % (where, feature, '/'.join(full), value, entry['mn'], entry['mx']))
    return problems


def write_json(path, data, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        if compact:
            json.dump(data, f, separators=(',', ':'))
        else:
            json.dump(data, f, indent=2)
            f.write('\n')


def baseline_doc():
    """The saved global base, so a weather without a file looks exactly like today's tested sky.
    Vectors are arrays here (SettingsUser tree); cloudMap needs version 3 or the block is reset on load."""
    b = CALIBRATION['savedBase']
    return {
        '_metadata': {'version': '0.2.0',
                      'description': PACK + ': the global base saved in game on 2026-11-18 (fallback for weathers without a file). '
                                     'Per-weather files are UNTESTED.'},
        'enableVolumetricClouds': True,
        'enableVanillaClouds': False,
        'aerosolType': 1,
        'aerosolLoading': 0.4,
        'cloudMap': {'version': 3, 'procedural': {'parameters': {'primary': {'range': b['cloudMap.procedural.parameters.primary.range']}}}},
        'cloudLayer': {
            'low': {'ndfAltitudeOffset': 1200.0, 'ndfAltitudeScale': 900.0, 'ndfScale': [24.66, 16.7], 'densityScale': 0.75},
            'cirrus': {'densityScale': 0.3},
            'wind': {'lowVelocity': [5.0, 0.0], 'highVelocity': [10.0, 0.0]},
        },
    }


MANIFEST = {
    'name': 'foxnne NAT III clouds (pass 2)',
    'version': '0.2.0',
    'type': 'CS',
    'author': 'foxnne',
    'description': 'UNTESTED DRAFT, pass 2. Per-weather volumetric cloud coverage, altitude, density, drift, high layer, haze '
                   '(Physical Sky) and height-fog strength (Exponential Height Fog) for the 111 NAT.CS III weathers, by sky type. '
                   'Applying a pack with scene files makes it the active pack: read notes/how-it-works.md section 8 first.',
    'tags': ['NAT.CS III', 'Physical Sky', 'volumetric clouds', 'draft'],
    'csVersion': '1.9.0',
    'requiredFeatures': ['PhysicalSky', 'ExponentialHeightFog', 'SceneManager', 'SkySync'],
    'requiredPlugins': ['NAT-ENB.esp', 'NAT-CS.esp'],
}


def flat(tree):
    return {'.'.join(p + (k,)): v for p, k, v in leaves(tree)}


def main():
    masters, recs = wthr_parse.load()
    write_json(os.path.join(HERE, 'nat-cs-wthr-records.json'), {'source': wthr_parse.PLUGIN, 'masters': masters, 'weathers': recs})
    cat = json.load(open(os.path.join(HERE, 'scene-catalog-pass2.json'), encoding='utf-8'))
    catalog = {(e['feature'], e['path'], e['key']): e for e in cat['rows']}

    # Only ever remove what this script generates.
    for sub in ('Weather', 'Baseline'):
        if os.path.isdir(os.path.join(PACK_DIR, sub)):
            shutil.rmtree(os.path.join(PACK_DIR, sub))

    rows, problems, user_fragment, files = [], [], {}, 0
    for w in recs:
        f = facts(w)
        wtype, sev = classify(w['editorId'], f)
        s = settings_for(wtype, sev, f)
        entries = []
        for period in PERIODS:
            for feature, tree in (('PhysicalSky', sky_tree(s, wtype, f['aurora'], period)),
                                  ('ExponentialHeightFog', fog_tree(s, period))):
                problems += validate(feature, tree, catalog, '%s/%s' % (w['editorId'], period))
                doc = {'_feature': feature,
                       '_metadata': {'description': '%s - %s, severity %.2f (%s) - %s' % (PACK, T[wtype]['label'], sev, w['editorId'], period),
                                     'timeOfDayEnabled': True}}
                doc.update(tree)
                write_json(os.path.join(PACK_DIR, 'Weather', w['spid'], period, '%s_%s.json' % (PACK, feature)), doc)
                files += 1
                for path, key, value in leaves(tree):
                    entries.append({'feature': feature, 'path': list(path), 'setting': key, 'value': value,
                                    'originalValue': value, 'paused': False, 'period': period})
        user_fragment[w['spid']] = {'entries': entries}
        rows.append(dict(w=w, f=f, type=wtype, sev=sev, s=s))

    write_json(os.path.join(PACK_DIR, PACK + '.json'), MANIFEST)
    write_json(os.path.join(PACK_DIR, 'Baseline', 'PhysicalSky.json'), baseline_doc())
    write_json(os.path.join(DRAFT, 'alt-user-overrides-pass2', 'SceneManager.weather.pass2.json'), user_fragment, compact=True)

    # ---- monotonic sanity: heavier severity never means less cloud / higher base within a type
    for name in TYPE_ORDER:
        members = sorted((r for r in rows if r['type'] == name), key=lambda r: r['sev'])
        for a, b in zip(members, members[1:]):
            if b['s']['inMin'] > a['s']['inMin'] + 1e-9 or b['s']['base'] > a['s']['base'] + 1e-9 or b['s']['dens'] < a['s']['dens'] - 1e-9:
                problems.append('not monotonic within %s: %s -> %s' % (name, a['w']['editorId'], b['w']['editorId']))

    # ---- summary: one representative per type
    counts = collections.Counter(r['type'] for r in rows)
    summary = {'_note': 'UNTESTED. One representative weather per sky type with its Day settings, for one frame per type. '
                        'Console: fw <formId>; NAT-ENB.esp ids need the load-order byte in place of the leading 00.',
               'pack': PACK, 'calibration': CALIBRATION, 'types': collections.OrderedDict()}
    for name in TYPE_ORDER:
        members = sorted((r for r in rows if r['type'] == name), key=lambda r: (r['sev'], r['w']['editorId']))
        if not members:
            continue
        rep = next((r for r in members if r['w']['editorId'] == PREFERRED_REPRESENTATIVE.get(name)), members[len(members) // 2])
        heavy = members[-1]

        def describe(r):
            day = flat(sky_tree(r['s'], r['type'], r['f']['aurora'], 'Day'))
            return {'editorId': r['w']['editorId'], 'formKey': r['w']['spid'], 'localFormId': r['w']['spid'].split('~')[0],
                    'plugin': r['w']['spid'].split('~')[1], 'severity': round(r['sev'], 3),
                    'aerosolLoadingEquivalent': r['s']['loading'],
                    'PhysicalSky.Day': day,
                    'ExponentialHeightFog': {'vanillaFogStrength.Day': r['s']['fogDay'], 'vanillaFogStrength.Night': r['s']['fogNight'],
                                             'halfOpacityDistanceDayM.atBaseline0.3': round(r['s']['fogHalfRawDayM']),
                                             'halfOpacityDistanceDayM.pass2': round(r['s']['fogHalfDayM'])}}
        t = T[name]
        summary['types'][name] = {
            'label': t['label'], 'rationale': t['why'], 'count': counts[name],
            'definition_lightest_to_heaviest': {k: t[k] for k in ('inMin', 'outMin', 'outMax', 'sec', 'base', 'thick', 'dens', 'cirrus', 'haze', 'fogHalfM')},
            'representative': describe(rep),
            'heaviestMember': describe(heavy) if heavy is not rep else None,
            'members': [{'editorId': r['w']['editorId'], 'formKey': r['w']['spid'], 'severity': round(r['sev'], 3)} for r in members],
        }
    write_json(os.path.join(DRAFT, 'pass2-sky-types.json'), summary)

    # ---- table
    out = ['# NAT.CS III weather table, pass 2 (untested)', '',
           'Generated by `draft/_generator/build_pass2.py`. Do not edit by hand; edit the sky types in the generator and re-run.',
           'Record facts are parsed from `NAT-CS.esp` (the winning override of all %d weathers). Nothing here was seen in game.' % len(rows), '',
           '## Sky types', '',
           'Each value is `lightest -> heaviest`; a weather sits between by its severity. inMin/outMin/outMax = '
           '`cloudMap.procedural.parameters.primary.range` x/z/w (y stays %s); sec = `secondary.range.x`; base/thick = '
           '`cloudLayer.low.ndfAltitudeOffset/ndfAltitudeScale` (m); dens = `cloudLayer.low.densityScale`; high = '
           '`cloudLayer.cirrus.densityScale`; haze = Continental loading at RH 50 (lo at fog far 150000, hi at 5000), written as '
           '`aerosolScatter`/`aerosolAbsorption`; fog half = shortest half-opacity distance allowed for height fog '
           '(`ExponentialHeightFog.vanillaFogStrength` is lowered from %s to reach it). Sun multiplier is 1.0 for every type (not written).' % (PRIMARY_IN_MAX, BASE_FOG_STRENGTH), '',
           '| Type | Weathers | inMin | outMin | outMax | sec | base m | thick m | dens | high | haze | fog half m | Rationale |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|']

    def rng(p, fmt='%g'):
        return fmt % p[0] if p[0] == p[1] else (fmt + ' -> ' + fmt) % p
    for name in TYPE_ORDER:
        t = T[name]
        out.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %g | %s | %s | %s |' % (
            name, counts[name], rng(t['inMin']), rng(t['outMin']), rng(t['outMax']), rng(t['sec']), rng(t['base']), rng(t['thick']),
            rng(t['dens']), t['cirrus'], rng(t['haze']), t['fogHalfM'] or 'baseline', t['why']))
    out += ['', '## Rules', '',
            '- **Type** (first match): other-realm name prefix -> special; storm rain particles -> storm; day fog far <= 15000 without snow/ash '
            'particles -> fog; rain particles -> rain; snow particles -> snow; day fog far <= 100000 or ash particles -> overcast; '
            'pleasant flag with at most one cloud layer of alpha, or wind <= 5 -> clear; wind <= 10 -> fair; otherwise partly.',
            '- **Severity**: dark = (0.92 - day sunlight luminance) / 0.72; alpha = (sum of day layer alphas - 3) / 7; all clamped 0..1. '
            'fair = alpha; partly = half alpha, half (0.92 - sun) / 0.32; overcast = 0.7 dark + 0.3 cloud-colour darkness; '
            'rain = 0.7 dark + 0.3 fog nearness; storm = half dark, half (wind - 100) / 110; snow = half dark, half (wind - 25) / 185, '
            'halved when a single cloud layer has alpha; fog = log position of day fog far between 15000 and 4000.',
            '- **Haze**: lo + (hi - lo) x fog nearness, fog nearness = log position of day fog far between 150000 and 5000.',
            '- **Cloud drift**: low = 3 + 0.06 x wind byte m/s (3..16), high = 2 x low, along +X.',
            '- **Height fog**: half-opacity distance at strength %s is computed from the record fog (near, far, power, max) the way the feature does; '
            'where it is shorter than the type floor, the strength is lowered so the distance becomes floor x (raw / floor)^%s. '
            'Day values for Sunrise/Day/Sunset, night values for Night, geometric mean for Dawn/Dusk.' % (BASE_FOG_STRENGTH, FOG_COMPRESS),
            '- **Aurora** (record has an aurora model; clear/fair/partly only): in Dawn, Dusk and Night inMin + %s and high layer 0.' % AURORA_IN_MIN_SHIFT, '',
            '## Every weather', '',
            'Class = record classification flag. Layers = enabled cloud layers / of those with alpha > 0 by day. Fog = day near/far (night far). '
            'Thunder = frequency byte (255 = none; lower = more). Fog str = `vanillaFogStrength` day / night; half m = resulting day half-opacity distance.', '',
            '| Editor ID | Form key | Class | Layers | Mean alpha | Sun lum | Fog day (night far) | Wind | Precipitation | Thunder | Aurora | Type | Sev | inMin | outMin | base-top m | dens | high | haze | low wind | Fog str | half m | Note |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (TYPE_ORDER.index(r['type']), r['sev'], r['w']['editorId'].lower(), r['w']['spid'])):
        f, s = r['f'], r['s']
        out.append('| %s | `%s` | %s | %d/%d | %.2f | %.2f | %d/%d (%d) | %d | %s | %d | %s | %s | %.2f | %g | %g | %d-%d | %g | %g | %g | %g | %g / %g | %d | %s |' % (
            r['w']['editorId'], r['w']['spid'], f['class'], f['layers'], f['layersAlphaDay'], f['alphaMeanDay'], f['sunLumDay'],
            f['fogNearDay'], f['fogFarDay'], f['fogFarNight'], f['wind'], f['precip'] or '-', f['thunder'], 'yes' if f['aurora'] else '',
            r['type'], r['sev'], s['inMin'], s['outMin'], s['base'], s['base'] + s['thick'], s['dens'], s['cirrus'], s['loading'],
            s['windLow'][0], s['fogDay'], s['fogNight'], min(s['fogHalfDayM'], 99999), NOTES.get(r['w']['editorId'], '')))
    os.makedirs(os.path.join(ROOT, 'notes'), exist_ok=True)
    with open(os.path.join(ROOT, 'notes', 'weather-table-2.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')

    print('weathers:', len(rows), 'scene files:', files)
    print('types:', ', '.join('%s %d' % (n, counts[n]) for n in TYPE_ORDER))
    print('aurora weathers:', sum(1 for r in rows if r['f']['aurora']))
    print('validation problems:', len(problems))
    for p in sorted(set(problems))[:40]:
        print('  ', p)


if __name__ == '__main__':
    main()

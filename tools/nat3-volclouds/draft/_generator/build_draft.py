"""Builds the foxnne-nat3-clouds draft pack from the group table below.

UNTESTED DRAFT. Every number in GROUPS is a guess derived from reading the fork source
(branch foxnne/nr-pr6) - nothing here has been seen in game. Edit GROUPS, re-run, re-copy.

Usage (run from anywhere, writes only under this draft folder and ..\\..\\notes):
    python -I build_draft.py "C:\\Modlists\\NGVO 8.0 Beta\\overwrite\\SKSE\\Plugins\\CommunityShaders\\LookWeathers.json"

Reads (read-only):
    nat-cs-weathers.json            the 111 WTHR records NAT-CS.esp overrides (spid + editor id)
    LookWeathers.json               game dump: record flags per weather (pleasant/cloudy/rainy/snow)
    physicalsky-scene-catalog.json  compiled scene catalog of the fork build, used to validate keys/ranges
Writes:
    ..\\foxnne-nat3-clouds\\                      the pack (manifest, Baseline, Weather/<spid>/<Period>/)
    ..\\baseline-variants\\                       quality / performance Baseline/PhysicalSky.json
    ..\\alt-user-overrides\\                      same values as SceneManager.json "weather" entries
    ..\\..\\notes\\weather-table.md
"""
import collections
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.dirname(HERE)
ROOT = os.path.dirname(DRAFT)
PACK = 'foxnne-nat3-clouds'
PACK_DIR = os.path.join(DRAFT, PACK)
PERIODS = ['Dawn', 'Sunrise', 'Day', 'Sunset', 'Dusk', 'Night']
DARK_PERIODS = {'Dawn', 'Dusk', 'Night'}

# --------------------------------------------------------------------------------------------
# Tagging: copy of look/webapp/weather_tags.py default_tags() (not imported, so nothing is
# written next to the original).
TAGS = ['clear', 'cloudy', 'overcast', 'fog', 'rain', 'snow', 'storm']


def default_tags(editor_id, rec=None):
    n = (editor_id or '').lower()
    rec = rec or {}
    t = {}
    if 'fog' in n or 'mist' in n:
        t['fog'] = 1
    if 'storm' in n or 'thunder' in n or 'blizzard' in n or 'tempest' in n:
        t['storm'] = 1
    if rec.get('rainy') or 'rain' in n or 'drizzle' in n:
        t['rain'] = 1
    if rec.get('snow') or 'snow' in n or 'blizzard' in n:
        t['snow'] = 1
    if 'overcast' in n or 'grey' in n or 'gloom' in n:
        t['overcast'] = 1
    elif (rec.get('cloudy') or 'cloud' in n) and not (t.get('rain') or t.get('snow') or t.get('fog')):
        t['cloudy'] = 1
    if not t:
        t['clear' if (rec.get('pleasant') or 'sun' in n or 'clear' in n or not rec) else 'cloudy'] = 1
    return t


# Worldspaces that are not in Physical Sky's default whitelist, or scripted skies: no low clouds.
SPECIAL_PREFIXES = ('sovngarde', 'soulcairn', 'dlc2apocrypha', 'blackreach', 'worldmap')
# Tag-derived group kept, but the tag itself is doubtful. Listed in the table as low confidence.
LOW_CONFIDENCE = {
    'SunnyDLC2': 'name says Sunny, record flag says cloudy (Solstheim ash haze)',
    'SunnyDLC2_ALT': 'name says Sunny, record flag says cloudy (Solstheim ash haze)',
    'StormDLC2': 'ash storm; tagged storm+snow only because the record uses the snow flag',
    'StormDLC2_ALT': 'ash storm; tagged storm+snow only because the record uses the snow flag',
    'DLC1Eclipse': 'scripted eclipse weather, flag cloudy',
    'DLC1FalmerValley_bf': 'Forgotten Vale blizzard/fog weather, fog distance 4000; flag only says cloudy',
    'DLC1FalmerValley_bfDark': 'Forgotten Vale blizzard/fog weather, fog distance 6000; flag only says cloudy',
    'SkyrimMQ206weather': 'quest weather, flag cloudy',
    'HelgenAttackWeather': 'quest weather (smoke), flag cloudy',
    'SkyrimDA02Weather': 'quest weather, flag cloudy',
    'BloatedMansGrottoFog': 'quest/grotto weather',
    'SkuldafnCloudy': 'name says Cloudy, record flag says snow',
    'SkyrimOvercastWar': 'civil-war battle weather (smoke)',
}


def classify(editor_id, rec):
    """Returns (tags, group, aurora)."""
    n = editor_id.lower()
    tags = default_tags(editor_id, rec)
    aurora = n.endswith('_a') or '_a_' in n
    if n.startswith(SPECIAL_PREFIXES):
        return tags, 'special', False
    if 'storm' in tags:
        group = 'snowstorm' if 'snow' in tags else 'storm'
    elif 'fog' in tags:
        group = 'fog'
    elif 'rain' in tags:
        group = 'rain'
    elif 'snow' in tags:
        group = 'snow_light' if 'clear' in n else 'snow'
    elif 'overcast' in tags:
        group = 'overcast'
    elif 'cloudy' in tags:
        group = 'cloudy'
    else:
        group = 'clear_sky' if n.startswith('sclearsky') else 'clear'
    return tags, group, aurora


# --------------------------------------------------------------------------------------------
# Group values. ALL GUESSES.
#   primary / secondary : coverage remap [inMin, inMax, outMin, outMax] of signed noise (-1..1).
#                         Raising inMin shrinks the cloudy AREA; outMax is the PEAK coverage.
#                         Density only appears where profile = verticalProfile * coverage^k exceeds
#                         roughly 0.3 (CloudNoise.hlsli:69), and saturates near 0.7.
#   gain                : constant coverage multiplier (coverageGain.range z == w). 0 = no low clouds.
#   base / span         : low layer base altitude and height span, metres above the worldspace
#                         zBottom (Tamriel -14500 units; 1 unit = 0.0142875 m, so Whiterun plains
#                         sit near 150-200 m and the highest peaks near 800-850 m on this scale).
#   density             : low.densityScale ("Extinction Scale", 0..1).
#   top                 : low.topExpansionScale (0..1).
#   bright/sunExt/viewExt/ambient : cloudLayer.lighting.*
#   cirrus              : cirrus.densityScale (0 hides it); cirrusCov = layer 0 remap.
#   dev / dist          : wind.development / wind.disturbance
GROUPS = {
    'clear_sky': dict(label='Clear sky (no low cloud)',
                      primary=[0.35, 1.0, 0.0, 0.40], secondary=[0.50, 1.0, 0.0, 0.30], gain=0.0,
                      base=1400.0, span=600.0, density=0.30, top=0.3,
                      bright=1.0, sunExt=0.5, viewExt=0.8, ambient=1.0,
                      cirrus=0.30, cirrusCov=[0.10, 1.0, 0.0, 0.50], cirrusAlt=9500.0, dev=0.15, dist=0.10),
    'clear': dict(label='Fair: few small cumulus',
                  primary=[0.30, 1.0, 0.0, 0.45], secondary=[0.50, 1.0, 0.0, 0.30], gain=1.0,
                  base=1300.0, span=700.0, density=0.35, top=0.3,
                  bright=1.0, sunExt=0.6, viewExt=0.8, ambient=1.0,
                  cirrus=0.50, cirrusCov=[-0.20, 0.9, 0.0, 0.55], cirrusAlt=9000.0, dev=0.20, dist=0.15),
    'cloudy': dict(label='Broken cumulus',
                   primary=[-0.15, 0.75, 0.0, 0.62], secondary=[0.0, 0.9, 0.0, 0.40], gain=1.0,
                   base=1100.0, span=1100.0, density=0.55, top=0.6,
                   bright=1.0, sunExt=0.85, viewExt=1.0, ambient=1.0,
                   cirrus=0.80, cirrusCov=[-0.50, 0.8, 0.0, 0.60], cirrusAlt=9000.0, dev=0.25, dist=0.20),
    'overcast': dict(label='Stratus deck',
                     primary=[-0.90, 0.30, 0.45, 0.85], secondary=[-0.50, 0.60, 0.30, 0.60], gain=1.0,
                     base=800.0, span=900.0, density=0.60, top=0.4,
                     bright=1.1, sunExt=0.9, viewExt=1.0, ambient=1.3,
                     cirrus=0.0, cirrusCov=[-0.70, 0.7, 0.0, 0.60], cirrusAlt=9000.0, dev=0.20, dist=0.15),
    'fog': dict(label='Low thin stratus (ground fog comes from height fog)',
                primary=[-0.80, 0.40, 0.35, 0.75], secondary=[-0.40, 0.70, 0.20, 0.50], gain=1.0,
                base=600.0, span=600.0, density=0.40, top=0.2,
                bright=1.15, sunExt=0.7, viewExt=0.8, ambient=1.4,
                cirrus=0.0, cirrusCov=[-0.70, 0.7, 0.0, 0.60], cirrusAlt=9000.0, dev=0.10, dist=0.10),
    'rain': dict(label='Nimbostratus',
                 primary=[-0.90, 0.20, 0.50, 0.90], secondary=[-0.50, 0.50, 0.35, 0.70], gain=1.0,
                 base=700.0, span=1500.0, density=0.70, top=0.6,
                 bright=1.0, sunExt=1.0, viewExt=1.1, ambient=1.2,
                 cirrus=0.0, cirrusCov=[-0.70, 0.7, 0.0, 0.60], cirrusAlt=9000.0, dev=0.35, dist=0.30),
    'storm': dict(label='Deep storm cloud',
                  primary=[-1.0, 0.0, 0.60, 1.0], secondary=[-0.60, 0.40, 0.45, 0.85], gain=1.0,
                  base=600.0, span=2600.0, density=0.90, top=1.0,
                  bright=0.9, sunExt=1.25, viewExt=1.2, ambient=1.0,
                  cirrus=0.0, cirrusCov=[-0.70, 0.7, 0.0, 0.60], cirrusAlt=9000.0, dev=0.50, dist=0.50),
    'snow': dict(label='Snow stratus, bright',
                 primary=[-0.80, 0.30, 0.40, 0.80], secondary=[-0.40, 0.60, 0.25, 0.55], gain=1.0,
                 base=700.0, span=1000.0, density=0.50, top=0.3,
                 bright=1.15, sunExt=0.8, viewExt=0.9, ambient=1.4,
                 cirrus=0.0, cirrusCov=[-0.70, 0.7, 0.0, 0.60], cirrusAlt=9000.0, dev=0.20, dist=0.20),
    'snow_light': dict(label='Light snow from thin broken cloud',
                       primary=[-0.10, 0.80, 0.0, 0.55], secondary=[0.10, 0.90, 0.0, 0.35], gain=1.0,
                       base=1000.0, span=900.0, density=0.45, top=0.4,
                       bright=1.1, sunExt=0.7, viewExt=0.9, ambient=1.2,
                       cirrus=0.50, cirrusCov=[-0.40, 0.8, 0.0, 0.55], cirrusAlt=9000.0, dev=0.20, dist=0.20),
    'snowstorm': dict(label='Blizzard deck',
                      primary=[-1.0, 0.0, 0.60, 0.95], secondary=[-0.60, 0.40, 0.40, 0.80], gain=1.0,
                      base=500.0, span=1800.0, density=0.80, top=0.7,
                      bright=1.0, sunExt=1.1, viewExt=1.1, ambient=1.3,
                      cirrus=0.0, cirrusCov=[-0.70, 0.7, 0.0, 0.60], cirrusAlt=9000.0, dev=0.45, dist=0.50),
    'special': dict(label='Other realms / map: no low cloud, no cirrus',
                    primary=[0.35, 1.0, 0.0, 0.40], secondary=[0.50, 1.0, 0.0, 0.30], gain=0.0,
                    base=1400.0, span=600.0, density=0.30, top=0.3,
                    bright=1.0, sunExt=0.5, viewExt=0.8, ambient=1.0,
                    cirrus=0.0, cirrusCov=[0.10, 1.0, 0.0, 0.50], cirrusAlt=9500.0, dev=0.15, dist=0.10),
}
GROUP_ORDER = ['clear_sky', 'clear', 'cloudy', 'overcast', 'fog', 'rain', 'storm', 'snow_light', 'snow', 'snowstorm', 'special']
# Aurora variants: in the dark periods thin the low layer and drop cirrus so the aurora stays visible.
AURORA_GAIN_SCALE = 0.5


def wind_for(wind_speed):
    """Cloud drift from the record's wind byte (0-255). Direction is a fixed guess (+X, slight +Y)."""
    w = max(0.0, min(255.0, float(wind_speed))) / 255.0
    low = round(3.0 + 20.0 * w, 2)
    high = round(8.0 + 30.0 * w, 2)
    return [low, round(low * 0.3, 2)], [high, round(high * 0.3, 2)]


def cirrus_state(cov):
    """One CirrusWeatherState endpoint (Ndf.h:269-284). Inside a state, vectors are arrays."""
    return {'states': [{'value': {
        'layers': [
            {'noise': 1, 'frequency': 1.0, 'offset': [0.0, 0.0], 'range': [float(x) for x in cov]},
            {'noise': 2, 'frequency': 1.0, 'offset': [0.0, 0.0], 'range': [-1.0, 1.0, 0.0, 1.0]},
        ],
        'localMap': '', 'localWeight': 0.0, 'localWindScale': 1.0, 'localBlendMode': 0,
    }, 'weight': 1.0}]}


def xyzw(v):
    return dict(zip('xyzw', [float(x) for x in v]))


def scene_values(group, wind_speed, aurora, period):
    """The nested PhysicalSky scene tree for one weather + period (vector components keyed x/y/z/w)."""
    g = GROUPS[group]
    gain = g['gain']
    cirrus = g['cirrus']
    if aurora and period in DARK_PERIODS:
        gain = round(gain * AURORA_GAIN_SCALE, 3)
        cirrus = 0.0
    low_v, high_v = wind_for(wind_speed)
    return {
        'cloudMap': {'procedural': {'parameters': {
            'primary': {'range': xyzw(g['primary'])},
            'secondary': {'range': xyzw(g['secondary'])},
            'coverageGain': {'range': {'z': float(gain), 'w': float(gain)}},
        }}},
        'cloudLayer': {
            'low': {
                'ndfAltitudeOffset': float(g['base']),
                'ndfAltitudeScale': float(g['span']),
                'densityScale': float(g['density']),
                'topExpansionScale': float(g['top']),
            },
            'lighting': {
                'brightness': float(g['bright']),
                'sunExtinction': float(g['sunExt']),
                'viewExtinction': float(g['viewExt']),
                'ambientStrength': float(g['ambient']),
            },
            'wind': {
                'lowVelocity': {'x': low_v[0], 'y': low_v[1]},
                'highVelocity': {'x': high_v[0], 'y': high_v[1]},
                'development': float(g['dev']),
                'disturbance': float(g['dist']),
            },
            'cirrus': {
                'altitude': float(g['cirrusAlt']),
                'densityScale': float(cirrus),
                'weather': cirrus_state(g['cirrusCov']),
            },
        },
    }


def is_blend(v):
    return isinstance(v, dict) and set(v.keys()) == {'states'}


def leaves(tree, path=()):
    for k, v in tree.items():
        if isinstance(v, dict) and not is_blend(v):
            yield from leaves(v, path + (k,))
        else:
            yield path, k, v


# --------------------------------------------------------------------------------------------
# Baseline. Vectors are arrays here (same tree a feature saves to SettingsUser.json).
BLACKLIST = [
    ('rayMarchRange',), ('shadowVolumeRange',), ('marchStepScale',), ('cloudNoise',),
    ('cloudLayer', 'cirrus', 'uvSize'), ('cloudRelightMix',), ('cloudOriginalMix',),
    ('silverLiningMix',), ('silverLiningSpread',), ('cloudShadowRemapRange',),
    ('cloudMap', 'type'), ('cloudMap', 'localTexelSize'), ('cloudMap', 'texture'),
    ('cloudMap', 'procedural', 'noise'), ('cloudMap', 'procedural', 'local'),
]

QUALITY = {
    'quality': dict(rayMarchRange=32.0, shadowVolumeRange=8.0, marchStepScale=0.5, cloudBlurRadius=1, halfResApShadow=False,
                    note='Fork defaults for the march. 1/16 of pixels traced per frame at quarter resolution; '
                         'step = (3 m + 0.366% of distance) x 0.5.'),
    'performance': dict(rayMarchRange=24.0, shadowVolumeRange=6.0, marchStepScale=1.0, cloudBlurRadius=2, halfResApShadow=True,
                        note='About half the march samples (step x1.0), shorter range, wider final blur to hide the '
                             'coarser steps, half-resolution aerial-perspective cloud shadow. Smaller shadow volume '
                             'means finer shadow texels (6 km / 256 = 23 m) but an earlier hand-off to the mean far shadow.'),
}


def baseline_doc(variant):
    q = QUALITY[variant]
    g = GROUPS['clear']  # weathers without a file of their own fall back to the fair-weather sky
    low_v, high_v = wind_for(10)
    return {
        '_metadata': {
            'version': '0.1.0',
            'description': 'foxnne-nat3-clouds (%s): volumetric clouds on, vanilla cloud meshes hidden, march quality, '
                           'fair-weather fallback sky. UNTESTED DRAFT 2026-11-17. %s' % (variant, q['note']),
        },
        'enableVolumetricClouds': True,
        'enableVanillaClouds': False,
        'rayMarchRange': q['rayMarchRange'],
        'shadowVolumeRange': q['shadowVolumeRange'],
        'marchStepScale': q['marchStepScale'],
        'cloudBlurRadius': q['cloudBlurRadius'],
        'halfResApShadow': q['halfResApShadow'],
        'cloudMap': {
            'version': 3,
            'procedural': {'parameters': {
                'primary': {'range': [float(x) for x in g['primary']]},
                'secondary': {'range': [float(x) for x in g['secondary']]},
                'coverageGain': {'range': [-1.0, 1.0, float(g['gain']), float(g['gain'])]},
            }},
        },
        'cloudLayer': {
            'low': {
                'ndfAltitudeOffset': float(g['base']),
                'ndfAltitudeScale': float(g['span']),
                'densityScale': float(g['density']),
                'topExpansionScale': float(g['top']),
            },
            'middle': {'enabled': False},
            'cirrus': {
                'enabled': True,
                'altitude': float(g['cirrusAlt']),
                'densityScale': float(g['cirrus']),
                'weather': cirrus_state(g['cirrusCov']),
            },
            'lighting': {
                'brightness': float(g['bright']),
                'sunExtinction': float(g['sunExt']),
                'viewExtinction': float(g['viewExt']),
                'ambientStrength': float(g['ambient']),
            },
            'wind': {
                'lowVelocity': low_v,
                'highVelocity': high_v,
                'development': float(g['dev']),
                'disturbance': float(g['dist']),
            },
        },
    }


MANIFEST = {
    'name': 'foxnne NAT III clouds',
    'version': '0.1.0',
    'type': 'CS',
    'author': 'foxnne',
    'description': 'UNTESTED DRAFT. Per-weather volumetric cloud settings (Physical Sky) for NAT.CS III: coverage, '
                   'layer altitude, density, lighting, wind and cirrus per weather group; march quality in Baseline. '
                   'Read notes/how-it-works.md before applying: applying a pack with scene files makes it the active pack.',
    'tags': ['NAT.CS III', 'Physical Sky', 'volumetric clouds', 'draft'],
    'csVersion': '1.9.0',
    'requiredFeatures': ['PhysicalSky', 'SceneManager', 'SkySync'],
    'requiredPlugins': ['NAT-ENB.esp', 'NAT-CS.esp'],
}


# --------------------------------------------------------------------------------------------
def validate(tree, catalog, where):
    """Checks every scene leaf against the compiled catalog: exists, transitionable, in range, not blacklisted."""
    problems = []
    for path, key, value in leaves(tree):
        full = path + (key,)
        if any(full[:len(b)] == b for b in BLACKLIST):
            problems.append('%s: %s is blacklisted for scenes' % (where, '/'.join(full)))
            continue
        entry = catalog.get(('/'.join(path), key))
        if not entry:
            problems.append('%s: %s not in catalog' % (where, '/'.join(full)))
            continue
        if 'Trans' not in entry['flags']:
            problems.append('%s: %s is not transitionable' % (where, '/'.join(full)))
        if is_blend(value):
            if entry['vtype'] != 'Blend':
                problems.append('%s: %s is not a blend setting' % (where, '/'.join(full)))
            total = sum(s['weight'] for s in value['states'])
            if total > 1.00001:
                problems.append('%s: %s weights sum to %s' % (where, '/'.join(full), total))
            continue
        if not isinstance(value, float):
            problems.append('%s: %s is not a float' % (where, '/'.join(full)))
        if entry['bounds'] == 'true' and not (float(entry['mn']) <= value <= float(entry['mx'])):
            problems.append('%s: %s = %s outside %s..%s' % (where, '/'.join(full), value, entry['mn'], entry['mx']))
    return problems


def write_json(path, data, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        if compact:
            json.dump(data, f, separators=(',', ':'))
        else:
            json.dump(data, f, indent=2)
            f.write('\n')


def main():
    look_path = sys.argv[1]
    nat = json.load(open(os.path.join(HERE, 'nat-cs-weathers.json'), encoding='utf-8'))['weathers']
    dump = json.load(open(look_path, encoding='utf-8'))
    by_spid = {w['spid'].lower(): w for w in dump}
    catalog = {(e['path'], e['key']): e for e in json.load(open(os.path.join(HERE, 'physicalsky-scene-catalog.json'), encoding='utf-8'))}

    # Only ever remove what this script generates.
    for sub in (os.path.join(PACK_DIR, 'Weather'), os.path.join(PACK_DIR, 'Baseline')):
        if os.path.isdir(sub):
            shutil.rmtree(sub)

    rows = []
    problems = []
    missing = []
    user_fragment = {}
    file_count = 0
    for w in nat:
        rec = by_spid.get(w['spid'].lower())
        if rec is None:
            missing.append(w)
            continue
        spid = rec['spid']  # the game's own spelling of the key
        editor_id = rec['editorId'] or w['editorId']
        tags, group, aurora = classify(editor_id, rec)
        entries = []
        for period in PERIODS:
            tree = scene_values(group, rec.get('windSpeed', 0), aurora, period)
            problems += validate(tree, catalog, '%s/%s' % (editor_id, period))
            doc = {
                '_feature': 'PhysicalSky',
                '_metadata': {
                    'description': '%s - %s%s (%s) - %s' % (PACK, GROUPS[group]['label'], ' / aurora' if aurora else '', editor_id, period),
                    'timeOfDayEnabled': True,
                },
            }
            doc.update(tree)
            write_json(os.path.join(PACK_DIR, 'Weather', spid, period, '%s_PhysicalSky.json' % PACK), doc)
            file_count += 1
            for path, key, value in leaves(tree):
                entries.append({'feature': 'PhysicalSky', 'path': list(path), 'setting': key, 'value': value,
                                'originalValue': value, 'paused': False, 'period': period})
        user_fragment[spid] = {'entries': entries}
        rows.append(dict(spid=spid, editorId=editor_id, tags=sorted(tags, key=TAGS.index), group=group, aurora=aurora,
                         wind=rec.get('windSpeed', 0), low=LOW_CONFIDENCE.get(editor_id, '')))

    write_json(os.path.join(PACK_DIR, PACK + '.json'), MANIFEST)
    write_json(os.path.join(PACK_DIR, 'Baseline', 'PhysicalSky.json'), baseline_doc('quality'))
    for variant in QUALITY:
        write_json(os.path.join(DRAFT, 'baseline-variants', variant, 'PhysicalSky.json'), baseline_doc(variant))
    write_json(os.path.join(DRAFT, 'alt-user-overrides', 'SceneManager.weather.PhysicalSky.json'), user_fragment, compact=True)

    # ---- weather table
    tag_counts = collections.Counter(t for r in rows for t in r['tags'])
    group_counts = collections.Counter(r['group'] for r in rows)
    out = ['# NAT.CS III weather table (draft, untested)', '',
           'Generated by `draft/_generator/build_draft.py` on 2026-11-17. Do not edit by hand; edit `GROUPS` and re-run.', '',
           'Scope: the %d weather records that `NAT-CS.esp` overrides (masters Skyrim.esm, Dawnguard.esm, Dragonborn.esm, NAT-ENB.esp), '
           'all of them present in `LookWeathers.json`. The folder key is the record\'s origin plugin, which is why no key says NAT-CS.esp.' % len(rows), '',
           'Tags come from `look/webapp/weather_tags.py` `default_tags()` (editor id + record flags). A weather can carry two tags; '
           'the *group* is the single value set it received (priority storm > fog > rain > snow > overcast > cloudy > clear).', '',
           '## Counts', '', '| Tag | Weathers |', '|---|---|']
    for t in TAGS:
        out.append('| %s | %d |' % (t, tag_counts.get(t, 0)))
    out += ['', '(Tags overlap: %d weathers carry two tags.)' % sum(1 for r in rows if len(r['tags']) > 1), '',
            '| Group | Weathers | of which aurora (_A) |', '|---|---|---|']
    for gname in GROUP_ORDER:
        out.append('| %s | %d | %d |' % (gname, group_counts.get(gname, 0), sum(1 for r in rows if r['group'] == gname and r['aurora'])))
    out += ['', '## Values per group', '',
            'coverage = `cloudMap.procedural.parameters.primary.range` as inMin, inMax -> outMin, outMax; gain = `coverageGain.range` z = w; '
            'base/span = `cloudLayer.low.ndfAltitudeOffset/Scale` in metres; density = `low.densityScale`; '
            'sunExt/viewExt/bright/ambient = `cloudLayer.lighting.*`; cirrus = `cirrus.densityScale`.', '',
            '| Group | Meaning | primary coverage | secondary coverage | gain | base m | span m | density | top | sunExt | viewExt | bright | ambient | cirrus |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for gname in GROUP_ORDER:
        g = GROUPS[gname]
        out.append('| %s | %s | %s, %s -> %s, %s | %s, %s -> %s, %s | %s | %d | %d | %s | %s | %s | %s | %s | %s | %s |' % (
            (gname, g['label']) + tuple(g['primary']) + tuple(g['secondary']) +
            (g['gain'], g['base'], g['span'], g['density'], g['top'], g['sunExt'], g['viewExt'], g['bright'], g['ambient'], g['cirrus'])))
    out += ['', 'Aurora variants (`_A`): same group, but in Dawn, Dusk and Night the gain is multiplied by %s and cirrus density is 0.' % AURORA_GAIN_SCALE,
            'Wind: low velocity = 3 + 20 x (record wind / 255) m/s along +X (Y = 0.3 X), high = 8 + 30 x (wind / 255). Direction is a fixed guess.', '',
            '## Every weather', '',
            '| Editor ID | Form key (folder) | Tags | Group | Aurora | gain (day) | primary outMax | base-top m | density | sunExt | cirrus (day) | Wind | Note |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (GROUP_ORDER.index(r['group']), r['editorId'].lower(), r['spid'])):
        g = GROUPS[r['group']]
        out.append('| %s | `%s` | %s | %s | %s | %s | %s | %d-%d | %s | %s | %s | %s | %s |' % (
            r['editorId'], r['spid'], ', '.join(r['tags']), r['group'], 'yes' if r['aurora'] else '', g['gain'], g['primary'][3],
            g['base'], g['base'] + g['span'], g['density'], g['sunExt'], g['cirrus'], r['wind'], r['low']))
    low = [r for r in rows if r['low'] or r['group'] == 'special']
    out += ['', '## Could not classify with confidence (%d)' % len(low), '',
            'These still have files, so nothing is missing from the pack, but the group is a fallback rather than a judgement.', '',
            '| Editor ID | Form key | Group given | Why doubtful |', '|---|---|---|---|']
    for r in sorted(low, key=lambda r: (r['group'], r['editorId'].lower())):
        why = r['low'] or 'other realm, map or interior-style sky; its worldspace is not in the Physical Sky default whitelist, so the file probably never applies'
        out.append('| %s | `%s` | %s | %s |' % (r['editorId'], r['spid'], r['group'], why))
    if missing:
        out += ['', '## In NAT-CS.esp but absent from LookWeathers.json', ''] + ['- %s `%s`' % (m['editorId'], m['spid']) for m in missing]
    nat_keys = {r['spid'].lower() for r in rows}
    others = collections.Counter(w['spid'].split('~', 1)[1] for w in dump if w['spid'].lower() not in nat_keys)
    out += ['', '## Weathers in LookWeathers.json that are NOT covered (%d)' % sum(others.values()), '',
            'Not NAT.CS III records, so they get no file and use the Baseline fallback (the fair-weather `clear` values).', '',
            '| Plugin | Weathers | Remark |', '|---|---|---|']
    remarks = {
        'Helios.esp': 'Helios_* copies, all flagged pleasant with fog 300000; not classified',
        'Helios_NAT III.esp': 'Helios_* copies of the NAT weathers; not classified',
        'Skyrim.esm': 'FXWthr* interior light/window weathers, DefaultWeather, EditorCloudPreview, TESTCloudyRain, Solitude/Blue Palace fog',
        'A Clear Map of Skyrim.esp': 'world map weathers',
        'WEC - Core.esp': 'window emittance weathers',
        'Lux.esp': 'interior lighting weathers and a few exterior variants',
    }
    for plugin, n in others.most_common():
        out.append('| %s | %d | %s |' % (plugin, n, remarks.get(plugin, '')))
    os.makedirs(os.path.join(ROOT, 'notes'), exist_ok=True)
    with open(os.path.join(ROOT, 'notes', 'weather-table.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out) + '\n')

    print('weathers:', len(rows), 'scene files:', file_count, 'missing from dump:', len(missing))
    print('tags:', dict(tag_counts))
    print('groups:', dict(group_counts))
    print('validation problems:', len(problems))
    for p in sorted(set(problems))[:40]:
        print('  ', p)


if __name__ == '__main__':
    main()

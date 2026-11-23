"""Pass 5 generator: closed-sky weathers only (overcast, rain, storm, snow, fog). Clear / fair / partly / special weathers
get NO Weather folder, and the Baseline holds nothing but the lightning switch, so the saved fair-weather look is untouched.

NOTHING HERE WAS TESTED IN GAME as a pack. The validator below is an offline copy of the game's entry check.

    python -I build_pass5.py

Reads (read-only):
    build_pass2 / build_pass3 / build_pass4          imported: record facts, type rules, pass-4 values, validator (no main() run)
    scene-catalog-pass5.json                          scene catalogue + policy of the CURRENT main checkout (extract_catalog5.py)
    ../sweeps-storm/snow_realistic.json               the snow variants shot in game (harness "variant" format)
    ../sweeps-pass4/pass4_types_day.json              cross-check: the overcast variant the user approved
    ../foxnne-nat3-clouds-pass4/                      cross-check: pass-5 files of pass-4 weathers must equal the pass-4 files
    ../foxnne-nat3-clouds/ + ../../notes/weather-table.md   pass-1 draft + groups (how sky_apply.py composes a variant with "group")
    SettingsUser.json (live) + SAVED_CANDIDATES       only to decide which snow_sunny keys can be left out, and for the Baseline report
Writes (only under ..\\ and ..\\..\\notes; pass 1-4 files are not touched):
    ../foxnne-nat3-clouds-pass5/                      pack: manifest, Baseline/PhysicalSky.json, Weather/<formkey>/<Period>/<pack>_<Feature>.json
    ../alt-user-overrides-pass5/SceneManager.weather.pass5.json   same values as user-layer "weather" entries (route B)
    ../../notes/weather-table-5.md
"""
import collections
import copy
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script directory
import build_pass2 as p2  # noqa: E402
import build_pass3 as p3  # noqa: E402
import build_pass4 as p4  # noqa: E402
import wthr_parse  # noqa: E402

DRAFT = os.path.dirname(HERE)
ROOT = os.path.dirname(DRAFT)
PACK = 'foxnne-nat3-clouds-pass5'
PACK_DIR = os.path.join(DRAFT, PACK)
USER_DIR = os.path.join(DRAFT, 'alt-user-overrides-pass5')
PASS4_DIR = os.path.join(DRAFT, p4.PACK)
PASS1_DIR = os.path.join(DRAFT, 'foxnne-nat3-clouds')
CS_DIR = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders'
PERIODS = p4.PERIODS

# ############################################################################################################
# ##   TUNING TABLE (pass 5). Everything else is pass 4, imported unchanged.                                ##
# ############################################################################################################

# ---- (A) Which weathers get entries: the pass-4 TYPE (pass-2 rules). Everything else gets no Weather folder.
CLOSED_TYPES = ('overcast', 'rain', 'storm', 'snow', 'fog')
REVIEW = dict(overcast='approved by the user in game (sweeps-pass4/pass4_types_day.json)',
              fog='approved by the user in game (sweeps-pass4/pass4_types_day.json)',
              rain='pass 4 unchanged, NOT yet reviewed', storm='pass 4 unchanged, NOT yet reviewed')

# ---- (B) Snow. Variants of sweeps-storm/snow_realistic.json (Day values, shot at 13:00 on weather "Snow").
SNOW_VARIANTS = os.path.join(DRAFT, 'sweeps-storm', 'snow_realistic.json')
SNOW_LIGHT_GROUP = 'snow_light'           # pass-1 group (notes/weather-table.md): SnowClear, SnowClear_Alt
SNOW_LIGHT_VARIANT = 'snow_sunny'         # broken cumulus, cloud brightness 2.0, DALC 0, sky saturation 1.3, +0.7 EV
SNOW_DECK_VARIANT = 'snow_overcast_approved'  # every other snow-type weather: the pass-4 overcast deck + SNOW_DECK_EXTRAS, +1.0 EV
# the only keys the variant may add to the pass-4 Day sky of OVERCAST_SOURCE (values come from the variant; written in EVERY period).
# They are what the approved shot inherited from the saved file of that moment.
SNOW_DECK_EXTRAS = ('cloudLayer.lighting.brightness', 'cloudLayer.low.topExpansionScale', 'cloudLayer.wind.development',
                    'cloudLayer.wind.disturbance')
OVERCAST_SOURCE = 'OvercastPF'            # the pass-4 overcast weather whose values (all six periods) the snow decks take
ASH_STORMS_GET_EXPOSURE = False           # StormDLC2 / StormDLC2_ALT (pass-1 group snowstorm, but ash and pass-4 type overcast)

# ---- (C) Exposure (PostProcessing / Histogram Auto Exposure / settings / ExposureCompensation).
EC_SAVED = -3.5                           # the fair-look value the variants were raised from (see notes: the live file differs)
# share of the Day raise per period, the pass-4 "dalc" scheme: full while the sun is up, half-way at Dawn / Dusk, nothing at Night
# (None = no entry: the period falls through to the saved value; at night the code uses NightExposureCompensation anyway)
EC_PERIOD_SHARE = p4.P(0.5, 1.0, 1.0, 1.0, 0.5, None)

# ---- (D) Saved settings a snow_sunny key is compared with. A key is LEFT OUT only if every file holds the variant's value
# (or the pack Baseline does and no file overrides it). More than one file because the live file changed during the review.
SAVED_LIVE = CS_DIR + '/SettingsUser.json'
# The fair look. NOT the live file: the running game / harness rewrote the live SettingsUser.json twice during the review
# (12:34 with the snow deck test, 12:57 with snow_sunny). The live file is only compared with this one and a warning printed.
SAVED_CANDIDATES = [CS_DIR + '/SettingsUser.foxnne-baseline-20261122.json']

# ---- (E) Baseline: only what closed weathers need and a pack cannot set per weather.
BASELINE_LIGHTNING = {'weatherMode': p4.LIGHTNING_WEATHER_MODE, 'rate': 0.0}

# ############################################################################################################
# ##   END OF TUNING TABLE                                                                                  ##
# ############################################################################################################

FEATURES = ('PhysicalSky', 'ExponentialHeightFog', 'ImageBasedLighting', 'PostProcessing')
EC_PATH = ('Histogram Auto Exposure', 'settings')
EC_KEY = 'ExposureCompensation'


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ---- sky_apply.py, reproduced offline -----------------------------------------------------------------------
def harness_merge(dst, src):
    """sky_apply.py merge(): xyzw dicts write into saved arrays, dicts recurse, everything else replaces."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), list) and set(v) <= set('xyzw'):
            for a, i in zip('xyzw', range(4)):
                if a in v and i < len(dst[k]):
                    dst[k][i] = v[a]
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            harness_merge(dst[k], v)
        else:
            dst[k] = copy.deepcopy(v)


def pass1_groups():
    """notes/weather-table.md rows -> ({editorId: group}, {group: (editorId, formkey)}) with sky_apply.py's representative rule."""
    rows = [[c.strip() for c in line.strip('|\n').split('|')]
            for line in open(os.path.join(ROOT, 'notes', 'weather-table.md'), encoding='utf-8') if re.match(r'\| \w+ \| `0x', line)]
    rep, group = {}, {}
    for r in rows:
        group.setdefault(r[0], r[3])   # the first table is the group table; later tables repeat editor ids
        if r[3] not in rep or (r[0].endswith(('TU', 'PF')) and not rep[r[3]][0].endswith(('TU', 'PF'))):
            rep[r[3]] = (r[0], r[1].strip('`'))
    return group, rep


def compose(variant, saved_sky, rep):
    """Full effective PhysicalSky of a variant the way sky_apply.py builds it: saved settings (+ pass-1 Baseline + the
    pass-1 Day file of the group's representative, only if the variant names a group) + the variant's "set".
    saved_sky is the SettingsUser.json "Physical Sky" block, i.e. only the keys that differ from the code defaults."""
    s = copy.deepcopy(saved_sky)
    layers = []
    if variant.get('group'):
        layers.append(load(os.path.join(PASS1_DIR, 'Baseline', 'PhysicalSky.json')))
        layers.append(load(os.path.join(PASS1_DIR, 'Weather', rep[variant['group']][1], 'Day', 'foxnne-nat3-clouds_PhysicalSky.json')))
    layers.append(variant.get('set', {}))
    for layer in layers:
        harness_merge(s, {k: v for k, v in layer.items() if not k.startswith('_')})
    return s, layers


def flat_any(tree):
    """Dotted leaves; arrays and xyzw dicts both become .x/.y/.z/.w components; a blend object stays one value."""
    out = collections.OrderedDict()

    def walk(node, path):
        for k, v in node.items():
            if k.startswith('_'):
                continue
            if isinstance(v, list) and len(v) <= 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
                for a, x in zip('xyzw', v):
                    out['.'.join(path + (k, a))] = x
            elif isinstance(v, dict) and not p3.is_blend(v):
                walk(v, path + (k,))
            else:
                out['.'.join(path + (k,))] = v
    walk(tree, ())
    return out


def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return a == b
    return abs(a - b) <= 1e-4 * max(1.0, abs(a), abs(b))   # SettingsUser.json holds float32 values


def nest(flat_items):
    tree = collections.OrderedDict()
    for dotted, v in flat_items:
        node = tree
        parts = dotted.split('.')
        for p in parts[:-1]:
            node = node.setdefault(p, collections.OrderedDict())
        node[parts[-1]] = v
    return tree


def strip_meta(doc):
    return {k: v for k, v in doc.items() if not k.startswith('_')}


# ---- what blocks a setting -------------------------------------------------------------------------------------
class Policy:
    def __init__(self, cat):
        self.cat = cat
        self.rows = {(e['feature'], e['path'], e['key']): e for e in cat['rows']}
        self.blacklist = [tuple(b) for b in cat['policy']['kSettingBlacklist']]
        self.whitelist = {b[0] for b in cat['policy']['kTimeOfDayFeatureWhitelist'] if len(b) == 1}
        self.lines = cat['policyLines']
        self.file = cat['policyFile']

    def verdict(self, feature, dotted):
        """(drivable, reason). dotted = setting address below the feature, vector components included."""
        parts = dotted.split('.')
        full = (feature,) + tuple(p for p in parts if p != 'settings')
        if feature not in self.whitelist:
            return False, 'feature %s is not in kTimeOfDayFeatureWhitelist (%s:%d-%d)' % (
                feature, self.file, min(self.lines['kTimeOfDayFeatureWhitelist'].values()), max(self.lines['kTimeOfDayFeatureWhitelist'].values()))
        for b in self.blacklist:
            if full[:len(b)] == b:
                return False, 'blacklisted: kSettingBlacklist entry { %s } at %s:%d' % (
                    ', '.join('"%s"' % x for x in b), self.file, self.lines['kSettingBlacklist']['/'.join(b)])
        row = self.rows.get((feature, '/'.join(parts[:-1]), parts[-1]))
        if not row:
            return False, 'no row in the compiled scene catalogue'
        if 'Scene' not in row['flags']:
            return False, 'catalogue row is not SceneControllable (flags %s)' % row['flags']
        if 'Trans' not in row['flags'] or row['vtype'] not in ('Float', 'Blend'):
            return False, 'catalogue row is %s, flags %s: not Transitionable, and a weather scene only takes blendable floats ' \
                          '(src/CSEditor/SceneManager/SceneSettingsInternal.cpp, IsSceneSettingValueAllowed, requireNumeric)' % (row['vtype'], row['flags'])
        rng = '%s..%s' % (row['mn'], row['mx']) if row['bounds'] == 'true' else 'no bounds'
        return True, '%s, %s, %s' % (row['vtype'], row['flags'], rng)


# asked about in the pass-5 brief: (feature, dotted address)
ASKED = [('PostProcessing', 'Histogram Auto Exposure.settings.ExposureCompensation'),
         ('PhysicalSky', 'cloudLayer.lighting.brightness'),
         ('PhysicalSky', 'sunlightColor.x'), ('PhysicalSky', 'sunlightColor.y'), ('PhysicalSky', 'sunlightColor.z'),
         ('PhysicalSky', 'cloudMap.procedural.parameters.primary.range.x'), ('PhysicalSky', 'cloudMap.procedural.parameters.primary.range.y'),
         ('PhysicalSky', 'cloudMap.procedural.parameters.primary.range.z'), ('PhysicalSky', 'cloudMap.procedural.parameters.primary.range.w'),
         ('PhysicalSky', 'cloudMap.procedural.parameters.secondary.range.x'), ('PhysicalSky', 'cloudMap.procedural.parameters.secondary.range.y'),
         ('PhysicalSky', 'cloudMap.procedural.parameters.secondary.range.z'), ('PhysicalSky', 'cloudMap.procedural.parameters.secondary.range.w'),
         ('PhysicalSky', 'cloudLayer.low.densityScale'),
         ('PhysicalSky', 'cloudLayer.lighting.deckLight'), ('PhysicalSky', 'cloudLayer.lighting.deckGroundLight'),
         ('PhysicalSky', 'cloudLayer.lighting.deckHorizonLight'),
         ('ImageBasedLighting', 'DALCAmount'), ('ImageBasedLighting', 'SkyIBLSaturation')]


def ec_tree(day_value, period):
    share = EC_PERIOD_SHARE[period]
    if share is None or day_value is None:
        return None
    v = round(EC_SAVED + (day_value - EC_SAVED) * share, 3)
    return {EC_PATH[0]: {EC_PATH[1]: {EC_KEY: float(v)}}}


def baseline_doc():
    return {'_metadata': {'version': '0.5.0',
                          'description': PACK + ': ONLY the lightning switch closed weathers need: "any weather" (mode 0, an integer a '
                                         'weather entry cannot carry) with a global rate of 0; storm weathers carry their own rate. '
                                         'No cloud, haze or high-layer value: the saved fair-weather look is not touched.'},
            'lightning': dict(BASELINE_LIGHTNING)}


MANIFEST = {
    'name': 'foxnne NAT III clouds (pass 5, closed skies)',
    'version': '0.5.0',
    'type': 'CS',
    'author': 'foxnne',
    'description': 'DRAFT, pass 5, not tested in game as a pack. Per-weather, per-period sky ONLY for closed skies: overcast and fog '
                   '(pass-4 values, approved), rain and storm (pass-4 values, not reviewed), snow (the approved overcast deck + a day '
                   'exposure raise; SnowClear = bright broken cumulus). Clear, fair, partly cloudy and other-realm weathers have no '
                   'entries and the Baseline holds only the lightning switch. No Ground Fog entries. Read notes/install-pass-5.md first.',
    'tags': ['NAT.CS III', 'Physical Sky', 'volumetric clouds', 'draft'],
    'csVersion': '1.9.0',
    'requiredFeatures': ['PhysicalSky', 'ExponentialHeightFog', 'ImageBasedLighting', 'PostProcessing', 'SceneManager', 'SkySync'],
    'requiredPlugins': ['NAT-ENB.esp', 'NAT-CS.esp'],
}


def main():
    masters, recs = wthr_parse.load()
    cat = load(os.path.join(HERE, 'scene-catalog-pass5.json'))
    val = p3.Validator(cat)
    pol = Policy(cat)
    problems, notes = [], []
    group1, rep1 = pass1_groups()
    variants = {v['name']: v for v in load(SNOW_VARIANTS)}
    saved = [(path, load(path)) for path in SAVED_CANDIDATES]
    saved_flat = [flat_any(doc.get('Physical Sky', {})) for _, doc in saved]
    live_doc = load(SAVED_LIVE)
    live_diff = []
    for section in ('Physical Sky', 'Image Based Lighting'):
        a, b = flat_any(saved[0][1].get(section, {})), flat_any(live_doc.get(section, {}))
        live_diff += ['%s / %s' % (section, k) for k in sorted(set(a) | set(b))
                      if not (k in a and k in b and (same(a[k], b[k]) if not isinstance(a[k], (dict, list)) else a[k] == b[k]))]
    ec_of = lambda doc: doc.get('Post Processing', {}).get(EC_PATH[0], {}).get(EC_PATH[1], {}).get(EC_KEY)
    if ec_of(live_doc) != ec_of(saved[0][1]):
        live_diff.append('Post Processing / %s' % EC_KEY)
    if ec_of(saved[0][1]) is None or not same(ec_of(saved[0][1]), EC_SAVED):
        problems.append('EC_SAVED %g is not the saved base value %s' % (EC_SAVED, ec_of(saved[0][1])))

    for d in (os.path.join(PACK_DIR, 'Weather'), os.path.join(PACK_DIR, 'Baseline'), USER_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)

    # ---- classify (pass-4 rules) and find the overcast source
    rows = []
    for w in recs:
        f = p2.facts(w)
        wtype, sev = p2.classify(w['editorId'], f)
        s = p4.settings_for(wtype, sev, f, w['editorId'])
        s['sev'] = sev
        rows.append(dict(w=w, f=f, type=wtype, sev=sev, s=s, group1=group1.get(w['editorId'])))
    src = [r for r in rows if r['w']['editorId'] == OVERCAST_SOURCE]
    if len(src) != 1 or src[0]['type'] != 'overcast':
        raise SystemExit('overcast source %s not found as an overcast weather' % OVERCAST_SOURCE)
    src = src[0]

    # ---- the snow deck variant must BE the approved overcast variant (Day) + exposure
    deck_var, sunny_var = variants[SNOW_DECK_VARIANT], variants[SNOW_LIGHT_VARIANT]
    approved = [v for v in load(os.path.join(DRAFT, 'sweeps-pass4', 'pass4_types_day.json')) if v['weather'] == OVERCAST_SOURCE]
    day_src = json.loads(json.dumps(p4.sky_tree(src['s'], 'overcast', src['f']['aurora'], 'Day')))
    day_src['cloudLayer']['cirrus']['uvSize'] = p3.CIRRUS_UV_SIZE          # the two global-only keys every sweep variant carries
    day_src['lightning']['weatherMode'] = p4.LIGHTNING_WEATHER_MODE
    if len(approved) != 1 or approved[0]['set'] != day_src:
        problems.append('pass-4 Day sky of %s is not the approved sweep variant' % OVERCAST_SOURCE)
    base_flat, deck_flat = flat_any(day_src), flat_any(deck_var['set'])
    deck_extras = collections.OrderedDict((k, float(v)) for k, v in deck_flat.items() if k not in base_flat)
    if any(k not in deck_flat or deck_flat[k] != v for k, v in base_flat.items()) or set(deck_extras) != set(SNOW_DECK_EXTRAS):
        problems.append('variant %s is not the pass-4 Day sky of %s + exactly SNOW_DECK_EXTRAS (extra keys: %s)' % (
            SNOW_DECK_VARIANT, OVERCAST_SOURCE, sorted(deck_extras)))

    def with_extras(tree):
        tree = json.loads(json.dumps(tree), object_pairs_hook=collections.OrderedDict)
        for dotted, v in deck_extras.items():
            node = tree
            parts = dotted.split('.')
            for p in parts[:-1]:
                node = node.setdefault(p, collections.OrderedDict())
            node[parts[-1]] = v
        return tree

    def without_extras(tree):
        tree = json.loads(json.dumps(tree))
        for dotted in deck_extras:
            node = tree
            parts = dotted.split('.')
            for p in parts[:-1]:
                node = node[p]
            del node[parts[-1]]
        return tree
    for feature, tree in (('ExponentialHeightFog', p4.fog_tree(src['s'], 'Day')), ('ImageBasedLighting', p4.ibl_tree(src['s'], 'overcast', 'Day'))):
        if dict(tree) != deck_var['features'].get(feature):
            problems.append('pass-4 Day %s of %s differs from variant %s' % (feature, OVERCAST_SOURCE, SNOW_DECK_VARIANT))
    extra = sorted(set(deck_var['features']) - {'ExponentialHeightFog', 'ImageBasedLighting', 'PostProcessing'})
    if extra:
        problems.append('%s changes features the pack does not write: %s' % (SNOW_DECK_VARIANT, extra))
    ec_deck = deck_var['features']['PostProcessing'][EC_PATH[0]][EC_PATH[1]][EC_KEY]
    ec_sunny = sunny_var['features']['PostProcessing'][EC_PATH[0]][EC_PATH[1]][EC_KEY]

    # ---- snow_sunny: compose like sky_apply.py, then keep the keys that differ from Baseline + saved
    composed, layers = compose(sunny_var, saved[0][1].get('Physical Sky', {}), rep1)
    touched = collections.OrderedDict()
    for layer in layers:
        touched.update(flat_any({k: v for k, v in layer.items() if not k.startswith('_')}))
    effective = flat_any(composed)
    baseline_flat = flat_any(strip_meta(baseline_doc()))
    sunny_day, sunny_dropped, sunny_blocked = collections.OrderedDict(), [], []
    for dotted in touched:
        value = effective[dotted]
        ok, why = pol.verdict('PhysicalSky', dotted)
        if not ok:
            sunny_blocked.append((dotted, value, why))
            continue
        in_saved = [sf[dotted] for sf in saved_flat if dotted in sf]
        if len(in_saved) == len(saved_flat) and all(same(x, value) for x in in_saved):
            sunny_dropped.append((dotted, value, 'every saved file holds it'))
        elif not in_saved and dotted in baseline_flat and same(baseline_flat[dotted], value):
            sunny_dropped.append((dotted, value, 'pack Baseline holds it and no saved file overrides it'))
        else:
            sunny_day[dotted] = float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else value
    sunny_ibl = collections.OrderedDict((k, float(v)) for k, v in sunny_var['features']['ImageBasedLighting'].items())
    sunny_fog = float(sunny_var['features']['ExponentialHeightFog']['vanillaFogStrength'])
    extra = sorted(set(sunny_var['features']) - {'ExponentialHeightFog', 'ImageBasedLighting', 'PostProcessing'})
    if extra:
        problems.append('%s changes features the pack does not write: %s' % (SNOW_LIGHT_VARIANT, extra))

    def sunny_trees(r, period):
        """snow_sunny in one period. Derived from Day the way pass 4 derives a closed type's periods:
        cloud field + cloud lighting period-independent; haze x the 'closed' hazeX curve (relative to Day, by the weather's
        moisture); DALC = Day value while the sun is up, half-way to the pass-4 base at Dawn / Dusk, the base at Night; the other
        ambient values constant; height fog x the weather's own pass-4 period ratio."""
        s = r['s']
        hx = p4.curve('closed', 'hazeX', period, s['k']) / p4.curve('closed', 'hazeX', 'Day', s['k'])
        sky = collections.OrderedDict()
        for dotted, v in sunny_day.items():
            if dotted.startswith('aerosolScatter.'):
                v = round(v * hx, 4)
            elif dotted.startswith('aerosolAbsorption.'):
                v = round(v * hx, 5)
            sky[dotted] = v
        ibl = collections.OrderedDict(sunny_ibl)
        base = p4.BASE['dalc']
        day = sunny_ibl['DALCAmount']
        ibl['DALCAmount'] = float(round(base if period == 'Night' else (day + base) / 2.0 if period in ('Dawn', 'Dusk') else day, 3))
        own = p4.fog_tree(s, period)['vanillaFogStrength'] / p4.fog_tree(s, 'Day')['vanillaFogStrength']
        return collections.OrderedDict([('PhysicalSky', nest(sky.items())),
                                        ('ExponentialHeightFog', {'vanillaFogStrength': float(round(sunny_fog * own, 4))}),
                                        ('ImageBasedLighting', ibl),
                                        ('PostProcessing', ec_tree(ec_sunny, period))])

    def trees_for(r, period):
        n = r['type']
        if r['mode'] == 'sunny':
            return sunny_trees(r, period)
        if r['mode'] == 'deck':     # the approved overcast deck, all six periods of the overcast source
            s, n, aurora, ec = src['s'], 'overcast', src['f']['aurora'], ec_deck
        else:                       # pass 4, unchanged
            s, aurora = r['s'], r['f']['aurora']
            ec = ec_deck if (r['mode'] == 'ash' and ASH_STORMS_GET_EXPOSURE) else None
        sky = p4.sky_tree(s, n, aurora, period)
        if r['mode'] == 'deck':
            sky = with_extras(sky)
        return collections.OrderedDict([('PhysicalSky', sky),
                                        ('ExponentialHeightFog', p4.fog_tree(s, period)),
                                        ('ImageBasedLighting', p4.ibl_tree(s, n, period)),
                                        ('PostProcessing', ec_tree(ec, period))])

    LABEL = dict(sunny='variant %s' % SNOW_LIGHT_VARIANT, deck='variant %s (= pass-4 %s + 4 extras)' % (SNOW_DECK_VARIANT, OVERCAST_SOURCE),
                 ash='pass 4 unchanged (ash storm)', p4='pass 4 unchanged')
    files = collections.Counter()
    user_fragment = collections.OrderedDict()
    written = []
    for r in rows:
        n, e = r['type'], r['w']['editorId']
        if n not in CLOSED_TYPES:
            r['mode'] = None
            continue
        if r['group1'] == SNOW_LIGHT_GROUP:
            r['mode'] = 'sunny'
        elif n == 'snow':
            r['mode'] = 'deck'
        elif r['group1'] == 'snowstorm':
            r['mode'] = 'ash'
        else:
            r['mode'] = 'p4'
        if n == 'snow' and r['group1'] not in ('snow_light', 'snow', 'snowstorm'):
            problems.append('%s: pass-4 type snow but pass-1 group %s' % (e, r['group1']))
        if r['mode'] == 'sunny' and n != 'snow':
            problems.append('%s: pass-1 group snow_light but pass-4 type %s' % (e, n))
        if r['mode'] == 'ash' and 'DLC2' not in e:
            problems.append('%s: pass-1 group snowstorm, pass-4 type %s, and not an ash storm: decide what it gets' % (e, n))
        entries = []
        for period in PERIODS:
            where = '%s/%s' % (e, period)
            for feature, tree in trees_for(r, period).items():
                if tree is None:
                    continue
                problems += val.check(feature, tree, where)
                doc = collections.OrderedDict([
                    ('_feature', feature),
                    ('_metadata', {'description': '%s - %s (%s) - %s - %s' % (PACK, p4.T[n]['label'], e, LABEL[r['mode']], period),
                                   'timeOfDayEnabled': True})])
                doc.update(tree)
                path = os.path.join(PACK_DIR, 'Weather', r['w']['spid'], period, '%s_%s.json' % (PACK, feature))
                p3.write_json(path, doc)
                files[feature] += 1
                written.append((r, period, feature, tree))
                for path_, key, value in p3.leaves(tree):
                    entries.append({'feature': feature, 'path': list(path_), 'setting': key, 'value': value,
                                    'originalValue': value, 'paused': False, 'period': period})
        user_fragment[r['w']['spid']] = {'entries': entries}

    p3.write_json(os.path.join(PACK_DIR, PACK + '.json'), MANIFEST)
    p3.write_json(os.path.join(PACK_DIR, 'Baseline', 'PhysicalSky.json'), baseline_doc())
    p3.write_json(os.path.join(USER_DIR, 'SceneManager.weather.pass5.json'), user_fragment, compact=True)

    # ---- checks beyond the catalogue
    with_entries = [r for r in rows if r['mode']]
    # 1. no fair / special weather has a folder; every closed one has
    on_disk = set(os.listdir(os.path.join(PACK_DIR, 'Weather')))
    if on_disk != {r['w']['spid'] for r in with_entries}:
        problems.append('Weather folders on disk do not match the closed-weather list')
    for r in rows:
        if r['type'] not in CLOSED_TYPES and r['w']['spid'] in on_disk:
            problems.append('%s (%s) has a Weather folder' % (r['w']['editorId'], r['type']))
    # 2. no Ground Fog anywhere
    if any(feature == 'GroundFog' for _, _, feature, _ in written):
        problems.append('Ground Fog entries written')
    # 3. pass-4 weathers and snow decks: files identical to the pass-4 pack files on disk (same weather / the overcast source)
    identical = collections.Counter()
    for r, period, feature, tree in written:
        if feature == 'PostProcessing' or r['mode'] == 'sunny':
            continue
        spid = src['w']['spid'] if r['mode'] == 'deck' else r['w']['spid']
        old = os.path.join(PASS4_DIR, 'Weather', spid, period, '%s_%s.json' % (p4.PACK, feature))
        if not os.path.exists(old):
            problems.append('%s/%s: no pass-4 file to compare %s with' % (r['w']['editorId'], period, feature))
        elif strip_meta(load(old)) != (without_extras(tree) if r['mode'] == 'deck' and feature == 'PhysicalSky' else json.loads(json.dumps(tree))):
            problems.append('%s/%s: %s differs from the pass-4 pack file' % (r['w']['editorId'], period, feature))
        else:
            identical[r['mode']] += 1
    # 4. snow_sunny Day reproduces the variant: every touched key is emitted, held by Baseline / saved, or listed as blocked
    for r in with_entries:
        if r['mode'] != 'sunny':
            continue
        day = flat_any(trees_for(r, 'Day')['PhysicalSky'])
        for dotted in touched:
            ok = (dotted in day and same(day[dotted], effective[dotted]) if not isinstance(effective[dotted], dict)
                  else day.get(dotted) == effective[dotted])
            if not ok and dotted not in [d for d, _, _ in sunny_dropped + sunny_blocked]:
                problems.append('%s: Day does not reproduce %s for %s' % (r['w']['editorId'], SNOW_LIGHT_VARIANT, dotted))
    # 5. exposure: never at Night, Day equals the variant
    for r, period, feature, tree in written:
        if feature == 'PostProcessing':
            v = tree[EC_PATH[0]][EC_PATH[1]][EC_KEY]
            want = {'sunny': ec_sunny, 'deck': ec_deck, 'ash': ec_deck}[r['mode']]
            if period == 'Night' or (period == 'Day' and v != want) or not (min(EC_SAVED, want) <= v <= max(EC_SAVED, want)):
                problems.append('%s/%s: exposure entry %s' % (r['w']['editorId'], period, v))
    # 6. Baseline: every key must be one a weather entry cannot carry, or needed as the global value of one
    for dotted, v in baseline_flat.items():
        if not dotted.startswith('lightning.'):
            problems.append('Baseline holds %s' % dotted)

    asked = [(feature, dotted) + pol.verdict(feature, dotted) for feature, dotted in ASKED]
    write_table(rows, with_entries, files, cat, asked, sunny_day, sunny_dropped, sunny_blocked, saved, ec_deck, ec_sunny, src, sunny_trees)

    counts = collections.Counter(r['type'] for r in with_entries)
    modes = collections.Counter(r['mode'] for r in with_entries)
    print('weathers in the record set:', len(rows), '| with entries:', len(with_entries),
          '(%s)' % ', '.join('%s %d' % (n, counts[n]) for n in CLOSED_TYPES), '| without:', len(rows) - len(with_entries))
    print('by source:', ', '.join('%s %d' % (LABEL[m], modes[m]) for m in ('p4', 'ash', 'deck', 'sunny')))
    print('scene files:', ', '.join('%s %d' % kv for kv in files.items()), '= %d' % sum(files.values()))
    print('user-layer entries:', sum(len(v['entries']) for v in user_fragment.values()))
    print('distinct scene settings written:', len(val.used), dict(collections.Counter(k.split(' ')[0] for k in val.used)))
    print('files identical to the pass-4 pack file:', dict(identical))
    print('snow_sunny PhysicalSky keys: emitted %d, left out %d, blocked %d' % (len(sunny_day), len(sunny_dropped), len(sunny_blocked)))
    for dotted, value, why in sunny_dropped:
        print('   left out:', dotted, '=', value, '(%s)' % why)
    for dotted, value, why in sunny_blocked:
        print('   BLOCKED :', dotted, '=', value if not isinstance(value, dict) else '{...}', '(%s)' % why)
    print('asked settings:')
    for feature, dotted, ok, why in asked:
        print('   %-8s %s %s  (%s)' % ('drivable' if ok else 'BLOCKED', feature, dotted, why))
    print('exposure: saved reference %g, snow deck Day %g, snow_sunny Day %g; live file holds %s' % (
        EC_SAVED, ec_deck, ec_sunny, saved[0][1].get('Post Processing', {}).get(EC_PATH[0], {}).get(EC_PATH[1], {}).get(EC_KEY)))
    print('saved base:', saved[0][0])
    if live_diff:
        print('WARNING: the live SettingsUser.json differs from the saved base in %d keys (it is NOT the fair look right now): %s' % (
            len(live_diff), ', '.join(live_diff[:12]) + (' ...' if len(live_diff) > 12 else '')))
    else:
        print('live SettingsUser.json equals the saved base in Physical Sky, Image Based Lighting and ExposureCompensation')
    print('catalog:', cat['source'])
    print('validation problems:', len(problems))
    for p in sorted(set(problems))[:60]:
        print('  ', p)
    return 1 if problems else 0


def write_table(rows, with_entries, files, cat, asked, sunny_day, sunny_dropped, sunny_blocked, saved, ec_deck, ec_sunny, src, sunny_trees):
    g = lambda v: ('%g' % v) if isinstance(v, (int, float)) and not isinstance(v, bool) else json.dumps(v)
    out = ['# NAT.CS III weather table, pass 5 (closed skies only)', '',
           'Generated by `draft/_generator/build_pass5.py`. Do not edit by hand; edit its TUNING TABLE and re-run.',
           '**Not tested in game as a pack.** Overcast / fog and the snow variants were seen in game as harness sweeps only.', '',
           'Catalogue: %s.' % cat['source'], '',
           '## Which weathers get entries', '',
           '| Pass-4 type | Weathers | Entries | Values | Review state |', '|---|---|---|---|---|']
    counts = collections.Counter(r['type'] for r in rows)
    for n in p4.TYPE_ORDER:
        members = [r for r in rows if r['type'] == n]
        if n not in CLOSED_TYPES:
            out.append('| %s | %d | none (no Weather folder) | saved look | - |' % (n, counts[n]))
            continue
        modes = collections.Counter(r['mode'] for r in members)
        if n == 'snow':
            out.append('| snow | %d | yes | %d x `%s` (pass-4 `%s`, all six periods, + brightness 1.7, topExpansionScale 0.4, wind development 0.2, disturbance 0.15 in every period) + day exposure; %d x `%s` | '
                       'deck: approved by the user as shot (the four extras are what the shot inherited from the saved file of that moment); `%s`: as shot, other periods derived, not reviewed |' % (
                           counts[n], modes['deck'], SNOW_DECK_VARIANT, OVERCAST_SOURCE, modes['sunny'], SNOW_LIGHT_VARIANT, SNOW_LIGHT_VARIANT))
        else:
            out.append('| %s | %d | yes | pass 4, unchanged%s | %s |' % (
                n, counts[n], ' (incl. %d ash storms, no exposure raise)' % modes['ash'] if modes['ash'] else '', REVIEW[n]))
    out += ['', 'Features written: %s = %d scene files. No Ground Fog entries (user decision).' % (
        ', '.join('%s %d' % kv for kv in files.items()), sum(files.values())), '',
            '## Period scheme', '',
            '- Pass-4 weathers and snow decks: the pass-4 files of that weather / of `%s`, value for value in every period (snow decks: apart from the four added keys) '
            '(checked against `draft/%s/`). Pass 4 keeps the cloud field and deck light in every period, Night included; '
            'DALC is the type value at Sunrise / Day / Sunset, half-way to 0.5 at Dawn / Dusk, 0.5 at Night.' % (OVERCAST_SOURCE, p4.PACK),
            '- Exposure (`ExposureCompensation`, reference %g): Day value of the variant at Sunrise / Day / Sunset, half of the raise at Dawn / Dusk, '
            '**no entry at Night** (falls through to the saved value). Snow deck Day %g, `%s` Day %g.' % (EC_SAVED, ec_deck, SNOW_LIGHT_VARIANT, ec_sunny),
            '- `%s` (not a closed deck; same scheme applied): cloud field, cloud lighting (brightness 2.0 included) and sky / env saturation constant; '
            'haze x the pass-4 `closed` hazeX curve relative to Day; DALC 0 at Sunrise / Day / Sunset, 0.25 at Dawn / Dusk, 0.5 at Night; '
            'height fog 0.1 x the weather\'s own pass-4 period ratio.' % SNOW_LIGHT_VARIANT, '',
            '| Weather | Period | haze x Day | aerosolScatter.x | DALC | skySat | fog strength | ExposureCompensation |', '|---|---|---|---|---|---|---|---|']
    for r in with_entries:
        if r['mode'] != 'sunny':
            continue
        for period in PERIODS:
            t = sunny_trees(r, period)
            hx = p4.curve('closed', 'hazeX', period, r['s']['k'])
            pp = t['PostProcessing']
            out.append('| %s | %s | %g | %s | %g | %g | %g | %s |' % (
                r['w']['editorId'] if period == 'Dawn' else '', period, round(hx, 4),
                g(flat_any(t['PhysicalSky']).get('aerosolScatter.x', '-')), t['ImageBasedLighting']['DALCAmount'],
                t['ImageBasedLighting']['SkyIBLSaturation'], t['ExponentialHeightFog']['vanillaFogStrength'],
                '-' if pp is None else g(pp[EC_PATH[0]][EC_PATH[1]][EC_KEY])))
    out += ['', '## `%s`: composed like `sky_apply.py`, then reduced' % SNOW_LIGHT_VARIANT, '',
            'The variant names no `group`, so its effective sky = saved settings + its `set`. Compared with: %s. '
            'A key is left out only if EVERY one of these files holds the variant value, or the pack Baseline does.' % ', '.join(
                '`%s`' % os.path.basename(p) for p, _ in saved), '',
            'Emitted (%d keys, Day): %s.' % (len(sunny_day), ', '.join('`%s` %s' % (k, g(v) if not isinstance(v, dict) else '(blend)') for k, v in sunny_day.items())), '',
            '| Left out / blocked | Value | Why |', '|---|---|---|']
    for dotted, value, why in sunny_dropped:
        out.append('| `%s` | %s | left out: %s |' % (dotted, g(value), why))
    for dotted, value, why in sunny_blocked:
        out.append('| `%s` | %s | **cannot be driven**: %s |' % (dotted, g(value), why))
    out += ['', '## Settings asked about: can a weather entry of a pack drive them?', '',
            '| Feature | Setting | Verdict | Catalogue row / blocking line |', '|---|---|---|---|']
    for feature, dotted, ok, why in asked:
        out.append('| %s | `%s` | %s | %s |' % (feature, dotted, 'drivable' if ok else '**NOT drivable**', why))
    out += ['', '## Pass-4 Baseline keys versus the saved settings (why pass 5 drops them)', '',
            'Baseline sits under the user layer (`src/BaselineManager.h`: "The user\'s own edits sit above this layer"): a Baseline key changes the '
            'fair-weather look whenever `SettingsUser.json` does not hold that key and the value is not the code default.', '',
            '| Pass-4 Baseline key | Value | Saved base | In pass 5 |', '|---|---|---|---|']
    live = flat_any(saved[0][1].get('Physical Sky', {}))
    keep = flat_any(strip_meta(baseline_doc()))
    for dotted, v in flat_any(strip_meta(p4.baseline_doc())).items():
        if dotted in live:
            state = 'holds %s: user value wins, Baseline key has no effect%s' % (g(live[dotted]), '' if same(live[dotted], v) else ' (and differs)')
        else:
            state = 'not held: the Baseline value would apply in EVERY weather without its own entry'
        out.append('| `%s` | %s | %s | %s |' % (dotted, g(v) if not isinstance(v, dict) else '(sparse-streak blend)', state,
                                               'kept' if dotted in keep else 'dropped'))
    out += ['', '## Every weather', '',
            '| Editor ID | Form key | Pass-4 type | Sev | Pass-1 group | Pass 5 | slab m | dens | deck light | DALC Day | fog Day / Night | Exposure Day | lightning |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    label = dict(sunny='`%s`' % SNOW_LIGHT_VARIANT, deck='`%s` (= %s + brightness 1.7, topExpansionScale 0.4, wind development 0.2 / disturbance 0.15)' % (SNOW_DECK_VARIANT, OVERCAST_SOURCE), ash='pass 4 (ash storm)', p4='pass 4')
    for r in sorted(rows, key=lambda r: (p4.TYPE_ORDER.index(r['type']), r['sev'], r['w']['editorId'].lower(), r['w']['spid'])):
        if not r['mode']:
            out.append('| %s | `%s` | %s | %.2f | %s | no entries | | | | | | | |' % (r['w']['editorId'], r['w']['spid'], r['type'], r['sev'], r['group1']))
            continue
        if r['mode'] == 'sunny':
            t = sunny_trees(r, 'Day')
            sky = flat_any(t['PhysicalSky'])
            night = sunny_trees(r, 'Night')['ExponentialHeightFog']['vanillaFogStrength']
            sv = lambda key: g(sky[key]) if key in sky else 'saved'
            cells = ('%s + %s' % (sv('cloudLayer.low.ndfAltitudeOffset'), sv('cloudLayer.low.ndfAltitudeScale')), sv('cloudLayer.low.densityScale'),
                     sv('cloudLayer.lighting.deckLight'), g(t['ImageBasedLighting']['DALCAmount']),
                     '%g / %g' % (t['ExponentialHeightFog']['vanillaFogStrength'], night), g(ec_sunny), 'rate 0 (Baseline)')
        else:
            s, n = (src['s'], 'overcast') if r['mode'] == 'deck' else (r['s'], r['type'])
            a = p4.air(n, s, 'Day')
            ec = ec_deck if r['mode'] == 'deck' or (r['mode'] == 'ash' and ASH_STORMS_GET_EXPOSURE) else None
            cells = ('%d + %d' % (s['base'], s['thick']), g(s['dens']), g(s['deckLight']), g(a['dalc']), '%g / %g' % (s['fogDay'], s['fogNight']),
                     '-' if ec is None else g(ec),
                     'rate 0' if s['ltI'] is None else '%g, %g/min, [%g, %g] km' % (s['ltI'], s['ltRate'], s['ltNear'], s['ltFar']))
        out.append('| %s | `%s` | %s | %.2f | %s | %s | %s |' % (r['w']['editorId'], r['w']['spid'], r['type'], r['sev'], r['group1'], label[r['mode']], ' | '.join(cells)))
    with open(os.path.join(ROOT, 'notes', 'weather-table-5.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    sys.exit(main())

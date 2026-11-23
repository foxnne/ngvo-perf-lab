"""Pass 3 generator: per-weather Physical Sky + Exponential Height Fog + Image Based Lighting scene files for the
111 NAT.CS III weathers, re-anchored on the in-game findings of 2026-11-18/19.

UNTESTED IN GAME as a whole. The anchors (ANCHORS below) were seen in game through the test harness; the scene files
themselves have never been loaded by the game, and every value between or beyond the anchors is a guess.

    python -I build_pass3.py            writes everything listed below
    python -I build_pass3.py --sim      also writes pass3-sim-variants.json (input for cloud-storms/ndf_sim.py)

Reads (read-only):
    NAT-CS.esp + masters (through wthr_parse.py)    the weather records
    scene-catalog-pass3.json                         compiled scene catalog rows + scene policy (extract_catalog3.py)
    build_pass2.py                                   imported for the record facts and the type/severity rules (unchanged)
Writes (only under ..\\ and ..\\..\\notes):
    ..\\foxnne-nat3-clouds-pass3\\                   pack: manifest, Baseline, Weather/<formkey>/<Period>/<pack>_<Feature>.json
    ..\\alt-user-overrides-pass3\\                   same values as SceneManager.json "weather" entries (route B)
    ..\\optional-groundfog-pass3\\                   OPTIONAL, separate: Ground Fog proposals (refused by the current build)
    ..\\pass3-sky-types.json                         per sky type: definition, members, representative + its settings
    ..\\..\\notes\\weather-table-3.md
Pass 2 files are not touched (nat-cs-wthr-records.json is not rewritten either).
"""
import collections
import copy
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script directory
import build_pass2 as p2  # noqa: E402  (record facts + classification; its main() is not run)
import wthr_parse  # noqa: E402

DRAFT = os.path.dirname(HERE)
ROOT = os.path.dirname(DRAFT)
PACK = 'foxnne-nat3-clouds-pass3'
PACK_DIR = os.path.join(DRAFT, PACK)
GROUNDFOG_DIR = os.path.join(DRAFT, 'optional-groundfog-pass3')
PERIODS = ['Dawn', 'Sunrise', 'Day', 'Sunset', 'Dusk', 'Night']
DARK_PERIODS = {'Dawn', 'Dusk', 'Night'}
TWILIGHT_PERIODS = {'Dawn', 'Sunrise', 'Sunset', 'Dusk'}

# --------------------------------------------------------------------------------------------
# ANCHORS: what was seen in game on 2026-11-18/19 (test harness, feature API; not scene files).
ANCHORS = {
    'globalBase': 'Saved in game: haze Continental loading 0.2 (aerosolScatter [2.522, 3.419, 4.575], aerosolAbsorption '
                  '[0.1327, 0.1466, 0.1604]); height fog vanillaFogStrength 0.1 (0.4 / 0.3 washed out the Whiterun plain); '
                  'low layer 1200 + 900 m, ndfScale [24.66, 16.7], primary.range [0.1, 0.65, 0, 0.65], cirrus densityScale 0.3.',
    'haze': 'Heavy haze hides all cloud structure: storm at 2.4x the old base (loading 0.95) = featureless grey wall at midday; '
            'at 0.45x of that (loading 0.38 = 1.9x the new base) readable at dusk, still murky at midday. '
            'Ceilings used here, as multiples of the new base: overcast 1.5, rain 1.8, storm 1.6, snow 2.0, fog 3.0.',
    'heightFog': 'Fog type at pass-2 values (FogPF strength 0.153, half-opacity ~260 m, haze loading 1.02) = near white-out at 13:00.',
    'modeling': 'The modeling layer decides how much of the slab is filled; default [-0.5, 0.6, 0, 0.5] exponent 1.6 keeps every '
                'cloud in the lowest 10-40 % of its slab. Pass 2 never set it.',
    'storm': 'Liked at dusk: sweeps/storm_towers.json 04_as03_low_wide_bases (primary [0, 0.5, 0, 0.95] exp 1, secondary '
             '[0.2, 0.8, 0, 0], modeling [-0.5, 0.5, 0.35, 1.0] exp 1, heightVariation [0.15, 0.75, 0.14, 0] exp 1, bottomTypeRange '
             '[-0.4, 0.5, 0, 0.1], 800 + 2600 m, density 1.0, bottomSpread 1.0 / 0.2, sunExtinction 1.6, viewExtinction 1.2, msAlbedo '
             '0.992, ambientStrength 0.7) and 06_as04_more_cloud_narrow_gaps (same, primary.range.x -0.25).',
    'rain': 'Liked at 17:30, fairly uniform at 13:00: sweeps/rain_structure.json 13_as12_dark_lighting (primary [-0.3, 0.45, 0, 0.9] '
            'exp 1, secondary [-0.3, 0.8, 0, 0.45], modeling [-0.5, 0.5, 0.2, 0.8] exp 1, 800 + 1700 m, density 0.9, sunExtinction 1.3, '
            'viewExtinction 1.1, msAlbedo 0.995, ambientStrength 0.8; heightVariation and bottomSpread at their defaults). '
            'AVOID (wavy streaks at low sun): 14_as13_low_wide_bases (heightVariation [0.15, 0.75, 0.10, 0] + bottomSpread 1.0 / 0.25) '
            'and 15 (the same with a coverage floor of 0.25).',
    'fair': 'Liked: sweeps/small_fragments.json 07 (primary.range [0.25, 0.5, 0, 0.65], secondary off [-0.2, 0.8, 0, 0]): fewer, '
            'bolder, well-shaped cumulus with clean sky between.',
    'overcast': 'Pass-2 overcast was too open (blue gaps).',
    'cirrus': 'Popcorn = the dense-cell pattern channel. Tested looks (sweeps/high_cloud.json): 06 sparse streaks, 05 large streaky '
              'sheets (0.5 glared near the sun at midday), 08 thin veil. All with uvSize 3.',
    'lightning': 'Whole-screen white flashes came from strikes as close as 0.35 km lighting thick fog near the camera.',
    'ambient': 'Under a dark storm sky snow and terrain stayed brightly lit: part of the fill is the game weather ambient '
               '(ImageBasedLighting DALCAmount, Baseline 0.5). 0.25 was used in the liked storm and rain frames.',
    'rayleigh': 'Rayleigh x2 = golden sunset at 17:30 but a pale midday sky.',
    'terrain': 'Whiterun plain ~155 m, Ilinalta ~215 m, peaks ~770 m (scaled metres above the map floor).',
    'drift': 'Pass-2 drift up to 15.6 / 31.2 m/s was never judged; capped at 9 m/s (low layer) here.',
}

BASE_LOADING = 0.2            # saved global haze (Continental, RH 50)
BASE_FOG_STRENGTH = 0.1       # Presets/foxnne-look/Baseline/ExponentialHeightFog.json
BASE_DALC = 0.5               # Presets/foxnne-look/Baseline/ImageBasedLighting.json
RAYLEIGH = (6.6049, 12.345, 29.413)        # PhysicalSky.h defaults (not overridden in SettingsUser.json)
RAYLEIGH_AP1 = (6.9344, 12.0203, 28.91)
RAYLEIGH_TWILIGHT = 2.0
FOG_COMPRESS = 0.5
FOG_MIN_STRENGTH = 0.004
LOW_DRIFT_CAP = 9.0

# --------------------------------------------------------------------------------------------
# High ("cirrus") layer looks. A look = one CirrusWeatherState (layers[0] coverage, layers[1] type) + altitude.
# Type layer noise 4 is not a noise slot (CirrusGenerate.cs.hlsl has cases 0..3): the value is the constant range.z.


def cirrus_state(cov, typ):
    return {'states': [{'weight': 1.0, 'value': {
        'layers': [{'noise': 1, 'frequency': 1.0, 'offset': [0.0, 0.0], 'range': [float(x) for x in cov]},
                   {'noise': 4, 'frequency': 1.0, 'offset': [0.0, 0.0], 'range': [float(x) for x in typ]}],
        'localMap': '', 'localWeight': 0.0, 'localWindScale': 1.0, 'localBlendMode': 0}}]}


CIRRUS_LOOKS = {
    'sparse': dict(label='sparse streaks (high_cloud 06)', altitude=9000.0, state=cirrus_state([-0.6, 0.5, 0.0, 0.75], [-1, 1, 0, 0])),
    'sheets': dict(label='large streaky sheets (high_cloud 05)', altitude=8000.0, state=cirrus_state([-0.9, 0.3, 0.25, 0.8], [-1, 1, 0, 0])),
    'veil': dict(label='thin veil (high_cloud 08)', altitude=8000.0, state=cirrus_state([-1.0, 0.0, 0.45, 0.9], [-1, 1, 0.25, 0.25])),
}
CIRRUS_UV_SIZE = 3.0   # global only (scene blacklist): Baseline

# --------------------------------------------------------------------------------------------
# Sky types. Each type is a list of (severity, values) points; a weather's values are interpolated linearly between
# the points by its severity (clamped at the ends). Missing keys come from D (= saved base / code defaults).
#   pri / priExp : cloudMap.procedural.parameters.primary.range [inMin, inMax, outMin, outMax] / .exponent
#   sec          : secondary.range (outMax 0 = small-fragment layer off)
#   mod / modExp : modeling.range / .exponent  (top type = how much of the slab a cloud fills)
#   hv / hvExp   : heightVariation.range / .exponent
#   btr          : bottomTypeRange
#   base / thick : cloudLayer.low.ndfAltitudeOffset / ndfAltitudeScale (m above the map floor)
#   dens         : cloudLayer.low.densityScale
#   spread / spreadH : cloudLayer.low.bottomSpreadScale / bottomSpreadHeight
#   sunExt / viewExt / msAlb / amb : cloudLayer.lighting.sunExtinction / viewExtinction / msAlbedo / ambientStrength
#   cirrus       : cloudLayer.cirrus.densityScale
#   dalc         : ImageBasedLighting.DALCAmount by day (None = no file, Baseline 0.5 applies)
#   ltI / ltRate : lightningIntensity / lightning.rate (storm only)
D = dict(pri=[0.1, 0.65, 0.0, 0.65], priExp=1.4, sec=[-0.2, 0.8, 0.0, 0.4],
         mod=[-0.5, 0.6, 0.0, 0.5], modExp=1.6, hv=[0.0, 1.0, 0.0, 0.02], hvExp=1.0, btr=[-0.4, 0.5, 0.0, 0.25],
         base=1200.0, thick=900.0, dens=0.75, spread=round((1 - 0.39) / 0.75, 4), spreadH=0.30,
         sunExt=1.0, viewExt=1.0, msAlb=0.999, amb=1.0, cirrus=0.0)
SEC_OFF = [-0.2, 0.8, 0.0, 0.0]


def pt(**kw):
    v = copy.deepcopy(D)
    v.update(kw)
    return v


T = collections.OrderedDict()
T['clear'] = dict(
    label='Clear',
    why='The liked fair-weather cut-off with a higher threshold: a few bold cumulus, small-fragment layer off; sparse high streaks.',
    points=[(0.0, pt(pri=[0.40, 0.65, 0.0, 0.65], sec=SEC_OFF, base=1400.0, thick=600.0, dens=0.60, cirrus=0.4))],
    cirrusLook='sparse', haze=(1.0, 1.0), fog=(1500, 1000), dalc=None, rayleigh=True)
T['fair'] = dict(
    label='Fair-weather cumulus',
    why='Lightest member = the liked small_fragments 07 look exactly; heavier members lower the threshold a little. Sparse high streaks.',
    points=[(0.0, pt(pri=[0.25, 0.50, 0.0, 0.65], sec=SEC_OFF, base=1300.0, thick=700.0, dens=0.70, cirrus=0.4)),
            (1.0, pt(pri=[0.19, 0.44, 0.0, 0.65], sec=SEC_OFF, base=1300.0, thick=700.0, dens=0.70, cirrus=0.4))],
    cirrusLook='sparse', haze=(1.0, 1.0), fog=(1500, 1000), dalc=None, rayleigh=True)
T['partly'] = dict(
    label='Partly cloudy',
    why='Same sharp cut-off as fair with a lower threshold (consistent cloud shapes), on the saved 1200 + 900 slab; '
        'large streaky high sheets, thinner by day (glare).',
    points=[(0.10, pt(pri=[0.14, 0.42, 0.0, 0.65], sec=SEC_OFF, base=1200.0, thick=900.0, dens=0.75, cirrus=0.5)),
            (0.52, pt(pri=[0.05, 0.35, 0.0, 0.68], sec=SEC_OFF, base=1200.0, thick=900.0, dens=0.75, cirrus=0.5)),
            (0.90, pt(pri=[-0.08, 0.25, 0.0, 0.70], sec=SEC_OFF, base=1100.0, thick=1000.0, dens=0.75, cirrus=0.5))],
    cirrusLook='sheets', cirrusPeriodScale={'Day': 0.6, 'Night': 0.6}, haze=(1.0, 1.15), fog=(1500, 1000), dalc=None, rayleigh=True)
T['overcast'] = dict(
    label='Overcast',
    why='Closed deck: coverage reaches solid over most of the field (low input range, secondary layer filling the gaps, floor <= 0.12), '
        'modeling layer fills 25-75 % of the slab so thickness varies (light and dark underside). Rain-13 style defaults for '
        'heightVariation / bottomSpread (no low wide bases). Thin veil above the lightest members only.',
    points=[(0.30, pt(pri=[-0.50, 0.35, 0.0, 0.88], priExp=1.0, sec=[-0.45, 0.6, 0.0, 0.50], mod=[-0.5, 0.5, 0.20, 0.65], modExp=1.0,
                      btr=[-0.4, 0.5, 0.0, 0.45], base=1000.0, thick=900.0, dens=0.75, sunExt=1.1, viewExt=1.0, msAlb=0.998, amb=0.95,
                      cirrus=0.15, dalc=0.35)),
            (0.50, pt(pri=[-0.60, 0.32, 0.04, 0.90], priExp=1.0, sec=[-0.5, 0.55, 0.0, 0.55], mod=[-0.5, 0.5, 0.22, 0.70], modExp=1.0,
                      btr=[-0.4, 0.5, 0.0, 0.45], base=970.0, thick=950.0, dens=0.78, sunExt=1.15, viewExt=1.05, msAlb=0.9975, amb=0.92,
                      cirrus=0.0, dalc=0.32)),
            (0.67, pt(pri=[-0.70, 0.30, 0.08, 0.92], priExp=1.0, sec=[-0.55, 0.5, 0.0, 0.60], mod=[-0.5, 0.5, 0.25, 0.75], modExp=1.0,
                      btr=[-0.4, 0.5, 0.0, 0.45], base=950.0, thick=1000.0, dens=0.80, sunExt=1.2, viewExt=1.05, msAlb=0.997, amb=0.9,
                      cirrus=0.0, dalc=0.30)),
            (0.90, pt(pri=[-0.80, 0.22, 0.12, 0.95], priExp=1.0, sec=[-0.6, 0.45, 0.0, 0.65], mod=[-0.5, 0.5, 0.30, 0.80], modExp=1.0,
                      btr=[-0.4, 0.5, 0.0, 0.45], base=900.0, thick=1100.0, dens=0.85, sunExt=1.3, viewExt=1.1, msAlb=0.996, amb=0.85,
                      cirrus=0.0, dalc=0.25))],
    cirrusLook='veil', haze=(1.1, 1.5), fog=(1800, 900), rayleigh=False)
T['rain'] = dict(
    label='Rain',
    why='Dark rain (RainPF) = the liked rain_structure 13 exactly, with a little more top-type spread in the Day period only '
        '(uniform at 13:00). Showers (bright-sun rain records) = a broken field with sunlit breaks under a thin veil.',
    points=[(0.25, pt(pri=[-0.05, 0.50, 0.0, 0.85], priExp=1.0, sec=[-0.2, 0.8, 0.0, 0.30], mod=[-0.5, 0.5, 0.20, 0.80], modExp=1.0,
                      base=900.0, thick=1400.0, dens=0.80, sunExt=1.15, viewExt=1.05, msAlb=0.997, amb=0.9, cirrus=0.15, dalc=0.35)),
            (0.50, pt(pri=[-0.18, 0.47, 0.0, 0.88], priExp=1.0, sec=[-0.25, 0.8, 0.0, 0.38], mod=[-0.5, 0.5, 0.20, 0.80], modExp=1.0,
                      base=850.0, thick=1550.0, dens=0.85, sunExt=1.22, viewExt=1.08, msAlb=0.996, amb=0.85, cirrus=0.0, dalc=0.30)),
            (0.76, pt(pri=[-0.30, 0.45, 0.0, 0.90], priExp=1.0, sec=[-0.3, 0.8, 0.0, 0.45], mod=[-0.5, 0.5, 0.20, 0.80], modExp=1.0,
                      base=800.0, thick=1700.0, dens=0.90, sunExt=1.3, viewExt=1.1, msAlb=0.995, amb=0.8, cirrus=0.0, dalc=0.25))],
    dayMod=[-0.5, 0.5, 0.12, 0.90],   # Day period only, scaled in by severity (see sky_tree)
    cirrusLook='veil', haze=(1.2, 1.8), fog=(1500, 800), rayleigh=False)
T['storm'] = dict(
    label='Thunderstorm',
    why='Lightest members = the liked storm_towers 04 (separate dark towers, low wide bases); StormPF and heavier = 06 '
        '(same with narrow gaps). Haze near the base value so the towers stay readable; own lightning, kept away from the camera.',
    points=[(0.41, pt(pri=[0.0, 0.5, 0.0, 0.95], priExp=1.0, sec=[0.2, 0.8, 0.0, 0.0], mod=[-0.5, 0.5, 0.35, 1.0], modExp=1.0,
                      hv=[0.15, 0.75, 0.14, 0.0], btr=[-0.4, 0.5, 0.0, 0.1], base=800.0, thick=2600.0, dens=1.0, spread=1.0, spreadH=0.2,
                      sunExt=1.6, viewExt=1.2, msAlb=0.992, amb=0.7, cirrus=0.0, dalc=0.25, ltI=0.15, ltRate=6.0)),
            (0.696, pt(pri=[-0.25, 0.5, 0.0, 0.95], priExp=1.0, sec=[0.2, 0.8, 0.0, 0.0], mod=[-0.5, 0.5, 0.35, 1.0], modExp=1.0,
                       hv=[0.15, 0.75, 0.14, 0.0], btr=[-0.4, 0.5, 0.0, 0.1], base=800.0, thick=2600.0, dens=1.0, spread=1.0, spreadH=0.2,
                       sunExt=1.6, viewExt=1.2, msAlb=0.992, amb=0.7, cirrus=0.0, dalc=0.25, ltI=0.22, ltRate=10.0)),
            (0.75, pt(pri=[-0.25, 0.5, 0.0, 0.95], priExp=1.0, sec=[0.2, 0.8, 0.0, 0.0], mod=[-0.5, 0.5, 0.35, 1.0], modExp=1.0,
                      hv=[0.15, 0.75, 0.14, 0.0], btr=[-0.4, 0.5, 0.0, 0.1], base=800.0, thick=2600.0, dens=1.0, spread=1.0, spreadH=0.2,
                      sunExt=1.6, viewExt=1.2, msAlb=0.992, amb=0.7, cirrus=0.0, dalc=0.25, ltI=0.25, ltRate=12.0))],
    lightningDistanceKm=[2.5, 9.0],
    cirrusLook='veil', haze=(1.0, 1.5), fog=(1000, 600), rayleigh=False)
T['snow'] = dict(
    label='Snow',
    why='Light snow = thin broken cloud under a veil; steady snow = a closed, bright deck (overcast shapes, lighter lighting); '
        'blizzard = a deeper deck with its base at 800 m (peaks in cloud is right for a snowstorm).',
    points=[(0.10, pt(pri=[0.0, 0.45, 0.0, 0.75], priExp=1.0, sec=[-0.2, 0.8, 0.0, 0.25], mod=[-0.5, 0.5, 0.15, 0.60], modExp=1.0,
                      base=1000.0, thick=900.0, dens=0.65, cirrus=0.15, dalc=0.40)),
            (0.25, pt(pri=[-0.15, 0.40, 0.0, 0.80], priExp=1.0, sec=[-0.3, 0.7, 0.0, 0.35], mod=[-0.5, 0.5, 0.18, 0.62], modExp=1.0,
                      base=970.0, thick=1000.0, dens=0.70, sunExt=1.05, msAlb=0.9985, amb=0.97, cirrus=0.10, dalc=0.38)),
            (0.53, pt(pri=[-0.55, 0.28, 0.04, 0.90], priExp=1.0, sec=[-0.5, 0.55, 0.0, 0.55], mod=[-0.5, 0.5, 0.22, 0.70], modExp=1.0,
                      base=900.0, thick=1200.0, dens=0.75, sunExt=1.1, viewExt=1.0, msAlb=0.998, amb=0.95, cirrus=0.0, dalc=0.30)),
            (0.96, pt(pri=[-0.75, 0.18, 0.10, 0.94], priExp=1.0, sec=[-0.6, 0.45, 0.0, 0.65], mod=[-0.5, 0.5, 0.28, 0.85], modExp=1.0,
                      base=800.0, thick=1600.0, dens=0.85, sunExt=1.25, viewExt=1.1, msAlb=0.996, amb=0.85, cirrus=0.0, dalc=0.25))],
    cirrusLook='veil', haze=(1.2, 2.0), fog=(1200, 500), rayleigh=False)
T['fog'] = dict(
    label='Fog',
    why='The fog itself is haze + height fog (+ the optional Ground Fog); the cloud is a thin closed stratus deck with its base '
        'at 900 m or higher, clear of the peaks, lit softly so it reads as bright grey.',
    points=[(0.17, pt(pri=[-0.55, 0.28, 0.04, 0.88], priExp=1.0, sec=[-0.5, 0.55, 0.0, 0.55], mod=[-0.5, 0.5, 0.20, 0.60], modExp=1.0,
                      base=950.0, thick=600.0, dens=0.60, cirrus=0.0, dalc=0.32)),
            (1.00, pt(pri=[-0.70, 0.20, 0.08, 0.92], priExp=1.0, sec=[-0.55, 0.5, 0.0, 0.60], mod=[-0.5, 0.5, 0.22, 0.65], modExp=1.0,
                      base=900.0, thick=700.0, dens=0.70, sunExt=1.05, cirrus=0.0, dalc=0.28))],
    cirrusLook='veil', haze=(2.0, 3.0), fog=(800, 400), rayleigh=False)
T['special'] = dict(
    label='Other realm / map',
    why='Worldspace is not in the Physical Sky whitelist, so the file most likely never applies; clear values without a high layer.',
    points=[(0.0, pt(pri=[0.40, 0.65, 0.0, 0.65], sec=SEC_OFF, base=1400.0, thick=600.0, dens=0.60, cirrus=0.0))],
    cirrusLook='sparse', haze=(1.0, 1.0), fog=(1500, 1000), dalc=None, rayleigh=False)
TYPE_ORDER = list(T)
AURORA_TYPES = ('clear', 'fair', 'partly')
AURORA_IN_SHIFT = 0.15
PREFERRED_REPRESENTATIVE = p2.PREFERRED_REPRESENTATIVE
VECTOR_KEYS = ('pri', 'sec', 'mod', 'hv', 'btr')
SCALAR_KEYS = ('priExp', 'modExp', 'hvExp', 'base', 'thick', 'dens', 'spread', 'spreadH', 'sunExt', 'viewExt', 'msAlb', 'amb', 'cirrus')
OPTIONAL_KEYS = ('dalc', 'ltI', 'ltRate')

# --------------------------------------------------------------------------------------------
# OPTIONAL Ground Fog proposal (separate file set; refused by the current build, see validate()).
# Amount default 1.0 (0..4), Thickness default 1.5 m (0.5..3). Values per period; fog scales with severity.
GROUND_FOG = {
    'clear': dict(Dawn=(1.5, 2.0), Sunrise=(1.0, 1.5), Day=(0.0, 1.5), Sunset=(0.0, 1.5), Dusk=(0.3, 1.5), Night=(0.6, 1.5)),
    'fair': dict(Dawn=(1.5, 2.0), Sunrise=(1.0, 1.5), Day=(0.0, 1.5), Sunset=(0.0, 1.5), Dusk=(0.3, 1.5), Night=(0.6, 1.5)),
    'partly': dict(Dawn=(1.2, 2.0), Sunrise=(0.8, 1.5), Day=(0.0, 1.5), Sunset=(0.0, 1.5), Dusk=(0.3, 1.5), Night=(0.5, 1.5)),
    'overcast': dict(Dawn=(0.8, 1.5), Sunrise=(0.5, 1.5), Day=(0.2, 1.5), Sunset=(0.2, 1.5), Dusk=(0.4, 1.5), Night=(0.5, 1.5)),
    'rain': dict(Dawn=(0.6, 1.5), Sunrise=(0.5, 1.5), Day=(0.4, 1.5), Sunset=(0.4, 1.5), Dusk=(0.5, 1.5), Night=(0.5, 1.5)),
    'storm': dict(Dawn=(0.0, 1.5), Sunrise=(0.0, 1.5), Day=(0.0, 1.5), Sunset=(0.0, 1.5), Dusk=(0.0, 1.5), Night=(0.0, 1.5)),
    'snow': dict(Dawn=(0.4, 1.5), Sunrise=(0.3, 1.5), Day=(0.2, 1.5), Sunset=(0.2, 1.5), Dusk=(0.3, 1.5), Night=(0.3, 1.5)),
    'fog': dict(Dawn=(3.0, 3.0), Sunrise=(3.0, 3.0), Day=(2.5, 3.0), Sunset=(2.5, 3.0), Dusk=(3.0, 3.0), Night=(3.0, 3.0)),
    'special': None,
}


# --------------------------------------------------------------------------------------------
def aerosol(loading):
    return ([round(c * loading, 4) for c in p2.CONTINENTAL_RH50_SCATTER],
            [round(c * loading, 5) for c in p2.CONTINENTAL_RH50_ABSORPTION])


def interp(points, sev):
    """Piecewise-linear over the (severity, values) points, clamped at both ends. A severity within 0.012 of a point
    takes the point itself, so the weather a point was written for (the tested look) gets its exact numbers."""
    for sv, pv in points:
        if abs(sev - sv) < 0.012:
            return copy.deepcopy(pv)
    if sev <= points[0][0]:
        return copy.deepcopy(points[0][1])
    if sev >= points[-1][0]:
        return copy.deepcopy(points[-1][1])
    for (s0, a), (s1, b) in zip(points, points[1:]):
        if s0 <= sev <= s1:
            t = (sev - s0) / (s1 - s0)
            out = {}
            for k in a:
                if a[k] is None or b.get(k) is None:
                    out[k] = None
                elif isinstance(a[k], list):
                    out[k] = [x + (y - x) * t for x, y in zip(a[k], b[k])]
                else:
                    out[k] = a[k] + (b[k] - a[k]) * t
            return out
    raise AssertionError


def wind_for(wind_byte):
    """Record wind byte -> cloud drift, low layer capped at 9 m/s (pass-2 speeds up to 15.6 / 31.2 were never judged).
    Sunny (10) 3.9, Cloudy (25) 4.4, Overcast (35) 4.8, Snow (50) 5.4, Rain (75) 6.3, Storm (150) and Snowstorm (210) 9.
    Direction +X as in the saved base (the record's wind direction byte is the same in every Tamriel weather)."""
    low = round(max(3.5, min(LOW_DRIFT_CAP, 3.5 + 0.0375 * wind_byte)), 2)
    return [low, 0.0], [round(2.0 * low, 2), 0.0]


def fog_strength(near, far, power, max_opacity, floor_m, min_m):
    """Follow-vanilla height fog. raw = half-opacity distance at the Baseline strength 0.1 (same formula as pass 2,
    mirrors ExponentialHeightFog::GetCommonBufferData). Below the type floor the strength is lowered so the distance
    becomes max(min_m, floor x (raw / floor)^0.5)."""
    raw = p2.half_distance_m(near, far, power, max_opacity, BASE_FOG_STRENGTH)
    if raw >= floor_m:
        return BASE_FOG_STRENGTH, raw, raw
    eff = max(min_m, floor_m * (raw / floor_m) ** FOG_COMPRESS)
    strength = round(max(FOG_MIN_STRENGTH, BASE_FOG_STRENGTH * raw / eff), 4)
    return strength, raw, raw * BASE_FOG_STRENGTH / strength   # distance actually reached (differs only at the minimum strength)


def settings_for(wtype, sev, f):
    """Period-independent numbers of one weather."""
    t = T[wtype]
    v = interp(t['points'], sev)
    for k in VECTOR_KEYS:
        v[k] = [round(x, 3) for x in v[k]]
    for k in SCALAR_KEYS:
        v[k] = round(v[k], 4)
    v['base'] = float(round(v['base'] / 10.0) * 10)
    v['thick'] = float(round(v['thick'] / 10.0) * 10)
    for k in OPTIONAL_KEYS:
        v[k] = round(v[k], 3) if v.get(k) is not None else None
    nearness = p2.fog_nearness(f['fogFarDay'])
    v['hazeX'] = round(t['haze'][0] + (t['haze'][1] - t['haze'][0]) * nearness, 3)
    v['loading'] = round(BASE_LOADING * v['hazeX'], 4)
    v['windLow'], v['windHigh'] = wind_for(f['wind'])
    floor_m, min_m = t['fog']
    day = fog_strength(f['fogNearDay'], f['fogFarDay'], f['fogPowerDay'], f['fogMaxDay'], floor_m, min_m)
    night = fog_strength(f['fogNearNight'], f['fogFarNight'], f['fogPowerNight'], f['fogMaxNight'], floor_m, min_m)
    v.update(fogDay=day[0], fogNight=night[0], fogTwilight=round(math.sqrt(day[0] * night[0]), 4),
             fogHalfRawDayM=day[1], fogHalfDayM=day[2], fogHalfRawNightM=night[1], fogHalfNightM=night[2])
    return v


def xyzw(vals, keys='xyzw'):
    return dict(zip(keys, [float(x) for x in vals]))


def sky_tree(s, wtype, sev, aurora, period):
    t = T[wtype]
    pri, mod, cirrus = list(s['pri']), list(s['mod']), s['cirrus']
    cirrus *= t.get('cirrusPeriodScale', {}).get(period, 1.0)
    if aurora and wtype in AURORA_TYPES and period in DARK_PERIODS:
        pri[0] = round(pri[0] + AURORA_IN_SHIFT, 3)
        pri[1] = round(pri[1] + AURORA_IN_SHIFT, 3)
        cirrus = 0.0
    if t.get('dayMod') and period == 'Day':
        # rain: more top-type spread at midday only, faded in from the showers end to the RainPF end
        lo, hi = t['points'][0][0], t['points'][-1][0]
        k = p2.clamp01((sev - lo) / (hi - lo))
        mod = [round(a + (b - a) * k, 3) for a, b in zip(mod, t['dayMod'])]
    look = CIRRUS_LOOKS[t['cirrusLook']]
    scatter, absorption = aerosol(s['loading'])
    tree = collections.OrderedDict()
    tree['aerosolScatter'] = xyzw(scatter, 'xyz')
    tree['aerosolAbsorption'] = xyzw(absorption, 'xyz')
    if t.get('rayleigh'):
        k = RAYLEIGH_TWILIGHT if period in TWILIGHT_PERIODS else 1.0
        tree['rayleighScatter'] = xyzw([round(c * k, 4) for c in RAYLEIGH], 'xyz')
        tree['rayleighScatterAP1'] = xyzw([round(c * k, 4) for c in RAYLEIGH_AP1], 'xyz')
    if s.get('ltI') is not None:
        tree['lightningIntensity'] = float(s['ltI'])
        tree['lightning'] = {'rate': float(s['ltRate']), 'distanceRange': xyzw(t['lightningDistanceKm'], 'xy')}
    tree['cloudMap'] = {'procedural': {'parameters': collections.OrderedDict([
        ('primary', {'range': xyzw(pri), 'exponent': float(s['priExp'])}),
        ('secondary', {'range': xyzw(s['sec'])}),
        ('modeling', {'range': xyzw(mod), 'exponent': float(s['modExp'])}),
        ('heightVariation', {'range': xyzw(s['hv']), 'exponent': float(s['hvExp'])}),
        ('bottomTypeRange', xyzw(s['btr'])),
    ])}}
    tree['cloudLayer'] = collections.OrderedDict([
        ('low', {'ndfAltitudeOffset': s['base'], 'ndfAltitudeScale': s['thick'], 'densityScale': float(s['dens']),
                 'bottomSpreadScale': float(s['spread']), 'bottomSpreadHeight': float(s['spreadH'])}),
        ('lighting', {'sunExtinction': float(s['sunExt']), 'viewExtinction': float(s['viewExt']),
                      'msAlbedo': float(s['msAlb']), 'ambientStrength': float(s['amb'])}),
        ('wind', {'lowVelocity': xyzw(s['windLow'], 'xy'), 'highVelocity': xyzw(s['windHigh'], 'xy')}),
        ('cirrus', {'altitude': float(look['altitude']), 'densityScale': float(round(cirrus, 3)),
                    'weather': copy.deepcopy(look['state'])}),
    ])
    return tree


def fog_tree(s, period):
    if period == 'Night':
        v = s['fogNight']
    elif period in ('Dawn', 'Dusk'):
        v = s['fogTwilight']
    else:
        v = s['fogDay']
    return {'vanillaFogStrength': float(v)}


def ibl_tree(s, period):
    """Less of the game's weather ambient under heavy skies so terrain follows the sky. Full reduction in the lit
    periods, half-way at Dawn/Dusk, Baseline value at Night (nights must not go black; untested)."""
    if s.get('dalc') is None:
        return None
    if period == 'Night':
        v = BASE_DALC
    elif period in ('Dawn', 'Dusk'):
        v = (s['dalc'] + BASE_DALC) / 2.0
    else:
        v = s['dalc']
    return {'DALCAmount': float(round(v, 3))}


def groundfog_tree(wtype, sev, period):
    g = GROUND_FOG.get(wtype)
    if not g:
        return None
    amount, thickness = g[period]
    if wtype == 'fog':
        amount = min(4.0, amount + 0.8 * sev)
    return {'Amount': float(round(amount, 2)), 'Thickness': float(thickness)}


# --------------------------------------------------------------------------------------------
def is_blend(v):
    """SceneBlend::IsValid (src/Utils/SceneBlend.h)."""
    if not isinstance(v, dict) or list(v) != ['states'] or not isinstance(v['states'], list):
        return False
    total = 0.0
    for st in v['states']:
        if not isinstance(st, dict) or not isinstance(st.get('value'), dict) or not isinstance(st.get('weight'), (int, float)):
            return False
        if st['weight'] < 0 or not math.isfinite(st['weight']):
            return False
        total += st['weight']
    return total <= 1.00001


def leaves(tree, path=()):
    for k, v in tree.items():
        if isinstance(v, dict) and not is_blend(v):
            yield from leaves(v, path + (k,))
        else:
            yield path, k, v


def flat(tree):
    return collections.OrderedDict(('.'.join(p + (k,)), v) for p, k, v in leaves(tree))


class Validator:
    """Offline equivalent of ValidateSceneSettingEntry for a weather scene (SceneType::TimeOfDay, requireNumeric):
    feature in the time-of-day whitelist, address not blacklisted, catalog row exists and is Transitionable,
    value is a float (or a valid blend for a Blend row), inside the catalog range where the row has bounds."""

    def __init__(self, cat):
        self.rows = {(e['feature'], e['path'], e['key']): e for e in cat['rows']}
        self.blacklist = [tuple(b) for b in cat['policy']['kSettingBlacklist']]
        self.whitelist = {b[0] for b in cat['policy']['kTimeOfDayFeatureWhitelist'] if len(b) == 1}
        self.used = collections.Counter()

    def check(self, feature, tree, where):
        problems = []
        for path, key, value in leaves(tree):
            full = (feature,) + tuple(p for p in path if p != 'settings') + (key,)
            name = '%s %s' % (feature, '/'.join(full[1:]))
            if feature not in self.whitelist:
                problems.append('%s: %s: feature is not whitelisted for weather (time-of-day) scenes' % (where, name))
                continue
            if any(full[:len(b)] == b for b in self.blacklist):
                problems.append('%s: %s is blacklisted for scenes' % (where, name))
                continue
            entry = self.rows.get((feature, '/'.join(path), key))
            if not entry:
                problems.append('%s: %s not in catalog' % (where, name))
                continue
            if 'Trans' not in entry['flags'] or 'Scene' not in entry['flags']:
                problems.append('%s: %s is not transitionable / scene-controllable' % (where, name))
            if entry['vtype'] == 'Blend':
                if not is_blend(value):
                    problems.append('%s: %s is not a valid blend object' % (where, name))
            elif entry['vtype'] != 'Float':
                problems.append('%s: %s is %s, not a float' % (where, name, entry['vtype']))
            elif not isinstance(value, float) or not math.isfinite(value):
                problems.append('%s: %s is not written as a finite float' % (where, name))
            elif entry['bounds'] == 'true' and not (float(entry['mn']) <= value <= float(entry['mx'])):
                problems.append('%s: %s = %s outside %s..%s' % (where, name, value, entry['mn'], entry['mx']))
            self.used[name] += 1
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
    """Global-only values + the saved global base, so a weather without a file looks like today's saved sky.
    SettingsUser tree: vectors are arrays; cloudMap needs version 3 or the block is reset on load.
    The user's own SettingsUser.json edits (aerosolLoading 0.2, primary.range, 1200 + 900, cirrus densityScale 0.3)
    sit above this and hold the same values."""
    return {
        '_metadata': {'version': '0.3.0',
                      'description': PACK + ': global base saved in game 2026-11-19 + high-layer UV size 3 and the sparse-streak '
                                     'high-layer pattern (not settable per weather / fallback). Per-weather files are UNTESTED.'},
        'enableVolumetricClouds': True,
        'enableVanillaClouds': False,
        'aerosolType': 1,
        'aerosolLoading': BASE_LOADING,
        'cloudMap': {'version': 3, 'procedural': {'parameters': {'primary': {'range': [0.1, 0.65, 0.0, 0.65]}}}},
        'cloudLayer': {
            'low': {'ndfAltitudeOffset': 1200.0, 'ndfAltitudeScale': 900.0, 'ndfScale': [24.66, 16.7], 'densityScale': 0.75},
            'cirrus': {'uvSize': CIRRUS_UV_SIZE, 'altitude': 9000.0, 'densityScale': 0.3,
                       'weather': copy.deepcopy(CIRRUS_LOOKS['sparse']['state'])},
            'wind': {'lowVelocity': [5.0, 0.0], 'highVelocity': [10.0, 0.0]},
        },
    }


MANIFEST = {
    'name': 'foxnne NAT III clouds (pass 3)',
    'version': '0.3.0',
    'type': 'CS',
    'author': 'foxnne',
    'description': 'UNTESTED DRAFT, pass 3. Per-weather volumetric cloud coverage, vertical fill, altitude, density, lighting, drift, '
                   'high layer, haze, twilight Rayleigh and storm lightning (Physical Sky), height-fog strength (Exponential Height Fog) '
                   'and weather-ambient amount (Image Based Lighting) for the 111 NAT.CS III weathers, by sky type. '
                   'Applying a pack with scene files makes it the active pack: read notes/install-pass-3.md first.',
    'tags': ['NAT.CS III', 'Physical Sky', 'volumetric clouds', 'draft'],
    'csVersion': '1.9.0',
    'requiredFeatures': ['PhysicalSky', 'ExponentialHeightFog', 'ImageBasedLighting', 'SceneManager', 'SkySync'],
    'requiredPlugins': ['NAT-ENB.esp', 'NAT-CS.esp'],
}


def nested_for_harness(tree):
    """Scene tree as-is: the harness merge() accepts {x,y,z,w} for vectors and replaces the blend object whole."""
    return json.loads(json.dumps(tree))


def fmt_vec(v):
    return '[' + ', '.join('%g' % x for x in v) + ']'


def main():
    masters, recs = wthr_parse.load()
    cat = json.load(open(os.path.join(HERE, 'scene-catalog-pass3.json'), encoding='utf-8'))
    val = Validator(cat)
    gf_val = Validator(cat)

    # Only ever remove what this script generates.
    for d in (os.path.join(PACK_DIR, 'Weather'), os.path.join(PACK_DIR, 'Baseline'), os.path.join(GROUNDFOG_DIR, 'Weather')):
        if os.path.isdir(d):
            shutil.rmtree(d)

    rows, problems, gf_problems, user_fragment, gf_fragment = [], [], [], {}, {}
    files = collections.Counter()
    for w in recs:
        f = p2.facts(w)
        wtype, sev = p2.classify(w['editorId'], f)
        s = settings_for(wtype, sev, f)
        entries, gf_entries = [], []
        for period in PERIODS:
            where = '%s/%s' % (w['editorId'], period)
            trees = [('PhysicalSky', sky_tree(s, wtype, sev, f['aurora'], period)),
                     ('ExponentialHeightFog', fog_tree(s, period)),
                     ('ImageBasedLighting', ibl_tree(s, period))]
            for feature, tree in trees:
                if tree is None:
                    continue
                problems += val.check(feature, tree, where)
                doc = collections.OrderedDict([
                    ('_feature', feature),
                    ('_metadata', {'description': '%s - %s, severity %.2f (%s) - %s' % (PACK, T[wtype]['label'], sev, w['editorId'], period),
                                   'timeOfDayEnabled': True})])
                doc.update(tree)
                write_json(os.path.join(PACK_DIR, 'Weather', w['spid'], period, '%s_%s.json' % (PACK, feature)), doc)
                files[feature] += 1
                for path, key, value in leaves(tree):
                    entries.append({'feature': feature, 'path': list(path), 'setting': key, 'value': value,
                                    'originalValue': value, 'paused': False, 'period': period})
            gtree = groundfog_tree(wtype, sev, period)
            if gtree is not None:
                gf_problems += gf_val.check('GroundFog', gtree, where)
                doc = collections.OrderedDict([
                    ('_feature', 'GroundFog'),
                    ('_metadata', {'description': '%s OPTIONAL Ground Fog proposal - %s (%s) - %s. UNTESTED; refused by builds whose '
                                                  'time-of-day whitelist lacks GroundFog.' % (PACK, T[wtype]['label'], w['editorId'], period),
                                   'timeOfDayEnabled': True})])
                doc.update(gtree)
                write_json(os.path.join(GROUNDFOG_DIR, 'Weather', w['spid'], period, '%s_GroundFog.json' % PACK), doc)
                files['GroundFog (optional)'] += 1
                for path, key, value in leaves(gtree):
                    gf_entries.append({'feature': 'GroundFog', 'path': list(path), 'setting': key, 'value': value,
                                       'originalValue': value, 'paused': False, 'period': period})
        user_fragment[w['spid']] = {'entries': entries}
        if gf_entries:
            gf_fragment[w['spid']] = {'entries': gf_entries}
        rows.append(dict(w=w, f=f, type=wtype, sev=sev, s=s))

    write_json(os.path.join(PACK_DIR, PACK + '.json'), MANIFEST)
    write_json(os.path.join(PACK_DIR, 'Baseline', 'PhysicalSky.json'), baseline_doc())
    write_json(os.path.join(DRAFT, 'alt-user-overrides-pass3', 'SceneManager.weather.pass3.json'), user_fragment, compact=True)
    write_json(os.path.join(GROUNDFOG_DIR, 'SceneManager.weather.groundfog.pass3.json'), gf_fragment, compact=True)

    # ---- sanity: heavier never means less cloud / higher base / thinner cloud within a type; hard limits from the brief
    for name in TYPE_ORDER:
        members = sorted((r for r in rows if r['type'] == name), key=lambda r: r['sev'])
        for a, b in zip(members, members[1:]):
            if (b['s']['pri'][0] > a['s']['pri'][0] + 1e-9 or b['s']['base'] > a['s']['base'] + 1e-9 or
                    b['s']['dens'] < a['s']['dens'] - 1e-9):
                problems.append('not monotonic within %s: %s -> %s' % (name, a['w']['editorId'], b['w']['editorId']))
    ceilings = {'clear': 1.0, 'fair': 1.0, 'partly': 1.15, 'overcast': 1.5, 'rain': 1.8, 'storm': 1.6, 'snow': 2.0, 'fog': 3.0, 'special': 1.0}
    for r in rows:
        s, n, e = r['s'], r['type'], r['w']['editorId']
        if s['hazeX'] > ceilings[n] + 1e-9:
            problems.append('%s: haze %.2fx above the %s ceiling' % (e, s['hazeX'], n))
        if s['pri'][2] > 0.15 + 1e-9:
            problems.append('%s: coverage floor %.2f above 0.15' % (e, s['pri'][2]))
        if s['windLow'][0] > LOW_DRIFT_CAP + 1e-9:
            problems.append('%s: low drift above the cap' % e)
        if n == 'fog' and s['base'] < 900:
            problems.append('%s: fog cloud base below 900 m' % e)
        if n not in ('storm', 'snow') and s['base'] < 800:
            problems.append('%s: base below 800 m outside storm/snow' % e)
        if n == 'rain' and (s['spread'] > 0.9 or s['hv'][2] > 0.05):
            problems.append('%s: rain uses the low-wide-base treatment' % e)

    # ---- summary: one representative per type
    counts = collections.Counter(r['type'] for r in rows)

    def describe(r):
        day_tree = sky_tree(r['s'], r['type'], r['sev'], r['f']['aurora'], 'Day')
        day = flat(day_tree)
        overrides = collections.OrderedDict()
        for period in PERIODS:
            if period == 'Day':
                continue
            other = flat(sky_tree(r['s'], r['type'], r['sev'], r['f']['aurora'], period))
            diff = collections.OrderedDict((k, v) for k, v in other.items() if day.get(k) != v)
            if diff:
                overrides[period] = diff
        s = r['s']
        d = collections.OrderedDict([
            ('editorId', r['w']['editorId']), ('formKey', r['w']['spid']), ('localFormId', r['w']['spid'].split('~')[0]),
            ('plugin', r['w']['spid'].split('~')[1]), ('severity', round(r['sev'], 3)),
            ('aerosolLoadingEquivalent', s['loading']), ('hazeMultipleOfSavedBase', s['hazeX']),
            ('PhysicalSky.Day', day),
            ('PhysicalSky.periodOverrides', overrides),
            ('ExponentialHeightFog', collections.OrderedDict([
                ('vanillaFogStrength.Day', s['fogDay']), ('vanillaFogStrength.Night', s['fogNight']),
                ('vanillaFogStrength.DawnDusk', s['fogTwilight']),
                ('halfOpacityDistanceDayM.atBaseline0.1', round(min(s['fogHalfRawDayM'], 99999))),
                ('halfOpacityDistanceDayM.pass3', round(min(s['fogHalfDayM'], 99999))),
                ('halfOpacityDistanceNightM.pass3', round(min(s['fogHalfNightM'], 99999)))])),
            ('ImageBasedLighting', None if s.get('dalc') is None else collections.OrderedDict(
                [('DALCAmount.Day', ibl_tree(s, 'Day')['DALCAmount']), ('DALCAmount.DawnDusk', ibl_tree(s, 'Dawn')['DALCAmount']),
                 ('DALCAmount.Night', ibl_tree(s, 'Night')['DALCAmount'])])),
            ('GroundFog.optionalUntested', None if not GROUND_FOG.get(r['type']) else collections.OrderedDict(
                (p, groundfog_tree(r['type'], r['sev'], p)) for p in PERIODS)),
        ])
        return d

    summary = collections.OrderedDict([
        ('_note', 'UNTESTED as scene files. One representative weather per sky type with its Day settings (flat dotted paths; vector '
                  'components .x/.y/.z/.w). "cloudLayer.cirrus.weather" is ONE value: the whole {"states": [...]} blend object. '
                  '"PhysicalSky.periodOverrides" lists, per other period, only the keys that differ from Day. '
                  '"globalOnly" must be set once globally (it cannot be driven per weather). '
                  'Console: fw <formId>; NAT-ENB.esp ids need the load-order byte in place of the leading 00.'),
        ('pack', PACK),
        ('globalOnly', {'PhysicalSky': {'cloudLayer.cirrus.uvSize': CIRRUS_UV_SIZE},
                        'why': 'cloudLayer.cirrus.uvSize is scene-blacklisted; all three high-layer looks were tested at 3.0. It is in the pack Baseline.'}),
        ('savedBase', {'aerosolLoading': BASE_LOADING, 'ExponentialHeightFog.vanillaFogStrength': BASE_FOG_STRENGTH,
                       'ImageBasedLighting.DALCAmount': BASE_DALC, 'rayleighScatter': list(RAYLEIGH), 'rayleighScatterAP1': list(RAYLEIGH_AP1)}),
        ('anchors', ANCHORS),
        ('types', collections.OrderedDict())])
    reps = {}
    for name in TYPE_ORDER:
        members = sorted((r for r in rows if r['type'] == name), key=lambda r: (r['sev'], r['w']['editorId']))
        if not members:
            continue
        rep = next((r for r in members if r['w']['editorId'] == PREFERRED_REPRESENTATIVE.get(name)), members[len(members) // 2])
        light, heavy = members[0], members[-1]
        reps[name] = (light, rep, heavy)
        t = T[name]
        summary['types'][name] = collections.OrderedDict([
            ('label', t['label']), ('rationale', t['why']), ('count', counts[name]),
            ('definition_points_by_severity', [collections.OrderedDict([('severity', sv)] + [(k, v) for k, v in pv.items()]) for sv, pv in t['points']]),
            ('highLayerLook', CIRRUS_LOOKS[t['cirrusLook']]['label']),
            ('hazeMultipleRange_fogFar150000_to_5000', list(t['haze'])),
            ('heightFog_floorM_minM', list(t['fog'])),
            ('rayleighTwilightX2', bool(t.get('rayleigh'))),
            ('lightningDistanceKm', t.get('lightningDistanceKm')),
            ('representative', describe(rep)),
            ('lightestMember', describe(light) if light is not rep else None),
            ('heaviestMember', describe(heavy) if heavy is not rep else None),
            ('members', [{'editorId': r['w']['editorId'], 'formKey': r['w']['spid'], 'severity': round(r['sev'], 3)} for r in members]),
        ])
    write_json(os.path.join(DRAFT, 'pass3-sky-types.json'), summary)

    # ---- emulation input (cloud-storms/ndf_sim.py): cloud map + slab of lightest / representative / heaviest member, Day
    if '--sim' in sys.argv:
        variants = []
        for i, name in enumerate(TYPE_ORDER):
            if name == 'special':
                continue
            seen = set()
            for tag, r in zip(('light', 'rep', 'heavy'), reps[name]):
                if r['w']['editorId'] in seen:
                    continue
                seen.add(r['w']['editorId'])
                tree = nested_for_harness(sky_tree(r['s'], r['type'], r['sev'], r['f']['aurora'], 'Day'))
                tree['cloudLayer'].pop('cirrus', None)
                variants.append({'name': 'p3_%d_%s_%s_%s' % (i, name, tag, r['w']['editorId']), 'set': tree})
        write_json(os.path.join(HERE, 'pass3-sim-variants.json'), variants)

    # ---- table
    def member_line(tag, r):
        s = r['s']
        day = sky_tree(s, r['type'], r['sev'], r['f']['aurora'], 'Day')
        modv = [day['cloudMap']['procedural']['parameters']['modeling']['range'][c] for c in 'xyzw']
        cir = [sky_tree(s, r['type'], r['sev'], False, p)['cloudLayer']['cirrus']['densityScale'] for p in ('Day', 'Sunset')]
        return ('| %s | %s | %s (%.2f) | %s ^%g | %s | %s ^%g | %s | %s | %d + %d | %g | %g / %g | %g / %g / %g / %g | %s | %gx (%g) | %g / %g | %d / %d | %s | %s | %g |' % (
            r['type'] if tag == 'rep' else '', tag, r['w']['editorId'], r['sev'], fmt_vec(s['pri']), s['priExp'], fmt_vec(s['sec']),
            fmt_vec(modv), s['modExp'], fmt_vec(s['hv']), fmt_vec(s['btr']), s['base'], s['thick'], s['dens'], s['spread'], s['spreadH'],
            s['sunExt'], s['viewExt'], s['msAlb'], s['amb'],
            ('%g' % cir[0]) if cir[0] == cir[1] else '%g day / %g twilight' % (cir[0], cir[1]),
            s['hazeX'], s['loading'], s['fogDay'], s['fogNight'], min(s['fogHalfDayM'], 99999), min(s['fogHalfNightM'], 99999),
            '-' if s.get('dalc') is None else '%g' % s['dalc'],
            '-' if s.get('ltI') is None else '%g, %g/min, %s km' % (s['ltI'], s['ltRate'], fmt_vec(T[r['type']]['lightningDistanceKm'])),
            s['windLow'][0]))

    out = ['# NAT.CS III weather table, pass 3 (untested)', '',
           'Generated by `draft/_generator/build_pass3.py`. Do not edit by hand; edit the sky types in the generator and re-run.',
           'Record facts are parsed from `NAT-CS.esp` (the winning override of all %d weathers). Types and severities are the pass-2 rules, unchanged.' % len(rows),
           '**Nothing here was seen in game as scene files.** The anchors (liked looks) are marked in the rationale.', '',
           '## Sky types', '',
           'One row per lightest member / representative / heaviest member of each type (actual generated values, Day period). '
           'primary / secondary / modeling / heightVariation = `cloudMap.procedural.parameters.<layer>.range` [inMin, inMax, outMin, outMax] '
           '(^ = exponent); btr = `bottomTypeRange`; slab = `cloudLayer.low.ndfAltitudeOffset + ndfAltitudeScale` (m); dens = `densityScale`; '
           'spread = `bottomSpreadScale / bottomSpreadHeight`; lighting = `cloudLayer.lighting` sunExtinction / viewExtinction / msAlbedo / ambientStrength; '
           'high = `cloudLayer.cirrus.densityScale`; haze = multiple of the saved base (Continental loading in brackets), written as '
           '`aerosolScatter` / `aerosolAbsorption`; fog = `ExponentialHeightFog.vanillaFogStrength` day / night and the half-opacity '
           'distance it gives (m, day / night); DALC = `ImageBasedLighting.DALCAmount` by day (- = no file, Baseline %g); '
           'lightning = `lightningIntensity`, `lightning.rate`, `lightning.distanceRange`; drift = low-layer wind m/s (high = 2x).' % BASE_DALC, '',
           '| Type | | Weather (sev) | primary | secondary | modeling | heightVariation | btr | slab m | dens | spread | lighting | high | haze | fog str | fog half m | DALC | lightning | drift |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for name in TYPE_ORDER:
        light, rep, heavy = reps[name]
        if light is not rep and light['sev'] < rep['sev'] - 1e-9:
            out.append(member_line('lightest', light))
        out.append(member_line('rep', rep))
        if heavy is not rep and heavy['sev'] > rep['sev'] + 1e-9:
            out.append(member_line('heaviest', heavy))
    out += ['', '| Type | Weathers | High-layer look | Haze range (fog far 150000 -> 5000) | Height-fog floor / minimum m | Rayleigh x2 at twilight | Rationale |',
            '|---|---|---|---|---|---|---|']
    for name in TYPE_ORDER:
        t = T[name]
        out.append('| %s | %d | %s | %gx -> %gx | %d / %d | %s | %s |' % (
            name, counts[name], CIRRUS_LOOKS[t['cirrusLook']]['label'] + (' (density 0: hidden)' if all(p[1]['cirrus'] == 0 for p in t['points']) else ''),
            t['haze'][0], t['haze'][1], t['fog'][0], t['fog'][1], 'yes' if t.get('rayleigh') else 'no', t['why']))
    out += ['', '## Rules', '',
            '- **Type and severity**: exactly the pass-2 rules (`build_pass2.classify`), see `weather-table-2.md`.',
            '- **Values**: each type is a list of (severity, values) points in the generator; a weather is interpolated linearly between '
            'the two nearest points and clamped at the ends. The points sit on the tested looks where one exists.',
            '- **Haze**: lo + (hi - lo) x fog nearness (log position of day fog far between 150000 and 5000), as a multiple of the saved '
            'Continental loading %g.' % BASE_LOADING,
            '- **Cloud drift**: low = 3.5 + 0.0375 x wind byte m/s, capped at %g; high = 2 x low; along +X.' % LOW_DRIFT_CAP,
            '- **Height fog**: half-opacity distance at the Baseline strength %g is computed from the record fog (near, far, power, max); '
            'where it is shorter than the type floor the strength is lowered so the distance becomes max(minimum, floor x (raw / floor)^%g). '
            'Day value for Sunrise/Day/Sunset, night value for Night, geometric mean for Dawn/Dusk.' % (BASE_FOG_STRENGTH, FOG_COMPRESS),
            '- **DALC**: the type value in Sunrise/Day/Sunset, half-way to the Baseline %g at Dawn/Dusk, the Baseline value at Night.' % BASE_DALC,
            '- **Rayleigh** (clear/fair/partly): x%g in Dawn, Sunrise, Sunset, Dusk; x1 in Day and Night (both `rayleighScatter` and `rayleighScatterAP1`).' % RAYLEIGH_TWILIGHT,
            '- **High layer**: per type one look (coverage + type pattern as a blend state, altitude) and a density; partly cloudy uses '
            '0.5 at twilight and 0.3 in Day and Night. `uvSize` 3 is global (Baseline).',
            '- **Rain, Day period only**: `modeling.range` z/w widened toward [0.12, 0.9] with severity (more thickness variation at midday).',
            '- **Aurora** (record has an aurora model; clear/fair/partly only): in Dawn, Dusk and Night primary inMin and inMax + %g and high layer 0.' % AURORA_IN_SHIFT, '',
            '## Every weather', '',
            'Fog = day near/far (night far). Fog str = `vanillaFogStrength` day / night; half m = resulting day half-opacity distance. '
            'pri = primary.range; mod = modeling.range z-w (Day); DALC = day value.', '',
            '| Editor ID | Form key | Sun lum | Fog day (night far) | Wind | Precipitation | Aurora | Type | Sev | pri | sec out | mod z-w | slab m | dens | sunExt | high | haze x | drift | Fog str | half m | DALC | Note |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (TYPE_ORDER.index(r['type']), r['sev'], r['w']['editorId'].lower(), r['w']['spid'])):
        f, s = r['f'], r['s']
        day = sky_tree(s, r['type'], r['sev'], False, 'Day')
        modv = day['cloudMap']['procedural']['parameters']['modeling']['range']
        out.append('| %s | `%s` | %.2f | %d/%d (%d) | %d | %s | %s | %s | %.2f | %s | %g | %g-%g | %d + %d | %g | %g | %g | %g | %g | %g / %g | %d | %s | %s |' % (
            r['w']['editorId'], r['w']['spid'], f['sunLumDay'], f['fogNearDay'], f['fogFarDay'], f['fogFarNight'], f['wind'],
            f['precip'] or '-', 'yes' if f['aurora'] else '', r['type'], r['sev'], fmt_vec(s['pri']), s['sec'][3], modv['z'], modv['w'],
            s['base'], s['thick'], s['dens'], s['sunExt'], day['cloudLayer']['cirrus']['densityScale'], s['hazeX'], s['windLow'][0],
            s['fogDay'], s['fogNight'], min(s['fogHalfDayM'], 99999), '-' if s.get('dalc') is None else '%g' % s['dalc'],
            p2.NOTES.get(r['w']['editorId'], '')))
    os.makedirs(os.path.join(ROOT, 'notes'), exist_ok=True)
    with open(os.path.join(ROOT, 'notes', 'weather-table-3.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')

    print('weathers:', len(rows))
    print('scene files:', ', '.join('%s %d' % kv for kv in files.items()))
    print('types:', ', '.join('%s %d' % (n, counts[n]) for n in TYPE_ORDER))
    print('aurora weathers:', sum(1 for r in rows if r['f']['aurora']))
    print('distinct scene settings written (pack):', len(val.used))
    print('catalog:', cat['source'])
    print('validation problems (pack):', len(problems))
    for p in sorted(set(problems))[:40]:
        print('  ', p)
    print('validation problems (optional Ground Fog set):', len(gf_problems), '- distinct:')
    for p in sorted(set(x.split(': ', 1)[1] for x in gf_problems))[:10]:
        print('  ', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())

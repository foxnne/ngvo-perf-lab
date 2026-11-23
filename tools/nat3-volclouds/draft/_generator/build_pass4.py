"""Pass 4 generator: per-weather, per-period sky settings for the 111 NAT.CS III weathers.

UNTESTED IN GAME. Nothing here was loaded by the game; every number in the TUNING TABLE below is provisional.

    python -I build_pass4.py

Reads (read-only):
    NAT-CS.esp + masters (through wthr_parse.py)     the weather records
    scene-catalog-pass4.json                          scene catalogue + policy (extract_catalog4.py; branches
                                                      foxnne/lightning-fix + foxnne/ground-fog-near)
    build_pass2.py / build_pass3.py                   imported: record facts, type / severity rules, the pass-3 fair-weather
                                                      cloud points, height-fog rule, validator (their main() is not run)
Writes (only under ..\\ and ..\\..\\notes; pass 1-3 files are not touched):
    ..\\foxnne-nat3-clouds-pass4\\                    pack: manifest, Baseline, Weather/<formkey>/<Period>/<pack>_<Feature>.json
                                                      (PhysicalSky, ExponentialHeightFog, ImageBasedLighting, GroundFog)
    ..\\alt-user-overrides-pass4\\                    same values as SceneManager.json "weather" entries (route B)
    ..\\pass4-sky-types.json                          per sky type: representative(s) + settings (harness format of pass 3)
    ..\\sweeps-pass4\\pass4_types_<period>[_rays].json  harness sweeps (Sunrise, Day, Sunset, Night)
    ..\\..\\notes\\weather-table-4.md
"""
import collections
import copy
import json
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script directory
import build_pass2 as p2  # noqa: E402
import build_pass3 as p3  # noqa: E402
import wthr_parse  # noqa: E402

DRAFT = os.path.dirname(HERE)
ROOT = os.path.dirname(DRAFT)
PACK = 'foxnne-nat3-clouds-pass4'
PACK_DIR = os.path.join(DRAFT, PACK)
USER_DIR = os.path.join(DRAFT, 'alt-user-overrides-pass4')
SWEEP_DIR = os.path.join(DRAFT, 'sweeps-pass4')
PERIODS = ['Dawn', 'Sunrise', 'Day', 'Sunset', 'Dusk', 'Night']
SWEEP_PERIODS = ['Sunrise', 'Day', 'Sunset', 'Night']
SWEEP_HOURS = {'Sunrise': 6.5, 'Day': 13, 'Sunset': 18.25, 'Night': 23}   # suggested --hours, not stored in the sweep files


def P(dawn, sunrise, day, sunset, dusk, night):
    return dict(zip(PERIODS, (dawn, sunrise, day, sunset, dusk, night)))


# ############################################################################################################
# ##                                                                                                        ##
# ##   TUNING TABLE - EVERYTHING HERE IS PROVISIONAL. Change numbers here only, then re-run the script.     ##
# ##   Each block names the in-game test whose result it is waiting for.                                    ##
# ##                                                                                                        ##
# ############################################################################################################

# ---- (A) Today's saved base. Update when the saved global look / look pack changes.
BASE = dict(
    loading=0.2,                          # saved haze: Continental, loading 0.2 (aerosolScatter [2.522, 3.419, 4.575])
    phaseG=0.6164,                        # saved PhysicalSky.aerosolPhaseG
    sun=(10.0, 9.7, 9.5),                 # PhysicalSky.h default sunlightColor (not edited in SettingsUser.json)
    rayleigh=(6.6049, 12.345, 29.413), rayleighAP1=(6.9344, 12.0203, 28.91),
    ozone=(2.2911, 1.5404, 0.0), ozoneAP1=(2.2499, 1.6602, 0.0),
    dalc=0.5, skySat=0.6, skyScale=1.21, envSat=0.8,   # Presets/foxnne-look/Baseline/ImageBasedLighting.json
    fogStrength=0.1,                      # Presets/foxnne-look/Baseline/ExponentialHeightFog.json
    gfMorning=1.4, gfEvening=0.8,         # Ground Fog code defaults (foxnne/ground-fog-near); only used for the "effective" columns
)

# ---- (B) MOISTURE 0..1 per weather = clamp(type + region + alternate).  WAITING ON: nothing; a design choice.
MOISTURE_TYPE = dict(clear=0.15, fair=0.40, partly=0.50, overcast=0.65, rain=0.85, storm=0.80, snow=0.40, fog=0.95, special=0.30)
MOISTURE_SHOWERS = 0.90                   # rain records under a bright sun (severity < 0.4): showers / after-rain air
MOISTURE_REGION = dict(MA=0.30, COMA=0.30, CO=0.25, FF=0.10, PF=0.05, VT=-0.05, FV=-0.10, RE=-0.15, TU=-0.15, SN=-0.20,
                       DLC2=0.0, DLC2_TU=-0.15, none=0.0)
HUMID_REGIONS = ('MA', 'COMA', 'CO')
MOISTURE_ALT_IN_HUMID = -0.20             # _A / _Alt / _ALT record in a humid region: the cleaner day
MOISTURE_ALT_ELSEWHERE = 0.15             # _A / _Alt / _ALT record elsewhere: the hazier day
DUST_REGION = dict(VT=0.6, DLC2=0.8, DLC2_TU=0.3)   # dry haze (volcanic dust / ash): present all day, warm and absorbing
DUST_ASH_STORM = 1.0                      # StormDLC2 / StormDLC2_ALT
NAMED_REGION = dict(Riften='FF', Karthspire='RE', BloatedMansGrotto='PF', Helgen='PF', Skuldafn='SN', Auriel='FV', FalmerValley='FV')
M_DRY, M_HUMID = 0.20, 0.80               # moisture at which a curve reaches its "dry" / "humid" column (k = 0 / 1)

# ---- (C) PERIOD CURVES. Every entry: period -> (dry, humid); value = dry + (humid - dry) * k, k from moisture.
# Group 'fair' = clear, fair, partly.  Group 'closed' = overcast, rain, storm, snow, fog (closed decks: sky colour hidden).
CURVES = {
    'fair': {
        # haze amount as a multiple of the saved base (loading 0.2). Day must stay <= 1.0 (user: haze clears at midday).
        # WAITING ON: godrays sweep (haze x2) and the aerosol x5-x10 test. If x5-x10 wins, raise the humid twilight numbers.
        'hazeX': P((1.0, 1.7), (1.1, 2.0), (0.6, 1.0), (1.1, 2.0), (1.0, 1.7), (0.6, 1.0)),
        # extra multiple on aerosolAbsorption only (darker haze).  WAITING ON: "darker / warmer haze" test.
        'absorbX': P((1.0, 1.3), (1.0, 1.5), (1.0, 1.0), (1.0, 1.5), (1.0, 1.3), (1.0, 1.0)),
        # blue weighting b of that absorption: rgb x (1, 1 + b/2, 1 + b) = warmer transmitted light.  WAITING ON: same test.
        'absorbBlue': P((0.0, 0.2), (0.0, 0.3), (0.0, 0.0), (0.0, 0.3), (0.0, 0.2), (0.0, 0.0)),
        # Rayleigh multiple (rayleighScatter + AP1). Tested: x3 best at 18:00, x2-x3 pales midday -> twilight only.
        'rayleighX': P((2.0, 2.5), (2.0, 3.0), (1.0, 1.0), (2.0, 3.0), (2.0, 2.5), (1.0, 1.0)),
        # ozone multiple (ozoneAbsorption + AP1). Tested: x3 with air x3 + haze x2 = richest.  WAITING ON: ozone x8 test.
        'ozoneX': P((1.5, 2.5), (1.5, 3.0), (1.0, 1.0), (1.5, 3.0), (1.5, 2.5), (1.0, 1.0)),
        # aerosol phase g (saved 0.6164). Tighter = smaller, more concentrated glow.  WAITING ON: phase g 0.75-0.9 test.
        'phaseG': P((0.66, 0.72), (0.70, 0.80), (0.6164, 0.6164), (0.70, 0.80), (0.66, 0.72), (0.6164, 0.6164)),
        # sun strength: multiple of sunlightColor.  WAITING ON: sunlightColor x0.4-0.6 test (low sun too big and bright).
        'sunX': P((0.9, 0.75), (0.8, 0.6), (1.0, 1.0), (0.8, 0.6), (0.9, 0.75), (1.0, 1.0)),
        # ambient mix (Image Based Lighting).  WAITING ON: sunsetamb sweep (saturation 1.0 / DALC 0 / sky light x1.5).
        'dalc': P((0.45, 0.35), (0.40, 0.25), (0.5, 0.5), (0.40, 0.25), (0.45, 0.35), (0.5, 0.5)),
        'skySat': P((0.70, 0.85), (0.80, 1.00), (0.6, 0.6), (0.80, 1.00), (0.70, 0.85), (0.6, 0.6)),
        'skyScale': P((1.25, 1.35), (1.30, 1.45), (1.21, 1.21), (1.30, 1.45), (1.25, 1.35), (1.21, 1.21)),
        'envSat': P((0.85, 0.90), (0.90, 1.00), (0.8, 0.8), (0.90, 1.00), (0.85, 0.90), (0.8, 0.8)),
        # Ground Fog: Amount (sheet + near volume) and FarAmount (valley layer). The feature's own time-of-day curve
        # (Morning 1.4 / MiddayAmount / Evening 0.8, burn-off, shade) multiplies these.  WAITING ON: first in-game look.
        'gfNear': P((0.5, 1.3), (0.5, 1.3), (0.5, 1.0), (0.4, 1.2), (0.4, 1.2), (0.3, 1.0)),
        'gfValley': P((0.5, 1.5), (0.5, 1.5), (0.4, 1.0), (0.4, 1.3), (0.4, 1.3), (0.3, 1.1)),
        # screen-space rays strength (Effects11 StandaloneSunMultiplier; Night = StandaloneMoonMultiplier).
        # NOT scene-drivable in this build: goes to the sky-types JSON and the *_rays sweeps only.  WAITING ON: godrays /
        # standalone_rays sweeps (saved strength 0.1; 0.3 and 1.0 tested).
        'rays': P((0.05, 0.30), (0.15, 0.60), (0.0, 0.10), (0.15, 0.60), (0.05, 0.30), (0.0, 0.15)),
    },
    'closed': {
        'hazeX': P((1.0, 1.15), (1.0, 1.15), (1.0, 1.0), (1.0, 1.15), (1.0, 1.15), (0.9, 1.0)),   # x the type's own Day haze
        'absorbX': P(*[(1.0, 1.0)] * 6), 'absorbBlue': P(*[(0.0, 0.0)] * 6),
        'rayleighX': P(*[(1.0, 1.0)] * 6), 'ozoneX': P(*[(1.0, 1.0)] * 6),
        'phaseG': P(*[(0.6164, 0.6164)] * 6), 'sunX': P(*[(1.0, 1.0)] * 6),
        # dalc: None = the type's own day value (heavy-sky points below) in Sunrise/Day/Sunset, half-way at Dawn/Dusk, base at Night
        'dalc': None,
        'skySat': P(*[(0.6, 0.6)] * 6), 'skyScale': P(*[(1.21, 1.21)] * 6), 'envSat': P(*[(0.8, 0.8)] * 6),
        'gfNear': None, 'gfValley': None,   # per type: GROUND_FOG_CLOSED
        'rays': P(*[(0.0, 0.0)] * 6),
    },
}
TYPE_GROUP = dict(clear='fair', fair='fair', partly='fair', overcast='closed', rain='closed', storm='closed', snow='closed',
                  fog='closed', special=None)
FAIR_DAY_HAZE_CAP = 1.0                   # Day haze of fair types never above today's base, dust included

# ---- (D) Dust (VT volcanic, DLC2 ash): added on top of the curves in EVERY period (dust does not burn off).
DUST = dict(hazeAdd=0.35,                 # + this x dust to the haze multiple
            absorbAdd=1.0,                # absorption x (1 + this x dust)
            blueAdd=0.4,                  # + this x dust to the blue weighting
            scatterTint=(1.0, 0.93, 0.82))   # aerosolScatter tint at dust 1 (warm, dusty)

# ---- (E) Ground Fog per weather (constant over the day) and for closed decks.
# fair group: (dry, humid).  MiddayAmount = share left on sunlit ground at midday; ShadowRetention = share kept in shade.
GROUND_FOG_FAIR = dict(midday=(0.0, 0.35), retention=(0.30, 0.70), burnOff=(1.0, 1.0))
# closed decks: near / valley at (dry, humid) x GROUND_FOG_CLOSED_PERIOD; no sun = weak burn-off, high midday share.
GROUND_FOG_CLOSED = dict(
    overcast=dict(near=(0.7, 1.0), valley=(0.8, 1.2), midday=0.5, retention=0.6, burnOff=0.5),
    rain=dict(near=(0.5, 0.8), valley=(0.8, 1.2), midday=0.6, retention=0.6, burnOff=0.3),
    storm=dict(near=(0.15, 0.25), valley=(0.4, 0.6), midday=0.6, retention=0.6, burnOff=0.3),
    snow=dict(near=(0.3, 0.5), valley=(0.4, 0.7), midday=0.5, retention=0.6, burnOff=0.5),     # x (1 - 0.6 x severity)
    fog=dict(near=(1.8, 2.4), valley=(1.8, 2.6), midday=1.0, retention=0.8, burnOff=0.15),     # + 0.8 x severity
)
GROUND_FOG_CLOSED_PERIOD = P(1.1, 1.1, 0.9, 1.0, 1.0, 1.0)

# ---- (F) Lightning (storm type only; every other weather writes lightning.rate 0).  WAITING ON: lf_main / lf_isolate sweeps.
# by severity: lightningIntensity (0-4 multiplier, default 1), lightning.rate (per minute), lightning.distanceRange (km)
LIGHTNING = [(0.38, dict(ltI=0.8, ltRate=4.0, ltNear=2.5, ltFar=12.0)),
             (0.696, dict(ltI=1.0, ltRate=8.0, ltNear=1.5, ltFar=9.0)),
             (0.75, dict(ltI=1.15, ltRate=10.0, ltNear=1.0, ltFar=8.0))]
LIGHTNING_WEATHER_MODE = 0                # global (Baseline): see notes, the storm records carry thunder byte 255

# ---- (G) Closed decks: heavy-sky recipes (heavy-sky/recipes/heavy-sky-types.json), UNTESTED.  WAITING ON: hs_types,
# hs_isolate, hs_tune, hs_ground sweeps. Storm base by severity (user: 350-500 m, 350 wraps the peaks).
STORM_BASE_M = [(0.38, 500.0), (0.61, 430.0), (0.696, 400.0), (0.75, 350.0)]
FOG_BASE_M = 230.0                        # recipe: stratus 75 m above the Whiterun plain. If the camera-in-cloud case on
                                          # hills is bad: 300-350 (heavy-sky NOTES 6.5), or 900 for the pass-3 look.
# haze ceilings per type, any period (multiple of the saved base)
HAZE_MAX = dict(clear=2.4, fair=2.4, partly=2.4, overcast=1.75, rain=2.1, storm=1.75, snow=2.3, fog=3.45, special=1.0)

# ############################################################################################################
# ##   END OF TUNING TABLE (the sky-type cloud points follow; fair types come from pass 3 unchanged)         ##
# ############################################################################################################

# Cloud point keys added in pass 4 (heavy-sky controls), with their OFF / code-default values for fair types.
D4 = dict(p3.D)
D4.update(soft=1.0, softH=0.68, billow=0.0, relief=[-0.9, 0.2, 0.0, 0.0], reliefExp=1.0, reliefFreq=1.0, reliefThick=0.0,
          deckLight=0.0, deckHalf=400.0, deckHorizon=0.0, deckGround=0.0, dalc=None)


def pt4(**kw):
    v = copy.deepcopy(D4)
    v.update(kw)
    return v


def deck(**kw):
    """Closed deck, heavy-sky recipe common part: coverage exactly 1 (primary output z == w), secondary off, no
    coverage-driven height variation (the fold source), bottomSpread 0.4, relief from its own noise."""
    v = pt4(pri=[-0.8, 0.1, 1.0, 1.0], priExp=1.0, sec=[0.2, 0.8, 0.0, 0.0], modExp=1.0, hv=[0.0, 1.0, 0.0, 0.0],
            btr=[-0.4, 0.5, 0.0, 0.1], spread=0.4, spreadH=0.2, reliefThick=0.5, cirrus=0.0)
    v.update(kw)
    return v


def upgraded(points):
    return [(sv, pt4(**pv)) for sv, pv in points]


def interp1(table, x):
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    raise AssertionError


T = collections.OrderedDict()
for _name in ('clear', 'fair', 'partly'):
    T[_name] = dict(p3.T[_name])
    T[_name]['points'] = upgraded(p3.T[_name]['points'])
    T[_name]['why'] = 'Pass 3 unchanged (looked good at 13:00 and 17:30). ' + p3.T[_name]['why']
T['overcast'] = dict(
    label='Overcast',
    why='heavy-sky "overcast" recipe at OvercastPF: closed stratocumulus deck (coverage exactly 1), base relief + billows from '
        'independent noise, light through the deck by column depth, deck lights the ground. Lighter members higher / thinner / '
        'brighter, heavier lower / deeper. Replaces the pass-3 deck that read as a flat even sky.',
    points=[(0.30, deck(mod=[-0.45, 0.45, 0.22, 0.80], relief=[-0.9, 0.2, 0.0, 0.12], base=800.0, thick=1200.0, dens=0.85,
                        soft=0.2, softH=0.15, billow=40.0, sunExt=1.15, viewExt=1.0, msAlb=0.9975, amb=0.55,
                        deckLight=1.6, deckHalf=480.0, deckHorizon=0.45, deckGround=0.55, dalc=0.35)),
            (0.67, deck(mod=[-0.45, 0.45, 0.22, 0.85], relief=[-0.9, 0.2, 0.0, 0.14], base=700.0, thick=1400.0, dens=0.90,
                        soft=0.2, softH=0.15, billow=50.0, sunExt=1.2, viewExt=1.0, msAlb=0.997, amb=0.5,
                        deckLight=1.6, deckHalf=420.0, deckHorizon=0.5, deckGround=0.5, dalc=0.30)),
            (0.90, deck(mod=[-0.45, 0.45, 0.22, 0.90], relief=[-0.9, 0.2, 0.0, 0.15], base=650.0, thick=1500.0, dens=0.95,
                        soft=0.2, softH=0.15, billow=60.0, sunExt=1.3, viewExt=1.05, msAlb=0.996, amb=0.45,
                        deckLight=1.8, deckHalf=400.0, deckHorizon=0.55, deckGround=0.4, dalc=0.25))],
    cirrusLook='veil', haze=p3.T['overcast']['haze'], fog=p3.T['overcast']['fog'])
T['rain'] = dict(
    label='Rain',
    why='heavy-sky "rain" recipe at RainPF: closed nimbostratus at 550 m, darker bases under thick columns. Fully closed for '
        'every member (open breaks let the sun through as a bright blob); showers = a higher, thinner, brighter closed deck.',
    points=[(0.25, deck(mod=[-0.45, 0.45, 0.22, 0.90], relief=[-0.9, 0.2, 0.0, 0.15], base=650.0, thick=1500.0, dens=0.95,
                        soft=0.2, softH=0.15, billow=60.0, sunExt=1.3, viewExt=1.05, msAlb=0.996, amb=0.45,
                        deckLight=1.8, deckHalf=400.0, deckHorizon=0.55, deckGround=0.4, dalc=0.35)),
            (0.76, deck(mod=[-0.45, 0.45, 0.22, 1.0], relief=[-0.9, 0.2, 0.0, 0.16], base=550.0, thick=1700.0, dens=1.0,
                        soft=0.2, softH=0.15, billow=70.0, sunExt=1.4, viewExt=1.1, msAlb=0.995, amb=0.4,
                        deckLight=2.0, deckHalf=380.0, deckHorizon=0.6, deckGround=0.3, dalc=0.25))],
    cirrusLook='veil', haze=p3.T['rain']['haze'], fog=p3.T['rain']['fog'])
_storm = dict(mod=[-0.45, 0.45, 0.25, 1.0], relief=[-0.9, 0.2, 0.0, 0.18], thick=2000.0, dens=1.0,   # recipe 1.1: catalogue max is 1.0
              soft=0.1, softH=0.12, billow=90.0, sunExt=1.6, viewExt=1.2, msAlb=0.992, amb=0.3,
              deckLight=2.5, deckHalf=330.0, deckHorizon=0.75, deckGround=0.2, dalc=0.25)
T['storm'] = dict(
    label='Thunderstorm',
    why='heavy-sky "storm" recipe: closed deck, 2000 m slab, largest relief, shortest half depth (darkest bases). Base by '
        'severity 500 m (lightest) -> 400 m (StormPF) -> 350 m (StormTU, peaks wrapped). No heightVariation / bottomSpread '
        'shaping (the folded bands). Own lightning rate / distance / intensity.',
    points=[(sv, deck(base=b, **_storm)) for sv, b in STORM_BASE_M],
    cirrusLook='veil', haze=p3.T['storm']['haze'], fog=p3.T['storm']['fog'])
_p3snow = dict(p3.T['snow']['points'])
T['snow'] = dict(
    label='Snow',
    why='Light snow under a bright sun (SkuldafnCloudy, SnowClear) = the pass-3 thin broken cloud under a veil, unchanged. '
        'Steady snow = heavy-sky "snow" recipe (thin bright closed deck, long half depth, soft base, shallow relief). '
        'Blizzard = the same, lower and deeper.',
    points=[(0.10, pt4(**_p3snow[0.10])), (0.25, pt4(**_p3snow[0.25])),
            (0.53, deck(mod=[-0.45, 0.45, 0.30, 0.65], relief=[-0.9, 0.2, 0.0, 0.08], base=600.0, thick=900.0, dens=0.80,
                        soft=0.8, softH=0.4, billow=25.0, sunExt=1.0, viewExt=1.0, msAlb=0.999, amb=1.0,
                        deckLight=1.3, deckHalf=600.0, deckHorizon=0.3, deckGround=0.5, dalc=0.30)),
            (0.96, deck(mod=[-0.45, 0.45, 0.30, 0.85], relief=[-0.9, 0.2, 0.0, 0.12], base=500.0, thick=1400.0, dens=0.90,
                        soft=0.5, softH=0.3, billow=40.0, sunExt=1.15, viewExt=1.05, msAlb=0.997, amb=0.7,
                        deckLight=1.5, deckHalf=450.0, deckHorizon=0.4, deckGround=0.4, dalc=0.25))],
    cirrusLook='veil', haze=p3.T['snow']['haze'], fog=p3.T['snow']['fog'])
T['fog'] = dict(
    label='Fog',
    why='heavy-sky "fog" recipe: soft closed stratus with its base at %d m (75 m above the Whiterun plain, hill tops inside), '
        'the air below it belongs to Ground Fog (high amounts, almost no burn-off) + haze + height fog as in pass 3.' % FOG_BASE_M,
    points=[(0.17, deck(mod=[-0.45, 0.45, 0.30, 0.60], relief=[-0.9, 0.2, 0.0, 0.06], base=FOG_BASE_M, thick=500.0, dens=0.60,
                        soft=1.0, softH=0.6, billow=15.0, sunExt=1.0, viewExt=1.0, msAlb=0.999, amb=1.0,
                        deckLight=1.2, deckHalf=500.0, deckHorizon=0.2, deckGround=0.4, dalc=0.32)),
            (1.00, deck(mod=[-0.45, 0.45, 0.30, 0.65], relief=[-0.9, 0.2, 0.0, 0.06], base=FOG_BASE_M, thick=600.0, dens=0.70,
                        soft=1.0, softH=0.6, billow=15.0, sunExt=1.05, viewExt=1.0, msAlb=0.999, amb=1.0,
                        deckLight=1.2, deckHalf=500.0, deckHorizon=0.2, deckGround=0.4, dalc=0.28))],
    cirrusLook='veil', haze=p3.T['fog']['haze'], fog=p3.T['fog']['fog'])
T['special'] = dict(p3.T['special'])
T['special']['points'] = upgraded(p3.T['special']['points'])
TYPE_ORDER = list(T)
FAIR_TYPES = ('clear', 'fair', 'partly')
VECTOR_KEYS = ('pri', 'sec', 'mod', 'hv', 'btr', 'relief')
SCALAR_KEYS = ('priExp', 'modExp', 'hvExp', 'base', 'thick', 'dens', 'spread', 'spreadH', 'sunExt', 'viewExt', 'msAlb', 'amb',
               'cirrus', 'soft', 'softH', 'billow', 'reliefExp', 'reliefFreq', 'reliefThick', 'deckLight', 'deckHalf',
               'deckHorizon', 'deckGround')
PREFERRED_REPRESENTATIVE = p2.PREFERRED_REPRESENTATIVE

# --------------------------------------------------------------------------------------------
REGION_RE = re.compile(r'(COMA|MA|CO|TU|SN|RE|PF|FF|VT|FV)(?=_|$)')
ALT_RE = re.compile(r'_(A|ALT|Alt)(?=_|$)')


def region_of(editor_id):
    """Region from the editor id: (region key, alternate flag, dust 0..1)."""
    alt = bool(ALT_RE.search(editor_id))
    m = REGION_RE.search(editor_id)
    suffix = m.group(1) if m else None
    if 'DLC2' in editor_id and not editor_id.startswith('DLC2Apocrypha'):
        region = 'DLC2_TU' if suffix == 'TU' else 'DLC2'
    elif suffix:
        region = suffix
    else:
        region = next((r for name, r in NAMED_REGION.items() if name in editor_id), 'none')
    dust = DUST_REGION.get(region, 0.0)
    if editor_id.startswith('StormDLC2'):
        dust = DUST_ASH_STORM
    return region, alt, dust


def moisture_of(editor_id, wtype, sev):
    region, alt, dust = region_of(editor_id)
    base = MOISTURE_TYPE[wtype]
    if wtype == 'rain' and sev < 0.4:
        base = MOISTURE_SHOWERS
    if wtype == 'special':
        return dict(region='-', alt=False, dust=0.0, moisture=base, k=0.0, parts=(base, 0.0, 0.0))
    reg = MOISTURE_REGION[region]
    altd = 0.0 if not alt else (MOISTURE_ALT_IN_HUMID if region in HUMID_REGIONS else MOISTURE_ALT_ELSEWHERE)
    m = round(p2.clamp01(base + reg + altd), 3)
    k = round(p2.clamp01((m - M_DRY) / (M_HUMID - M_DRY)), 3)
    return dict(region=region, alt=alt, dust=dust, moisture=m, k=k, parts=(base, reg, altd))


def curve(group, name, period, k):
    dry, humid = CURVES[group][name][period]
    return dry + (humid - dry) * k


def settings_for(wtype, sev, f, editor_id):
    """Period-independent numbers of one weather."""
    t = T[wtype]
    v = p3.interp(t['points'], sev)
    for key in VECTOR_KEYS:
        v[key] = [round(x, 3) for x in v[key]]
    for key in SCALAR_KEYS:
        v[key] = round(v[key], 4)
    v['base'] = float(round(v['base'] / 10.0) * 10)
    v['thick'] = float(round(v['thick'] / 10.0) * 10)
    v['deckHalf'] = float(round(v['deckHalf'] / 10.0) * 10)
    v['billow'] = float(round(v['billow']))
    v['dalc'] = round(v['dalc'], 3) if v.get('dalc') is not None else None
    v['closedDeck'] = v['pri'][2] >= 1.0 and v['pri'][3] >= 1.0
    nearness = p2.fog_nearness(f['fogFarDay'])
    v['hazeDayRecord'] = round(t['haze'][0] + (t['haze'][1] - t['haze'][0]) * nearness, 3)   # pass-3 rule (closed group)
    v['windLow'], v['windHigh'] = p3.wind_for(f['wind'])
    floor_m, min_m = t['fog']
    day = p3.fog_strength(f['fogNearDay'], f['fogFarDay'], f['fogPowerDay'], f['fogMaxDay'], floor_m, min_m)
    night = p3.fog_strength(f['fogNearNight'], f['fogFarNight'], f['fogPowerNight'], f['fogMaxNight'], floor_m, min_m)
    v.update(fogDay=day[0], fogNight=night[0], fogTwilight=round(math.sqrt(day[0] * night[0]), 4),
             fogHalfRawDayM=day[1], fogHalfDayM=day[2], fogHalfRawNightM=night[1], fogHalfNightM=night[2])
    v.update(moisture_of(editor_id, wtype, sev))
    if wtype == 'storm':
        lt = {key: round(interp1([(sv, d[key]) for sv, d in LIGHTNING], sev), 2) for key in LIGHTNING[0][1]}
        v.update(lt)
    else:
        v.update(ltI=None, ltRate=0.0, ltNear=None, ltFar=None)
    return v


def air(wtype, s, period):
    """All period-dependent, moisture-dependent numbers of one weather in one period (the curves applied)."""
    group, k, dust = TYPE_GROUP[wtype], s['k'], s['dust']
    if group is None:   # other realms: neutral, as today's base
        return dict(hazeX=1.0, absorbX=1.0, absorbBlue=0.0, rayleighX=1.0, ozoneX=1.0, phaseG=BASE['phaseG'], sunX=1.0,
                    scatterTint=(1.0, 1.0, 1.0), dalc=None, skySat=None, skyScale=None, envSat=None, gfNear=None, gfValley=None,
                    gfMidday=None, gfRetention=None, gfBurnOff=None, rays=0.0)
    a = {name: curve(group, name, period, k) for name in ('hazeX', 'absorbX', 'absorbBlue', 'rayleighX', 'ozoneX', 'phaseG',
                                                         'sunX', 'skySat', 'skyScale', 'envSat', 'rays')}
    if group == 'fair':
        a['hazeX'] += DUST['hazeAdd'] * dust
        if period == 'Day':
            a['hazeX'] = min(a['hazeX'], FAIR_DAY_HAZE_CAP)
        a['dalc'] = curve(group, 'dalc', period, k)
        a['gfNear'] = curve(group, 'gfNear', period, k)
        a['gfValley'] = curve(group, 'gfValley', period, k)
        g = GROUND_FOG_FAIR
        a['gfMidday'], a['gfRetention'], a['gfBurnOff'] = (g[n][0] + (g[n][1] - g[n][0]) * k for n in ('midday', 'retention', 'burnOff'))
    else:
        a['hazeX'] = s['hazeDayRecord'] * a['hazeX'] + 0.15 * dust
        if s.get('dalc') is None:
            a['dalc'] = BASE['dalc']
        elif period == 'Night':
            a['dalc'] = BASE['dalc']
        elif period in ('Dawn', 'Dusk'):
            a['dalc'] = (s['dalc'] + BASE['dalc']) / 2.0
        else:
            a['dalc'] = s['dalc']
        g = GROUND_FOG_CLOSED[wtype]
        scale = GROUND_FOG_CLOSED_PERIOD[period]
        near = g['near'][0] + (g['near'][1] - g['near'][0]) * k
        valley = g['valley'][0] + (g['valley'][1] - g['valley'][0]) * k
        if wtype == 'snow':
            near *= 1.0 - 0.6 * s['sev']
            valley *= 1.0 - 0.6 * s['sev']
        if wtype == 'fog':
            near += 0.8 * s['sev']
            valley += 0.8 * s['sev']
        a['gfNear'], a['gfValley'] = min(4.0, near * scale), min(4.0, valley * scale)
        a['gfMidday'], a['gfRetention'], a['gfBurnOff'] = g['midday'], g['retention'], g['burnOff']
    a['hazeX'] = min(a['hazeX'], HAZE_MAX[wtype])
    a['absorbX'] *= 1.0 + DUST['absorbAdd'] * dust
    a['absorbBlue'] += DUST['blueAdd'] * dust
    a['scatterTint'] = tuple(1.0 + (c - 1.0) * dust for c in DUST['scatterTint'])
    for name in a:
        if isinstance(a[name], float):
            a[name] = round(a[name], 4)
    return a


def xyzw(vals, keys='xyzw'):
    return dict(zip(keys, [float(x) for x in vals]))


def sky_tree(s, wtype, aurora, period):
    t = T[wtype]
    a = air(wtype, s, period)
    pri, cirrus = list(s['pri']), s['cirrus']
    cirrus *= t.get('cirrusPeriodScale', {}).get(period, 1.0)
    if aurora and wtype in p3.AURORA_TYPES and period in p3.DARK_PERIODS:
        pri[0] = round(pri[0] + p3.AURORA_IN_SHIFT, 3)
        pri[1] = round(pri[1] + p3.AURORA_IN_SHIFT, 3)
        cirrus = 0.0
    look = p3.CIRRUS_LOOKS[t['cirrusLook']]
    loading = BASE['loading'] * a['hazeX']
    b = a['absorbBlue']
    scatter = [round(c * loading * tint, 4) for c, tint in zip(p2.CONTINENTAL_RH50_SCATTER, a['scatterTint'])]
    absorption = [round(c * loading * a['absorbX'] * w, 5) for c, w in zip(p2.CONTINENTAL_RH50_ABSORPTION, (1.0, 1.0 + b / 2.0, 1.0 + b))]
    tree = collections.OrderedDict()
    tree['aerosolScatter'] = xyzw(scatter, 'xyz')
    tree['aerosolAbsorption'] = xyzw(absorption, 'xyz')
    tree['aerosolPhaseG'] = float(a['phaseG'])
    tree['rayleighScatter'] = xyzw([round(c * a['rayleighX'], 4) for c in BASE['rayleigh']], 'xyz')
    tree['rayleighScatterAP1'] = xyzw([round(c * a['rayleighX'], 4) for c in BASE['rayleighAP1']], 'xyz')
    tree['ozoneAbsorption'] = xyzw([round(c * a['ozoneX'], 4) for c in BASE['ozone']], 'xyz')
    tree['ozoneAbsorptionAP1'] = xyzw([round(c * a['ozoneX'], 4) for c in BASE['ozoneAP1']], 'xyz')
    tree['sunlightColor'] = xyzw([round(c * a['sunX'], 4) for c in BASE['sun']], 'xyz')
    if s.get('ltI') is not None:
        tree['lightningIntensity'] = float(s['ltI'])
        tree['lightning'] = {'rate': float(s['ltRate']), 'distanceRange': xyzw([s['ltNear'], s['ltFar']], 'xy')}
    else:
        tree['lightning'] = {'rate': 0.0}
    tree['cloudMap'] = {'procedural': {'parameters': collections.OrderedDict([
        ('primary', {'range': xyzw(pri), 'exponent': float(s['priExp'])}),
        ('secondary', {'range': xyzw(s['sec'])}),
        ('modeling', {'range': xyzw(s['mod']), 'exponent': float(s['modExp'])}),
        ('heightVariation', {'range': xyzw(s['hv']), 'exponent': float(s['hvExp'])}),
        ('bottomTypeRange', xyzw(s['btr'])),
        ('baseRelief', {'range': xyzw(s['relief']), 'exponent': float(s['reliefExp']), 'frequency': float(s['reliefFreq'])}),
        ('baseReliefThickness', float(s['reliefThick'])),
    ])}}
    tree['cloudLayer'] = collections.OrderedDict([
        ('low', {'ndfAltitudeOffset': s['base'], 'ndfAltitudeScale': s['thick'], 'densityScale': float(s['dens']),
                 'bottomSpreadScale': float(s['spread']), 'bottomSpreadHeight': float(s['spreadH']),
                 'bottomSoftness': float(s['soft']), 'bottomSoftnessHeight': float(s['softH']),
                 'baseBillowHeight': float(s['billow'])}),
        ('lighting', {'sunExtinction': float(s['sunExt']), 'viewExtinction': float(s['viewExt']),
                      'msAlbedo': float(s['msAlb']), 'ambientStrength': float(s['amb']),
                      'deckLight': float(s['deckLight']), 'deckHalfDepth': float(s['deckHalf']),
                      'deckHorizonLight': float(s['deckHorizon']), 'deckGroundLight': float(s['deckGround'])}),
        ('wind', {'lowVelocity': xyzw(s['windLow'], 'xy'), 'highVelocity': xyzw(s['windHigh'], 'xy')}),
        ('cirrus', {'altitude': float(look['altitude']), 'densityScale': float(round(cirrus, 3)),
                    'weather': copy.deepcopy(look['state'])}),
    ])
    return tree


def fog_tree(s, period):
    return p3.fog_tree(s, period)


def ibl_tree(s, wtype, period):
    a = air(wtype, s, period)
    if a['dalc'] is None:
        return None
    return collections.OrderedDict([('DALCAmount', float(round(a['dalc'], 3))), ('SkyIBLSaturation', float(round(a['skySat'], 3))),
                                    ('SkyIBLScale', float(round(a['skyScale'], 3))), ('EnvIBLSaturation', float(round(a['envSat'], 3)))])


def groundfog_tree(s, wtype, period):
    a = air(wtype, s, period)
    if a['gfNear'] is None:
        return None
    return collections.OrderedDict([('Amount', float(round(a['gfNear'], 3))), ('FarAmount', float(round(a['gfValley'], 3))),
                                    ('MiddayAmount', float(round(a['gfMidday'], 3))), ('ShadowRetention', float(round(a['gfRetention'], 3))),
                                    ('BurnOffStrength', float(round(a['gfBurnOff'], 3)))])


def gf_effective(s, wtype, period):
    """Near amount on sunlit ground after the feature's own time-of-day curve: Amount x lerp(1, curve, BurnOffStrength).
    curve = MorningAmount (Dawn, Sunrise), MiddayAmount (Day), EveningAmount (Sunset, Dusk), their mean at Night."""
    a = air(wtype, s, period)
    if a['gfNear'] is None:
        return None
    c = {'Dawn': BASE['gfMorning'], 'Sunrise': BASE['gfMorning'], 'Day': a['gfMidday'], 'Sunset': BASE['gfEvening'],
         'Dusk': BASE['gfEvening'], 'Night': (BASE['gfMorning'] + BASE['gfEvening']) / 2.0}[period]
    return round(a['gfNear'] * (1.0 + (c - 1.0) * a['gfBurnOff']), 3)


def rays_block(s, wtype, period):
    """Effects11 standalone rays: NOT scene-drivable. Harness-only (the *_rays sweeps) and documentation."""
    v = air(wtype, s, period)['rays']
    on = v > 0.005
    d = collections.OrderedDict([('StandaloneRays', on), ('StandaloneSunRays', on and period != 'Night'),
                                 ('StandaloneMoonRays', on and period == 'Night')])
    if on:
        d['StandaloneMoonMultiplier' if period == 'Night' else 'StandaloneSunMultiplier'] = round(v, 3)
    return d


FEATURE_TREES = (('PhysicalSky', lambda s, t, au, p: sky_tree(s, t, au, p)),
                 ('ExponentialHeightFog', lambda s, t, au, p: fog_tree(s, p)),
                 ('ImageBasedLighting', lambda s, t, au, p: ibl_tree(s, t, p)),
                 ('GroundFog', lambda s, t, au, p: groundfog_tree(s, t, p)))


def baseline_doc():
    d = p3.baseline_doc()
    d['_metadata'] = {'version': '0.4.0',
                      'description': PACK + ': global base saved in game 2026-11-19 + high-layer UV size 3, the sparse-streak high-layer '
                                     'pattern, and lightning set to "any weather" with a global rate of 0 (storm weathers carry their '
                                     'own rate). Per-weather files are UNTESTED.'}
    d['lightning'] = {'weatherMode': LIGHTNING_WEATHER_MODE, 'rate': 0.0}
    return d


MANIFEST = {
    'name': 'foxnne NAT III clouds (pass 4)',
    'version': '0.4.0',
    'type': 'CS',
    'author': 'foxnne',
    'description': 'UNTESTED DRAFT, pass 4. Per-weather, per-period sky for the 111 NAT.CS III weathers: haze, air, ozone, glow and sun '
                   'strength follow the sun height and a per-weather moisture value; closed heavy-sky decks for overcast, rain, storm, '
                   'snow and fog; storm lightning (Physical Sky); height-fog strength (Exponential Height Fog); ambient mix (Image '
                   'Based Lighting); Ground Fog amounts. Needs a build that contains foxnne/heavy-sky, foxnne/lightning-fix and '
                   'foxnne/ground-fog-near. Read notes/install-pass-4.md first.',
    'tags': ['NAT.CS III', 'Physical Sky', 'volumetric clouds', 'draft'],
    'csVersion': '1.9.0',
    'requiredFeatures': ['PhysicalSky', 'ExponentialHeightFog', 'ImageBasedLighting', 'GroundFog', 'SceneManager', 'SkySync'],
    'requiredPlugins': ['NAT-ENB.esp', 'NAT-CS.esp'],
}

NOT_DRIVABLE = collections.OrderedDict([
    ('Effects11.StandaloneRays / StandaloneSunRays / StandaloneMoonRays / StandaloneSunMultiplier / StandaloneMoonMultiplier',
     'catalogue rows are Persisted | Hidden (not transitionable, not scene-controllable) and Effects11 is in no scene whitelist. '
     'Values are in "Effects11.notSceneDrivable" per representative and in the *_rays sweeps; set one global strength, or make the '
     'keys scene-controllable + whitelist Effects11 for time-of-day scenes.'),
    ('SkySync.HorizonFadeElevation / HorizonFadeHours',
     'rows are scene-controllable but the SkySync feature is not in kTimeOfDayFeatureWhitelist: global only (saved 1.5; look pack 9.3).'),
    ('VolumetricLighting.* and ViewAtmosphere.*', 'whole features are scene-blacklisted: global only.'),
    ('PhysicalSky.lightning.weatherMode', 'Integer row, not transitionable: global only. In the pack Baseline as 0.'),
    ('PhysicalSky.cloudLayer.cirrus.uvSize', 'blacklisted: Baseline (3.0), as in pass 3.'),
    ('PhysicalSky.cloudMap.procedural.parameters.baseRelief.noise', 'blacklisted integer slot: code default 1 is what the recipes use.'),
    ('PhysicalSky.aerosolType / aerosolLoading / aerosolHumidity', 'blacklisted: haze is written as aerosolScatter / aerosolAbsorption coefficients.'),
    ('PhysicalSky.cloudLayer.low.densityScale 1.1 (storm recipe)', 'catalogue range is 0..1: written as 1.0.'),
])
GLOBAL_ONLY = {'PhysicalSky': {'cloudLayer.cirrus.uvSize': p3.CIRRUS_UV_SIZE, 'lightning.weatherMode': LIGHTNING_WEATHER_MODE,
                               'cloudMap.procedural.parameters.baseRelief.noise': 1},
               'why': 'uvSize and baseRelief.noise are scene-blacklisted; lightning.weatherMode is an integer (not blendable). All three '
                      'are in the pack Baseline or are code defaults; the sweep files set uvSize and weatherMode in every variant.'}


def write_json(path, data, compact=False):
    p3.write_json(path, data, compact)


def fmt_vec(v):
    return p3.fmt_vec(v)


def main():
    masters, recs = wthr_parse.load()
    cat = json.load(open(os.path.join(HERE, 'scene-catalog-pass4.json'), encoding='utf-8'))
    val = p3.Validator(cat)

    for d in (os.path.join(PACK_DIR, 'Weather'), os.path.join(PACK_DIR, 'Baseline'), SWEEP_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)

    rows, problems, user_fragment = [], [], {}
    files = collections.Counter()
    for w in recs:
        f = p2.facts(w)
        wtype, sev = p2.classify(w['editorId'], f)
        s = settings_for(wtype, sev, f, w['editorId'])
        s['sev'] = sev
        entries = []
        for period in PERIODS:
            where = '%s/%s' % (w['editorId'], period)
            for feature, make in FEATURE_TREES:
                tree = make(s, wtype, f['aurora'], period)
                if tree is None:
                    continue
                problems += val.check(feature, tree, where)
                doc = collections.OrderedDict([
                    ('_feature', feature),
                    ('_metadata', {'description': '%s - %s, severity %.2f, moisture %.2f (%s) - %s' % (
                        PACK, T[wtype]['label'], sev, s['moisture'], w['editorId'], period), 'timeOfDayEnabled': True})])
                doc.update(tree)
                write_json(os.path.join(PACK_DIR, 'Weather', w['spid'], period, '%s_%s.json' % (PACK, feature)), doc)
                files[feature] += 1
                for path, key, value in p3.leaves(tree):
                    entries.append({'feature': feature, 'path': list(path), 'setting': key, 'value': value,
                                    'originalValue': value, 'paused': False, 'period': period})
        user_fragment[w['spid']] = {'entries': entries}
        rows.append(dict(w=w, f=f, type=wtype, sev=sev, s=s))

    write_json(os.path.join(PACK_DIR, PACK + '.json'), MANIFEST)
    write_json(os.path.join(PACK_DIR, 'Baseline', 'PhysicalSky.json'), baseline_doc())
    write_json(os.path.join(USER_DIR, 'SceneManager.weather.pass4.json'), user_fragment, compact=True)

    # ---- sanity checks beyond the catalogue
    for name in TYPE_ORDER:
        members = sorted((r for r in rows if r['type'] == name), key=lambda r: r['sev'])
        for a, b in zip(members, members[1:]):
            if (b['s']['pri'][0] > a['s']['pri'][0] + 1e-9 or b['s']['base'] > a['s']['base'] + 1e-9 or
                    b['s']['dens'] < a['s']['dens'] - 1e-9):
                problems.append('not monotonic within %s: %s -> %s' % (name, a['w']['editorId'], b['w']['editorId']))
    fair_unchanged = 0
    for r in rows:
        s, n, e = r['s'], r['type'], r['w']['editorId']
        for period in PERIODS:
            a = air(n, s, period)
            if a['hazeX'] > HAZE_MAX[n] + 1e-9:
                problems.append('%s/%s: haze %.2fx above the %s ceiling' % (e, period, a['hazeX'], n))
            if n in FAIR_TYPES and period == 'Day' and a['hazeX'] > FAIR_DAY_HAZE_CAP + 1e-9:
                problems.append('%s: Day haze %.2fx above today\'s base' % (e, a['hazeX']))
            if not (0.0 <= a['phaseG'] <= 0.95):
                problems.append('%s/%s: phase g %.3f' % (e, period, a['phaseG']))
        if s['windLow'][0] > p3.LOW_DRIFT_CAP + 1e-9:
            problems.append('%s: low drift above the cap' % e)
        if n in ('overcast', 'rain', 'storm', 'fog') and not s['closedDeck']:
            problems.append('%s: %s deck is not closed (primary output z, w must be 1)' % (e, n))
        if s['closedDeck'] and (s['hv'][2] != 0.0 or s['hv'][3] != 0.0 or s['spread'] > 0.4 + 1e-9):
            problems.append('%s: closed deck uses the fold-prone shaping (heightVariation / bottomSpread)' % e)
        if s['closedDeck'] and not (900.0 <= s['thick'] <= 2000.0) and n != 'fog':
            problems.append('%s: slab %d m outside 900-2000' % (e, s['thick']))
        if n == 'storm' and not (350.0 <= s['base'] <= 500.0):
            problems.append('%s: storm base %d m outside 350-500' % (e, s['base']))
        if (n == 'storm') != (s['ltI'] is not None) or (n != 'storm' and s['ltRate'] != 0.0):
            problems.append('%s: lightning on a non-storm weather / missing on a storm' % e)
        # fair types: the cloud field must be exactly the pass-3 one (every key pass 3 wrote, all six periods)
        if n in FAIR_TYPES:
            s3 = p3.settings_for(n, r['sev'], r['f'])
            for period in PERIODS:
                old = p3.sky_tree(s3, n, r['sev'], r['f']['aurora'], period)
                new = sky_tree(s, n, r['f']['aurora'], period)
                oldf = {k: v for k, v in p3.flat({'cloudMap': old['cloudMap'], 'cloudLayer': old['cloudLayer']}).items()}
                newf = p3.flat({'cloudMap': new['cloudMap'], 'cloudLayer': new['cloudLayer']})
                diff = [k for k, v in oldf.items() if newf.get(k) != v]
                if diff:
                    problems.append('%s/%s: fair-weather cloud field differs from pass 3: %s' % (e, period, diff[:4]))
            fair_unchanged += 1

    # ---- representatives
    counts = collections.Counter(r['type'] for r in rows)

    def describe(r):
        s, n = r['s'], r['type']
        day = p3.flat(sky_tree(s, n, r['f']['aurora'], 'Day'))
        overrides = collections.OrderedDict()
        for period in PERIODS:
            if period == 'Day':
                continue
            other = p3.flat(sky_tree(s, n, r['f']['aurora'], period))
            diff = collections.OrderedDict((k, v) for k, v in other.items() if day.get(k) != v)
            if diff:
                overrides[period] = diff

        def per_period(make):
            out = collections.OrderedDict()
            for period in PERIODS:
                tree = make(period)
                if tree is None:
                    return None
                for k, v in tree.items():
                    out['%s.%s' % (k, period)] = v
            return out
        curves = collections.OrderedDict()
        for period in PERIODS:
            a = air(n, s, period)
            curves[period] = collections.OrderedDict((k, a[k]) for k in ('hazeX', 'absorbX', 'absorbBlue', 'rayleighX', 'ozoneX',
                                                                         'phaseG', 'sunX', 'dalc', 'skySat', 'skyScale', 'envSat',
                                                                         'gfNear', 'gfValley', 'rays'))
            curves[period]['gfNearEffectiveSunlit'] = gf_effective(s, n, period)
        return collections.OrderedDict([
            ('editorId', r['w']['editorId']), ('formKey', r['w']['spid']), ('localFormId', r['w']['spid'].split('~')[0]),
            ('plugin', r['w']['spid'].split('~')[1]), ('severity', round(r['sev'], 3)),
            ('moisture', s['moisture']), ('moistureCurvePosition', s['k']), ('region', s['region']), ('alternateRecord', s['alt']),
            ('dust', s['dust']),
            ('PhysicalSky.Day', day),
            ('PhysicalSky.periodOverrides', overrides),
            ('ExponentialHeightFog', collections.OrderedDict([
                ('vanillaFogStrength.Day', s['fogDay']), ('vanillaFogStrength.Night', s['fogNight']),
                ('vanillaFogStrength.DawnDusk', s['fogTwilight']),
                ('halfOpacityDistanceDayM', round(min(s['fogHalfDayM'], 99999))),
                ('halfOpacityDistanceNightM', round(min(s['fogHalfNightM'], 99999)))])),
            ('ImageBasedLighting', per_period(lambda p: ibl_tree(s, n, p))),
            ('GroundFog', per_period(lambda p: groundfog_tree(s, n, p))),
            ('Effects11.notSceneDrivable', per_period(lambda p: rays_block(s, n, p)) if TYPE_GROUP[n] else None),
            ('curveValues', curves),
        ])

    reps = collections.OrderedDict()
    for name in TYPE_ORDER:
        members = sorted((r for r in rows if r['type'] == name), key=lambda r: (r['sev'], r['w']['editorId']))
        rep = next((r for r in members if r['w']['editorId'] == PREFERRED_REPRESENTATIVE.get(name)), members[len(members) // 2])
        opposite = other = None
        if name in FAIR_TYPES:
            # second representative: the dust-free member farthest from the representative in moisture (ties: the more humid);
            # third, only where it adds something: the extreme on the other side if its curve position differs by > 0.2
            pool = [r for r in members if r is not rep and r['s']['dust'] == 0.0]
            opposite = max(pool, key=lambda r: (abs(r['s']['moisture'] - rep['s']['moisture']), r['s']['moisture'], r['w']['editorId']))
            side = 1 if opposite['s']['moisture'] > rep['s']['moisture'] else -1
            far = max(pool, key=lambda r: (-side * r['s']['moisture'], r['w']['editorId']))
            if abs(far['s']['k'] - rep['s']['k']) > 0.2 and far is not opposite:
                other = far
        reps[name] = dict(rep=rep, opposite=opposite, other=other, light=members[0], heavy=members[-1], members=members)

    summary = collections.OrderedDict([
        ('_note', 'UNTESTED. Same shape as pass3-sky-types.json: per type a "representative" with "PhysicalSky.Day" (flat dotted paths; '
                  'vector components .x/.y/.z/.w; "cloudLayer.cirrus.weather" is ONE value, the whole {"states": [...]} blend object) and '
                  '"PhysicalSky.periodOverrides" (per other period only the keys that differ from Day). New in pass 4: fair types '
                  '(clear, fair, partly) also carry "representativeOppositeMoisture"; feature blocks use "<Setting>.<Period>" keys for all '
                  'six periods ("ImageBasedLighting", "GroundFog"); "Effects11.notSceneDrivable" is a harness-only proposal; '
                  '"curveValues" shows the multipliers behind the numbers. "globalOnly" must be set once globally.'),
        ('pack', PACK),
        ('requiresBuild', 'foxnne/heavy-sky + foxnne/lightning-fix + foxnne/ground-fog-near merged'),
        ('globalOnly', GLOBAL_ONLY),
        ('notSceneDrivable', NOT_DRIVABLE),
        ('savedBase', BASE),
        ('moistureRule', collections.OrderedDict([
            ('formula', 'moisture = clamp01(type + region + alternate); curve position k = clamp01((moisture - %g) / (%g - %g))' % (M_DRY, M_HUMID, M_DRY)),
            ('type', MOISTURE_TYPE), ('showers', MOISTURE_SHOWERS), ('region', MOISTURE_REGION),
            ('alternateInHumidRegion', MOISTURE_ALT_IN_HUMID), ('alternateElsewhere', MOISTURE_ALT_ELSEWHERE),
            ('dustRegion', DUST_REGION), ('namedRegion', NAMED_REGION)])),
        ('curves', CURVES), ('dust', DUST), ('groundFogFair', GROUND_FOG_FAIR), ('groundFogClosed', GROUND_FOG_CLOSED),
        ('lightningBySeverity', [dict(severity=sv, **d) for sv, d in LIGHTNING]),
        ('suggestedHours', SWEEP_HOURS),
        ('types', collections.OrderedDict())])
    for name, g in reps.items():
        t = T[name]
        summary['types'][name] = collections.OrderedDict([
            ('label', t['label']), ('rationale', t['why']), ('count', counts[name]), ('curveGroup', TYPE_GROUP[name]),
            ('definition_points_by_severity', [collections.OrderedDict([('severity', sv)] + list(pv.items())) for sv, pv in t['points']]),
            ('highLayerLook', p3.CIRRUS_LOOKS[t['cirrusLook']]['label']),
            ('hazeDayRange_closedTypes_fogFar150000_to_5000', list(t['haze'])),
            ('heightFog_floorM_minM', list(t['fog'])),
            ('representative', describe(g['rep'])),
            ('representativeOppositeMoisture', describe(g['opposite']) if g['opposite'] else None),
            ('representativeOtherExtreme', describe(g['other']) if g['other'] else None),
            ('lightestMember', describe(g['light']) if g['light'] is not g['rep'] else None),
            ('heaviestMember', describe(g['heavy']) if g['heavy'] is not g['rep'] else None),
            ('members', [{'editorId': r['w']['editorId'], 'formKey': r['w']['spid'], 'severity': round(r['sev'], 3),
                          'moisture': r['s']['moisture'], 'region': r['s']['region'], 'dust': r['s']['dust']} for r in g['members']]),
        ])
    write_json(os.path.join(DRAFT, 'pass4-sky-types.json'), summary)

    # ---- harness sweeps: one file per period, variants = each representative with that period's values applied
    sweep_reps = []
    for name in TYPE_ORDER:
        if name == 'special':
            continue
        g = reps[name]
        if g['opposite'] is None:
            sweep_reps.append((name, '', g['rep']))
        else:
            for r in sorted((x for x in (g['rep'], g['opposite'], g['other']) if x), key=lambda r: r['s']['moisture']):
                sweep_reps.append((name, 'm%02d' % round(r['s']['moisture'] * 100), r))
    sweep_files = []
    for period in SWEEP_PERIODS:
        for with_rays in (False, True):
            variants = []
            for i, (name, tag, r) in enumerate(sweep_reps):
                s, n = r['s'], r['type']
                tree = json.loads(json.dumps(sky_tree(s, n, r['f']['aurora'], period)))
                tree['cloudLayer']['cirrus']['uvSize'] = p3.CIRRUS_UV_SIZE
                tree['lightning']['weatherMode'] = LIGHTNING_WEATHER_MODE
                feats = collections.OrderedDict([('ExponentialHeightFog', fog_tree(s, period)),
                                                 ('ImageBasedLighting', ibl_tree(s, n, period)),
                                                 ('GroundFog', groundfog_tree(s, n, period))])
                if with_rays:
                    feats['Effects11'] = rays_block(s, n, period)
                variants.append(collections.OrderedDict([
                    ('name', '%02d_%s_%s%s' % (i, name, (tag + '_') if tag else '', r['w']['editorId'])),
                    ('set', tree), ('features', feats), ('weather', r['w']['editorId']), ('settle', 16)]))
            fn = 'pass4_types_%s%s.json' % (period.lower(), '_rays' if with_rays else '')
            write_json(os.path.join(SWEEP_DIR, fn), variants)
            sweep_files.append((fn, len(variants)))

    write_table(rows, reps, counts)

    print('weathers:', len(rows))
    print('scene files:', ', '.join('%s %d' % kv for kv in files.items()), '= %d' % sum(files.values()))
    print('types:', ', '.join('%s %d' % (n, counts[n]) for n in TYPE_ORDER))
    print('user-layer entries:', sum(len(v['entries']) for v in user_fragment.values()))
    print('distinct scene settings written (pack):', len(val.used))
    print('  by feature:', dict(collections.Counter(k.split(' ')[0] for k in val.used)))
    print('fair-type weathers whose cloud field equals pass 3 in all six periods:', fair_unchanged, 'of', sum(counts[n] for n in FAIR_TYPES))
    print('sweeps:', ', '.join('%s (%d)' % x for x in sweep_files))
    print('catalog:', cat['source'])
    print('validation problems:', len(problems))
    for p in sorted(set(problems))[:60]:
        print('  ', p)
    return 1 if problems else 0


def write_table(rows, reps, counts):
    out = ['# NAT.CS III weather table, pass 4 (untested)', '',
           'Generated by `draft/_generator/build_pass4.py`. Do not edit by hand; edit the TUNING TABLE at the top of the generator and re-run.',
           'Record facts are parsed from `NAT-CS.esp`. Types and severities are the pass-2 rules, unchanged.',
           '**Nothing here was seen in game.** Every number of the tuning table is provisional.', '',
           '## Moisture rule', '',
           '`moisture = clamp01(type + region + alternate)`; curve position `k = clamp01((moisture - %g) / (%g - %g))` (k 0 = the "dry" column of a curve, 1 = the "humid" column).' % (M_DRY, M_HUMID, M_DRY), '',
           '| Part | Values |', '|---|---|',
           '| type | %s; rain under a bright sun (showers, severity < 0.4) %g |' % (', '.join('%s %g' % kv for kv in MOISTURE_TYPE.items()), MOISTURE_SHOWERS),
           '| region (editor id suffix) | %s |' % ', '.join('%s %+g' % kv for kv in MOISTURE_REGION.items()),
           '| named records | %s |' % ', '.join('%s -> %s' % kv for kv in NAMED_REGION.items()),
           '| alternate record (`_A`, `_Alt`, `_ALT`) | %+g in a humid region (MA, CO, COMA: the cleaner day), %+g elsewhere (the hazier day) |' % (MOISTURE_ALT_IN_HUMID, MOISTURE_ALT_ELSEWHERE),
           '| dust (separate value, not moisture) | %s; Solstheim ash storms %g. Adds haze x %g, absorption x (1 + %g x dust), blue weighting + %g x dust, scatter tint toward %s in every period. |' % (
               ', '.join('%s %g' % kv for kv in DUST_REGION.items()), DUST_ASH_STORM, DUST['hazeAdd'], DUST['absorbAdd'], DUST['blueAdd'], fmt_vec(DUST['scatterTint'])),
           '', '## Period curves (the tuning table)', '',
           'Each cell: dry -> humid. Group `fair` = clear, fair, partly; group `closed` = overcast, rain, storm, snow, fog.', '',
           '| Group | Curve | Dawn | Sunrise | Day | Sunset | Dusk | Night |', '|---|---|---|---|---|---|---|---|']
    for group in ('fair', 'closed'):
        for name, c in CURVES[group].items():
            if c is None:
                out.append('| %s | %s | per type, see below | | | | | |' % (group, name))
            else:
                out.append('| %s | %s | %s |' % (group, name, ' | '.join('%g -> %g' % c[p] if c[p][0] != c[p][1] else '%g' % c[p][0] for p in PERIODS)))
    out += ['', 'hazeX: fair = multiple of the saved base (loading %g), Day capped at %g; closed = multiple of the type\'s own Day haze (pass-3 record rule). '
            'absorbX / absorbBlue: `aerosolAbsorption` x absorbX x (1, 1 + b/2, 1 + b). rayleighX / ozoneX: multiples of the code defaults. '
            'sunX: multiple of `sunlightColor` %s. gfNear / gfValley: Ground Fog `Amount` / `FarAmount`. rays: Effects11 standalone rays strength (not scene-drivable).' % (
                BASE['loading'], FAIR_DAY_HAZE_CAP, fmt_vec(BASE['sun'])), '',
            'Ground Fog, fair group per weather: MiddayAmount %g -> %g, ShadowRetention %g -> %g, BurnOffStrength %g.' % (
                GROUND_FOG_FAIR['midday'] + GROUND_FOG_FAIR['retention'] + (GROUND_FOG_FAIR['burnOff'][0],)), '',
            '| Closed type | Amount dry -> humid | FarAmount dry -> humid | MiddayAmount | ShadowRetention | BurnOffStrength |', '|---|---|---|---|---|---|']
    for name, g in GROUND_FOG_CLOSED.items():
        out.append('| %s | %g -> %g | %g -> %g | %g | %g | %g |' % (name, g['near'][0], g['near'][1], g['valley'][0], g['valley'][1], g['midday'], g['retention'], g['burnOff']))
    out += ['', 'Closed types x period factor %s; snow x (1 - 0.6 x severity); fog + 0.8 x severity.' % ', '.join('%s %g' % (p, GROUND_FOG_CLOSED_PERIOD[p]) for p in PERIODS),
            '', '## Representatives: values per period', '',
            'haze = multiple of the saved base; air / ozone = Rayleigh / ozone multiple; g = aerosol phase g; sun = sun strength multiple; '
            'DALC / skySat / skyScale = Image Based Lighting; GF near / valley = Ground Fog Amount / FarAmount; GF eff = near amount left on sunlit '
            'ground after the feature\'s own time-of-day curve; rays = proposed standalone rays strength (not drivable).', '',
            '| Weather (type, moisture) | Period | haze | absorb x (blue b) | air | ozone | g | sun | DALC | skySat | skyScale | GF near | GF valley | GF eff | rays |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for name in TYPE_ORDER:
        if name == 'special':
            continue
        g = reps[name]
        for r in [x for x in (g['rep'], g['opposite'], g['other']) if x]:
            s = r['s']
            for period in PERIODS:
                a = air(name, s, period)
                out.append('| %s | %s | %g | %g (%g) | %g | %g | %g | %g | %g | %g | %g | %g | %g | %g | %g |' % (
                    '%s (%s, m %.2f%s)' % (r['w']['editorId'], name, s['moisture'], ', dust %g' % s['dust'] if s['dust'] else '') if period == 'Dawn' else '',
                    period, a['hazeX'], a['absorbX'], a['absorbBlue'], a['rayleighX'], a['ozoneX'], a['phaseG'], a['sunX'], round(a['dalc'], 3),
                    a['skySat'], a['skyScale'], a['gfNear'], a['gfValley'], gf_effective(s, name, period), a['rays']))
    out += ['', '## Sky types: cloud field (period-independent except the aurora and high-layer rules of pass 3)', '',
            'primary / modeling = `cloudMap.procedural.parameters.<layer>.range`; relief = `baseRelief.range` z-w (lift as a share of the slab) x `baseReliefThickness`; '
            'slab = `ndfAltitudeOffset + ndfAltitudeScale`; soft = `bottomSoftness / bottomSoftnessHeight`; billow = `baseBillowHeight` m; '
            'lighting = sunExtinction / viewExtinction / msAlbedo / ambientStrength; deck = deckLight / deckHalfDepth m / deckHorizonLight / deckGroundLight; '
            'lightning = `lightningIntensity`, `lightning.rate`, `lightning.distanceRange` km.', '',
            '| Type | | Weather (sev) | primary | secondary | modeling | hv | relief | slab m | dens | spread | soft | billow | lighting | deck | high | haze Day | fog str day / night | DALC day | lightning | drift |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']

    def member_line(tag, r):
        s = r['s']
        a = air(r['type'], s, 'Day')
        cir = [sky_tree(s, r['type'], False, p)['cloudLayer']['cirrus']['densityScale'] for p in ('Day', 'Sunset')]
        return '| %s | %s | %s (%.2f) | %s ^%g | %s | %s ^%g | %s | %g-%g x%g | %d + %d | %g | %g / %g | %g / %g | %g | %g / %g / %g / %g | %g / %d / %g / %g | %s | %gx | %g / %g | %s | %s | %g |' % (
            r['type'] if tag == 'rep' else '', tag, r['w']['editorId'], r['sev'], fmt_vec(s['pri']), s['priExp'], fmt_vec(s['sec']),
            fmt_vec(s['mod']), s['modExp'], fmt_vec(s['hv']), s['relief'][2], s['relief'][3], s['reliefThick'], s['base'], s['thick'], s['dens'],
            s['spread'], s['spreadH'], s['soft'], s['softH'], s['billow'], s['sunExt'], s['viewExt'], s['msAlb'], s['amb'],
            s['deckLight'], s['deckHalf'], s['deckHorizon'], s['deckGround'],
            ('%g' % cir[0]) if cir[0] == cir[1] else '%g day / %g twilight' % (cir[0], cir[1]),
            a['hazeX'], s['fogDay'], s['fogNight'], '-' if a['dalc'] is None else '%g' % a['dalc'],
            'rate 0' if s['ltI'] is None else '%g, %g/min, [%g, %g] km' % (s['ltI'], s['ltRate'], s['ltNear'], s['ltFar']), s['windLow'][0])
    for name in TYPE_ORDER:
        g = reps[name]
        if g['light'] is not g['rep'] and g['light']['sev'] < g['rep']['sev'] - 1e-9:
            out.append(member_line('lightest', g['light']))
        out.append(member_line('rep', g['rep']))
        if g['heavy'] is not g['rep'] and g['heavy']['sev'] > g['rep']['sev'] + 1e-9:
            out.append(member_line('heaviest', g['heavy']))
    out += ['', '| Type | Weathers | Rationale |', '|---|---|---|']
    for name in TYPE_ORDER:
        out.append('| %s | %d | %s |' % (name, counts[name], T[name]['why']))
    out += ['', '## Every weather', '',
            'haze = multiple of the saved base per period (Dawn / Sunrise / Day / Sunset / Dusk / Night); air / ozone / g / sun = Sunset values; '
            'GF = Ground Fog Amount / FarAmount at Sunrise, Day, Sunset; mid = MiddayAmount.', '',
            '| Editor ID | Form key | Type | Sev | Region | Alt | Dust | Moisture (type + region + alt) | k | haze D / Sr / Day / Ss / Du / N | air | ozone | g | sun | slab m | dens | deck light | GF Sunrise | GF Day | GF Sunset | mid | lightning | Thunder byte | Note |',
            '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (TYPE_ORDER.index(r['type']), r['sev'], r['w']['editorId'].lower(), r['w']['spid'])):
        s, n = r['s'], r['type']
        hz = [air(n, s, p)['hazeX'] for p in PERIODS]
        ss = air(n, s, 'Sunset')
        gf = [(air(n, s, p)['gfNear'], air(n, s, p)['gfValley']) for p in ('Sunrise', 'Day', 'Sunset')]
        out.append('| %s | `%s` | %s | %.2f | %s | %s | %s | %.2f (%g %+g %+g) | %.2f | %s | %g | %g | %g | %g | %d + %d | %g | %g | %s | %s | %s | %s | %s | %d | %s |' % (
            r['w']['editorId'], r['w']['spid'], n, r['sev'], s['region'], 'yes' if s['alt'] else '', ('%g' % s['dust']) if s['dust'] else '',
            s['moisture'], s['parts'][0], s['parts'][1], s['parts'][2], s['k'], ' / '.join('%g' % round(x, 2) for x in hz),
            ss['rayleighX'], ss['ozoneX'], ss['phaseG'], ss['sunX'], s['base'], s['thick'], s['dens'], s['deckLight'],
            *[('-' if a is None else '%g / %g' % (a, b)) for a, b in gf], '-' if ss['gfMidday'] is None else '%g' % ss['gfMidday'],
            'rate 0' if s['ltI'] is None else '%g, %g/min, [%g, %g] km' % (s['ltI'], s['ltRate'], s['ltNear'], s['ltFar']),
            r['f']['thunder'], p2.NOTES.get(r['w']['editorId'], '')))
    with open(os.path.join(ROOT, 'notes', 'weather-table-4.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    sys.exit(main())

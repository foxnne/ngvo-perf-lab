"""Writes the storm-cloud sweep files of draft/sweeps-storm (sky_sweep.py format). UNTESTED IN GAME.
usage: python -I build_storm_sweeps.py        (reads pass4_types_day.json for the pass-4 storm recipe; writes ../*.json)

Every variant: {"name", "label" (what it tests), "look_for", "scene" (can a per-weather scene carry it?), "cost",
"weather", "settle", "set": {Physical Sky keys}}. sky_sweep.py only reads name / set / weather / settle / features.
Fair-weather files are meant for --stock (variants on top of the saved live settings). Design: notes/storm-clouds-design.md."""
import copy, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
P4 = os.path.join(os.path.dirname(OUT), 'sweeps-pass4', 'pass4_types_day.json')

def R(x, y, z, w): return {'x': x, 'y': y, 'z': z, 'w': w}
def V2(x, y): return {'x': x, 'y': y}

def deep(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict): deep(dst[k], v)
        else: dst[k] = copy.deepcopy(v)
    return dst

def mix(*parts):
    out = {}
    for p in parts: deep(out, p)
    return out

def params(**layers): return {'cloudMap': {'procedural': {'parameters': layers}}}
def low(**kv): return {'cloudLayer': {'low': kv}}
def light(**kv): return {'cloudLayer': {'lighting': kv}}
def horizon(**kv): return {'cloudLayer': {'horizon': kv}}

# Weather-map noise inputs: the code defaults (Ndf.h:124-127), written out in full because a JSON list replaces the
# whole array and a missing field falls back to the NdfNoiseParameters default, not to the slot default.
def noise_inputs(slot3_frequency=12):
    def p(**kv):
        d = dict(type=1, seed=1337, frequency=16, octaves=4, persistence=0.5, lacunarity=2, contrast=1.0, bias=0.0, repetitions=1, responseExponent=1.0)
        d.update(kv); return {'parameters': d, 'texturePath': ''}
    return {'cloudMap': {'procedural': {'noise': [
        p(type=0, frequency=4),
        p(type=1, frequency=4, octaves=6, persistence=0.6, contrast=1.6, bias=-0.02, repetitions=2, responseExponent=1.8),
        p(type=1, frequency=32),
        p(type=2, frequency=slot3_frequency, contrast=1.1, bias=-0.05, responseExponent=2.0)]}}}

# Detail (shape) noise bands: code defaults (CloudNoiseGenerator.h:32-35) with other base frequencies.
def shape_noise(f0, f1, f2, f3):
    def b(f, o, pers, e, c, bias, pm=0.0): return dict(frequency=f, octaves=o, persistence=pers, exponent=e, contrast=c, bias=bias, perlinMix=pm)
    return {'cloudNoise': {'shape': [b(f0, 5, 0.625, 3.489, 0.960, 0.133, 1.0), b(f1, 4, 0.5, 1.164, 1.628, 0.317),
                                     b(f2, 4, 0.5, 0.996, 1.262, 0.115), b(f3, 4, 0.6, 1.031, 1.463, 0.226)]}}

def var(name, label, look, sets, weather, scene='per-weather scene: yes', cost='same as live', settle=14, features=None):
    v = {'name': name, 'label': label, 'look_for': look, 'scene': scene, 'cost': cost, 'weather': weather, 'settle': settle, 'set': mix(*sets)}
    if features: v['features'] = features
    return v

GLOBAL = 'GLOBAL ONLY (noise slot / noise input / cloudNoise are not scene keys): would change every weather'

# ------------------------------------------------------------------------------------------------ towering_day
FAIR = 'SunnyPF'
SLAB = low(ndfAltitudeOffset=1000.0, ndfAltitudeScale=3500.0)                      # 1.0 .. 4.5 km (top type 1 fills to ~4.2 km)
TALL = params(modeling={'range': R(-0.5, 0.5, 0.3, 1.0), 'exponent': 1.0})
CORE = params(modeling={'noise': 3, 'frequency': 1.0, 'offset': V2(0.0, 0.0), 'range': R(0.35, 0.95, 0.15, 1.0), 'exponent': 1.0})
SOLID = params(primary={'range': R(0.35, 0.55, 0.0, 1.0), 'exponent': 1.0}, secondary={'range': R(-0.2, 0.8, 0.0, 0.0)})
BASE = mix(low(bottomSpreadScale=1.0, bottomSpreadHeight=0.15, bottomSoftness=0.15, bottomSoftnessHeight=0.12),
           params(bottomTypeRange=R(-0.4, 0.5, 0.0, 0.05), heightVariation={'range': R(0.0, 1.0, 0.0, 0.0)}))
BIG = [SLAB, CORE, SOLID, noise_inputs(5)]
towering = [
    var('00_live', 'Reference: the saved fair-weather sky, nothing changed.', 'Baseline for every other tile.', [{}], FAIR),
    var('01_tall_slab_tall_types', 'Thickness: slab 1.0-4.5 km (live 1.2-2.1) and top types 0.3-1.0 (live 0-0.33), same coverage map.',
        'Every existing cumulus becomes a 1.5-3.5 km column; heights vary at random (type noise is not tied to the cells). Expect a crowd of thin towers, not one mass.',
        [SLAB, TALL], FAIR, cost='HIGH: slab 3.9x thicker, every horizontal ray stays inside it'),
    var('02_core_towers', 'Top type driven by the SAME noise as coverage (modeling.noise 3): each cell is a dome, tallest in its middle, low at its rim.',
        'Cells read as single cumulus congestus with a rounded summit instead of flat-topped columns of random height.',
        [SLAB, CORE], FAIR, scene=GLOBAL + ' (modeling.noise)', cost='HIGH (thick slab)'),
    var('03_solid_cores', '02 + steep coverage (primary 0.35..0.55 -> 0..1, exponent 1) and the small-fragment layer off.',
        'Fewer cells with clear sky between; hard cauliflower outline (coverage reaches the solid 0.7) instead of soft, see-through edges.',
        [SLAB, CORE, SOLID], FAIR, scene=GLOBAL + ' (modeling.noise)', cost='HIGH (thick slab), fewer occupied rays'),
    var('04_few_large_cells', '03 + coverage noise input at frequency 5 instead of 12: cells ~5 x 3.3 km instead of 2 x 1.4 km.',
        'One or two huge isolated clouds in the province, like the reference picture. Is the dome too smooth (no mid-size lobes)?',
        BIG, FAIR, scene=GLOBAL + ' (noise input 3 + modeling.noise)', cost='HIGH (thick slab)'),
    var('05_big_tile', '03 + weather-map tile 50 x 33.9 km instead of 24.66 x 16.7 (everything 2x bigger): the scene-drivable way to larger cells.',
        'Same question as 04. Compare cell size and edge softness with 04 (the map is 512 px: 98 m per texel here).',
        [SLAB, CORE, SOLID, low(ndfScale=V2(50.0, 33.86))], FAIR, scene='per-weather scene: ndfScale yes, but a transition zooms the field; modeling.noise is GLOBAL', cost='HIGH (thick slab)'),
    var('06_flat_dark_base', '04 + flat hard base: no base lift with coverage, wide bottoms (bottomSpread 1.0 / 0.15), dense bottom type, short base ramp.',
        'One level, flat, dark underside under the whole cloud; a wider foot than the tower (shelf).',
        BIG + [BASE], FAIR, scene=GLOBAL, cost='HIGH (thick slab)'),
    var('07_contrast', '06 + lighting contrast: sunExtinction 1.8, ambientStrength 0.55, msAlbedo 0.994, densityScale 1.0.',
        'Near-black shadowed flank and base against a bright sunlit side. Watch for crushed blacks and a dirty grey sunlit face (msAlbedo).',
        BIG + [BASE, light(sunExtinction=1.8, ambientStrength=0.55, msAlbedo=0.994), low(densityScale=1.0)], FAIR, scene=GLOBAL, cost='HIGH (thick slab)'),
    var('08_no_top_expansion', '06 with topExpansionScale 0: the plain cone profile instead of the expanded (bulged) top.',
        'Does the upper half lose its shoulder / anvil-like bulge? Tells how much of the "anvil" the expansion LUT gives.',
        BIG + [BASE, low(topExpansionScale=0.0)], FAIR, scene=GLOBAL, cost='HIGH (thick slab)'),
    var('09_big_billows', '06 + detail noise at lower base frequencies (3,3,4,9 -> 1,2,3,6 cells per 230 m tile). EXPERIMENTAL: the response curves were tuned for the defaults.',
        'Larger cauliflower lobes (up to 230 m instead of ~77 m), less "popcorn". May thin or thicken all cloud; judge only the lobe size.',
        BIG + [BASE, shape_noise(1, 2, 3, 6)], FAIR, scene=GLOBAL + ' (cloudNoise)', cost='HIGH (thick slab); noise regenerates over ~32 frames', settle=20),
]

# ------------------------------------------------------------------------------------------------ front_horizon
BAND = horizon(enabled=True, pleasantAmount=1.0, coverage=0.7, type=0.0, baseAltitude=900.0, topAltitude=9000.0, distance=45.0, density=2.0)
# storm-region mask: both gain layers read noise slot 1 at layer frequency 0.5 (slot 1 holds 2 repetitions, so 0.5 tiles).
def mask(offset_x=0.0, gx=-0.25, gy=0.10):
    g = lambda z: {'noise': 1, 'frequency': 0.5, 'exponent': 1.0, 'offset': V2(offset_x, 0.0), 'range': R(gx, gy, z, 1.0)}
    return params(coverageGain=g(0.65), modelingGain=g(0.03),
                  primary={'range': R(0.1, 0.65, 0.0, 1.0)},                      # live input interval, output to 1.0: x gain 0.65 = live
                  modeling={'range': R(-0.5, 0.5, 0.25, 1.0), 'exponent': 1.0})
FSLAB = low(ndfAltitudeOffset=1000.0, ndfAltitudeScale=4000.0)
FRONT = [FSLAB, mask()]
DARK = mix(light(sunExtinction=1.6, ambientStrength=0.6, msAlbedo=0.994), low(densityScale=1.0, bottomSpreadScale=1.0, bottomSpreadHeight=0.15))
GAINS = 'per-weather scene: ranges yes; the gain layers must read slot 1 GLOBALLY (harmless while their output stays 1..1)'
def front(tag):
    return [
        var('00_live', 'Reference: saved fair-weather sky (horizon band at its default: coverage 0.5 x pleasant 0.6, top 3.2 km at 60 km = 3 degrees).',
            'Baseline. From plains_west the default band is hidden behind the mountains.', [{}], FAIR),
        var('01_band_towers', 'Horizon band as a distant storm line: towers (type 0), top 9 km, 45 km away, coverage 0.7, density 2.',
            'Cumulus towers standing 8-11 degrees above the true horizon behind the terrain, fair sky overhead untouched. Painted look? Repetition along the horizon?',
            [BAND], FAIR, cost='negligible (analytic, per sky pixel)'),
        var('02_band_dark', '01 + stronger self-shadow: shade 8 (default 4), sunlit 0.3 (default 0.22).',
            'Dark bases and far sides, bright sunlit faces: at sunset a glowing rim on backlit towers.',
            [BAND, horizon(shade=8.0, sunlit=0.3)], FAIR, cost='negligible'),
        var('03_band_wall', '01 as a continuous wall: type 0.55 (half bank, half towers), coverage 1.0, top 7 km.',
            'An unbroken storm shelf along the whole horizon with towers rising from it: the "approaching front" reading.',
            [BAND, horizon(type=0.55, coverage=1.0, topAltitude=7000.0)], FAIR, cost='negligible'),
        var('04_front_mask', 'Ray-marched front: slab 1-5 km; a low-frequency mask (gain layers on noise slot 1 at frequency 0.5) switches regions between the live fair coverage (gain 0.65, top type x0.03) and solid tall cells (gain 1).',
            'A region of large dark towers somewhere in the sky with ordinary fair cumulus elsewhere. Fair cumulus get thicker (lowest type still fills ~15-20% of the 4 km slab): acceptable?',
            FRONT, FAIR, scene=GAINS, cost='HIGH: slab 4.4x thicker'),
        var('05_front_shifted', '04 with the mask moved 0.12 tile (about 3 km) east-west: what the wind does to it over time.',
            'The storm region sits somewhere else: shows how the front approaches / passes. Compare with 04.',
            [FSLAB, mask(offset_x=0.12)], FAIR, scene=GAINS, cost='HIGH (thick slab)'),
        var('06_front_dark', '04 + storm lighting: sunExtinction 1.6, ambientStrength 0.6, msAlbedo 0.994, densityScale 1.0, wide bases.',
            'The storm region reads dark and heavy. Note the fair region darkens with it (lighting is global, not per region).',
            FRONT + [DARK], FAIR, scene=GAINS, cost='HIGH (thick slab)'),
        var('07_front_flat_far', '04 with curvatureRadius 300 km (live 74.9): the cloud layer no longer sinks towards the horizon.',
            'Far cells (10-30 km) stay above the terrain horizon and stack up into a wall; near cells unchanged. Does the far deck look like a ceiling?',
            FRONT + [low(curvatureRadius=300.0)], FAIR, scene=GAINS + '; curvatureRadius is a float (a transition tilts the far field)', cost='HIGHER: far rays stay in the slab longer'),
        var('08_front_plus_band', '04 + 02: ray-marched front and the dark horizon band behind it.',
            'Depth: near towers in front of a far storm line. Do the two layers match in colour and darkness?',
            FRONT + [BAND, horizon(shade=8.0, sunlit=0.3)], FAIR, scene=GAINS, cost='HIGH (thick slab)'),
    ]

# ------------------------------------------------------------------------------------------------ storm_overhead_day / cloud_terrain_meeting
STORM = 'StormPF'
p4 = {v['name']: v for v in json.load(open(P4))}['10_storm_StormPF']
P4SET = copy.deepcopy(p4['set']); P4FEAT = copy.deepcopy(p4.get('features', {}))
NOFLASH = {'lightning': {'rate': 0.0}}                                            # no lightning in the stills
def storm(name, label, look, sets, **kw):
    return var(name, label, look, [P4SET, NOFLASH] + sets, STORM, features=P4FEAT, settle=16, **kw)
relief = lambda w, thick=0.5, freq=1.0: params(baseRelief={'range': R(-0.9, 0.2, 0.0, w), 'exponent': 1.0, 'frequency': freq}, baseReliefThickness=thick)
overhead = [
    storm('00_p4_storm', 'Reference: the pass-4 StormPF recipe (closed deck 400-2400 m, relief 0.18, billow 90 m, deck light 2.5 / half depth 330 m).',
          'Baseline for the other tiles.', [{}]),
    storm('01_no_deck_light', '00 with deckLight 0 (and deckGroundLight 0).', 'What the deck light adds: without it the underside should go uniformly dark; with it thin columns glow.',
          [light(deckLight=0.0, deckGroundLight=0.0)]),
    storm('02_relief_big', '00 with base relief 0.35 of the slab (700 m of base height variation) and thickness coupling 0.8.',
          'Broad shelves and hollows in the underside: lower dark bellies under thick columns, high bright vaults between.',
          [relief(0.35, 0.8)]),
    storm('03_relief_fine', '00 with base relief at frequency 2 (half-size shelves), 0.25 of the slab.',
          'More, smaller rolls. Too busy / repetitive?', [relief(0.25, 0.6, 2.0)]),
    storm('04_billow_250', '00 with baseBillowHeight 250 m (clamp 400).', 'Rounded pouches hanging from the base (mammatus-like), metre-scale relief from the detail noise.',
          [low(baseBillowHeight=250.0)]),
    storm('05_thick_thin_contrast', '00 with strong column contrast: top type 0.1..1.0 over a narrow noise interval and deckHalfDepth 220 m.',
          'Dark thick cores next to bright thin lanes: the "rolling" light-and-dark pattern seen from below.',
          [params(modeling={'range': R(-0.2, 0.3, 0.1, 1.0), 'exponent': 1.0}), light(deckHalfDepth=220.0)]),
    storm('06_broken_deck', '00 with coverage 0.55..1.0 instead of a constant 1 (primary -0.6..0.0 -> 0.55..1.0).',
          'The deck thins into ragged, eroded lanes where coverage drops: structure from the cloud itself rather than from lighting.',
          [params(primary={'range': R(-0.6, 0.0, 0.55, 1.0), 'exponent': 1.0})]),
    storm('07_dark_base', '00 darker: deckHalfDepth 200 m, ambientStrength 0.15, msAlbedo 0.985, sunExtinction 2.2.',
          'A threatening, near-black underside. Check the ground does not go too dark and distant deck does not turn to a black band.',
          [light(deckHalfDepth=200.0, ambientStrength=0.15, msAlbedo=0.985, sunExtinction=2.2)]),
    storm('08_tall_storm', '00 with a 4.5 km slab (400-4900 m).', 'Deeper, darker deck; towers above it only matter from high ground. Mostly a cost test.',
          [low(ndfAltitudeScale=4500.0)], cost='HIGH: slab 2.25x thicker than pass 4'),
    storm('09_dense_sheared', '00 with densityScale 1.5, viewExtinction 1.5 and fast sheared wind (low 14, high 30 m/s, development 0.6, disturbance 0.6).',
          'Crisper underside detail; the upper part of each column leans downwind (shear is capped at 150 m). Look in motion, not only in the still.',
          [low(densityScale=1.5), light(viewExtinction=1.5), {'cloudLayer': {'wind': {'lowVelocity': V2(14.0, 0.0), 'highVelocity': V2(30.0, 0.0), 'development': 0.6, 'disturbance': 0.6}}}]),
]

MIST = {'cloudMap': {'localCloud': {'states': [{'weight': 1.0, 'value': {
    'asset': 'tamriel-mist-separate', 'worldspace': 'Tamriel', 'enabled': True, 'center': [146.227, 233.964], 'size': [6960.415, 5498.143],
    'rotation': 0.0, 'altitude': 192.0, 'heightSpan': 640.0, 'strength': 1.0, 'modelingWeight': 1.0, 'heightWeight': 1.0, 'feather': 0.0,
    'modelingAlpha': True, 'modelingBlend': 2, 'flatAltitude': True}}]}}}
def blob(center, size, altitude, span):                       # diag-one-blob: disc radius = 600 m x size / 3840, bottom = altitude, top = altitude + 0.18 x span
    return {'weight': 1.0, 'value': {'asset': 'diag-one-blob', 'worldspace': 'Tamriel', 'enabled': True, 'center': center, 'size': [size, size],
            'rotation': 0.0, 'altitude': altitude, 'heightSpan': span, 'strength': 1.0, 'modelingWeight': 1.0, 'heightWeight': 1.0, 'feather': 0.0,
            'modelingAlpha': True, 'modelingBlend': 2, 'flatAltitude': True}}
# one state only: blend-state weights must total <= 1 and a Separate slab's coverage is multiplied by its weight
CAP_WEST = {'cloudMap': {'localCloud': {'states': [blob([-1944.0, -913.0], 2400.0, 430.0, 1000.0)]}}}
CAP_THROAT = {'cloudMap': {'localCloud': {'states': [blob([778.7, -745.8], 3200.0, 640.0, 1400.0)]}}}
STRUCT = mix(params(primary={'range': R(-0.5, 0.1, 0.5, 1.0), 'exponent': 1.0}, modeling={'range': R(-0.15, 0.3, 0.08, 1.0), 'exponent': 1.0}),
             light(deckLight=3.5, deckHalfDepth=260.0, ambientStrength=0.45))
terrain = [
    storm('00_p4_storm', 'Reference: pass-4 StormPF (base 400 m + relief up to +360 m; at the west ridge, 3 km away, the layer is 122 m lower).',
          'How much of the ridge (crest 466-514 m) is inside cloud now.', [{}]),
    storm('01_flat_base_420', 'Base 420 m with base relief OFF (relief only ever lifts the base).', 'Ridge crests west of the plains (base there ~300 m) inside the slab: do the top 150-200 m of the slopes fade?',
          [low(ndfAltitudeOffset=420.0), relief(0.0)]),
    storm('02_base_350_midslope', 'Base 350 m, relief 0.04: the layer meets the west range at mid-slope (~230 m there).', 'Upper half of the range gone, Throat buried; low hills still clear. Is the fade into the cloud gradual or a hard line?',
          [low(ndfAltitudeOffset=350.0), relief(0.04)]),
    storm('03_thin_slab_hard_base', '02 with a 900 m slab (350-1250 m), top types 0.6-1.0, densityScale 1.5: the base ramp is ~10% of the slab, so 90 m instead of 200 m.',
          'Terrain should disappear within a much shorter height above the base (the tall slab makes the first 200 m a thin haze).',
          [low(ndfAltitudeOffset=350.0, ndfAltitudeScale=900.0, densityScale=1.5), relief(0.04), params(modeling={'range': R(-0.45, 0.45, 0.6, 1.0), 'exponent': 1.0}), light(deckHalfDepth=200.0)],
          cost='lower than pass 4 (thinner slab)'),
    storm('04_strong_curvature', '00 with curvatureRadius 45 km (live 74.9): the layer drops 200 m at 3 km and 355 m at 4 km while staying at 400 m overhead.',
          'Distant ranges vanish into the cloud although the deck overhead keeps its height. Does the far deck visibly bend down?',
          [low(curvatureRadius=45.0)]),
    storm('05_mist_banks', '02 + terrain-anchored mist banks (local cloud state tamriel-mist-separate, Separate layer, 192-832 m). NEEDS the mod "foxnne - Cloud Weather Map" enabled in the running profile and a build with Separate-layer local clouds.',
          'Ragged scud clinging to ridge crests, saddles and the Throat below the deck. If nothing changes against 02 the asset or the build is missing.',
          [low(ndfAltitudeOffset=350.0), relief(0.04), MIST], scene='per-weather scene: yes (cloudMap.localCloud is a blend state)', cost='MEDIUM: trace range widens to 192 m.., local-layer shader variant'),
    storm('06_thick_thin_deck', 'Target "dark thick regions next to bright thin gaps": 02 + coverage 0.5..1.0 (not a constant 1), top type 0.08..1.0 over a narrow interval, deckLight 3.5, deckHalfDepth 260 m, ambientStrength 0.45.',
          'Bright, near-white thin lanes and holes beside dark thick masses instead of an even grey. If the thin parts are still grey raise deckLight (max 4) or lighting.brightness; if thick parts are not dark shorten deckHalfDepth.',
          [low(ndfAltitudeOffset=350.0), relief(0.04), STRUCT]),
    storm('07_cap_west_crest', 'Target "cap cloud on a peak": 02 + one authored disc as a Separate local slab (asset diag-one-blob, coverage 0.8 = solid core, eroded rim) on the west crest at yaw 250 from the plains camera: 430-610 m, radius 375 m. NEEDS the mod + Separate build as 05.',
          'plains_west, left of centre: a smooth-bodied cap with a ragged lower rim sitting on the crest. It is a flat disc with the stock cone profile, not a lens: judge feasibility, not beauty.',
          [low(ndfAltitudeOffset=350.0), relief(0.04), CAP_WEST], scene='per-weather scene: yes (blend state)', cost='MEDIUM (local-layer shader variant)'),
    storm('08_cap_throat', 'Same cap on the Throat of the World: 640-890 m, radius 500 m (summit 770 m). Deck base raised to 450 m so the cap is seen under it.',
          'plains_throat view: summit inside a cap that touches the slope with a ragged fringe, deck above. With base 350 the Throat top is simply inside the deck.',
          [low(ndfAltitudeOffset=450.0), relief(0.04), CAP_THROAT], scene='per-weather scene: yes (blend state)', cost='MEDIUM (local-layer shader variant)'),
    storm('09_photo_attempt', 'All settings-reachable targets together: base 350 mid-slope + thick/thin deck (06) + mist banks (05).',
          'Closest to the alpine photo: summits gone, scud on the slopes below the base, structured deck. Is the ground still well lit (deckGroundLight 0.2 here)?',
          [low(ndfAltitudeOffset=350.0), relief(0.04), STRUCT, MIST], scene='per-weather scene: yes', cost='MEDIUM'),
]

def write(name, variants):
    for v in variants: json.dumps(v)
    with open(os.path.join(OUT, name), 'w', newline='\n') as f: json.dump(variants, f, indent=1)
    print(name, len(variants))

write('towering_day.json', towering)
write('front_horizon_day.json', front('day'))
write('front_horizon_sunset.json', front('sunset'))
write('storm_overhead_day.json', overhead)
write('cloud_terrain_meeting.json', terrain)

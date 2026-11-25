"""Sky-type recipes: each function edits a PhysicalSky settings dict in place to build one real closed sky from layers
(middle sheet, low layer, cirrus). Used by sky_types.py (Ilinalta view) and cloud_studio.py (orbit views)."""
OFF = [0.2, 0.8, 0.0, 0.0]


def low(s, base, slab, primary, modeling=(-0.5, 0.6, 0.1, 0.5), density=0.7, soft=(1.0, 0.7), spread=(0.8, 0.3), billow=0.0, exp=1.0):
    p = s['cloudMap']['procedural']['parameters']; l = s['cloudLayer']['low']
    p['primary']['range'] = list(primary); p['primary']['exponent'] = exp; p['secondary']['range'] = list(OFF)
    p['modeling']['range'] = list(modeling); p['modeling']['exponent'] = 1.0; p['bottomTypeRange'] = [-0.4, 0.5, 0.0, 0.05]
    p['heightVariation']['range'] = [0.0, 1.0, 0.0, 0.0]
    l.update(ndfAltitudeOffset=float(base), ndfAltitudeScale=float(slab), densityScale=density, bottomSoftness=soft[0], bottomSoftnessHeight=soft[1],
             bottomSpreadScale=spread[0], bottomSpreadHeight=spread[1], baseBillowHeight=billow)


def sheet(s, altitude, thickness, density, cells=0.1, soft=0.5, coverage=(-1.0, 1.0, 1.0, 1.0)):
    m = s['cloudLayer']['middle']
    m.update(enabled=True, altitude=float(altitude), thickness=float(thickness), densityScale=density, cellStrength=cells, stratusCellStrength=0.1, edgeSoftness=soft)
    m['weather']['states'][0]['value']['layers'][0]['range'] = list(coverage)


def light(s, sun, **k):
    s['sunlightColor'] = [sun, sun * 0.97, sun * 0.95]; s['cloudLayer']['lighting'].update(k)


def t1(s):   # high thin overcast: no low cloud, a thin sheet and a full high veil
    low(s, 1200, 900, (0.1, 0.65, 0.0, 0.0)); sheet(s, 4200, 700, 0.006, cells=0.0, soft=0.9)
    c = s['cloudLayer']['cirrus']; c['densityScale'] = 1.0; c['weather']['states'][0]['value']['layers'][0]['range'] = [-1.0, 1.0, 0.6, 1.0]
    light(s, 4.5, deckLight=0.0)


def t2(s):   # grey overcast with low scud: smooth sheet above, sparse ragged soft low cloud
    sheet(s, 2800, 1200, 0.03); low(s, 500, 350, (0.15, 0.6, 0.0, 0.7), density=0.55)
    s['cloudLayer']['cirrus']['densityScale'] = 0.0; light(s, 1.1, deckLight=0.3, ambientStrength=0.6, sunExtinction=1.2)


def t3(s):   # broken deck with gaps: one low layer of even cells, high patches behind
    low(s, 1100, 600, (-0.1, 0.35, 0.0, 1.0), modeling=(-0.4, 0.5, 0.15, 0.6), density=0.9, soft=(0.5, 0.3), spread=(0.5, 0.25))
    s['cloudLayer']['cirrus']['densityScale'] = 0.25; light(s, 5.0, deckLight=0.5, sunExtinction=1.6, ambientStrength=0.6)


def t4(s):   # steady rain: thick low sheet with denser ragged scud under it
    sheet(s, 2200, 1500, 0.05); low(s, 350, 500, (-0.1, 0.5, 0.0, 0.9), density=0.7)
    s['cloudLayer']['cirrus']['densityScale'] = 0.0; light(s, 0.5, deckLight=0.3, ambientStrength=0.5, sunExtinction=1.2)


def t8(s):   # snow sky: one pale featureless sheet, no low cloud
    sheet(s, 1800, 1500, 0.03, cells=0.0, soft=0.9); low(s, 1200, 900, (0.1, 0.65, 0.0, 0.0))
    s['cloudLayer']['cirrus']['densityScale'] = 0.0; light(s, 1.6, deckLight=0.0, brightness=1.3)


def t9(s):   # low cloud in mountains: a shallow soft layer below the peaks under a darker sheet
    sheet(s, 3200, 900, 0.03); low(s, 150, 320, (-0.3, 0.3, 0.0, 1.0), modeling=(-0.5, 0.6, 0.5, 0.8), density=0.6, soft=(1.0, 0.8))
    s['cloudLayer']['cirrus']['densityScale'] = 0.0; light(s, 2.0, deckLight=0.3, ambientStrength=0.7, sunExtinction=1.0)


R = [('1_high_thin_overcast', '1  HIGH THIN OVERCAST', t1), ('2_overcast_with_scud', '2  GREY OVERCAST WITH LOW SCUD', t2), ('3_broken_deck', '3  BROKEN DECK WITH GAPS', t3),
     ('4_steady_rain', '4  STEADY RAIN (sky only)', t4), ('8_snow_sky', '8  SNOW SKY (sky only)', t8), ('9_mountain_low_cloud', '9  LOW CLOUD IN MOUNTAINS', t9)]

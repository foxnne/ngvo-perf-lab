# Per-weather pass 2 (2026-11-18)

OFFLINE work. **Nothing here was tested in game.** The only tested numbers are the calibration points of
2026-11-18 (saved global base, inMin behaviour, high-layer density, terrain heights, haze 0.4 / 0.7, height-fog
white-out). Everything between and beyond them is an educated guess.

Fork read at HEAD f9e0f038d (one modified shader in the tree). The old draft was written against 5451c7e.

## Files

| What | Where |
|---|---|
| Generator (new) | `draft/_generator/build_pass2.py` (run: `python -I build_pass2.py`) |
| WTHR parser | `draft/_generator/wthr_parse.py` -> `draft/_generator/nat-cs-wthr-records.json` (all parsed facts) |
| Catalog extractor | `draft/_generator/extract_catalog.py` -> `draft/_generator/scene-catalog-pass2.json` (368 rows, from `build/PR-Tracy/generated`, 2026-11-18 13:20) |
| Pack | `draft/foxnne-nat3-clouds-pass2/` : manifest, `Baseline/PhysicalSky.json`, `Weather/<formkey>/<Period>/foxnne-nat3-clouds-pass2_PhysicalSky.json` and `..._ExponentialHeightFog.json` (111 x 6 x 2 = 1332 files) |
| Same values as user-layer entries (route B) | `draft/alt-user-overrides-pass2/SceneManager.weather.pass2.json` |
| One representative per sky type + its settings | `draft/pass2-sky-types.json` |
| Table of all 111 weathers | `notes/weather-table-2.md` (generated) |
| Old draft, old generator, old table | untouched |

Layout and file schema are the old draft's (`how-it-works.md` sections 1, 2, 8): per-period files only,
`_metadata.timeOfDayEnabled: true`, vector components keyed x/y/z/w, floats only. New in pass 2: a second feature file
per period for `ExponentialHeightFog`.

## What changed in the source since the old draft

- Scene blacklist (`src/CSEditor/SceneManager/SceneSettingsPolicy.h`) still bars `aerosolType`, `aerosolLoading`,
  `aerosolHumidity`. Per-weather haze therefore has to be written as the coefficients a mixture resolves to:
  `aerosolScatter.{x,y,z}`, `aerosolAbsorption.{x,y,z}` (and `aerosolPhaseG`, which does not change with loading, so it
  is not written). The editor's own scene aerosol picker does the same (`PhysicalSky.cpp:349-420`).
  `Aerosol::Evaluate` = OPAC table row x loading (`PhysicalSky/Aerosol.cpp`, `AerosolData.inl`). Check: Continental,
  RH 50, loading 0.4 -> scatter [5.044, 6.838, 9.150], exactly what `SettingsUser.json` holds today.
- Newly barred per scene: `coverageGain.noise/exponent`, `modelingGain.noise/exponent`, `heightVariation.noise`,
  `heightFromCoverage`, `localBlendMode`, `localMaskPath`. The remap ranges are still allowed. Pass 2 uses none of them.
- Catalog: the PhysicalSky rows are unchanged apart from two new ones (`masserDiskRad`, `secundaDiskRad`). All 19
  PhysicalSky leaves and the one ExponentialHeightFog leaf that pass 2 writes exist, are transitionable floats and are
  inside their UI ranges (generator validation: 0 problems).
- Discovery code (`SceneSettingsDiscovery.cpp:656-706`, `SceneSettingsOverwrites.cpp:176-212`) is as described in
  `how-it-works.md`: folder = form key, feature from `_feature`, period folders Dawn/Sunrise/Day/Sunset/Dusk/Night.
- `SceneSettings/SceneManager.json` user layer: 271 weather keys, PostProcessing (Look Grade) entries only, all of them
  `paused: true` now. Active pack is still `e11:fnenb Cabbage`, baseline pack `foxnne-look`.

## Height fog: where its strength comes from

`Presets/foxnne-look/Baseline/ExponentialHeightFog.json` has `vanillaFogStrength` 0.3 and leaves `useVanillaFogSettings`
at its default 1 ("Follow Vanilla Fog"). In that mode `fogDensity`, `fogHeightFalloff` and `startDistance` are **not**
the levers (the UI greys them out); the density is derived per frame from the weather's fog near/far/power/max and
multiplied by `vanillaFogStrength` (`ExponentialHeightFog.cpp:204-213`, `:810`):

```
target    = 0.5 x fogMax
reference = (far - near) x target^(1 / power)
opacity at distance d (eye level, no height falloff) = 1 - (1 - target)^(strength x d / reference)
```

So the one per-weather float is `vanillaFogStrength` (0..4). Half-opacity distance at the baseline 0.3, computed from
the records:

| Weather | Day | Night |
|---|---|---|
| SunnyPF (0/150000, power 0.65) | 2399 m | 2170 m |
| OvercastPF (0/50000) | 629 m | 584 m |
| RainPF (1500/50000) | 611 m | 710 m |
| FogPF (0/12000 day, 0/5000 night) | 134 m | 73 m |
| StormPF (0/12000 day, 0/5000 night) | 139 m | 74 m |
| Snowstorm (0/15000, power 0.3 day, 0.15 night) | 64 m | 5 m |
| DLC1FalmerValley_bf (0/4000, power 0.4) | 29 m | 15 m |
| Snow (0/200000 day; night power 0.125) | 2807 m | 11 m |
| SnowOvercast (night power 0.2) | 2807 m | 149 m |
| Snow_Alt (0/15000; night power 0.0, clamped to 0.01) | 222 m | 0.1 m |

That explains the white-out: the exponential curve matches vanilla fog at one near point and then keeps climbing where
vanilla fog flattens at its max. Records with a low fog power are hit hardest, and several snow records have a night
power of 0.125 to 0.2 (`Snow_Alt` 0.0), which the formula turns into a wall a few metres away. Pass 2 lowers the
strength per weather and period so the half-opacity distance is at least a per-type floor, keeping some of the
difference between records (distance = floor x (raw / floor)^0.3; strength never below 0.01, never above 0.3). The
second fog layer of the baseline (`fogDensity2` 0.008) is a constant and is not touched.

## Record fields: usable or not

| Field | Verdict |
|---|---|
| Precipitation (MNAM -> SPGD editor id) | **Best type signal.** RainParticles 9, RainStormParticles 5, snow particles 9, ash 3, Blackreach/Sovngarde 2, none 83. |
| Fog distance, power, max (FNAM) | **Usable.** Day far is 150000 for every fair/cloudy record, 50000 for overcast/rain, 12000 for fog/storm, 4000-6000 Forgotten Vale. Drives overcast-vs-partly, the fog type, haze and height fog. Night values differ and are used for the night height fog. |
| Sunlight colour by day (NAM0) | **Usable**, the best darkness signal (luminance 0..1): 0.90-0.94 sunny, 0.61-0.94 cloudy, 0.22-0.65 overcast, 0.24-0.34 rain (0.76 for three "showers" records), 0.19-0.38 storm (0.66 for the spell storm FXMagicStormRain). Drives severity inside overcast/rain/storm/snow. |
| Wind speed (DATA) | **Usable**, cleanly stepped: 5 SClearSky, 10 Sunny, 25 Cloudy, 35 Overcast, 50 Snow, 75 Rain, 150 Storm, 210 Snowstorm. Drives cloud drift, clear-vs-fair-vs-partly, storm and snow severity. |
| Classification flags (DATA) | Partly usable: pleasant 27, cloudy 57, rainy 14, snow 12, none 1. "cloudy" covers everything from Sunny Solstheim to fog; three Cloudy records are flagged pleasant; ash storms are flagged snow. Used only for the clear test. |
| Cloud layer alpha (JNAM) | **Weak.** NAT stacks 5-17 enabled layers and the day mean alpha does not order the types (Sunny 0.26-0.88, Cloudy 0.53-0.93, Overcast 0.28-0.58, Fog 0.17-0.38). Used only as a small nudge inside fair (inMin 0.25..0.15) and partly, plus "at most one layer with alpha" as the clear test. |
| Cloud layer colour (PNAM) | Usable as darkness of the cloud art (0.21-0.32 storm, 0.47-0.83 overcast, 0.95 fair). Small weight in overcast severity only. |
| Cloud layer speeds (QNAM/RNAM), textures | Not used. Per-layer art choices (86 distinct textures), no ordering by weather. |
| Wind direction (DATA) | **Useless**: byte 43 in 109 records, 0 in Blackreach and the world map. Cloud drift stays +X as in the saved base. |
| Thunder frequency (DATA) | **Useless**: 255 in 106 records including every Storm*; only FXMagicStormRain (15), the two Snowstorms (203), RainPF (241) and CloudyVT (246) differ. Storm is taken from the particle type instead. |
| Sun glare, sun damage (DATA) | Not needed; sun damage tracks the sunlight colour (255 sunny, ~200 cloudy, 40-76 overcast/rain). |
| Times of day | 4 in every record (NAM0 272 bytes = 17 colours x 4, JNAM/PNAM 512 bytes = 32 layers x 4). No 8-period records. |
| Aurora model (MODL) | Present in 37 records, but not only auroras (Sovngarde, Soul Cairn, Apocrypha, Forgotten Vale, eclipse carry one too). The aurora rule is limited to clear/fair/partly, where it selects the `_A` records plus CloudyDLC1_Auriel. |

Two records share the editor id `CloudyDLC2_A` (different form ids); both get files.

## Sky types

Nine types (the eight asked for, plus `special` for skies whose worldspace Physical Sky does not run in). Blizzards did
not get a type of their own: they are the heavy end of `snow`. Ash storms went to `overcast`. Each number is
lightest -> heaviest member; the full table with rationale is at the top of `weather-table-2.md`.

| Type | n | inMin | outMin | outMax | base m | thick m | density | high layer | haze loading | height-fog floor |
|---|---|---|---|---|---|---|---|---|---|---|
| clear | 5 | 0.45 | 0 | 0.65 | 1400 | 600 | 0.60 | 0 | 0.40 -> 0.50 | baseline 0.3 |
| fair | 20 | 0.25 -> 0.15 | 0 | 0.65 | 1300 | 700 | 0.70 | 0 | 0.40 -> 0.50 | baseline |
| partly | 27 | 0.10 -> -0.15 | 0 | 0.65 | 1200 -> 1100 | 900 -> 1000 | 0.75 | 0.30 | 0.40 -> 0.55 | baseline |
| overcast | 14 | -0.35 -> -0.60 | 0 -> 0.15 | 0.65 -> 0.70 | 1000 -> 900 | 800 -> 1000 | 0.75 -> 0.85 | 0 | 0.50 -> 0.70 | 1200 m |
| rain | 8 | -0.30 -> -0.70 | 0 -> 0.20 | 0.65 -> 0.72 | 950 -> 800 | 1100 -> 1500 | 0.80 -> 0.95 | 0 | 0.60 -> 0.85 | 900 m |
| storm | 5 | -0.70 -> -0.90 | 0.20 -> 0.30 | 0.72 -> 0.78 | 800 -> 700 | 1800 -> 2400 | 0.95 -> 1.0 | 0 | 0.80 -> 1.0 | 500 m |
| snow | 9 | -0.10 -> -0.70 | 0 -> 0.20 | 0.65 -> 0.72 | 950 -> 750 | 900 -> 1500 | 0.65 -> 0.85 | 0 | 0.55 -> 0.90 | 700 m |
| fog | 10 | -0.30 -> -0.50 | 0 -> 0.10 | 0.65 | 700 -> 650 | 500 -> 600 | 0.50 -> 0.60 | 0 | 0.80 -> 1.10 | 350 m |
| special | 13 | 0.45 | 0 | 0.65 | 1400 | 600 | 0.60 | 0 | 0.40 | baseline |

The haze range is spanned by fog distance (lo at day fog far 150000, hi at 5000), not by severity; every clear, fair
and partly record has fog far 150000, so all of them get 0.40. Cloud drift comes from the record's wind byte alone
(low 3.3 m/s SClearSky, 3.6 Sunny, 4.5 Cloudy, 5.1 Overcast, 6 Snow, 7.5 Rain, 12 Storm, 15.6 Snowstorm; high = 2 x low).

Anchors: fair is the liked look (inMin 0.2, high layer off); partly starts at the saved global base (inMin 0.1,
1200/900, 0.75, high layer 0.3); overcast straddles the tested -0.4 "full broken-to-overcast" field. inMax stays 0.65
everywhere. Sun multiplier is 1.0 for every type (`sunlightColor` is not written): the cloud shadow dims the ground, and
doing both would darken twice. `cloudLayer.lighting.*` is not written either (stays at the saved 1.0).

Rules (also printed in the table): type from particles, fog far, flag + layer count, wind; severity inside a type from
sunlight darkness, wind, fog nearness, layer alpha; haze and drift as above; height fog as in the section above; aurora
records (clear/fair/partly) get inMin + 0.15 and no high layer in Dawn, Dusk and Night. The generator checks that within
a type a higher severity never gives a higher inMin, a higher base or a lower density.

Representatives for one frame per type (`draft/pass2-sky-types.json` has their full Day settings):
clear SClearSkyPF `0x7F00~NAT-ENB.esp`, fair SunnyPF `0x81A~Skyrim.esm`, partly CloudyPF `0x12F89~Skyrim.esm`,
overcast OvercastPF `0x53B6~NAT-ENB.esp`, rain RainPF `0xC821F~Skyrim.esm`, storm StormPF `0xC8220~Skyrim.esm`,
snow Snow `0x4D7FB~Skyrim.esm`, fog FogPF `0xC821E~Skyrim.esm`.

## Assumptions that need an in-game check

1. **Coverage below -0.4 and above 0.2 is extrapolated.** Only -0.4, 0.1 and 0.2 were seen. Is 0.45 (clear) nearly
   cloudless, and does -0.5..-0.9 close the field further or was -0.4 already the limit?
2. **`secondary.range.x`** is raised to 0.3 for clear and lowered for overcast and worse. The secondary field was at its
   default (-0.2) in every test; whether it is what leaves cumulus at inMin 0.2 is unknown.
3. **`outMin` (coverage floor) 0.1-0.3 and `outMax` 0.70-0.78** for overcast/rain/storm/snow/fog: untested. outMax was
   reported to do little when lowered; raising it may also do little.
4. **Overcast and storm darkness at noon.** Lighting stays at 1.0 and density goes up to 1.0 with a 2.2 km deep storm
   deck. The very first test (defaults, 1.8 km deck at 0.75) read as too dark and grey. If overcast is too dark, lower
   `cloudLayer.lighting.sunExtinction` for that type rather than the coverage. Look Grade entries are all paused now, so
   there is no second darkening from the grade.
5. **Bases 650-800 m for fog/storm/blizzard** put the peaks (700-770 m) in cloud on purpose. Check from the Whiterun
   plain that this reads as "peaks in cloud" and not as a veil over the vista; the 600 m limit is respected everywhere.
6. **Deck depth and cost**: storm 1800-2400 m and rain/snow up to 1500 m against the tested 900 m. March cost grows
   roughly with depth; not measured.
7. **High layer**: 0 for every type except partly (0.3, the saved value). A clear sky is therefore empty blue. If that
   is too bare, 0.15-0.2 on clear is the first thing to try.
8. **Haze as coefficients.** That a weather's `aerosolScatter`/`aerosolAbsorption` survive while the base has
   `aerosolType` 1 follows from `PhysicalSky::LoadSettings` (it re-derives only when type, loading or humidity change),
   but was not seen working. Loading 0.55-1.1 for bad weather is a guess; 0.7 looked milky on a clear day, which is the
   intent for rain. Touching the aerosol sliders in the menu while a weather scene is active may re-derive and overwrite.
9. **Height-fog floors** (1200/900/700/500/350 m half-opacity) and the 0.3 compression exponent are guesses; the formula
   ignores the height falloff, `fogDensity2` and the volumetric-fog path. First check: FogPF at Whiterun, day and night
   (strength 0.153 / 0.101 against 0.3), then Snow at night (0.017 against 0.3).
10. **Drift speeds** up to 15.6 / 31.2 m/s (Snowstorm): whether that looks like a blizzard or like a time-lapse.
11. **Dawn/Dusk height-fog value** is the geometric mean of the day and night strengths; the game blends the record's
    day and night fog on its own schedule, which may not line up with the Scene Manager periods.
12. **Type edge cases** listed in the Note column of the table (FogRain as fog, ash storms as overcast, the three
    bright-sun rain records as showers, SunnyFV_A as clear, Karthspire/BloatedMansGrotto typed by record not by name).
13. **Solstheim and Forgotten Vale** use other map floors (`zBottom` 256 and 3000 units); the same base altitudes were
    used there without checking terrain heights in those worldspaces.

## Not confirmed from files (mechanism)

- Everything in `how-it-works.md` section 9 still stands: no file of either draft has been loaded by the game, so
  "loads without a `[SceneSettings]` warning" is unverified. The validation is against the catalog of the
  `build/PR-Tracy` tree of today 13:20, which may not be the deployed DLL.
- Two feature files in one period folder: fine by example. The Azure Hearth reference carries four per folder
  (`AzureHearth_ExponentialHeightFog.json`, `_ImageBasedLighting`, `_PhysicalSky`, `_PostProcessing`), flat and per period.
  Its ExponentialHeightFog values were not compared with pass 2.
- The active-pack side effect: applying a pack with scene files replaces `e11:fnenb Cabbage` as the active pack
  (`how-it-works.md` section 8). Still unknown what that changes. Route B (`alt-user-overrides-pass2`) avoids it.
- How a partial `cloudMap` / `cloudLayer` object in a Baseline file merges with lower layers. The pass-2 Baseline only
  repeats the saved global base, and the user layer above it holds the same values, so either way the result is the same.
- Whether hiding vanilla clouds also hides NAT's aurora or other sky meshes.
- `lightningIntensity` (saved 0.04) was left alone; the record's thunder frequency gives nothing to drive it with.

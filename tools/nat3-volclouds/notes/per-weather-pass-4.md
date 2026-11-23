# Per-weather pass 4 (2026-11-19)

OFFLINE work. **Nothing here was tested in game**: no scene file, no sweep, no number. Pass 1-3 files are untouched.
Every number in the generator's TUNING TABLE is provisional (see "Waiting on" below).

Needs a build that contains all three branches: `foxnne/heavy-sky`, `foxnne/lightning-fix`, `foxnne/ground-fog-near`.

## Files

| What | Where |
|---|---|
| Generator | `draft/_generator/build_pass4.py` (`python -I build_pass4.py`). The marked TUNING TABLE at the top holds every per-period / per-moisture number. Imports `build_pass2.py` (record facts, type / severity rules) and `build_pass3.py` (fair-weather cloud points, height-fog rule, validator); neither is modified or re-run. |
| Catalogue extractor | `draft/_generator/extract_catalog4.py` -> `scene-catalog-pass4.json` |
| Pack | `draft/foxnne-nat3-clouds-pass4/`: manifest, `Baseline/PhysicalSky.json`, `Weather/<formkey>/<Period>/foxnne-nat3-clouds-pass4_<Feature>.json`: PhysicalSky 666, ExponentialHeightFog 666, ImageBasedLighting 588, GroundFog 588 = 2508 scene files (98 non-realm weathers x 6 periods carry all four) |
| Route B (user-layer entries) | `draft/alt-user-overrides-pass4/SceneManager.weather.pass4.json` (56664 entries); `merge_user_layer4.py` builds the merged copy (not run) |
| Representatives | `draft/pass4-sky-types.json` (pass-3 shape + second / third representative for fair types, per-period feature blocks) |
| Harness sweeps | `draft/sweeps-pass4/pass4_types_{sunrise,day,sunset,night}.json` (13 variants each; exactly what the pack would apply) and `..._rays.json` (the same + the proposed Effects11 rays strength, which the pack cannot deliver) |
| Table of all 111 weathers | `notes/weather-table-4.md` (generated: moisture rule, curves, representatives per period, cloud field per type, every weather) |
| Install note | `notes/install-pass-4.md` |

## Scene catalogue (re-extracted)

- `cs-wt-lightning` @ 4c3fbcd1b (`foxnne/lightning-fix`; contains heavy-sky, not ground-fog-near) and `cs-wt-groundfog3` @ 6e2dbed45
  (`foxnne/ground-fog-near`), both clean. Neither has a build tree, so each worktree's own
  `cmake/generate_scene_settings_catalog.py --source-dir <worktree> --out-dir <session scratch>` was run (1684 and 1677
  entries; nothing written into the worktrees, scratch copies deleted afterwards).
- `scene-catalog-pass4.json`: 524 rows (PhysicalSky 335, ExponentialHeightFog 56, GroundFog 47 from groundfog3,
  ImageBasedLighting 15, SkySync 15, Effects11 10, VolumetricLighting 21, ViewAtmosphere 19, Skylighting 6).
  Policy = union of both `SceneSettingsPolicy.h` (blacklist 71, time-of-day whitelist 13). `GroundFog` is in the
  time-of-day whitelist in BOTH trees.
- Cross-check of the two trees: only the expected differences (heavy-sky + new lightning rows and the
  `baseRelief.noise` blacklist row only in lightning; 16 new Ground Fog rows only in groundfog3; old
  `lightning.cloudLuminance / channelLuminance` only in groundfog3; `lightning.channelRadius` range differs).
  The Ground Fog rows pass 4 uses exist only in groundfog3 until the merge.

## Drivable or not

| Asked for | Verdict | Where it went |
|---|---|---|
| haze amount and tint: `aerosolScatter.xyz`, `aerosolAbsorption.xyz` | drivable (floats, no bounds) | per weather, per period |
| aerosol phase g: `aerosolPhaseG` | drivable (-0.999..0.999) | per weather, per period |
| Rayleigh / ozone multiples: `rayleighScatter(+AP1)`, `ozoneAbsorption(+AP1)` | drivable | per weather, per period |
| sun strength: `sunlightColor.xyz` | drivable | per weather, per period |
| heavy-sky: `baseRelief.range / exponent / frequency`, `baseReliefThickness`, `baseBillowHeight`, `bottomSoftness(Height)`, `deckLight`, `deckHalfDepth`, `deckHorizonLight`, `deckGroundLight` | drivable | per weather (off values in fair weathers) |
| lightning: `lightningIntensity` (0..4), `lightning.rate` (0..600), `lightning.distanceRange.xy` (0.05..50) | drivable | storms: all three; every other weather: `rate` 0 |
| ambient: IBL `DALCAmount`, `SkyIBLSaturation`, `SkyIBLScale`, `EnvIBLSaturation` | drivable | per weather, per period (98 weathers) |
| Ground Fog `Amount` (sheet + near volume), `FarAmount` (valley), `MiddayAmount`, `ShadowRetention`, `BurnOffStrength` | drivable (feature whitelisted) | per weather, per period (98 weathers). Also drivable, not used: `NearDensity`, `MorningAmount`, `EveningAmount`, `Thickness`, ... |
| light shafts: Effects11 `StandaloneRays`, `StandaloneSunRays`, `StandaloneMoonRays`, `StandaloneSunMultiplier`, `StandaloneMoonMultiplier` | **NOT drivable**: rows are `Persisted, Hidden` only (not transitionable, not scene-controllable) and Effects11 is in no scene whitelist | the strength curve is computed anyway: `Effects11.notSceneDrivable` in `pass4-sky-types.json` and the `*_rays` sweeps. To deliver it: one global strength, or make the keys scene-controllable + whitelist Effects11 |
| Sky Sync horizon fade (`HorizonFadeElevation`, `HorizonFadeHours`) | **NOT drivable**: rows are scene-controllable but `SkySync` is not in `kTimeOfDayFeatureWhitelist` | global only (saved 1.5; look pack Baseline 9.3). Not in the table |
| game Volumetric Lighting strength, View Atmosphere | **NOT drivable**: whole features blacklisted | global only |
| `lightning.weatherMode` | **NOT drivable**: integer, not transitionable | pack Baseline (0), see Lightning |
| `cloudLayer.cirrus.uvSize`, `baseRelief.noise`, `aerosolType / Loading / Humidity` | not drivable (blacklisted), as before | Baseline (uvSize 3) / code default / coefficients |
| storm recipe `densityScale` 1.1 | out of the catalogue range 0..1 | written as 1.0 |

## 1. Moisture

`moisture = clamp01(type + region + alternate)`; curve position `k = clamp01((moisture - 0.2) / 0.6)` (k 0 = "dry" column of a
curve, k 1 = "humid" column).

- type: clear 0.15, fair 0.40, partly 0.50, overcast 0.65, rain 0.85 (rain under a bright sun = showers 0.90), storm 0.80,
  snow 0.40, fog 0.95.
- region = editor-id suffix: MA / COMA +0.30, CO +0.25, FF +0.10, PF +0.05, VT -0.05, FV -0.10, RE -0.15, TU -0.15, SN -0.20,
  Solstheim (DLC2) 0, DLC2_TU -0.15, no suffix 0. Named records: Riften -> FF, Karthspire -> RE, BloatedMansGrotto and
  Helgen -> PF, Skuldafn -> SN, Auriel and FalmerValley -> FV.
- alternate (`_A`, `_Alt`, `_ALT`): -0.20 in a humid region (MA, CO, COMA: the cleaner day), +0.15 elsewhere (the hazier day),
  so the two records of a region give different sunsets.
- DUST is a separate value, not moisture: VT 0.6, DLC2 0.8, DLC2_TU 0.3, Solstheim ash storms 1.0. Dust does not burn
  off: in every period haze + 0.35 x dust (fair Day still capped at the base), absorption x (1 + dust), blue weighting
  + 0.4 x dust, scatter tinted toward [1, 0.93, 0.82]. No effect on Ground Fog.

Resulting ranges (full table: `weather-table-4.md`, "Every weather"): clear 0.00-0.45, fair 0.20-0.70, partly 0.30-0.80,
overcast 0.50-0.95, rain 0.70-1.00, storm 0.65-0.90, snow 0.20-0.55, fog 0.80-1.00. Examples: SunnySN 0.20, SunnyTU 0.25,
SunnyTU_A 0.40, SunnyPF 0.45, SunnyPF_A 0.60, SunnyMA 0.70, SunnyMA_A 0.50, CloudySN 0.30, CloudyPF 0.55, CloudyMA 0.80.

## 2. Period curves

One table (`CURVES` in the generator), each cell dry -> humid. Group `fair` = clear, fair, partly. Group `closed` =
overcast, rain, storm, snow, fog: the deck hides the sky, so air / ozone / glow / sun stay at x1 and only haze, ambient and
Ground Fog move.

| fair group | Dawn | Sunrise | Day | Sunset | Dusk | Night |
|---|---|---|---|---|---|---|
| haze x base (loading 0.2) | 1.0 -> 1.7 | 1.1 -> 2.0 | 0.6 -> 1.0 | 1.1 -> 2.0 | 1.0 -> 1.7 | 0.6 -> 1.0 |
| absorption x (on top of haze) | 1 -> 1.3 | 1 -> 1.5 | 1 | 1 -> 1.5 | 1 -> 1.3 | 1 |
| absorption blue weighting b | 0 -> 0.2 | 0 -> 0.3 | 0 | 0 -> 0.3 | 0 -> 0.2 | 0 |
| Rayleigh x | 2 -> 2.5 | 2 -> 3 | 1 | 2 -> 3 | 2 -> 2.5 | 1 |
| ozone x | 1.5 -> 2.5 | 1.5 -> 3 | 1 | 1.5 -> 3 | 1.5 -> 2.5 | 1 |
| phase g (saved 0.6164) | 0.66 -> 0.72 | 0.70 -> 0.80 | 0.6164 | 0.70 -> 0.80 | 0.66 -> 0.72 | 0.6164 |
| sun strength x | 0.9 -> 0.75 | 0.8 -> 0.6 | 1 | 0.8 -> 0.6 | 0.9 -> 0.75 | 1 |
| DALCAmount (base 0.5) | 0.45 -> 0.35 | 0.40 -> 0.25 | 0.5 | 0.40 -> 0.25 | 0.45 -> 0.35 | 0.5 |
| SkyIBLSaturation (base 0.6) | 0.70 -> 0.85 | 0.80 -> 1.0 | 0.6 | 0.80 -> 1.0 | 0.70 -> 0.85 | 0.6 |
| SkyIBLScale (base 1.21) | 1.25 -> 1.35 | 1.30 -> 1.45 | 1.21 | 1.30 -> 1.45 | 1.25 -> 1.35 | 1.21 |
| EnvIBLSaturation (base 0.8) | 0.85 -> 0.90 | 0.90 -> 1.0 | 0.8 | 0.90 -> 1.0 | 0.85 -> 0.90 | 0.8 |
| Ground Fog Amount (near) | 0.5 -> 1.3 | 0.5 -> 1.3 | 0.5 -> 1.0 | 0.4 -> 1.2 | 0.4 -> 1.2 | 0.3 -> 1.0 |
| Ground Fog FarAmount (valley) | 0.5 -> 1.5 | 0.5 -> 1.5 | 0.4 -> 1.0 | 0.4 -> 1.3 | 0.4 -> 1.3 | 0.3 -> 1.1 |
| rays strength (not drivable) | 0.05 -> 0.30 | 0.15 -> 0.60 | 0 -> 0.10 | 0.15 -> 0.60 | 0.05 -> 0.30 | 0 -> 0.15 (moon) |

Fair group, per weather (not per period): Ground Fog `MiddayAmount` 0 -> 0.35, `ShadowRetention` 0.30 -> 0.70,
`BurnOffStrength` 1. Ground Fog has its OWN time-of-day curve in code (Morning 1.4, Midday = MiddayAmount, Evening 0.8,
smooth in game time, plus terrain shade); the per-period Amount / FarAmount above multiply it. So mist, haze and rays fall
together toward midday and return toward evening, and humid weathers keep some of all three at midday.

Closed group: haze = the type's own Day haze (pass-3 record rule, about 1.2-1.4x; fog 2-3x) x 1.0 -> 1.15 in Dawn /
Sunrise / Sunset / Dusk, x 0.9 -> 1.0 at Night; DALC = the type value by day, half-way to 0.5 at Dawn / Dusk, 0.5 at
Night (pass-3 rule); other IBL keys at base; rays 0. Ground Fog per type (dry -> humid, x 1.1 Dawn / Sunrise, x 0.9 Day):

| | Amount | FarAmount | MiddayAmount | ShadowRetention | BurnOffStrength |
|---|---|---|---|---|---|
| overcast | 0.7 -> 1.0 | 0.8 -> 1.2 | 0.5 | 0.6 | 0.5 |
| rain | 0.5 -> 0.8 | 0.8 -> 1.2 | 0.6 | 0.6 | 0.3 |
| storm | 0.15 -> 0.25 | 0.4 -> 0.6 | 0.6 | 0.6 | 0.3 |
| snow (x (1 - 0.6 x severity)) | 0.3 -> 0.5 | 0.4 -> 0.7 | 0.5 | 0.6 | 0.5 |
| fog (+ 0.8 x severity) | 1.8 -> 2.4 | 1.8 -> 2.6 | 1.0 | 0.8 | 0.15 |

Numbers for the representatives (Sunrise = Sunset except Ground Fog; "GF eff" = near amount left on sunlit ground after the
feature's own curve):

| Weather | Period | haze | absorb x (b) | air | ozone | g | sun | DALC / skySat / skyScale | GF near / valley | GF eff | rays |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SunnySN (dry fair, m 0.20) | Sunrise | 1.10 | 1.0 (0) | 2.0 | 1.5 | 0.70 | 0.80 | 0.40 / 0.80 / 1.30 | 0.50 / 0.50 | 0.70 | 0.15 |
| | Day | 0.60 | 1 | 1 | 1 | 0.616 | 1 | 0.5 / 0.6 / 1.21 | 0.50 / 0.40 | 0.00 | 0 |
| | Sunset | 1.10 | 1.0 (0) | 2.0 | 1.5 | 0.70 | 0.80 | 0.40 / 0.80 / 1.30 | 0.40 / 0.40 | 0.32 | 0.15 |
| | Night | 0.60 | 1 | 1 | 1 | 0.616 | 1 | 0.5 / 0.6 / 1.21 | 0.30 / 0.30 | 0.33 | 0 |
| SunnyPF (fair, m 0.45) | Sunset | 1.48 | 1.21 (0.13) | 2.42 | 2.13 | 0.74 | 0.72 | 0.34 / 0.88 / 1.36 | 0.73 / 0.78 | 0.59 | 0.34 |
| | Day | 0.77 | 1 | 1 | 1 | 0.616 | 1 | 0.5 / 0.6 / 1.21 | 0.71 / 0.65 | 0.10 | 0.04 |
| SunnyMA (humid fair, m 0.70) | Sunrise | 1.85 | 1.42 (0.25) | 2.83 | 2.75 | 0.78 | 0.63 | 0.28 / 0.97 / 1.42 | 1.17 / 1.33 | 1.63 | 0.52 |
| | Day | 0.93 | 1 | 1 | 1 | 0.616 | 1 | 0.5 / 0.6 / 1.21 | 0.92 / 0.90 | 0.27 | 0.08 |
| | Sunset | 1.85 | 1.42 (0.25) | 2.83 | 2.75 | 0.78 | 0.63 | 0.28 / 0.97 / 1.42 | 1.07 / 1.15 | 0.85 | 0.52 |
| | Night | 0.93 | 1 | 1 | 1 | 0.616 | 1 | 0.5 / 0.6 / 1.21 | 0.88 / 0.97 | 0.97 | 0.12 |
| CloudyMA (most humid partly, m 0.80) | Sunset | 2.00 | 1.5 (0.3) | 3.0 | 3.0 | 0.80 | 0.60 | 0.25 / 1.0 / 1.45 | 1.20 / 1.30 | 0.96 | 0.60 |
| OvercastPF (m 0.70) | Sunset / Day / Night | 1.38 / 1.23 / 1.21 | 1 | 1 | 1 | 0.616 | 1 | DALC 0.30 / 0.30 / 0.50 | 0.95 / 1.13, 0.85 / 1.02, 0.95 / 1.13 | 0.86 / 0.64 / 1.00 | 0 |
| RainPF (m 0.90) | Sunset / Day / Night | 1.60 / 1.39 / 1.39 | 1 | 1 | 1 | 0.616 | 1 | DALC 0.25 / 0.25 / 0.50 | 0.80 / 1.20, 0.72 / 1.08, 0.80 / 1.20 | 0.75 / 0.63 / 0.82 | 0 |
| StormPF (m 0.85) | Sunset / Day / Night | 1.58 / 1.37 / 1.37 | 1 | 1 | 1 | 0.616 | 1 | DALC 0.25 / 0.25 / 0.50 | 0.25 / 0.60, 0.23 / 0.54, 0.25 / 0.60 | 0.24 / 0.20 / 0.26 | 0 |
| Snow (m 0.40) | Sunset / Day / Night | 1.26 / 1.20 / 1.12 | 1 | 1 | 1 | 0.616 | 1 | DALC 0.30 / 0.30 / 0.50 | 0.25 / 0.34, 0.23 / 0.31, 0.25 / 0.34 | 0.23 / 0.17 / 0.26 | 0 |
| FogPF (m 1.00) | Sunset / Day / Night | 3.15 / 2.74 / 2.74 | 1 | 1 | 1 | 0.616 | 1 | DALC 0.32 / 0.32 / 0.50 | 2.54 / 2.74, 2.28 / 2.46, 2.54 / 2.74 | 2.46 / 2.28 / 2.57 | 0 |

All six periods for every representative: `weather-table-4.md`, "Representatives".

## 3. Cloud fields

- clear / fair / partly: pass 3 unchanged. Checked by the generator: for all 52 weathers and all six periods every
  `cloudMap` / `cloudLayer` key pass 3 wrote has the same value. New heavy-sky keys are written at their off values
  (deckLight 0, deckGroundLight 0, baseBillowHeight 0, baseRelief output 0-0, bottomSoftness 1 / 0.68).
- overcast, rain, storm, steady snow, blizzard, fog: closed decks from `heavy-sky/recipes/heavy-sky-types.json`. Common:
  coverage exactly 1 (`primary.range` [-0.8, 0.1, 1, 1]), secondary off, `heightVariation` [0, 1, 0, 0] (the fold source is
  off), `bottomSpread` 0.4 / 0.2, relief from its own noise x `baseReliefThickness` 0.5.

| Type (weather, severity) | slab m | dens | modeling z-w | relief | soft | billow m | sunExt / viewExt / msAlbedo / ambient | deckLight / half m / horizon / ground | DALC day |
|---|---|---|---|---|---|---|---|---|---|
| overcast lightest (OvercastFF 0.32) | 800 + 1210 | 0.85 | 0.22-0.80 | 0.12 | 0.2 / 0.15 | 40 | 1.15 / 1 / 0.9975 / 0.55 | 1.6 / 480 / 0.45 / 0.55 | 0.35 |
| overcast rep (OvercastPF) = recipe | 700 + 1400 | 0.90 | 0.22-0.85 | 0.14 | 0.2 / 0.15 | 50 | 1.2 / 1 / 0.997 / 0.5 | 1.6 / 420 / 0.5 / 0.5 | 0.30 |
| overcast heaviest (OvercastVT 0.86) | 660 + 1480 | 0.94 | 0.22-0.89 | 0.15 | 0.2 / 0.15 | 58 | 1.28 / 1.04 / 0.996 / 0.46 | 1.77 / 400 / 0.54 / 0.42 | 0.26 |
| rain showers (0.25) | 650 + 1500 | 0.95 | 0.22-0.90 | 0.15 | 0.2 / 0.15 | 60 | 1.3 / 1.05 / 0.996 / 0.45 | 1.8 / 400 / 0.55 / 0.4 | 0.35 |
| rain rep (RainPF) = recipe | 550 + 1700 | 1.0 | 0.22-1.0 | 0.16 | 0.2 / 0.15 | 70 | 1.4 / 1.1 / 0.995 / 0.4 | 2.0 / 380 / 0.6 / 0.3 | 0.25 |
| storm (recipe, density 1.0) | base + 2000 | 1.0 | 0.25-1.0 | 0.18 | 0.1 / 0.12 | 90 | 1.6 / 1.2 / 0.992 / 0.3 | 2.5 / 330 / 0.75 / 0.2 | 0.25 |
| snow rep (Snow) = recipe | 600 + 900 | 0.80 | 0.30-0.65 | 0.08 | 0.8 / 0.4 | 25 | 1 / 1 / 0.999 / 1 | 1.3 / 600 / 0.3 / 0.5 | 0.30 |
| blizzard (Snowstorm 0.96) | 500 + 1400 | 0.90 | 0.30-0.85 | 0.12 | 0.5 / 0.3 | 40 | 1.15 / 1.05 / 0.997 / 0.7 | 1.5 / 450 / 0.4 / 0.4 | 0.25 |
| fog rep (FogPF) = recipe | 230 + 500 | 0.60 | 0.30-0.60 | 0.06 | 1.0 / 0.6 | 15 | 1 / 1 / 0.999 / 1 | 1.2 / 500 / 0.2 / 0.4 | 0.32 |
| fog heaviest (Forgotten Vale) | 230 + 600 | 0.70 | 0.30-0.65 | 0.06 | 1.0 / 0.6 | 15 | 1.05 / 1 / 0.999 / 1 | 1.2 / 500 / 0.2 / 0.4 | 0.28 |

- Storm base by severity: FXSkyrimStormBlowingGrass (0.38) 500 m, FXMagicStormRain (0.41) 490 m, StormFF (0.61) 430 m,
  StormPF (0.70) 400 m, StormTU (0.73) 370 m; the 350 m end is reached at severity 0.75 (no record is that severe).
- Rain is closed for every member, showers included (a higher, thinner, brighter deck instead of pass-3 broken cloud).
- Light snow under a bright sun (SkuldafnCloudy, SnowClear, SnowClear_Alt): pass-3 thin broken cloud under a veil, unchanged.
- Height fog (`vanillaFogStrength`), drift and the high layer follow the pass-3 rules unchanged. Closed decks have no high layer.

## 4. Lightning

- Storm weathers only: `lightningIntensity` / `lightning.rate` / `lightning.distanceRange` by severity:
  0.38 -> 0.8, 4 / min, [2.5, 12] km; StormPF -> 1.0, 8 / min, [1.5, 9] km; 0.75 -> 1.15, 10 / min, [1, 8] km
  (StormTU 1.09, 9.2 / min, [1.2, 8.4]; StormFF 0.95, 7 / min, [1.8, 9.8]). Old `cloudLuminance` / `channelLuminance`
  are not written. `cloudGlow`, `boltLuminance`, `sceneIlluminance` stay global.
- Every other weather writes `lightning.rate` 0.
- **Finding from the records:** `lightning.weatherMode` 1 (the new default) lets automatic discharges happen only in weathers
  whose thunder byte is not 0 / 255. In `NAT-CS.esp` the byte is **255 for StormPF, StormFF, StormTU and
  FXSkyrimStormBlowingGrass** (15 only for FXMagicStormRain) and it is **not 255 for RainPF (241), CloudyVT (246),
  Snowstorm and Snowstorm_Alt (203)**. With mode 1 that means no lightning in four of the five storms, and lightning at the
  global rate (6 / min) in heavy rain, one partly cloudy volcanic sky and blizzards. Pass 4 therefore puts
  `lightning.weatherMode` 0 and a global `lightning.rate` 0 in the pack Baseline and lets the storm files carry the rate.
  Alternative: keep mode 1 and patch the thunder bytes in the weather plugin. (The lightning notes themselves say the gate
  was not verified against the engine; I read `NAT-CS.esp`, not the new volumetric-lighting patch plugin.)
- The saved `lightningIntensity` 0.04 now means 4 %; storms write their own value, so it only matters for the global default.

## What changed from pass 3

| Area | Pass 3 | Pass 4 |
|---|---|---|
| Haze | one value per weather, all day (1.0x fair; 1.1-3x heavy) | fair types per period and moisture: Day 0.6-1.0x, twilight 1.0-2.0x, night 0.6-1.0x; heavy types +0-15 % at twilight; dust for VT / Solstheim |
| Haze colour, glow | never written | absorption x1-1.5 blue-weighted at low sun; phase g 0.70-0.80 at low sun |
| Rayleigh | x2 at twilight (fair types) | x2 (dry) to x3 (humid) at Sunrise / Sunset, x2-2.5 at Dawn / Dusk, x1 Day / Night |
| Ozone, sun strength | never written | ozone x1.5-3 at twilight; sun x0.8-0.6 at Sunrise / Sunset |
| Ambient | DALC for heavy types only | DALC + sky / env saturation + sky scale per period for all 98 weathers (fair types: only twilight differs from the look pack) |
| Ground Fog | optional set, refused by the build | in the pack: Amount / FarAmount per period, MiddayAmount / ShadowRetention / BurnOffStrength per weather |
| Overcast / rain / storm / snow / fog decks | broken or semi-closed fields, bases 800-950 m, storm with heightVariation + bottomSpread 1.0 | heavy-sky recipes: coverage exactly 1, base relief, billows, deck light, deck ground light; bases 230-800 m; no fold-prone shaping; storm 370-500 m |
| Rain Day-only modeling tweak, showers as broken cloud | yes | removed (closed deck, recipe modeling range) |
| Lightning | intensity 0.15-0.25 (old meaning), 6-12 / min, [2.5, 9] km | new keys: intensity 0.8-1.15, 4-10 / min, [1-2.5, 8-12] km; rate 0 elsewhere; weatherMode 0 in the Baseline |
| Fair / clear / partly clouds | | unchanged (verified key by key) |

## Validation

`python -I build_pass4.py`: 111 weathers, 2508 scene files, 89 distinct settings (PhysicalSky 79, ExponentialHeightFog 1,
ImageBasedLighting 4, GroundFog 5), **0 problems**. Per leaf, as in pass 3: feature in the time-of-day whitelist, address
not blacklisted, catalogue row exists, Transitionable + SceneControllable, written as a finite float (or a valid blend for
the one Blend row), inside the catalogue range where the row has bounds. Also checked: monotonic within a type, haze
ceilings, fair-type Day haze <= today's base, overcast / rain / storm / fog decks closed, no closed deck with
heightVariation or bottomSpread > 0.4, closed slabs 900-2000 m (fog excepted), storm base 350-500 m, lightning only on
storms, fair-type cloud fields identical to pass 3. A second, independent walk over the written files gave the same
result (2508 files, 89 settings, 0 problems, 111 folders = the 111 record form keys, six periods each), and every key in
the sweep files has a catalogue row (the two global-only keys and Effects11 excepted).
Not validated: anything the game does at load; that the merged build's catalogue equals the two offline generator runs.

## Waiting on (provisional numbers and the test that settles each)

| Numbers (tuning-table block) | Test |
|---|---|
| haze twilight multiples 1.1-2.0 (C `hazeX`) | godrays sweep (haze x2), aerosol x5-x10 test |
| absorption x and blue weighting (C `absorbX`, `absorbBlue`), dust tint (D) | "darker / warmer haze" test |
| ozone x1.5-3 (C `ozoneX`) | ozone x8 test |
| phase g 0.70-0.80 (C `phaseG`) | phase g 0.75-0.9 test |
| sun strength 0.8-0.6 (C `sunX`) | sunlightColor x0.4-0.6 test |
| DALC / SkyIBLSaturation / SkyIBLScale / EnvIBLSaturation at twilight (C) | sunsetamb sweep (saturation 1.0 / DALC 0 / sky x1.5). If the look pack Baseline changes, change block A too |
| rays strength (C `rays`) and whether it can be per weather at all | godrays / standalone_rays sweeps + a code change |
| Sky Sync horizon fade | not in the table: global only |
| Ground Fog amounts, midday share, shade retention (C, E) | first in-game look at Ground Fog phase 3 through scenes |
| all closed-deck values, storm base 370-500 m, fog base 230 m (G) | hs_types, hs_isolate, hs_tune, hs_ground sweeps |
| lightning intensity / rate / distance (F), weatherMode | lf_main, lf_isolate sweeps; the thunder-byte question |
| Rayleigh x2-x3 | tested at 18:00 on plains_west only; Sunrise, Dawn, Dusk are assumed symmetric |

## Assumptions and risks to check in game

1. Period timing: scene periods hold their value and cross-fade at the climate's boundaries. The warm window seen was
   18:00-18:30; whether "Sunset" covers exactly that, and how the Dusk values (x2-2.5 air, haze 1.0-1.7) look at 18:50, is
   unknown. Ground Fog's own curve runs on game time, not on periods.
2. `sunlightColor` scales everything the sun lights, the sky included, not only the disc. x0.6 in humid weather may
   darken the whole sunset; auto exposure will partly hide it.
3. `aerosolPhaseG` is written explicitly in every period (0.6164 by day). If the saved global value changes, change block A.
   The same holds for Rayleigh, ozone, sun colour (code defaults) and the four IBL keys (look-pack values).
4. Dry Day haze 0.6x base: distance may read too crisp / too blue. Night at 0.6-1.0x is a guess.
5. Fog: stratus base at 230 m puts the camera inside cloud on any ground above it (heavy-sky NOTES 6.5), and pass-3 haze
   2.7-3x + Ground Fog 2.3-2.8 stack on top. `FOG_BASE_M` in the tuning table: 300-350, or 900 for the pass-3 look.
6. Closed decks + `deckGroundLight` add light on the ground on top of DALC 0.25-0.35 (heavy-sky risk 3): may be milky.
7. Snow: light snow keeps pass-3 broken cloud but sits in the `closed` curve group (no twilight colour changes).
8. Ground Fog `Amount` also scales with wind inside the feature; storms are low twice (0.15-0.25 and wind).
9. Moisture ignores the record's own fog distances (pass-3 haze used them; closed types still do for their Day haze).
10. Pass-3 open items that still stand: blend-valued `cloudLayer.cirrus.weather` from a scene file never loaded, drift,
    height-fog floors, type edge cases, special realms.

## Log

- Read pass-3 notes / generator, `pass-4-plan.md`, heavy-sky notes + recipes, lightning-fix notes, Ground Fog phase 3 notes.
- Regenerated both catalogues offline; wrote `extract_catalog4.py` -> `scene-catalog-pass4.json`.
- Checked drivability; found Effects11 rays and Sky Sync horizon fade not drivable, storm density 1.1 out of range.
- Read (read-only) SettingsUser.json and the foxnne-look Baseline for the saved base values.
- Found the thunder-byte problem with `lightning.weatherMode` 1.
- Wrote `build_pass4.py`; run: 0 problems; independent file walk: 0 problems.
- Changed representative selection so the sweeps hold a dry (SunnySN 0.20), middle (SunnyPF 0.45) and humid (SunnyMA 0.70)
  fair weather, likewise partly (CloudySN 0.30 / CloudyPF 0.55 / CloudyMA 0.80) and clear (SClearSkyPF 0.20 / SClearSkyCOMA 0.45).
- Wrote `merge_user_layer4.py` (compiled, not run), `install-pass-4.md`. Nothing installed, game not started.

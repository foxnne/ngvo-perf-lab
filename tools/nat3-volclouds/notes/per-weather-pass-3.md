# Per-weather pass 3 (2026-11-19)

OFFLINE work. **Nothing here was tested in game.** The anchors below were seen in game through the test harness
(feature API), not as scene files; no scene file of any pass has been loaded by the game yet. Everything between and
beyond the anchors is derived or guessed.

Fork read at HEAD fdc32bfce (branch foxnne/nr-pr6, "merge: Ground Fog phase 1"), tree clean apart from an untracked
`extern/AntiLag2-SDK/`. Scene catalogue: `build/PR-Tracy/generated/SceneSettingsCatalog.generated.cpp`, 2026-11-19 06:48.

## Files

| What | Where |
|---|---|
| Generator | `draft/_generator/build_pass3.py` (run: `python -I build_pass3.py [--sim]`). Imports `build_pass2.py` for record facts and the type/severity rules; pass-2 files are not rewritten. |
| Catalogue + scene policy extractor | `draft/_generator/extract_catalog3.py` -> `scene-catalog-pass3.json` (403 rows: PhysicalSky 312, ExponentialHeightFog 56, GroundFog 20, ImageBasedLighting 15; blacklist 70 rows, time-of-day whitelist 12 features) |
| Pack | `draft/foxnne-nat3-clouds-pass3/`: manifest, `Baseline/PhysicalSky.json`, `Weather/<formkey>/<Period>/foxnne-nat3-clouds-pass3_<Feature>.json`: PhysicalSky 666, ExponentialHeightFog 666, ImageBasedLighting 276 (46 weathers x 6) = 1608 scene files |
| Same values as user-layer entries (route B) | `draft/alt-user-overrides-pass3/SceneManager.weather.pass3.json` (32904 entries); `merge_user_layer3.py` -> `SceneManager.merged.json` (snapshot merge with the live file of 2026-11-18 09:33) |
| OPTIONAL Ground Fog proposals | `draft/optional-groundfog-pass3/Weather/...` (588 files) + `SceneManager.weather.groundfog.pass3.json`. Refused by the current build, see below. |
| One representative per sky type | `draft/pass3-sky-types.json` |
| Table of all 111 weathers | `notes/weather-table-3.md` (generated) |
| Install note | `notes/install-pass-3.md` |
| Offline emulation of the cloud maps | `draft/_generator/pass3-sim-variants.json` -> `draft/_generator/sim3/*.png`, `summary.txt` (run with `cloud-storms/ndf_sim.py`) |

`pass3-sky-types.json` keeps the pass-2 shape per representative (`editorId`, `formKey`, `PhysicalSky.Day` as flat dotted
paths, `ExponentialHeightFog` with `vanillaFogStrength.Day` / `.Night`) and adds: `PhysicalSky.periodOverrides` (per other
period only the keys that differ from Day), `ImageBasedLighting` (`DALCAmount.Day` / `.DawnDusk` / `.Night` or null),
`GroundFog.optionalUntested`, `lightestMember`, top-level `globalOnly` (`cloudLayer.cirrus.uvSize` 3.0, must be set
globally by the harness) and `savedBase`. One flat key is not a number: `cloudLayer.cirrus.weather` is the whole
`{"states": [...]}` blend object (arrays inside), which the harness `merge()` replaces whole.

## Anchors used (in-game, 2026-11-18/19)

1. Saved global base: haze Continental loading 0.2, height fog `vanillaFogStrength` 0.1, low layer 1200 + 900,
   `ndfScale` [24.66, 16.7], primary.range [0.1, 0.65, 0, 0.65], cirrus density 0.3.
2. Storm: `cloud-storms/sweeps/storm_towers.json` 04 and 06 liked at dusk. Rain: `rain_structure.json` 13 liked at 17:30,
   uniform at 13:00; 14 and 15 gave wavy streaks at low sun.
3. Fair: `small_fragments.json` 07 liked. 4. Overcast (pass 2) too open. 5. High layer: `high_cloud.json` 06 / 05 / 08.
6. Lightning flashes from 0.35 km strikes. 7. Terrain too bright under storm (DALC 0.25 used in the liked frames).
8. Rayleigh x2 good at sunset, pale at midday. 9. Terrain heights 155 / 215 / 770 m. 10. Drift never judged.

**Discrepancy in the brief, resolved here:** the rain numbers in the brief include heightVariation [0.15, 0.75, 0.10, 0] and
bottomSpread 1.0 / 0.25. Those two belong to variant 14 ("low wide bases"), which is one of the two variants to avoid; the
liked variant 13 has both at their defaults. Pass 3 uses variant 13 (defaults for both).

## Scene-drivable or not (checked against the catalogue + `SceneSettingsPolicy.h`)

All 57 distinct settings the pack writes are catalogue rows of type Float (56) or Blend (1), flagged Transitionable and
SceneControllable, not blacklisted, and their features are in the time-of-day whitelist that weather scenes use.

| Asked for | Verdict | Where it went |
|---|---|---|
| `modeling.range/.exponent`, `heightVariation.range/.exponent`, `bottomTypeRange`, `primary.exponent`, `bottomSpreadScale/Height`, `cloudLayer.lighting.{sunExtinction,viewExtinction,msAlbedo,ambientStrength}` | drivable | per-weather files |
| `cloudLayer.cirrus.altitude`, `.densityScale` | drivable | per-weather files |
| cirrus coverage / type layers (`weather.states[0].value.layers[0/1]`) | drivable, but only as ONE entry: `cloudLayer.cirrus.weather` (catalogue type Blend, the whole `{"states":[...]}` object). The layer `noise` index is part of the state and travels with it. | per-weather files (and the sparse-streak state in the Baseline as fallback) |
| `cloudLayer.cirrus.uvSize` | **not drivable**: in the catalogue but blacklisted (`{ "PhysicalSky", "cloudLayer", "cirrus", "uvSize" }`) | `Baseline/PhysicalSky.json` (3.0), and `globalOnly` in `pass3-sky-types.json` |
| `lightningIntensity`, `lightning.rate`, `lightning.distanceRange.{x,y}` | drivable (0..4, 0..600, 0.05..50) | storm files only |
| `ImageBasedLighting.DALCAmount` | drivable (0..1); feature is whitelisted | `..._ImageBasedLighting.json` for overcast / rain / storm / snow / fog |
| `rayleighScatter.{x,y,z}`, `rayleighScatterAP1.{x,y,z}` | drivable (no UI bounds) | clear / fair / partly files, per period |
| `ExponentialHeightFog.vanillaFogStrength` | drivable (0..4) | every weather |
| `GroundFog.Amount`, `.Thickness` (and all 18 other keys) | **not drivable in this build**: catalogue rows exist (float, scene-controllable), but `GroundFog` is in neither `kTimeOfDayFeatureWhitelist` nor `kLocationFeatureWhitelist` (file last changed 2026-11-17, before the Ground Fog merge). `ValidateSceneSettingEntry` refuses with "is not whitelisted for this scene type". Needs `{ "GroundFog" },` added to `kTimeOfDayFeatureWhitelist` + rebuild. | separate optional set, do not install yet |
| `aerosolType/Loading/Humidity`, per-layer `noise` slots, `cirrus.enabled` (boolean) | not drivable, as before | haze as coefficients; others not needed |

Other source facts: cirrus type "noise 4" is not a slot (`CirrusGenerate.cs.hlsl` has cases 0..3), so the type is the
constant `range.z` (0 = streak channel, 0.25 = streak/tuft mix). Baseline files are deep-merged
(`Util::Settings::MergeSettings`) and user edits are a diff from the base, so the Baseline `uvSize` survives the user's
own `cloudLayer.cirrus.densityScale` edit. `IBL` `DALCMode` 3 in the foxnne-look Baseline is migrated to 2 on load.

## Pass-3 sky types

Types, members and severities are the pass-2 rules unchanged (9 types; clear 5, fair 20, partly 27, overcast 14, rain 8,
storm 5, snow 9, fog 10, special 13). Each type is now a list of (severity, values) points; a weather is interpolated
between the nearest points (a severity within 0.012 of a point takes the point exactly, so the tested looks are exact).
Every weather writes the same full cloud key set (also the keys it leaves at their defaults), so no value depends on
what a lower layer holds. Representative rows (Day period); full rows for lightest / heaviest members are in
`weather-table-3.md`.

| Type (rep) | primary.range ^exp | secondary.range | modeling.range ^exp | heightVariation | bottomTypeRange | slab m | dens | bottomSpread | sunExt / viewExt / msAlbedo / ambient | high layer | haze x base | fog str day / night (half m) | DALC day | drift |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clear (SClearSkyPF) | [0.40, 0.65, 0, 0.65] ^1.4 | off [-0.2, 0.8, 0, 0] | default [-0.5, 0.6, 0, 0.5] ^1.6 | default [0, 1, 0, 0.02] | default [-0.4, 0.5, 0, 0.25] | 1400 + 600 | 0.60 | default 0.813 / 0.30 | 1 / 1 / 0.999 / 1 | sparse streaks 0.4 @ 9000 | 1.0 | 0.1 / 0.1 (7200 / 3580) | - | 3.7 |
| fair (SunnyPF) | [0.25, 0.50, 0, 0.65] ^1.4 (heaviest [0.19, 0.44]) | off | default | default | default | 1300 + 700 | 0.70 | default | 1 / 1 / 0.999 / 1 | sparse streaks 0.4 @ 9000 | 1.0 | 0.1 / 0.1 | - | 3.9 |
| partly (CloudyPF) | [0.05, 0.35, 0, 0.68] ^1.4 (lightest [0.13, 0.42, 0, 0.65], heaviest [-0.07, 0.26, 0, 0.70]) | off | default | default | default | 1200 + 900 (heaviest 1110 + 990) | 0.75 | default | 1 / 1 / 0.999 / 1 | large streaky sheets @ 8000: 0.5 twilight, 0.3 Day and Night | 1.0 | 0.1 / 0.1 | - | 4.4 |
| overcast (OvercastPF) | [-0.70, 0.30, 0.08, 0.92] ^1 (lightest [-0.51, 0.35, 0, 0.88], heaviest [-0.78, 0.23, 0.11, 0.95]) | [-0.55, 0.5, 0, 0.60] | [-0.5, 0.5, 0.25, 0.75] ^1 | default | [-0.4, 0.5, 0, 0.45] | 950 + 1000 (1000 + 900 .. 910 + 1080) | 0.80 | default | 1.2 / 1.05 / 0.997 / 0.9 | none (thin veil 0.14 -> 0 for severity < 0.5) | 1.23 (range 1.1 - 1.5) | 0.1 / 0.099 (1890 / 1780) | 0.30 (0.35 .. 0.26) | 4.8 |
| rain (RainPF) | [-0.30, 0.45, 0, 0.90] ^1 (showers [-0.05, 0.50, 0, 0.85]) | [-0.3, 0.8, 0, 0.45] (showers out 0.30) | [-0.5, 0.5, 0.20, 0.80] ^1; Day period [.., 0.12, 0.90] | default | default | 800 + 1700 (showers 900 + 1400) | 0.90 (0.80) | default | 1.3 / 1.1 / 0.995 / 0.8 | none (showers: thin veil 0.15) | 1.39 (1.2 - 1.8) | 0.1 / 0.1 (1830 / 2130) | 0.25 (0.35) | 6.3 |
| storm (StormPF) | [-0.25, 0.5, 0, 0.95] ^1 (lightest [0.0, 0.5, 0, 0.95]) | off [0.2, 0.8, 0, 0] | [-0.5, 0.5, 0.35, 1.0] ^1 | [0.15, 0.75, 0.14, 0] ^1 | [-0.4, 0.5, 0, 0.1] | 800 + 2600 | 1.0 | 1.0 / 0.2 | 1.6 / 1.2 / 0.992 / 0.7 | none | 1.37 (1.0 - 1.5) | 0.0645 / 0.037 (645 / 600) | 0.25 | 9.0 |
| snow (Snow) | [-0.55, 0.28, 0.04, 0.90] ^1 (lightest [0, 0.45, 0, 0.75], blizzard [-0.75, 0.18, 0.10, 0.94]) | [-0.5, 0.55, 0, 0.55] | [-0.5, 0.5, 0.22, 0.70] ^1 | default | default | 900 + 1200 (1000 + 900 .. 800 + 1600) | 0.75 (0.65 .. 0.85) | default | 1.1 / 1 / 0.998 / 0.95 (blizzard 1.25 / 1.1 / 0.996 / 0.85) | none (light snow: thin veil 0.15) | 1.2 (1.2 - 2.0; blizzard 1.74) | 0.1 / 0.0069 (8400 / 500) | 0.30 (0.40 .. 0.25) | 5.4 |
| fog (FogPF) | [-0.55, 0.28, 0.04, 0.88] ^1 (heaviest [-0.70, 0.20, 0.08, 0.92]) | [-0.5, 0.55, 0, 0.55] | [-0.5, 0.5, 0.20, 0.60] ^1 | default | default | 950 + 600 (heaviest 900 + 700) | 0.60 (0.70) | default | 1 / 1 / 0.999 / 1 | none | 2.74 (2.0 - 3.0) | 0.0709 / 0.0525 (567 / 419) | 0.32 | 4.1 |
| special | as clear, high layer 0 | | | | | 1400 + 600 | 0.60 | | | none | 1.0 | 0.1 / 0.1 | - | |

Storm only: `lightningIntensity` 0.15 (lightest) -> 0.22 (StormPF) -> 0.24 (StormTU), `lightning.rate` 6 -> 10 -> 11.2 per
minute, `lightning.distanceRange` [2.5, 9] km. Every other type leaves the global values (0.04, 3/min, 0.35..7 km).
Clear / fair / partly only: `rayleighScatter` and `rayleighScatterAP1` x2 in Dawn, Sunrise, Sunset, Dusk; x1 in Day, Night.
DALC: type value in Sunrise / Day / Sunset, half-way to 0.5 at Dawn / Dusk, 0.5 (Baseline) at Night.
Aurora records (clear / fair / partly): in Dawn, Dusk, Night primary inMin and inMax + 0.15, high layer 0 (pass-2 rule).
Baseline (`Baseline/PhysicalSky.json`): the saved base + `cloudLayer.cirrus.uvSize` 3.0, cirrus altitude 9000 and the
sparse-streak state as the fallback high-layer pattern.

Offline emulation (`ndf_sim.py`, cloud map + vertical profile only, no erosion / lighting / haze; "cover" = columns with
profile > 0.45, "solid" = profile >= 0.7):

| Variant | cover | solid | body thickness median / p90 |
|---|---|---|---|
| clear | 4 % | 0 % | 47 / 70 m |
| fair lightest (= tested 07) / heaviest | 13 % / 19 % | 0 % | 55 / 82 m |
| partly lightest / rep / heaviest | 22 / 32 / 47 % | 0 % | 88 / 123 m |
| overcast lightest / rep / heaviest | 74 / 89 / 95 % | 21 / 45 / 59 % | 298 / 429 / 545 m median |
| rain showers / RainPF (Day values) | 41 / 63 % | 12 / 23 % | 492 / 628 m median |
| storm lightest (= tested 04) / StormPF (= tested 06) | 48 / 67 % | 19 / 24 % | 1278 / 1235 m median |
| snow lightest / rep / blizzard | 37 / 86 / 96 % | 0 / 46 / 66 % | 246 / 445 / 962 m median |
| fog rep / heaviest | 85 / 94 % | 42 / 59 % | 199 / 272 m median |

The emulation reproduces its own earlier figures for the tested variants (rain 13: 63 / 22-23 %, storm 04: 48 / 19 %,
storm 06: 67 / 24 %), so the generated trees are the tested settings. The pass-2 rain and storm decks measured
23 % and 59 % cover, 0 % solid, 110-170 m thick in the same emulation (cloud-storms NOTES 4.2).

## What changed from pass 2 and why

| Area | Pass 2 | Pass 3 | Why |
|---|---|---|---|
| Haze | loading 0.40 - 1.10 (2x - 5.5x today's base) | 1.0x - 3.0x of loading 0.2, per-type ceilings 1.5 / 1.8 / 1.5 / 2.0 / 3.0 | heavy haze hid all cloud structure (finding 1) |
| Height fog | lowered from 0.3 to floors 1200 / 900 / 700 / 500 / 350 m, exponent 0.3 | Baseline is 0.1; floors 1800 / 1500 / 1000 / 1200 / 800 m with hard minimums 900 / 800 / 600 / 500 / 400 m, exponent 0.5; fair types get a 1500 m safety floor | fog white-out at 13:00: FogPF day half-opacity distance 262 m -> 567 m (2.2x), minimum in the fog type 166 m -> 400 m |
| Vertical fill | modeling layer never written (clouds in the lowest 10-40 % of the slab) | modeling.range / exponent written for every type; exponent 1 and filled ranges for overcast, rain, storm, snow, fog | finding 2 |
| Storm | closed sheet with a 0.2-0.3 coverage floor, 700-800 + 1800-2400 | tested 04 (lightest) -> 06 (StormPF, StormTU): no floor, towers, 800 + 2600, dark lighting | liked at dusk |
| Rain | closed sheet, floor up to 0.2 | tested 13; showers a broken field; Day-only wider modeling range | liked at 17:30; "a little more variation" at 13:00; no floor, no low wide bases (artifacts) |
| Fair / clear / partly | inMax 0.65 everywhere, secondary layer on (clear: raised) | steep cut-off (inMax = inMin + 0.25..0.33), secondary off | small-fragment fix liked |
| Overcast / snow / fog decks | broken field (-0.35..-0.6 with default modeling) | closed decks: 74-95 % cover, 21-59 % solid in the emulation; floor <= 0.12; bottomTypeRange w 0.45 for a ragged / dense underside mix (overcast) | pass-2 overcast too open; floor limit from the rain artifact |
| Cloud lighting | never written | sunExtinction / viewExtinction / msAlbedo / ambientStrength per type | part of the liked storm and rain looks |
| High layer | density only (0, or 0.3 for partly) with the default popcorn pattern | three tested looks as blend states + altitude; uvSize 3 in the Baseline | finding 5 |
| Lightning | untouched | storm: intensity 0.15-0.25, 6-12 / min, 2.5-9 km | finding 6 |
| Ambient | untouched | DALCAmount 0.25-0.40 by day under heavy skies | finding 7 |
| Rayleigh | untouched | x2 at twilight for clear / fair / partly | finding 8 |
| Cloud bases | fog 650-700, storm 700-800, blizzard 750 | fog 900-950; storm 800; blizzard 800; nothing else below 900 | finding 9 |
| Drift | 3 + 0.06 x wind byte, up to 15.6 / 31.2 m/s | 3.5 + 0.0375 x wind byte, capped 9 / 18 m/s | finding 10 |

## Validation

`python -I build_pass3.py`: 111 weathers, 1608 scene files, **0 problems** against the catalogue of 2026-11-19 06:48 and
the policy header at HEAD fdc32bfce. Checked per leaf: feature in the time-of-day whitelist, address not blacklisted,
catalogue row exists, Transitionable + SceneControllable, Float written as a finite float (or a valid blend for the Blend
row), inside the catalogue range where the row has bounds. Also checked: monotonic within a type (heavier never means a
higher threshold, a higher base or a lower density), haze ceilings, coverage floor <= 0.15, drift cap, fog base >= 900 m,
no base below 800 m outside storm / snow, rain without the low-wide-base treatment. A second, independent walk over the
written files gave the same result (1608 files, 57 distinct settings, 0 problems, 111 folders = the 111 record form keys,
six period folders each). The optional Ground Fog set fails as expected: 1176 entries "feature is not whitelisted".
Not validated: that the deployed DLL is the build this catalogue came from, and anything the game does at load.

## Assumptions that need an in-game check

1. **Scene files have never been loaded.** In particular the blend-valued entry `cloudLayer.cirrus.weather` from a pack
   file / user entry is unverified (it passes every check I could read: `IsSceneSettingPrimitive`, `IsBlendable`,
   `IsCompatibleSceneSettingValue`). If it is refused, every weather shows the Baseline sparse streaks at its own
   density (partly cloudy would get streaks at 0.5 / 0.3, veil types streaks at 0.15).
2. **Storm at midday.** StormPF haze is 1.37x the new base (the readable-at-dusk frame was 1.9x and still murky at
   midday) and height fog 0.0645 (tested 0.06). If midday is still murky, lower the storm haze range toward 1.0.
3. **Storm rep is variant 06, lightest storms variant 04.** Both were liked at dusk; which one a storm overhead should
   be is a choice. Swap the two points in the generator to reverse it.
4. **Rain Day-only modeling range** [.., 0.12, 0.9] (tested: [.., 0.2, 0.8]) is the only answer to "a little more
   variation at 13:00" that avoids heightVariation / bottomSpread. It may do too little, and the map now changes shape
   slowly between periods. Rain distance is also clearer than in the liked frame (fog 0.1 instead of 0.229, haze 1.39x
   instead of 2.0x): if rain looks too crisp, raise `vanillaFogStrength` toward 0.15 first.
5. **Overcast / snow / fog decks are new shapes** (emulated only): closed enough? Underside light-and-dark visible, or a
   flat grey lid? Is the overcast `bottomTypeRange` w 0.45 the right lever, and do floors of 0.04-0.12 produce the wavy
   streaks seen with 0.25? (If yes, set the floors to 0.)
6. **Which of heightVariation / bottomSpread caused the rain artifact** is unknown (variant 14 changed both). Only the
   storm type uses them (as tested at dusk); check the storm at low sun for the same streaks.
7. **Clear** ([0.40, 0.65]) and **partly** ([0.14..-0.08, +0.28..0.33]) thresholds are extrapolated from the one liked
   fair setting. The fair test ran on SunnyPF; which slab it ran on (saved 1200 + 900 / 0.75 or pass-2 1300 + 700 / 0.70)
   I could not tell from the sweep file; pass 3 keeps 1300 + 700 / 0.70.
8. **High layer**: sheets at 0.3 in Day AND Night (night is my guess), 0.5 at twilight; veil only over the lightest
   overcast / showers / light snow; altitude 9000 (streaks) vs 8000 (sheets, veil) changes with the weather.
9. **DALC**: 0.25-0.40 by day was only seen at 0.25 in the storm / rain frames. Night stays 0.5 and Dawn / Dusk half-way
   so nights do not go black: unverified in both directions. Mode is "DALC + Sky" (2).
10. **Lightning**: intensity 0.15-0.25 with strikes no closer than 2.5 km; whether the flash is now too weak, and whether
    thunder delay (7 s at 2.5 km) reads well. A placed supercell inside 9 km would capture all strikes (none installed).
11. **Rayleigh x2 at Dawn and Dusk** (deep twilight) and at Sunrise: only 17:30 was seen. Night is x1.
12. **Height fog floors** and the 0.5 exponent are guesses; the formula ignores height falloff, `fogDensity2` and the
    volumetric path. Snow nights need strengths of 0.004-0.011 to reach 500 m (record fog power 0.125-0.2 at night):
    check Snow and Snowstorm at night. A blizzard at 500 m half-opacity may now be too clear.
13. **Fog type**: haze 2.7-3.0x + fog 0.07 + a closed stratus deck at 950 m. Is it still "fog" without the Ground Fog
    feature? (Fog-type weathers are where the optional Ground Fog set matters most.)
14. **Deck depth and cost**: storm 2600 m, rain 1700 m, blizzard 1600 m slabs, now actually filled. Not measured.
15. **Drift** 9 / 18 m/s for storm and blizzard, 3.7-6.3 otherwise: never seen.
16. Pass-2 items that still stand: type edge cases (ash storms as overcast, FogRain as fog, ...), Solstheim / Forgotten
    Vale terrain heights, the Dawn / Dusk fog value being a geometric mean, haze coefficients surviving a menu edit.
17. **Ground Fog** (optional set): untested and not loadable in this build; `Thickness` is 0.5-3 m only, and the default
    `Amount` is 1.0 in every weather, so the fair-weather Day value 0 would remove what is there today.

## Not confirmed from files (mechanism)

- Applying the pack makes it the active pack in place of `e11:fnenb Cabbage` (`UnifiedPresetCatalog::ApplyPack`): it
  reloads scene overwrites and form edits and re-selects the Post Processing pipeline (already active). I found no other
  effect in source, but it was not tried. See `install-pass-3.md`.
- The catalogue is from the `build/PR-Tracy` tree; whether the deployed DLL is that build was not checked.

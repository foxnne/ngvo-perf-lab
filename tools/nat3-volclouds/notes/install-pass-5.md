# Pass 5: closed skies only (2026-11-22). Nothing installed, not tested in game as a pack

Target root: `C:\Modlists\NGVO 8.0 Beta\mods\CS Settings\SKSE\Plugins\CommunityShaders\`
Source root: `C:\Users\foxnn\dev\nat3-volclouds\draft\`

Generator: `draft\_generator\build_pass5.py` (`python -I build_pass5.py`; imports pass 2-4, which are untouched).
Catalogue: `draft\_generator\scene-catalog-pass5.json`, made by `extract_catalog5.py` from the main checkout
`C:\Users\foxnn\dev\skyrim-community-shaders` @ 072c003d5 (`foxnne/llf-shadowless-spots`) with the checkout's own
`cmake\generate_scene_settings_catalog.py` run into a scratch folder (1812 entries; nothing written into the checkout).
Table of every weather and every check: `notes\weather-table-5.md` (generated).

## What the pack holds

- 46 of the 111 NAT.CS III weathers have a Weather folder: overcast 14, rain 8, storm 5, snow 9, fog 10.
  The other 65 (clear 5, fair 20, partly 27, other realms 13) have **no folder**: they show the saved look.
- 873 scene files: PhysicalSky 276, ExponentialHeightFog 276, ImageBasedLighting 276 (46 weathers x 6 periods),
  PostProcessing 45 (9 snow weathers x 5 periods, never Night). **No Ground Fog entries** (user decision).
- **Overcast (14) and fog (10): exactly the pass-4 values**, approved in game from `sweeps-pass4\pass4_types_day.json`.
  The two ash storms (StormDLC2, StormDLC2_ALT; pass-1 group "snowstorm", pass-4 type overcast) are among the 14 and get no
  exposure raise (`ASH_STORMS_GET_EXPOSURE = False` in the tuning table).
- **Rain (8) and storm (5): pass-4 values unchanged. NOT yet reviewed in game.**
- **Snow, deck (7: Snow, Snow_Alt, SnowOvercast, SnowOvercast_Alt, Snowstorm, Snowstorm_Alt, SkuldafnCloudy)**: variant
  `snow_overcast_approved` = the pass-4 files of `OvercastPF` in all six periods (PhysicalSky, height fog, Image Based
  Lighting; wind and height fog included, so the weather's own record-derived values of pass 4 are gone) plus, in EVERY
  period, the four values the approved shot had inherited from the saved file of that moment:
  `cloudLayer.lighting.brightness` 1.7, `cloudLayer.low.topExpansionScale` 0.4, `cloudLayer.wind.development` 0.2,
  `cloudLayer.wind.disturbance` 0.15 (all four drivable: Transitionable floats), plus `ExposureCompensation`.
  Overcast weathers themselves stay pure pass 4 (no extras). No snow / snowstorm difference. SkuldafnCloudy was thin
  broken cloud in pass 4; it is pass-1 group "snow", so it gets the deck too.
- **Snow, light (2: SnowClear, SnowClear_Alt)**: variant `snow_sunny` as shot (Day). Other periods are derived, not
  reviewed: see "Period scheme" in `weather-table-5.md`.
- Exposure (`PostProcessing / Histogram Auto Exposure / settings / ExposureCompensation`): snow deck -2.5, `snow_sunny`
  -2.8 at Sunrise / Day / Sunset; half of the raise from -3.5 at Dawn / Dusk (-3.0 / -3.15); no entry at Night.

Checked by the generator (offline): every entry against the catalogue + policy (feature whitelisted for weather scenes,
not blacklisted, row exists, Transitionable + SceneControllable float or blend, inside its range); the 792 files of pass-4
weathers and snow decks equal the pass-4 pack files value for value (snow decks: after taking the four extras out); `snow_overcast_approved` equals the approved pass-4
`08_overcast_OvercastPF` variant + exactly the four extras; no fair / special weather has a folder; no Ground Fog; no exposure entry at Night;
Baseline holds only `lightning.*`. 0 problems.

## Baseline (`Baseline\PhysicalSky.json`)

Only `lightning.weatherMode` 0 and `lightning.rate` 0.

- Why needed: `weatherMode` is an integer (not blendable), so no weather entry can carry it, and with the default mode 1
  the NAT storm records (thunder byte 255) get no lightning (pass-4 finding). With mode 0 the global rate must be 0 or
  every weather with a suitable cloud would flash; storm weathers carry their own rate (4-10 / min).
- Effect outside closed weathers: no automatic lightning in any weather without a storm entry. That is the only thing the
  Baseline changes in clear weather, and nothing visible unless a fair or other-realm weather was showing lightning before.
- **Left out because they would alter clear weather** (pass-4 Baseline keys the saved base does not hold, so the
  Baseline value would apply everywhere): `cloudLayer.cirrus.uvSize` 3 (code default 1), `cloudLayer.cirrus.weather`
  (sparse-streak pattern). Left out because the saved file overrides them anyway (no effect, some now differ from what is
  saved): `enableVolumetricClouds`, `enableVanillaClouds`, `aerosolType`, `aerosolLoading`, `cloudMap` primary range,
  `cloudLayer.low.*`, `cloudLayer.cirrus.altitude / densityScale`, `cloudLayer.wind.*`. Full list with the saved-base values:
  "Pass-4 Baseline keys versus the saved settings" in `weather-table-5.md`.
- Consequence for `snow_sunny`: it was shot with high-layer UV size 3, which only a Baseline or the saved settings can set
  (see below). In the pack its high layer uses whatever UV size is saved (code default 1 if never saved).

## Can the pack drive it? (current main checkout)

All settings asked about are drivable per weather: catalogue rows are Float, `Persisted | Transitionable |
SceneControllable`, their features are in `kTimeOfDayFeatureWhitelist`, no blacklist entry matches.

| Setting | Verdict |
|---|---|
| PostProcessing `Histogram Auto Exposure / settings / ExposureCompensation` | drivable, -5..5. `PostProcessing` is whitelisted at `SceneSettingsPolicy.h:136` |
| PhysicalSky `cloudLayer.lighting.brightness` | drivable, 0..4 |
| PhysicalSky `sunlightColor.xyz` | drivable, no bounds |
| PhysicalSky `cloudMap.procedural.parameters.primary / secondary.range.xyzw` | drivable, -16..16 |
| PhysicalSky `cloudLayer.low.densityScale` | drivable, 0..1 |
| PhysicalSky `cloudLayer.lighting.deckLight / deckGroundLight / deckHorizonLight` | drivable, 0..4 / 0..4 / 0..0.95 |
| ImageBasedLighting `DALCAmount`, `SkyIBLSaturation` | drivable, 0..1 / 0..2 |

Not drivable, and therefore not emitted (both are in the `snow_sunny` variant):

| Setting | Blocked by | Smallest change that would allow it |
|---|---|---|
| PhysicalSky `cloudLayer.cirrus.uvSize` (3.0) | blacklist entry `{ "PhysicalSky", "cloudLayer", "cirrus", "uvSize" }` at `src\CSEditor\SceneManager\SceneSettingsPolicy.h:34`. The catalogue row itself is a Transitionable float, 0.1..32 | delete that one line (not done; whether blending a UV size between weathers looks acceptable is untested) |
| PhysicalSky `lightning.weatherMode` (0) | catalogue row is `Integer`, flags `Persisted | SceneControllable` without `Transitionable`; a weather scene only accepts blendable floats (`src\CSEditor\SceneManager\SceneSettingsInternal.cpp`, `IsSceneSettingValueAllowed`, the `requireNumeric` test, about line 971, and `IsCatalogSettingAllowedForSceneType`) | none small: weather scenes would have to accept stepped integer values. Stays in the Baseline |

Caveat on exposure, read from the source, not tested: `src\Features\PostProcessing\HistogramAutoExposure.cpp:80` blends
`ExposureCompensation` to `NightExposureCompensation` between 19:00-21:00 and 05:00-07:00 by game hour, so the entry does
nothing at night anyway; and lines 85-95 replace the compensation while a physical camera state is active (Cinematic
Camera is enabled in the saved settings). The harness variants set the same key, so whatever the user saw there is what
the entry does.

## Read this before installing: the live saved file keeps being overwritten

`SettingsUser.json` was rewritten by the running game / harness twice during the review: at 12:34 with the snow deck
test sky, and again at **12:57 with the `snow_sunny` test sky** (after it had been restored): broken-cumulus cloud map,
brightness 2.0, cirrus UV size 3, DALC 0, sky saturation 1.3, `lightning.weatherMode` 0. Exposure is -3.5.

- The generator therefore does NOT read the live file as the saved base. It uses
  `SettingsUser.foxnne-baseline-20261122.json` (`SAVED_CANDIDATES` in the tuning table), compares the live file with it on
  every run and prints a warning while they differ (30 keys at the last run).
- Before installing: close the game, restore Physical Sky / Image Based Lighting of `SettingsUser.json` from that file
  again, and re-run the generator until the warning is gone. The pack leaves all 65 fair / special weathers on the saved
  values, so whatever is saved IS the clear-weather look.
- `snow_sunny`: 71 PhysicalSky keys written. 6 left out: 5 because the saved base holds the same value (`aerosolPhaseG`,
  primary range z, base 1200 + 900, cirrus density 0.3) and `lightning.rate` 0, which the pack Baseline holds. If those
  saved values are changed later, SnowClear follows them.
- Pass-4 files (overcast, fog, rain, storm) do not write `cloudLayer.lighting.brightness`, `topExpansionScale`,
  `wind.development / disturbance`, `coverageGain`, `ndfScale` or `cloudLayer.cirrus.uvSize`: those come from the saved
  settings. If overcast / fog were approved on the same polluted base as snow, they inherited the same four extras and
  pure pass 4 will look different (darker cloud: brightness code default instead of 1.7). Not determined.

## Route A (recommended): as the active pack

Game closed for every file step. Back up `SettingsUser.json` and `SceneSettings\SceneManager.json`.
The build must be the current main checkout or newer (heavy-sky, lightning and the PostProcessing whitelist entry are in
it). Remove `Presets\foxnne-nat3-clouds-pass4\` (or pass 3) if present: same weathers.

1. Copy `draft\foxnne-nat3-clouds-pass5\` to `Presets\foxnne-nat3-clouds-pass5\` (beside `foxnne-look`): manifest
   `foxnne-nat3-clouds-pass5.json`, `Baseline\PhysicalSky.json`, `Weather\<formkey>\<Period>\foxnne-nat3-clouds-pass5_<Feature>.json`
   (875 files in all).
2. Start the game, Presets page, apply "foxnne NAT III clouds (pass 5, closed skies)" once. Side effect:
   `Presets.activePackId` changes from `e11:fnenb Cabbage` to `foxnne-nat3-clouds-pass5`, i.e. **the current active pack
   is replaced**; check that the look that pack supplied is not lost (if it is, use route B). `foxnne-look` stays a Baseline pack.
3. `CommunityShaders.log`: no `[SceneSettings]` warning ("not whitelisted", "blacklisted", "not permitted by the compiled
   scene settings catalog", "not a supported scene-manager setting") and no "Skipped Baseline file" is expected.
4. Physical Sky menu: Lightning shows "any weather" and rate 0 in clear weather.
5. `fw` a clear weather first and confirm it is unchanged, then OvercastPF `53B6`, Snow `4D7FB`, SnowClear `8476`, a fog,
   a rain and a storm, at 13:00 and at night.

Remove: delete `Presets\foxnne-nat3-clouds-pass5\`, restore the `SettingsUser.json` backup (brings back the previous active pack).

## Route B: user-layer entries, active pack untouched

1. Copy the pack WITHOUT its `Weather` folder (Baseline only) and enable it as a Baseline pack, or set Lightning to
   "any weather" / rate 0 by hand.
2. Right before installing run `python -I draft\_generator\merge_user_layer5.py` (not run yet): reads the live
   `SceneManager.json`, writes `draft\alt-user-overrides-pass5\SceneManager.merged.json` (22599 entries from
   `SceneManager.weather.pass5.json` added; same feature / path / setting / period replaced). Copy it over
   `SceneSettings\SceneManager.json`.
3. Same log check.

Remove: restore the `SceneManager.json` backup, delete the pack folder, restore `SettingsUser.json`.

## Verified versus assumed

- Verified offline by the generator: the list under "Checked by the generator".
- Read from the source, not run: missing periods fall through to the layer below (`SceneSettingsResolve.cpp:852`,
  `value_or(lower)`); Baseline sits under the user layer (`src\BaselineManager.h`); the exposure blend above.
- Assumed: that the game's entry check equals the offline copy (it adds one test the copy cannot make: the value must be
  compatible with the live feature value); that applying a pack as active behaves as in pass 3 / 4 notes (never done for
  these packs); that a weather with entries blending to one without returns cleanly to the saved look.
- Not determined: which saved base the overcast / fog approval was shot on; what keeps rewriting the live `SettingsUser.json`;
  whether the ash storms should get the snow exposure raise; the look of `snow_sunny` outside 13:00 and with UV size 1.

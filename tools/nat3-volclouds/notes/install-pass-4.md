# Installing pass 4 for a test (nothing was installed; untested in game)

Target root: `C:\Modlists\NGVO 8.0 Beta\mods\CS Settings\SKSE\Plugins\CommunityShaders\`
Source root: `C:\Users\foxnn\dev\nat3-volclouds\draft\`

## Before anything

1. **Build first.** Pass 4 needs ONE build that contains `foxnne/heavy-sky`, `foxnne/lightning-fix` and
   `foxnne/ground-fog-near`. On an older build the heavy-sky, new lightning and Ground Fog entries are refused ("not
   permitted by the compiled scene settings catalog"), and what is left (coverage exactly 1 without deck light or relief)
   is the flat sheet again. Clear the shader cache with that deploy (heavy-sky and lightning changed constant buffers).
2. **Sweeps before files.** The harness sweeps need no install and show the same values:
   `draft\sweeps-pass4\pass4_types_sunrise.json`, `..._day.json`, `..._sunset.json`, `..._night.json` (13 variants each:
   clear dry / humid, fair dry / middle / humid, partly dry / middle / humid, overcast, rain, storm, snow, fog; each
   names its real weather). Shoot each file at the hour of its period, because the values are that period's values and
   Ground Fog adds its own time-of-day curve from the game hour: suggested `--hours 6.5` (sunrise), `13` (day), `18.25`
   (sunset; the warm window seen was 18:00-18:30), `23` (night). Example:
   `python sky_sweep.py p4_sunset C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-pass4\pass4_types_sunset.json --view plains_west --hours 18.25`
   - Every variant sets `cloudLayer.cirrus.uvSize` 3 and `lightning.weatherMode` 0 (global-only keys).
   - The `*_rays.json` twins add the proposed screen-space rays strength (Effects11 `StandaloneRays` + multiplier).
     The pack cannot deliver that (not scene-drivable): use them only to judge the rays curve.
3. Game closed for every file step (files added while the game runs are not seen through the MO2 VFS).
   Back up `SettingsUser.json` and `SceneSettings\SceneManager.json`.

## Recommended: route A (as the active pack)

Same reasoning as pass 3: one folder to copy and one to delete, nothing merged into the user file, the user layer stays
yours. Side effect: `Presets.activePackId` changes to `foxnne-nat3-clouds-pass4` (restoring the `SettingsUser.json`
backup undoes it). If the pass-3 pack is installed, remove `Presets\foxnne-nat3-clouds-pass3\` first: the two packs
write the same weathers.

1. Copy `draft\foxnne-nat3-clouds-pass4\` to `Presets\foxnne-nat3-clouds-pass4\` (beside `foxnne-look`):
   - `foxnne-nat3-clouds-pass4.json` (manifest)
   - `Baseline\PhysicalSky.json`: saved base + high-layer UV size 3 + fallback streak pattern + `lightning.weatherMode` 0 and
     `lightning.rate` 0 (storm weathers carry their own rate; see the lightning finding in `per-weather-pass-4.md`)
   - `Weather\<formkey>\<Dawn|Sunrise|Day|Sunset|Dusk|Night>\foxnne-nat3-clouds-pass4_PhysicalSky.json` and
     `..._ExponentialHeightFog.json` (111 weathers), `..._ImageBasedLighting.json` and `..._GroundFog.json` (98 weathers):
     2508 files.
2. Start the game, open the Presets page, apply "foxnne NAT III clouds (pass 4)" once. `foxnne-look` stays enabled as a
   Baseline pack; the per-weather Image Based Lighting files sit above its Baseline values.
3. Check `CommunityShaders.log` for `[SceneSettings]` warnings ("not whitelisted", "blacklisted", "not permitted by the
   compiled scene settings catalog") and "Skipped Baseline file". None are expected on the merged build. A warning about
   `GroundFog` means the build lacks the Ground Fog whitelist entry; about `deckLight` / `baseRelief` / `lightning` that it
   lacks heavy-sky / lightning-fix; about `cloudLayer.cirrus.weather` that the blend entry was refused (still never loaded).
4. Check in the Physical Sky menu that Lightning shows "any weather" (mode 0) and rate 0 outside storms. The saved
   `lightningIntensity` 0.04 only matters outside storms now (storms write 0.8-1.15).
5. `fw <formId>` per representative (`draft\pass4-sky-types.json`) at sunrise, 13:00, 18:00-18:30 and night.

Remove: delete `Presets\foxnne-nat3-clouds-pass4\`, restore the `SettingsUser.json` backup.

## Route B (user-layer entries, active pack untouched)

Only if losing the current active pack matters. 56664 entries go into the user file, so this is the heavier route.

1. Copy `draft\foxnne-nat3-clouds-pass4\` WITHOUT its `Weather` folder to `Presets\foxnne-nat3-clouds-pass4\` and apply it
   once (Baseline only: UV size 3, lightning mode 0 / rate 0).
2. Run `python -I draft\_generator\merge_user_layer4.py` right before installing (reads the live `SceneManager.json`, writes
   `draft\alt-user-overrides-pass4\SceneManager.merged.json`; entries with the same feature / path / setting / period are
   replaced, everything else is kept). Copy that file over `SceneSettings\SceneManager.json`.
3. Same log check. The entries then show as your own and can be edited per weather.

Remove: restore the `SceneManager.json` backup, delete the pack folder, restore `SettingsUser.json`.

## Not delivered by the pack (set globally if wanted)

- Screen-space rays (Effects11 `StandaloneRays`, `StandaloneSunMultiplier`, `StandaloneMoonMultiplier`): not scene-drivable.
  The intended per-period strength is in `pass4-sky-types.json` under `Effects11.notSceneDrivable`.
- Sky Sync horizon fade: global only.
- Game Volumetric Lighting strength: global only (feature is scene-blacklisted).

## When the test results arrive

Edit the TUNING TABLE at the top of `draft\_generator\build_pass4.py` (blocks A-G, each marked with the test it waits on)
and run `python -I build_pass4.py`: pack, user-layer file, sky types, sweeps and `weather-table-4.md` are all rewritten
and re-validated.

# Installing pass 3 for a test (nothing was installed; untested in game)

Target root: `C:\Modlists\NGVO 8.0 Beta\mods\CS Settings\SKSE\Plugins\CommunityShaders\`
Source root: `C:\Users\foxnn\dev\nat3-volclouds\draft\`

Game closed for every step (files added while the game runs are not seen through the MO2 VFS).
Back up first: `SettingsUser.json` and `SceneSettings\SceneManager.json`.

## Recommended now: route A (as the active pack)

Why A: one folder to copy and one to delete, nothing is merged into the 1.6 MB user file, the user layer stays yours
(the paused Look Grade entries keep working on top), and the values show as pack values in the editor. The known side
effect is that `Presets.activePackId` changes from `e11:fnenb Cabbage` to `foxnne-nat3-clouds-pass3`; in source that only
reloads scene overwrites / form edits and re-selects the Post Processing pipeline, which is already the active one.
Restoring the `SettingsUser.json` backup undoes it.

1. Copy the folder `draft\foxnne-nat3-clouds-pass3\` to `Presets\foxnne-nat3-clouds-pass3\` (beside `foxnne-look`). Result:
   - `Presets\foxnne-nat3-clouds-pass3\foxnne-nat3-clouds-pass3.json` (manifest)
   - `Presets\foxnne-nat3-clouds-pass3\Baseline\PhysicalSky.json` (saved base + high-layer UV size 3 + fallback streak pattern)
   - `Presets\foxnne-nat3-clouds-pass3\Weather\<formkey>\<Dawn|Sunrise|Day|Sunset|Dusk|Night>\foxnne-nat3-clouds-pass3_PhysicalSky.json`
     and `..._ExponentialHeightFog.json` (111 weathers), `..._ImageBasedLighting.json` (46 weathers) - 1608 files.
2. Start the game, open the Presets page, apply "foxnne NAT III clouds (pass 3)" once. `foxnne-look` stays enabled as a
   Baseline pack; the two do not overlap (foxnne-look has no `PhysicalSky.json`).
3. Check `CommunityShaders.log` for `[SceneSettings]` warnings ("not whitelisted", "blacklisted", "not permitted by the
   compiled scene settings catalog") and for "Skipped Baseline file". None are expected. A warning about
   `cloudLayer.cirrus.weather` means the blend entry was refused: tell me, the high layer then needs another route.
4. `fw <formId>` per representative (`draft\pass3-sky-types.json`), at 13:00 and 17:30 at least.

Remove: delete `Presets\foxnne-nat3-clouds-pass3\`, restore the `SettingsUser.json` backup (or re-apply the previous preset).

Do NOT copy `draft\optional-groundfog-pass3\` yet: this build refuses Ground Fog in weather scenes (the feature is
missing from `kTimeOfDayFeatureWhitelist` in `src\CSEditor\SceneManager\SceneSettingsPolicy.h`). After adding
`{ "GroundFog" },` there and rebuilding, copy `draft\optional-groundfog-pass3\Weather\` over
`Presets\foxnne-nat3-clouds-pass3\Weather\` (it only adds `foxnne-nat3-clouds-pass3_GroundFog.json` files, 98 weathers).

## Route B (user-layer entries, active pack untouched)

Use this only if losing `e11:fnenb Cabbage` as the active pack turns out to matter.

1. Copy `draft\foxnne-nat3-clouds-pass3\` WITHOUT its `Weather` folder to `Presets\foxnne-nat3-clouds-pass3\`
   (manifest + `Baseline\PhysicalSky.json` only). Apply it once on the Presets page: a Baseline-only pack does not
   replace the active pack. This is needed for the global high-layer UV size 3.
2. Run `python -I draft\_generator\merge_user_layer3.py` right before installing (it reads the live
   `SceneSettings\SceneManager.json` and writes `draft\alt-user-overrides-pass3\SceneManager.merged.json`: the live file
   plus 32904 pass-3 entries on the 111 weather keys, existing entries kept). Copy that file over
   `SceneSettings\SceneManager.json`.
3. Same log check as above. The entries then show as your own (green) and can be edited per weather.

Remove: restore the `SceneManager.json` backup, delete the pack folder, restore `SettingsUser.json`.

## Harness (no install)

`draft\pass3-sky-types.json` has, per type, `representative` -> `PhysicalSky.Day` (flat dotted keys, the cirrus pattern
as one `cloudLayer.cirrus.weather` object), `PhysicalSky.periodOverrides` (apply the matching period on top of Day when
shooting at another hour: rain and partly differ between 13:00 and 17:30, and clear / fair / partly carry Rayleigh x2 at
twilight), `ExponentialHeightFog`, `ImageBasedLighting`, plus top-level `globalOnly` (`cloudLayer.cirrus.uvSize` 3.0)
that has to be set for every shot.

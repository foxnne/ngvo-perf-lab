# Community Shaders 2.0 rc.2 merge review (2026-11-23)

Research only. Nothing was merged, committed, built or checked out. The only writes to the repo were
`git fetch` on `upstream`, `bottled`, `openshaders`, and the loose objects that
`git merge-tree --write-tree` stores for its simulated merges (not reachable from any ref).

Repo: `C:\Users\foxnn\dev\skyrim-community-shaders`, branch `foxnne/llf-shadowless-spots`, HEAD `d2199b167`
(2026-11-22). Working tree still has the uncommitted `src/Features/SkySync.{h,cpp}` change (untouched).

## 1. Where the fork stands

| Ref | Commit | Date |
|---|---|---|
| `v2.0.0-rc.2` = `upstream/dev` | `363ac0246` feat(psky): derive moon disc from moonlight (#3250) | 2026-11-23 |
| `v2.0.0-rc.1` | `a03587448` | 2026-11-18 |
| merge-base(HEAD, upstream/dev) | `ff64d2512` perf(tree-wind): pair trunk cards through a grid (#3234) | 2026-11-22 |
| `upstream/main` | `5db085e77` release 1.9.0 (not relevant) | 2026-09-23 |
| `bottled/Bottle-Compendium` | `a2ebc86e6` | 2026-11-23 |
| `openshaders/dev` | `6fdd88da4` | 2026-11-23 |

- rc.2 is 50 commits after rc.1 (2026-11-19 to 2026-11-23).
- **By ancestry the fork already contains 45 of those 50** (it came in with the Bottle-Compendium merge
  `9194a0a7a`, which contained upstream up to `ff64d2512`). rc.1 is fully contained.
- **HEAD is missing 5 upstream commits, all dated 2026-11-23:**

| Commit | Subject | Files |
|---|---|---|
| `902cab022` | fix(ssgi): upsample edge test and normal mip 0 (#3244) | SSGI ini, `prefilterNormal.cs.hlsl`, `upsample.cs.hlsl`, `ScreenSpaceGI.cpp` |
| `f9aedebe8` | feat(psky): support per weather storm (#3214) | `Storm.cpp/.h`, `CloudStorm.hlsli`, `StormData.hlsli`, `CloudLighting.hlsli`, `Volumetrics.cs.hlsl`, `PhysicalSky.cpp/.h`, translations, catalog test |
| `5d0d2b1f5` | fix(compat): block incompatible DLLs (#3249) | `XSEPlugin.cpp` |
| `c90aec074` | refactor(pp): widen asphere index math (#3246) | `PostProcessing/PhysicalLensModel.h` |
| `363ac0246` | feat(psky): derive moon disc from moonlight (#3250) | `PhysicalSky.cpp/.h`, new `PhysicalSky/MoonTexture.cpp/.h`, `Sky.hlsl`, `SharedData.hlsli`, `SkySync.cpp` (comment only), `SceneWidgetInterceptor`, `Utils/UI`, translations |

Important caveat: "contained by ancestry" does not mean "active". The merge `9194a0a7a` deliberately kept the
fork's own Tree Wind and dropped upstream's Tree Wind performance commits (its own message says so, and also
says "Not built, not tested"). See section 2.

## 2. Release notes mapped to commits

Status key: HAVE = commit is an ancestor of HEAD and the code was spot-checked in HEAD; PARTLY; LACK.

| Release note | Upstream commit(s) | Main files | Fork |
|---|---|---|---|
| Copy individual Scene Manager pages | `950e39a14` feat(cs-editor): copy scene settings per feature (#3222) | `SceneCopyModal.cpp`, `SceneSettingsCopy.cpp`, `SceneSettingsManager.h` | HAVE |
| LL controls for locations | `c9754e022` feat(cs-editor): scene-control Linear Lighting (#3221) | `SceneSettingsPolicy.h` | HAVE (fork line 122; fork also lists `useWithEffects11` as not scene-controllable) |
| Parallax PBR grass | `2292f2099` feat(grass): add parallax to pbr grass (#3192) | `RunGrass.hlsl`, `GrassLighting.hlsli`, `ExtendedMaterials`, `TruePBR.cpp` | HAVE |
| Cloud quality presets, more quality controls | `864c999b2` (#3197), `01687e5da` perf(psky): low quality settings (#3200), `efd1885f0` scene shadows on clouds toggle (#3211) | `PhysicalSky.cpp/.h`, cloud shaders | HAVE (`kCloudQualityLow/Medium/High` in `PhysicalSky.h`) |
| Moon textures and brightness | `2d0dc9034` moon resizing and disk lighting (#3202), `9534fce91` moon disc brightness (#3239), **`363ac0246`** derive moon disc from moonlight (#3250) | `LightDisk.hlsli`, `Sky.hlsl`, `PhysicalSky.cpp/.h`, `MoonTexture.cpp` | PARTLY: has #3202 and #3239; **lacks #3250**, which replaces what #3239 added |
| Per-weather storm clouds | **`f9aedebe8`** (#3214) | `Storm.cpp/.h`, storm shaders, `PhysicalSky` | **LACK** |
| UI fixes | `57415a544` profiling page (#3209), `9b94b4ac9` Development Conditions button (#3201), part of `363ac0246` (HSV colour edit helper in `Utils/UI`) | menu files | HAVE except the `Util::ColorEdit3` helper in #3250 |
| Fixed flickering character lighting | `a6e89268b` (#3215) | `Lighting.hlsl`, `TruePBR.cpp` | HAVE |
| Fixed time pausing | `55292ca4e` keep a manual time pause on close (#3213) | `EditorWindow.cpp`, `SceneSettingsUI` | HAVE |
| Fixed white outlines on grass | `12df79f0c` match depth alpha filtering (#3223) | `RunGrass.hlsl` | HAVE by ancestry (not line-checked against the fork's grass edits) |
| Fixed IBL flicker | `eba920802` supersample sky IBL and reflection sky SH (#3218), `cec55ed4c` distance fallback to specular (#3220) | `DiffuseIBLCS.hlsl`, `Reflection.cs.hlsl`, `IBL.hlsli` | HAVE |
| PSky locked to LL, PP to PSky | `4fe6cad85` fix(modes): lock psky and LL to PP mode (#3212) | `LinearLighting.cpp/.h`, `PhysicalSky.cpp`, `PostProcessingMode.cpp` | HAVE, with a fork change on top (see section 5) |
| Fixed preset export errors | `5a8729377` effects11 save only edited values (#3195), `876ef88ac` ignore unknown keys instead of skipping file (#3217) | `Effect.cpp`, `BaselineManager`, `SettingsCatalog.cpp`, `State.cpp` | HAVE |
| Fixed stutter on cell crossings with large presets | `2cbbf8de7` (#3224) | `SceneSettingsLocationTargets.cpp`, new `Utils/EditorIDCache.cpp` | HAVE |
| Tree Wind fixes incl. a stutter | `36e3bd779` lean direction (#3240), `129da0f8e` build bend data off-thread (#3238), `ff64d2512` pair trunk cards through a grid (#3234) | `TreeWind.hlsli`, `TreeShapes.cpp/.h`, `TreeWind.cpp` | **PARTLY**: #3240 applied by hand to one of two places (see below). **#3238 and #3234 are ancestors but their code is not in HEAD** (merge kept the fork's TreeShapes; no `kPairDistance`, no job queue). The stutter fix is therefore not active. |
| VL settings from preset not applying on load | `bd35bfc4b` (#3216) | `VolumetricLighting.cpp/.h` | HAVE (`ApplyIfChanged` present) |
| Wetness making complex-material surfaces dull | `10f0dc847` keep glossy roughness in deferred rain (#3208) (`398d29e68` was reverted by `d524cd373`) | `Lighting.hlsl` | HAVE |
| Faster shader compile, FXC optimisation off | `d8885e36a` (#3196) | `ShaderCache.cpp`, new `Utils/ShaderCompileFlags.h` | HAVE |
| Improved VRAM usage | `99c03fda9` pp share targets (#3189), `10b6f74c7` release idle colour scratch targets (#3235), `d12605c48` release retained grass mats (#3237) | `PostProcessing*`, `GrassMeshLibrary.h` | HAVE (fork has its own edits in `PostProcessing.cpp`; not re-verified) |
| Performance | `15be229eb`, `1227d8ab7`, `7991062f6`, `9d2853fc3`, `5dad195d8` | PP grading, Skylighting, Water, PSky water sampler | HAVE |
| Misc fixes | `c435c4326`, `2b05afa10`, `bd6b29f53`, `24f9dce55`, `0e06285b2`, `2add8c1f8`, `bf123dfdd` (DevBench pending compiles), `1bd3f69cd`, `ff1b52e52`, `6d4c15537` | various | HAVE |
| Misc fixes (today) | `902cab022` SSGI, `5d0d2b1f5` DLL block list, `c90aec074` lens | | LACK |

Tree Wind detail: in HEAD, `features/Tree Wind/Shaders/TreeWind/TreeWind.hlsli:74` uses the new direction
`float2(cos(Wind.w), sin(Wind.w))`, but the fork's bespoke-tree path at line 321 (`GetBespokeOffset`) still
uses the old `float2(sin(Wind.w), cos(Wind.w))`. So the hand-masked Whiterun tree may lean a different way
than ordinary trees, rain and snow. Not verified in game.

## 3. Merge difficulty (HEAD + upstream/dev)

`git merge-tree --write-tree HEAD upstream/dev` reports 9 conflicting files. Everything else auto-merges
(including `Sky.hlsl`, `SkySync.cpp`, `CloudLighting.hlsli`, `Storm.cpp/.h`, `Utils/UI.*`, translations).

| Area | Files | From | Rating | Notes |
|---|---|---|---|---|
| Plugin block list | `src/XSEPlugin.cpp` | `5d0d2b1f5` | Low | One list. Keep the fork's `reversed_z.dll` entry and add upstream's `NativeMeshLightFlickerFix.dll`, `DripSim.dll`, `DripSimRain.dll`. |
| Physical Sky constant buffer | `package/Shaders/Common/SharedData.hlsli`, `src/Features/PhysicalSky.h` | `363ac0246` | Low to medium | Fork added `oceanColorAmount`, `oceanParams` before `diskBrightness`; upstream replaces `diskBrightness` with `moonDiscRadiance[2]`. Keep ocean fields, then `moonDiscRadiance[2]`. Buffer grows by 16 bytes; C++ and HLSL order must match. |
| Physical Sky settings and Reset | `src/Features/PhysicalSky.cpp` (3 hunks) | `f9aedebe8`, `363ac0246` | **Medium, with a trap** | The fork serialises settings in two halves (`PSKY_SETTINGS_A` / `_B`, commit `68831fe48`) because of the 64-member macro limit. Git only flags the canonical `#if 0` list. **`PSKY_SETTINGS_A` must be edited by hand** (`masserDiscBrightnessEV, secundaDiscBrightnessEV` -> `masserDiscMatchLight, secundaDiscMatchLight`) and `supercellStorms` added to `PSKY_SETTINGS_B`, or the build breaks / the settings silently do not save. Third hunk: keep the fork's ocean cbData lines, take upstream's `discRadiance` block in place of `diskBrightness`. |
| Volumetric cloud shader | `features/Physical Sky/Shaders/PhysicalSky/Volumetrics.cs.hlsl` (2 hunks) | `f9aedebe8` | **Medium to high** | Fork has +337 lines here. Hunk 1: fork renamed `sampleNDF` to `sampleWeatherNDF` and wraps it; upstream split the same function into `SampleCloudShapingStart` + `SampleWeatherCloudModel`. Hunk 2: upstream moved the shape-noise coordinate code into a new `WeatherCloudNoisePosition()`; the fork's cloud de-tiling (`CLOUD_DETILE_AMOUNT`, `CLOUD_DETILE_SLICE`) sits in exactly that code and must be moved into the new function, which upstream now also calls from the storm fade path. Needs a visual check of clouds afterwards. |
| SSGI | `ScreenSpaceGI.ini`, `prefilterNormal.cs.hlsl`, `upsample.cs.hlsl` (deleted in HEAD), `ScreenSpaceGI.cpp` | `902cab022` | **High / not applicable** | The fork runs Bottled's NRD-based SSGI rewrite (version 5-1-0, `a4085e248`), upstream's fix is for the old 4-3-x pipeline. Resolve all four as "ours". |

Fork-customised areas and the 5 missing commits:

- TreeWind: no conflict, not touched.
- PhysicalSky / volumetric clouds: all the real work is here (above).
- SkySync: `363ac0246` changes one comment; auto-merges in the committed tree. **But the uncommitted SkySync
  change will make `git merge` refuse to start** (the merge needs to update that file). Commit or stash it first.
- Scene Manager / presets: only `SceneWidgetInterceptor` (new `InterceptColor3`), auto-merges.
- LODShadows, Water.hlsl, Lighting.hlsl, RunGrass.hlsl, DevBenchBridge: not touched by the 5 commits.

Overall: a small merge. Two easy conflicts, one medium (with the two-halves trap), one shader that needs care,
one feature to skip.

## 4. Bottled and open-shaders

### Bottled (2 commits after `11a412709`)

| Commit | What | Applies? |
|---|---|---|
| `309f40969` fix grass using wrong ambient | `RunGrass.hlsl`: when SSGI "Replace Ambient" is on, grass transmission no longer uses unoccluded vanilla ambient; passes a boost through `Masks.z`. `composite.cs.hlsl`: clamp of `Masks.z` raised from 1 to 8. | One trivial conflict in `RunGrass.hlsl` (line ~1356): fork's `Masks2` line carries the Neural Rendering foliage category. Keep the fork's `Masks2`, take the new `Masks` line with `ssgiTransmissionBoost`. The rest auto-merges. Low. Only matters with SSGI Replace Ambient on. |
| `a2ebc86e6` block hdr if not 10bit | `HDRDisplay.cpp/.h`, `Rows_HDR.cpp`: holds HDR off when the swap chain is 8-bit. **Also contains an unrelated fog change** in `ExponentialHeightFog.cpp`: "Original Fog Color Override" now also works with "use weather fog settings" outdoors (hue only). | Applies cleanly (no conflicts). Low. The fog part does nothing for the current pack: no file under `CS Settings` sets `originalFogColorOverride`. |

Bottled "shadow pop-in" fix: **not found**. Searched every `bottled/*` branch for commits not in HEAD since
2026-11-17; only the two commits above exist. It is not public yet (or was squashed into something already
merged, e.g. `4a75b110e` "PCSS sun size from Physical Sky", which HEAD has). Could not verify further.

### open-shaders shadow fade commits (2026-11-20)

HEAD is 3951 commits behind `openshaders/dev`; these are separate lines of development.

| Commit | Touches | Can it be cherry-picked? |
|---|---|---|
| `1034fab9a` fade shadows across slot swaps (#1207) | `src/Features/LightLimitFix/ShadowScheduler.cpp`, `ShadowCasterManager.*`, `ShadowCasterMath.h`, `ShadowCasterUI.cpp` | **No.** None of these files exist in HEAD. The fork's LLF folder only has `Common.h`, `LightAttach.*`, `LightAttachGate.h`; its local shadows come from Bottled's implementation (`GetLocalShadowWithLightFade` etc.). |
| `6b6bcb790` hold edge lights the engine culls (#1206) | same Shadow Caster files | **No**, same reason. |
| `86100237d` fade contact shadows instead of cutting (#1209) | `LightLimitFix.hlsli`, `Lighting.hlsl`, `Water.hlsl`, `LightLimitFix.cpp` | **Not as a patch** (conflicts in all 5 files; the fork's contact shadows are a different implementation). The idea ports in a few lines: the fork's `GetContactShadowSteps` (`LightLimitFix.hlsli:382`) still drops step count with distance and rounds, which is the banding this commit removes. The fork already fades strength (`strengthScale`), so it is partly covered. |
| also seen: `679639333`, `9064aceb0`, `bfd581d63`, `93af63c61`, `7ef472975` | Shadow Caster files and shared shaders | No, same reason. `25b229281` (leaf mips in `Utility.hlsl`) is the only one that merges without conflict. |

To get open-shaders' shadow fade behaviour, the fork would have to port the whole Shadow Caster system
(about 15 files), or re-implement the fade idea on Bottled's local shadows. That is a project, not a pick.

## 5. Behaviour changes to know about

### Physical Sky / Linear Lighting / Post Processing lock (`4fe6cad85`, already in the fork)

- `LinearLighting::Settings::enableLinearLighting` is gone. LL is on in Post Processing mode and off in
  Vanilla mode; the checkbox is read-only (`upstream/dev:src/Features/LinearLighting.cpp:61`, `:148`).
- `PhysicalSky::IsActive()` now requires Post Processing mode
  (`upstream/dev:src/Features/PhysicalSky.cpp:619`; fork `src/Features/PhysicalSky.cpp:631-635`).
- The fork added `useWithEffects11` so LL can run in Effects 11 mode, **but Physical Sky still turns off in
  Effects 11 mode in the fork too.** This matters for the roadmap item "port fnenb to Effects 11": in Effects 11
  mode there is no Physical Sky, no volumetric clouds. The current pack is safe: all 42 `pipeline` entries under
  `CS Settings` say `PostProcessing`, and no file contains `enableLinearLighting`.

### Preset file format (`876ef88ac`, already in the fork)

- A preset file with keys the feature does not know is no longer skipped whole; the unknown keys are dropped
  and the rest applies, with a "loaded with some settings ignored" notice. Good for the per-weather pack.
- No change to folder layout or file naming between rc.1 and rc.2.

### Settings key changes in PhysicalSky

- **No renames in `cloudLayer.*` or `cloudMap.*`** between rc.1 and rc.2 (checked `PhysicalSky.h`,
  `PhysicalSky.cpp` serialisation lists and `src/Features/PhysicalSky/`). The pack's keys (including the
  fork-only `cloudLayer.lighting.deck*`) are not affected.
- Changed defaults (already in the fork via `864c999b2`): missing keys now fall back to the Medium preset,
  `rayMarchRange` 32 -> 10 km, `marchStepScale` 0.5 -> 0.8, `cloudAmbientSHOnly` true,
  `cloudFastReconstruction` true (`upstream/dev:src/Features/PhysicalSky.h:128-130`). The pack sets
  `rayMarchRange` 41 explicitly in 4 files; the other quality keys are not set anywhere in the pack, so they
  follow these defaults unless SettingsUser.json holds them (not checked key by key).
- New in the 5 missing commits: `masserDiscBrightnessEV` / `secundaDiscBrightnessEV` removed,
  `masserDiscMatchLight` / `secundaDiscMatchLight` and `supercellStorms` added. No file under `CS Settings`
  contains the removed keys, so nothing is lost.

### Per-weather storm control (`f9aedebe8`, not in the fork)

- One new setting: `SceneBlend supercellStorms` in `PhysicalSky::Settings`
  (`upstream/dev:src/Features/PhysicalSky.h:232`, serialised at `PhysicalSky.cpp:219`). It is scene-controllable
  and transitionable; its value is `{ "instances": { "<stormId>": true|false } }`.
- UI: while a scene is armed in Scene Manager, the "Storm Instances" section becomes "Supercell Storms" with
  "Override Supercell Storms in this scene", "Add Supercell Storm", per-storm checkbox, "Remove storm"
  (`upstream/dev:src/Features/PhysicalSky/Storm.cpp:609-683`).
- Runtime: each non-volcanic storm instance gets an activation weight that ramps over the Scene Manager's
  location transition time (`Storm.cpp:39-52`, `:134-160`, `:578-584`); the shader fades the storm's density,
  erosion and light with it (`CloudStormData.lifecycle`, `Storm.h:64`, `StormData.hlsli:26`).
- **Without a scene override nothing changes**: a missing selection keeps each instance's own `enabled` flag
  (`Storm.cpp:41`). Volcanic instances are never scene-controlled.

### Moon disc and moonlight (`363ac0246`, not in the fork)

- Removes the two "Disc Brightness" EV sliders that rc.2's notes mention via #3239 and adds two checkboxes,
  "Disc Matches Light Color": `masserDiscMatchLight`, `secundaDiscMatchLight`, default `true`
  (`upstream/dev:src/Features/PhysicalSky.h:158-159`, UI at `PhysicalSky.cpp:836-864`).
- Disc brightness is no longer a free control. It is computed so the drawn disc integrates to the moon's
  illuminance (`PhysicalSky.cpp:2152-2174`, shader `package/Shaders/Sky.hlsl:626-634`,
  `SharedData.hlsli:593`).
- **Moonlight itself changes**: `masserColor` / `secundaColor` are multiplied by a phase factor measured from
  the moon textures (mean luminance of the bound phase texture over the full-moon texture;
  `PhysicalSky.cpp:2063`, `:2066`, `MoonTexture.cpp:58`). "Lunar Illuminance" now means full-moon illuminance.
  Nights away from full moon get darker. This will shift night exposure and the look baseline.
- Interaction with Sky Sync: with Physical Sky driving the light colour, Sky Sync multiplies by the moon's
  fade alpha only (`SkySync.cpp:481-485`), so the New / Crescent / Full Moon Intensity sliders appear not to
  shape that path. How this combines with the uncommitted "Hidden Moon Intensity" change was not tested;
  it scales `colors[idx]`, which still feeds that multiply, so it should keep working. **Unverified.**
- Custom moon textures (any moon retexture in the modlist) now directly set night brightness per phase.

### Other

- `a2ebc86e6` (Bottled) changes what "Original Fog Color Override" does when weather fog settings are used.
  Not used by the pack today.
- `5d0d2b1f5` makes CS refuse to run alongside `NativeMeshLightFlickerFix.dll`, `DripSim.dll`,
  `DripSimRain.dll`. Not checked whether the modlist has any of these; worth a look before taking it.

## 6. Recommendation

Before anything: commit (or stash) the SkySync work in progress; a merge cannot start with it dirty.

Take now, smallest first:

1. `c90aec074` (lens index math): no conflict, no behaviour change.
2. `5d0d2b1f5` (DLL block list): one-line conflict. First check the modlist for the three DLL names.
3. Bottled `a2ebc86e6` (HDR guard + fog override): applies cleanly.
4. Bottled `309f40969` (grass ambient under SSGI Replace Ambient): one trivial conflict, keep the fork's
   `Masks2` line.
5. Fix the bespoke-tree wind direction at `TreeWind.hlsli:321` to match line 74 (fork-side one-liner, check
   in game on the Whiterun tree).

Take next, as its own step with a build and a look at the sky:

6. `f9aedebe8` (per-weather storms). Default behaviour is unchanged, so it is safe to carry; the cost is the
   `Volumetrics.cs.hlsl` resolution (move the de-tile code into `WeatherCloudNoisePosition`) and adding
   `supercellStorms` to both the canonical list and `PSKY_SETTINGS_B`.

Skip:

- `902cab022` (SSGI): targets the old SSGI; the fork uses Bottled's NRD SSGI. Resolve as "ours".
- open-shaders `1034fab9a`, `6b6bcb790` and the other Shadow Caster commits: the code they patch is not in the
  fork.

Needs the user's decision:

- **`363ac0246` (moon)**: it changes night brightness (phase-scaled moonlight) and removes the disc brightness
  sliders. Either take it and re-tune nights / re-save the baseline, or hold it until the look work is at a
  good stopping point. It can be left out while taking 1-6, but leaving it out long-term means every later
  upstream merge in `PhysicalSky.cpp` conflicts a little more.
- **Tree Wind stutter fixes** (`129da0f8e` off-thread bend data, `ff64d2512` grid pairing): deliberately not
  taken in the last merge. If Tree Wind stutter on cell load still shows in the flybench, these need a manual
  port onto the fork's `TreeShapes.cpp` (which is about 1150 lines ahead of upstream). Medium to high effort.
- **Physical Sky in Effects 11 mode**: currently impossible in both upstream and the fork. If the fnenb /
  Effects 11 route is still wanted with Physical Sky, the fork needs its own change to `PhysicalSky::IsActive()`.
- **open-shaders shadow fades**: port the idea of `86100237d` (contact shadow distance fade, small) now, and
  decide separately whether the Shadow Caster system is worth porting.
- Bottled's "shadow pop-in" fix: wait until it appears in the repo, or ask InTheBottle which commit it is.

## Not verified

- Nothing was built or run. All "applies cleanly" statements are from `git merge-tree` simulations.
- "HAVE" rows were confirmed by ancestry plus a spot check of a marker in HEAD for most items; the grass white
  outline fix, the VRAM changes in `PostProcessing.cpp` and the IBL fixes were not line-compared against the
  fork's own edits in the same files.
- Whether the fork's `GetBespokeOffset` wind direction is a real bug or intended.
- The Sky Sync / phase interaction after `363ac0246`, including the uncommitted Hidden Moon Intensity change.
- Whether SettingsUser.json holds cloud quality keys that override the new Medium defaults.
- Whether the modlist contains any of the three newly blocked DLLs.
- Bottled's "shadow pop-in" fix could not be located.

# Shadow and forest levers - current values (read-only audit, 2026-11-17)

Profile `foxnne-nsfw`, `C:\Modlists\NGVO 8.0 Beta`. Nothing was changed, nothing was launched.

Legend for the "Source" column:
- **[R]** read directly from the named file in this audit.
- **[I]** inferred (engine behaviour, load-order rule, or general Skyrim knowledge, not measured).

"Vanilla Ultra" = Bethesda SSE launcher Ultra preset. Where I am not confident it says "unknown".
"Live?" = can be changed without a restart. `setini` behaviour is general knowledge [I], not tested here.

File shorthand:
- PREFS = `profiles\foxnne-nsfw\skyrimprefs.ini`
- INI = `profiles\foxnne-nsfw\skyrim.ini`
- CUSTOM = `profiles\foxnne-nsfw\skyrimcustom.ini`
- CSUSER = `mods\CS Settings\SKSE\Plugins\CommunityShaders\SettingsUser.json` (delta file: only values that differ from defaults)
- CSPACK = `mods\CS Settings\SKSE\Plugins\CommunityShaders\Presets\foxnne-look\Baseline\<Feature>.json` (baseline pack `foxnne-look`, listed in CSUSER `Presets.baselinePackIds`)
- SRC = `C:\Users\foxnn\dev\skyrim-community-shaders\src`

Caveats that apply to the whole document:
1. I assumed the MO2 profile uses profile-local INIs (the three files exist in the profile folder). Not verified against `settings.ini` of the profile.
2. CS effective value = code default (SRC) overridden by CSPACK, overridden by CSUSER. The layering order is inferred from file layout, not from reading the loader. The deployed `CommunityShaders.dll` was assumed to match the source tree defaults; not verified.
3. A key "not set" means it appears in none of PREFS / INI / CUSTOM, so the engine's built-in default applies.

---

## 1. Shadow settings

### 1a. Game INI

| Lever | Current | Source | Vanilla Ultra | Visible effect | Restart? | Live? |
|---|---|---|---|---|---|---|
| `fShadowDistance` [Display] | **10000** | [R] PREFS:81 | 8000 | Range of sun shadow cascades. Larger = more casters per cascade and blurrier shadows per texel. | No | `setini "fShadowDistance:Display" N` generally works live [I] |
| `iShadowMapResolution` | **2048** | [R] PREFS:93 | 4096 | Sharpness of sun/local shadows. Already below Ultra. | Yes [I] | No |
| `iNumSplits` | **2** | [R] PREFS:86 | 2 | Number of sun cascades. CS fix supports 1-3 (SRC `EngineFixes\ShadowmapCascadeRasterizerFix.h:72-78`, default 2, min 1, max 3). | Yes [I] (CS reads it once at install, `...RasterizerFix.cpp:10`) | Exposed in CS menu as a game setting, but takes effect after restart [I] |
| `fFirstSliceDistance` | **2896** | [R] INI:79 and CUSTOM:17 | 2800 (believed) | Extent of the near (sharp) cascade. Smaller = sharper near shadows, fewer casters in cascade 0, more in cascade 1. | unknown | unknown |
| `iNumFocusShadow` | 0 | [R] PREFS:85 | unknown | Extra focus shadow maps for actors. Already off. | - | - |
| `fFocusShadowMapDoubleEveryXUnit` | 450 | [R] PREFS:67 | 450 | Irrelevant with focus shadows at 0. | - | - |
| `iShadowMaskQuarter` | 4 | [R] PREFS:94 | 4 | Shadow mask resolution divider. CS reads it (SRC `Globals.cpp:299`). | Yes [I] | No |
| `bDrawLandShadows` | 1 | [R] PREFS:49 | 1 (believed) | Terrain casts into the shadow map. | Yes [I] | unknown |
| `bTreesReceiveShadows` | 1 | [R] PREFS:61 | 1 | Trees receive sun shadows. | Yes [I] | unknown |
| `bDisableHighTreeShadow` | 1 | [R] INI:61 | unknown | Tall trees excluded from shadow casting (tied to the next key). | unknown | unknown |
| `fMaxHeightShadowCastingTrees` | 5000 | [R] INI:90 | unknown | Height cutoff used with the key above. | unknown | unknown |
| `bDisableShadowJumps` | 1 | [R] INI:62 | unknown | Sun shadow moves in steps instead of continuously. | - | - |
| `fSunShadowUpdateTime` / `fSunUpdateThreshold` | 0.25 / 1.5 | [R] INI:104,106 | 1 / 0.5 (believed) | How the sun shadow direction steps. Cosmetic, not a cost lever. | No | `setini` [I] |
| `fShadowDirectionalBiasScale` | 0.47 | [R] INI:97, CUSTOM:23 | unknown | Bias only. Not a cost lever. | - | - |
| `fPoissonRadiusScale` | 4.0 | [R] INI:91 | unknown | Shadow filter radius. | - | - |
| `fInteriorShadowDistance` | 3000 | [R] PREFS:69 | 3000 | Interiors only. | - | - |
| `fLightLODStartFade` | 3500 | [R] PREFS:72, CUSTOM:22 | 3500 | Distance where point lights fade. | No | `setini` [I] |
| `fLightLODRange` | 26624 (INI) / 24576 (CUSTOM) | [R] INI:89, CUSTOM:21 | unknown | CUSTOM is expected to win over INI [I]. | - | - |
| `bVolumetricLightingEnable` / `iVolumetricLightingQuality` | 1 / 2 | [R] PREFS:65,98 | 1 / 2 | Vanilla god rays; CS Volumetric Lighting has its own quality (see 1c). | - | - |
| `bShadowsOnGrass` | **not set** | [R] absent from all three files | unknown | Grass receives shadows. Engine default applies. With CS replacing the Grass shader, the CS Grass Lighting feature decides the actual look [I]. | - | - |
| `fShadowBiasScale`, `fShadowLODMaxStartFade`, `fShadowLODStartFade`, `fSplitOverlap` | **not set** | [R] absent | unknown | Engine defaults. | - | - |

### 1b. Runtime overrides outside CS

| Item | Finding | Source |
|---|---|---|
| SSE Display Tweaks | Winning file is `mods\NGVO - MCM and INI Settings\SKSE\Plugins\SSEDisplayTweaks.ini` (modlist line 28, above `SSE Display Tweaks` at line 2143). It contains **no shadow, LOD or tree keys** (sections: Main, Render, HAVOK, Controls, Window, Papyrus, Miscellaneous, OSD). Render section: borderless, `EnableVSync=true`, `FramerateLimit=240`. | [R] grep for "shadow" = 0 hits; [Render] section read in full |
| Shadow Boost / dynamic shadow plugin | **None found** by name in `modlist.txt` (searched "Shadow", "eFPS", "Occlusion"). Only cosmetic shadow mods (Window Shadows Ultimate, Shadows Of Sunlight). | [R] modlist grep. I did not scan DLLs. |
| Skyrim Performance Solution (SPS.dll) | The earlier audit `audit\skse_plugins.md` line 17 records that SPS hooks "shadow accumulate/render" and that its shadow cache and its occlusion are **auto-off** because CS HiZ is active. Not re-verified today. | [R] of the earlier audit file only |
| `NGVO - Fur Shell Shadow Optimization` | Present but **disabled** (`-`, modlist line 9). | [R] |

### 1c. Community Shaders (fork, branch foxnne/nr-pr6)

Defaults are from the `.h` Settings structs. "Current" = default unless CSPACK / CSUSER lists the key.

| Feature / setting | Default (SRC) | Current | Source | Effect | Live? |
|---|---|---|---|---|---|
| **Shadowmap Cascade Rasterizer Fix** (engine fix) | per-cascade depth bias; `maxCascades = 3`; exposes `iNumSplits:Display` 1-3 | iNumSplits 2 | [R] `EngineFixes\ShadowmapCascadeRasterizerFix.h` | Bias quality. No distance setting. | iNumSplits at restart [I] |
| **Shadowmap Cascade Culling Fix** (engine fix) | no settings | on if installed | [R] `EngineFixes\ShadowmapCascadeCullingFix.h` | Pulls cascade culling planes in by 2x fSplitOverlap; slightly fewer casters per cascade. | - |
| **Sun Shadow Mask Fix** (engine fix) | no settings | - | [R] `EngineFixes\SunShadowMaskFix.h` | Fixes one-frame unshadowed pop. Reads shadow distance. | - |
| **HiZ Occlusion Culling** `enableHiZCulling` | true | true (not overridden) | [R] `Features\HiZOcclusion.h:127`, CSUSER:37-40 | Skips draws hidden behind geometry, for the camera pass **and for sun shadow casters** (`kSunShadowPass`, `IsShadowCasterOccluded`). Most forest-relevant CS lever. | CS menu, live |
| HiZ `conservativeBias` | 0.025 | **0.02** | [R] CSUSER:38 | Lower = more aggressive culling, more pop risk. Slider 0-0.05. | CS menu |
| HiZ `motionMarginFrames` | 10 | **5** | [R] CSUSER:39 | Lower = more culling while moving. | CS menu |
| HiZ `shadowSweepDistance` ("Shadow Reach") | 2048 | 2048 (default) | [R] `HiZOcclusion.h:146`, `.cpp:367` (slider 0-16384) | How far along the sun direction a caster's shadow is assumed to reach before the caster can be culled. Lower = more shadow casters culled, risk of shadows popping off for off-screen trees. | CS menu |
| HiZ `guardAngle` | 10 deg | default | [R] `.h:147` | Turn guard. | CS menu |
| HiZ `consecutiveOccludedThreshold` | 1 | default | [R] `.h:145` | - | CS menu |
| HiZ per-render-mode table `cullRenderMode` | array of 30, initialised `{ true }` | not in CSUSER | [R] `.h:150`, `.cpp:39, 256-289, 555-558, 2001-2011` | **Likely only the World pass is culled.** `{ true }` sets only element 0 (render mode 0 = World) in C++; `RestoreDefaultSettings` is `settings = {}`; I found no `fill(true)`; CSUSER has no `cullRenderMode` key. Cullable modes are 0 (World, camera), 12 (Sun Shadow Mask, camera) and 14 (Sun Shadow Cascades, shadow + caster occlusion). So modes 12 and 14 are probably **off** right now [I - confirm in the CS menu table; the "Shadow Reach" slider is greyed out unless mode 14 is ticked, `.cpp:366`]. | CS menu |
| **Screen Space Shadows** `Enable` | 1 | 1 | [R] `Features\ScreenSpaceShadows.h:27-37` | Contact shadows from the sun, full-screen compute pass. | CS menu |
| SSS `SampleCount` (multiplier, x60 samples scaled by resolution) | 1 | **2** | [R] CSPACK ScreenSpaceShadows.json:7; `ScreenSpaceShadows.cpp:105` | Ray reach. Changing it recompiles the raymarch shader. | CS menu |
| SSS `FilterShadowMask` | 0 | **1** | [R] CSPACK:6 | Extra depth-aware blur of the engine shadow mask. | CS menu |
| SSS `Denoise` | 1 | 1 | [R] .h | - | CS menu |
| SSS `MaxRayLength` | 24 | 24 | [R] .h | - | CS menu |
| SSS `SurfaceThickness` | 0.01 | 0.02 | [R] CSPACK:8 | - | CS menu |
| **Volumetric Shadows** | no settings (`HasSettings() = false`), core feature | on | [R] `Features\VolumetricShadows.h` | Downsamples + blurs the sun shadow map for particles/decals. Fixed cost, scales with shadow map size. | No lever |
| **Terrain Shadows** `EnableTerrainShadow` | true | true (not overridden) | [R] `Features\TerrainShadows.h:31-34` | Heightmap terrain shadows; compute pass, not geometry-dependent. | CS menu |
| **Capsule Shadows** `Enabled` | true | **false** | [R] CSUSER:18-20 | Already off. | CS menu |
| **Light Limit Fix** `EnableContactShadows` | false | **true** | [R] CSPACK LightLimitFix.json:6 | Per-light screen-space contact shadows (`ContactShadowMaxSteps` 4, `MaxDistance` 1024 by default). Cost scales with visible point lights, so small in a forest by day [I]. | CS menu |
| LLF `EnableLocalShadows` | false | false (not overridden) | [R] `Features\LightLimitFix.h:497` | Cached local shadow slices (slots 16, updates/frame 4). Off. | CS menu, hooks installed at startup |
| **Skylighting** `OcclusionUpdateInterval` | 33 ms | 33 ms (not overridden) | [R] `Features\Skylighting.h:58`, `.cpp:92,581` | Skylighting re-renders an occlusion (top-down depth) capture of the scene at most every N ms. In a forest that capture draws many trees [I]. Slider 0-100 ms. | CS menu |
| Skylighting `OcclusionDistanceCulling` | 0 | 0 | [R] `.h:59`, `.cpp:480-482` | >0 raises the minimum occluder radius with distance, i.e. drops small distant occluders from the capture. Slider 0-1. | CS menu |
| Skylighting `MaxZenith` / `MinDiffuseVisibility` / `MinSpecularVisibility` | 1.571 / 0.1 / 0.1 | 1.222 / 0.29 / 0.2 | [R] CSPACK Skylighting.json | Look only. | CS menu |
| **Volumetric Lighting** `ExteriorQuality` | 2 | **1** | [R] CSUSER:187-190 | Froxel grid size. CSPACK also defines `ExteriorCustomSize` 288x256x130; whether quality 1 or the custom size is in use I did not verify. | CS menu |
| **Interior Sun** `InteriorShadowDistance` | 5000 | default | [R] `Features\InteriorSun.h:39` | Interiors only. | - |
| **Sky Sync** `MinShadowElevation` | unknown | 7.2 | [R] CSUSER:179 | Clamps how low the sun shadow direction goes. Lower sun = longer shadows = more casters per cascade [I]. | CS menu |
| **Cloud Shadows** | Settings struct not located by my grep | unknown | - | Cheap texture lookup [I]. | - |

No CS feature in this tree overrides `fShadowDistance`, `iShadowMapResolution` or the cascade split distances ([R] grep of SRC for those names: only `iNumSplits` and `iShadowMaskQuarter` are referenced).

---

## 2. Tree, LOD and foliage settings

### 2a. Game INI

| Lever | Current | Source | Vanilla Ultra | Visible effect | Restart? | Live? |
|---|---|---|---|---|---|---|
| `uGridsToLoad` | 5 | [R] INI:129, CUSTOM:46 | 5 | Loaded full-detail cell grid. | Yes | No |
| `uLargeRefLODGridSize` | 9 | [R] PREFS:114 | 11 (believed) | Large-reference ring. But DynDOLOD `iNearGrid=11` overrides the near grid at runtime (see 2b) [I]. | Yes [I] | No |
| `fTreeLoadDistance` [TerrainManager] | 233155 | [R] PREFS:180 (and DynDOLOD override, same value) | 75000 | Distance tree LOD is shown. **Keep** (3D tree LOD requirement). | No | `setini` / DynDOLOD MCM [I] |
| `fBlockLevel0Distance` | 100000 | [R] PREFS:176 | 35000 | LOD4 object/terrain ring. | No | `setini` + LOD refresh [I] |
| `fBlockLevel1Distance` | 180500 | [R] PREFS:177 | 70000 | LOD8 ring. | same | same |
| `fBlockMaximumDistance` | 327680 | [R] PREFS:178 | 250000 | LOD16/32 ring. | same | same |
| `fSplitDistanceMult` | 1.0 | [R] PREFS:179 | 1.5 | Terrain LOD split. Already below Ultra. | same | same |
| `fLODFadeOutMultObjects` | **30** | [R] PREFS:136 | 15 | Fade distance of full-detail objects inside loaded cells (rocks, logs, shrubs, clutter statics). | No | `setini "fLODFadeOutMultObjects:LOD"` [I] |
| `fLODFadeOutMultItems` | 10 | [R] PREFS:135 | 15 | Same for items. | No | `setini` [I] |
| `fLODFadeOutMultActors` | **30** | [R] PREFS:134 | 15 | Same for actors. | No | `setini` [I] |
| `fLODFadeOutMultSkyCell` | 1 | [R] PREFS:137 | 1 | - | - | - |
| `fTreesMidLODSwitchDist` | **10240 (PREFS) vs 9999999 (CUSTOM)** | [R] PREFS:82, CUSTOM:29 | 9999999 (believed) | Distance where full trees switch to their mid LOD. Conflict: which file wins depends on whether the engine treats it as a prefs setting. I believe PREFS wins for this key but did not verify. Check in game with `getini "fTreesMidLODSwitchDist:Display"`. | unknown | `setini` unknown |
| `fMeshLODLevel1FadeTreeDistance` / `Level2` | 6144 / 10240 | [R] PREFS:76,78 | 2844 / 2048 (believed) | Distance at which full-model trees drop mesh LOD levels. Higher than Ultra. | unknown | unknown |
| `fMeshLODLevel1FadeDist` / `Level2` | 6144 / 10240 | [R] PREFS:75,77 | 4096 / 3072 (believed) | Same for other meshes. | unknown | unknown |
| `bRenderSkinnedTrees` | 1 | [R] PREFS:183 | 1 | Skinned (animated) trees. | Yes [I] | unknown |
| `uiMaxSkinnedTreesToRender` | **120** | [R] PREFS:184 | 40 | Max trees rendered with skinned animation; the rest are static. 3x Ultra. | unknown | unknown |
| `bEnableTreeAnimations` | 1 | [R] INI:202 | 1 | Tree sway. | Yes [I] | unknown |
| `bEnableTrees` | 1 | [R] INI:203 | 1 | - | - | - |
| `fUpdateBudget` [Trees] | 1.5 | [R] INI:204 | 1.5 (believed) | ms budget for tree animation updates. | - | - |
| `fLeafAnimDampenDistStart` / `End` | 3600 / 4600 | [R] PREFS:70-71 | 3600 / 4600 | Leaf animation fade distance. | No | `setini` [I] |
| `bEnableLandFade` | 0 | [R] INI:63, CUSTOM:8 | unknown | - | - | - |
| Grass: `iMinGrassSize` 60, `iGrassCellRadius` 2, `fGrassFadeRange` 7000, `bEnableGrassFade` 0, `fGrassStartFadeDistance` **999999**, `fGrassMaxStartFadeDistance` 7000 | - | [R] INI:132-142, PREFS:118-121 | 7000 start fade | **Keep** (grass requirement). Listed for completeness. NGIO `GrassControl.ini`: `Extend-grass-distance=true`, `Overwrite-grass-distance=-10000` (= no override), `DynDOLOD-Grass-Mode=0`, `Only-load-from-cache=true`. | - | - |

### 2b. DynDOLOD runtime overrides

Two files, both read:
- Defaults: `mods\DynDOLOD - Settings Loader\MCM\Config\DynDOLOD\settings.ini` (modlist line 635, above `DynDOLOD DLL NG and Scripts 3.00` at 1933)
- User overrides (win over defaults per the header comment of the defaults file): `overwrite\MCM\Settings\DynDOLOD.ini`

| Key | Defaults file | User override | Effective [I] | Matches PREFS? |
|---|---|---|---|---|
| `fTreeLoadDistance` | 180500 | **233155** | 233155 | yes |
| `fBlockLevel0Distance` | 100000 | - | 100000 | yes |
| `fBlockLevel1Distance` | 180500 | - | 180500 | yes |
| `fBlockMaximumDistance` | 327680 | - | 327680 | yes |
| `fSplitDistanceMult` | 1.00 | - | 1.00 | yes |
| `fSkyCellRefFadeDistance` | 600000 | 186275 | 186275 | yes (PREFS [MAIN]) |
| `iNearGrid` | 11 | - | 11 | Near (full-model/large-ref style) dynamic LOD grid |
| `iFarGrid` | 21 | - | 21 | Far dynamic LOD grid |
| `bLoadSettingsonReload` | 1 | - | 1 | DynDOLOD re-applies these on every load, so a `setini` on the TerrainManager keys is overwritten at next load [I] |

All DynDOLOD keys can be changed live in the DynDOLOD MCM (the DLL applies them at runtime) [I].

### 2c. CS features touching trees/foliage

| Feature | Current | Source | Note |
|---|---|---|---|
| Tree Wind | `Enabled` default true, `MinDistance` 10000, `NearRampEnd` 40000; nothing overridden in CSUSER | [R] `Features\TreeWind.h:21-40` | Vertex-shader sway for distant/LOD trees. Memory notes say Tree Wind had a LOD rebuild cost finding (see flybench notes). |
| Grass Optimizations | `MinPixelSize` 3 (def 2), `MidLODPixelSize` 20 (def 8), `FarLODPixelSize` 8 (def 4), `MeshCostBias` 0.301 (def 0.25), `EnableOcclusionCulling` true (def), `RenderDistanceOverride` 0 (def) | [R] CSPACK GrassOptimizations.json, `Features\GrassOptimizations.h:33-55` | Already tuned more aggressively than default. Grass must be kept, so listed only. |
| Replace Original Shaders: DistantTree, Grass | both true | [R] CSUSER:149-160 | - |

---

## 3. Shortlist - HYPOTHESES TO BE MEASURED, not findings

Ranking is my reasoning about a dense forest (many alpha-tested, shadow-casting trees inside the loaded 5x5 grid, sun shadow map rendered twice for 2 cascades). None of this was measured. Grass density/distance and 3D tree LOD distances are left alone.

1. **`fShadowDistance` 10000 -> 8000 (Ultra) or 6000.** Current value is 25% above Ultra. Each cascade re-draws every caster in range with alpha test; tree count in range grows roughly with distance squared, so 10000 -> 8000 is about 36% fewer casters in the far cascade. Visual loss: far shadows end sooner (Terrain Shadows and LOD shading still cover the distance). Live via `setini`, so cheap to A/B.
2. **HiZ Occlusion: enable culling for "Sun Shadow Cascades (14)" (and "Sun Shadow Mask (12)") in the per-pass table.** From the source defaults and the saved settings, only the World pass appears to be culled today (see 1c), so shadow-caster occlusion culling - the feature built for exactly this case - is probably not running. No intended visual loss; risk is shadows popping when a culled caster's shadow should still be visible (tune "Shadow Reach", default 2048). Confirm the current state in the CS menu first. Live in CS menu.
3. **`uiMaxSkinnedTreesToRender` 120 -> 40 (Ultra).** 3x Ultra. Skinned trees cost CPU skinning and cannot be batched/instanced like static ones, in both main and shadow passes. Forest-specific by definition. Visual loss: fewer near trees animate with the vanilla skinned sway. Interaction with CS Tree Wind and Dynamic Wind Framework is unknown. Probably needs a restart.
4. **`fMeshLODLevel1FadeTreeDistance` / `Level2FadeTreeDistance` 6144 / 10240 -> lower, and resolve the `fTreesMidLODSwitchDist` conflict.** These keep full-detail tree meshes at highest mesh LOD roughly 2-5x further than Ultra. Only matters if the installed tree meshes actually contain LOD levels (unknown; many modded trees do not), so measure before caring.
5. **`fLODFadeOutMultObjects` 30 -> 15-20 (and Actors 30 -> 15).** 2x Ultra. Forest floors are full of small statics (logs, rocks, shrubs, mushrooms); each also casts into both cascades. Visual loss: small objects fade in closer. Live via `setini`.
6. **Skylighting `OcclusionUpdateInterval` 33 -> 66-100 ms and/or `OcclusionDistanceCulling` 0 -> 0.25-0.5.** The occlusion capture is an extra scene render that sees all the trees. Raising the interval amortises it; distance culling drops small distant occluders. Visual loss: slower skylight occlusion update when moving. Live in CS menu.
7. **Screen Space Shadows `SampleCount` 2 -> 1 and `FilterShadowMask` 1 -> 0.** Full-screen cost, not forest-specific, but it is a pure GPU saving if the GPU is the limit; the first step is to learn whether the forest drop is CPU (draw calls) or GPU bound - if CPU bound, skip this one. Live in CS menu (shader recompile on sample change).
8. **`fFirstSliceDistance` 2896 (try ~2000) or `iNumSplits`.** Shrinking the first slice moves casters from the high-density near cascade to the far one; effect on total cost is uncertain and near shadows get sharper while mid shadows get softer. Lowest confidence. Not recommended: `iNumSplits` 1 (large visual loss) and `iShadowMapResolution` (already 2048).

Deliberately not on the list: `bDrawLandShadows`, `bTreesReceiveShadows` (large visual loss for a forest), Capsule Shadows / local shadows (already off), Volumetric Lighting quality (already 1), TerrainManager distances and grass (must be kept).

### First thing to measure
Whether the forest is CPU/draw-call bound or GPU bound (CS Performance Overlay / existing flybench). Levers 1-5 mostly cut draw calls and vertex work; 6-7 cut GPU passes.

---

## 4. Surprises

- CS HiZ occlusion culling probably does not cover the sun shadow cascade pass (default array initialiser enables render mode 0 only; nothing saved overrides it). Inferred from source + settings file, not seen in game.
- `fShadowDistance` 10000 is above Ultra (8000) while `iShadowMapResolution` 2048 is below Ultra (4096): long but coarse shadows.
- `uiMaxSkinnedTreesToRender` = 120 (Ultra 40).
- `fLODFadeOutMultObjects` and `...Actors` = 30 (Ultra 15).
- `fTreesMidLODSwitchDist` is set to two different values (PREFS 10240, CUSTOM 9999999).
- `fGrassStartFadeDistance` = 999999 in PREFS with `bEnableGrassFade=0` (grass never fades; out of scope but notable).
- `bShadowsOnGrass`, `fShadowBiasScale`, `fShadowLODMaxStartFade` are not set anywhere.
- `skyrimprefs.ini [Launcher] sD3DDevice` still says "NVIDIA GeForce RTX 4090" (stale string; the GPU is a 5080). Harmless as far as I know.
- SSE Display Tweaks has `EnableVSync=true` and `FramerateLimit=240`; no shadow/LOD involvement.
- CS Skylighting, HiZ shadow-caster culling and SPS all hook the shadow/cull path; SPS's own shadow cache and occlusion are reported auto-off in the earlier plugin audit (not re-checked).

# Bottled Shaders update vs our fork, 2026-11-25

Read-only research. Nothing was merged, committed, built or pushed. The dry merge ran in a throwaway
worktree (`C:\Users\foxnn\dev\_bottled-merge-check`), which has been aborted and removed.

- Fork: `C:\Users\foxnn\dev\skyrim-community-shaders`, `foxnne/merge-rc2-1123` @ 309ad1d52 (`checkpoint-2026-11-25`)
- Upstream: `bottled/Bottle-Compendium` a2ebc86e6 -> **b59b66389**
- Merge bases: **two** (criss-cross): a2ebc86e6 (our last Compendium merge) and 363ac0246 (upstream dev,
  which we had already merged ourselves). The Bottle merge e9a9cf9e2 only brings dev commits we already have.
- Other bottled branches: none active. Apart from Compendium, the newest is `dclf-port` (2026-11-04); `dev` was last updated on 2026-09-26.
- Main checkout has **uncommitted** edits to `Effect.hlsl` and `HistogramAutoExposure.cpp/.h`. Commit or stash them
  before a real merge, because HistogramAutoExposure conflicts in any case.

## 1. New commits (all by InTheBottle)

| Commit | Date | Subject | Files |
|---|---|---|---|
| e9a9cf9e2 | 11-23 | Merge upstream/dev into Bottle-Compendium | dev up to 363ac0246 (already in our fork) |
| be13d93f5 | 11-23 | Update Utility.hlsl | Utility.hlsl (per-cascade shadow compare offset) |
| 840fdde27 | 11-24 | OS fixes | Lighting.hlsl (tree snow normal), Utility.hlsl, ScreenSpaceGI.cpp, ScreenSpaceShadows.cpp, SnowDeformation.cpp, Hooks.cpp, VanillaSettingsEngine.cpp, ShaderCache.cpp/.h |
| fd4e06510 | 11-24 | skin fixes | Skin.hlsli, BRDF.hlsli, Skin.h, Skin/Editor/Files.*, Workspace.cpp, Material.*, Runtime/Renderer.cpp, docs |
| 9eb9d8a73 | 11-24 | nms skin | Skin.ini (0-4-0), Skin.hlsli, SharedData.hlsli, Lighting.hlsl, Skin.h, Editor/Controls.cpp, Material.*, Parameters.def, Renderer.cpp, en.json, docs |
| 8359029f6 | 11-25 | il sat | PostProcessing.ini, ScreenSpaceGI.ini, en.json, HistogramAutoExposure.cpp/.h, ScreenSpaceGI.cpp/.h |
| cdb908e98 | 11-25 | fix(skin): remove shadow grain, add specular AA | Skin.hlsli, Lighting.hlsl, Parameters.def, docs |
| f3aa5c8c3 | 11-25 | skin light | Skin.hlsli, DeferredCompositeCS.hlsl, Deferred.cpp/.h, en.json |
| b59b66389 | 11-25 | skin shimmer fixes | SSGI composite.cs.hlsl, diffuseGI.cs.hlsl, ScreenSpaceGI.cpp, SkySync.cpp/.h |

## 2. Skin-related changes and the black-skin bug

**Key point:** nearly all of the skin shader work is behind `skinEnabled`
(`skinData.skinParams.w > 0`), which is `float(settings.EnableSkin)`. Ours is **false**, so in our
setup this code doesn't run. Our fork has no Skin changes of its own since a2ebc86e6, so all of it
merges cleanly.

| Change | What it does | Black skin? |
|---|---|---|
| `BRDF::D_Charlie` (fd4e065) | `pow(roughness,-4)` -> `rcp(max(r^2,1e-4))`. The old form gives inf and NaN as roughness approaches 0 (`pow(1,inf)`). | It's a real NaN guard, but only the Advanced Skin fuzz lobe uses it. FuzzRoughness is clamped to at least 0.1 and the path is gated off for us. **No.** |
| `PenumbraScattering` (fd4e065) | Replaces the pow/ratio form with `s + bleed*s*(1-s)`, a red bleed in the shadow edge. | The old form was already clamped and NaN-safe. Gated. **No.** |
| Convention textures (fd4e065) | Auto-picks `<base>_rfaos.dds` / `<base>_wet.dds` next to the diffuse or normal map when no layer specifies them. Adds `textureSpecified` to track an explicit "none". | Only used when the Skin feature is on. A wrong `_rfaos` could darken skin, but not make it black, and only with EnableSkin. **No.** |
| Normal-map self-shadow (9eb9d8a) | New `Skin::NormalMapShadow`: an 8-step trace of the sun across the skin normal map. New `shadowParams` (strength 0.6, length 1.5, hardness 6, contact 0.5). `SkinData` grows 112->128 bytes and `PerGeometryData` 144->160; HLSL and C++ change together. Skin contact shadows now use the geometric normal and are scaled by `ContactShadowStrength`. | Darkens grooves only. Gated. **No.** |
| Shadow grain + specular AA (cdb908e) | The trace uses the step midpoint instead of screen noise. Both roughness lobes are widened by normal variance (`FilterRoughness`). Defaults: SecondarySpecularStrength 0.15->0.1, PhysicalSecondRoughness 0.75->1.0. | Specular only. Gated. **No.** |
| Skin light (f3aa5c8) | Forward path: per-channel wrapped diffuse (RGB wrap 0.4/0.15/0.1 x SSS width). MultiBounceAO is now coloured (previously `.y` grey). Deferred composite: skin pixels (`Masks.x>0 && Masks.y<1.5`) get SSGI AO from a 3x3 depth-weighted blur. New debug views 11 "Diffuse Lighting" and 12 "SSGI AO". | The diffuse/AO part is gated. **The SSGI AO blur is not gated**: it runs on the masks, so it affects us. It smooths AO and can't make skin black. **No.** The two debug views are useful for diagnosing black skin (see below). |
| Skin shimmer (b59b663) | SSGI IL on skin pixels: 5x5 tap blur over skin-only neighbours. Skin uses half the AO power on the cubemap fallback (`SSGI_SKIN_FALLBACK_AO_SCALE`). Binds MASKS at SSGI diffuse t1. SkySync holds the sun/shadow direction unless it moves more than 0.1 deg (stops shadow crawl). | Not gated; it slightly brightens skin ambient. If SSGI AO or the fallback drove skin to black, this would only soften it. **No.** |

**Verdict: none of this explains or fixes intermittent black skin.** Our symptoms point away from the
Skin feature: the material is normal, toggling Skin, Advanced Skin or SSS has no effect, and EnableSkin is off.
They point to something per-draw or per-session: a stale or unready shader permutation, a wrong bound resource,
or tint/constant data captured at a bad time.

Two upstream changes come close to that area, but neither is a likely fix:
- **`ShaderCache::Clear(type)` -> `compilationSet.ClearType(type)` (840fdde).** Before this, clearing one
  shader type wiped the whole compile queue, including demanded tasks of other types. In our fork that happens when
  the LLF visualisation is toggled, when Dynamic Cubemaps recompile (ImageSpace) and on shader file-watcher reloads. If such a clear
  lands while Lighting skin permutations are still queued (for example, right after a load during background compile), those
  draws fall back until they are requested again. That resembles the harness note "save loaded while shaders were
  still compiling -> wrong face tint for the session". It's worth taking, but it only matters if one of those clears happens.
- **Hooks.cpp `BSShader_LoadShaders` (840fdde).** The precompile pass applied `ModifyShaderLookup` twice to the
  same descriptors (forward, then deferred on the already-modified value). It now uses separate copies. For Lighting
  the transform is almost idempotent, and it only runs in disk-cache/non-background precompile. It's unlikely to be our bug.

Diagnosis suggestion once merged: when skin goes black, use Deferred debug view 11 (Diffuse Lighting)
and 12 (SSGI AO). If albedo is fine and diffuse lighting is 0, the cause is lighting or shadow. If the albedo
target itself is 0, the cause is the material/permutation path.

## 3. Merge estimate

`git merge-tree` and a real `--no-commit` merge in a throwaway worktree both report **5 conflicting files, 1 hunk each**.
Everything else auto-merges, including Lighting.hlsl's skin blocks, Utility.hlsl, SharedData.hlsli, Skin/*,
SkySync, ShaderCache, Hooks, Deferred and the SSGI shaders.

| File | Conflict | Difficulty |
|---|---|---|
| `features/Screen Space GI/Shaders/Features/ScreenSpaceGI.ini` | Version 5-1-0 vs 5-2-0 | Trivial: take 5-2-0 |
| `src/Features/ScreenSpaceGI.cpp` (GetCommonBufferData) | Ours adds `FallbackSkyBoost`; theirs uses `settings.ILSaturation` instead of 1.0 | Easy: keep both lines |
| `src/XSEPlugin.cpp` (blocked DLLs) | Upstream blocks NativeMeshLightFlickerFix.dll, DripSim.dll and DripSimRain.dll; our fork deliberately leaves them out | Easy: **keep ours** (the modlist runs all three) |
| `package/Shaders/Lighting.hlsl` (deferred screen-space shadows) | Ours: LOD tree crown and near-tree-leaf softening. Theirs: skin `contactLightAngle`/`contactStrength` | Medium: keep both blocks, ours first, then theirs; keep their `contactLightAngle` in the SKINNED lerp and in the `>= 0` test |
| `src/Features/PostProcessing/HistogramAutoExposure.cpp` (GetExposureParameters) | Ours: day/night/interior range blend + flight +3 EV. Theirs: `InteriorBrightening` lowers the interior minimum | Medium (design): ours already has `InteriorAdaptationRange`. Keep ours and **set `InteriorBrightening` to 0 or drop it**. Otherwise it auto-merges into the .h with a **2 EV default** and adds 2 EV more interior brightening on top of our tuned interior range. Our uncommitted HistogramAutoExposure edits add to this conflict. |

Semantic checks after resolving:
- `ScreenSpaceGI.cpp` merged binding `srvs[1] = MASKS` for the diffuse GI pass. Check that our fork's extra SSGI
  passes don't use t1 in diffuseGI (they bind t1 only in other passes; it looked fine).
- `Util::TraverseCollision` (used by the SnowDeformation change) already exists in our fork (`src/Utils/ActorUtils.cpp`).
- Saved skin material JSON gains 4 parameters. Old files still load with defaults.

## 4. Other things that matter to us

- **Shadows (be13d93, 840fdde, Utility.hlsl):** the cascade 1/2 depth bias now scales from cascade 0's bias
  by projection depth scale (`min(engineOffset, ...)`), so it's never larger than the engine's. Distant cascades get tighter contact
  (less peter-panning, possibly slightly more acne). Alpha-tested shadow-map draws now sample without `MipBias`, so
  DLSS's negative bias no longer makes foliage shadows noisy. Both are good for us.
- **ScreenSpaceShadows guard (840fdde):** skips when the active shadow scene isn't the main one, or when there's no
  sun light. This avoids a null crash and stops cubemap or secondary scenes using the wrong sun.
- **SkySync 0.1 deg shadow-direction hold (b59b663):** less shadow shimmer from sub-pixel sun motion and fewer
  shadow-map changes. Good for TAA/FG stability. Check that our Sky Sync and Flybench timescale/fast-travel
  arcs still look smooth (the hold is skipped during transitions and lightning flashes).
- **SSGI:** mip count clamps to resolution (safe at tiny sizes). New user `ILSaturation` (default 1.0, no change).
  The skin IL/AO blurs add about 25+9 taps on skin pixels only, which is negligible.
- **Tree snow (840fdde):** tree snow coverage now uses the pre-view-flip normal, which fixes snow on the wrong side of
  tree cards. Auto-merged with our tree-lighting code; give it a visual check on snowy trees.
- **Terrain blending:** **not touched.** The 10-unit blend band (floating feet) still needs our own work.
- **NR, frame generation, clouds, performance core:** not touched in this update.
- **VanillaSettingsEngine.cpp (840fdde):** native-menu refactor, not reviewed in depth. It auto-merges.

## Recommendation

Merging is optional and low risk. It's 5 small conflicts, about 30 minutes of work, and it doesn't fix black skin. For now,
cherry-pick the parts that help us without the skin work: the ShaderCache `ClearType` change, the Hooks.cpp precompile
descriptor fix, the ScreenSpaceShadows guard, the Utility.hlsl shadow changes and SkySync's direction hold. Merge all of it
when convenient. When merging, keep our exposure model (InteriorBrightening = 0) and our DLL block list.
Keep chasing black skin separately, as a draw/permutation/resource problem, using the new deferred debug views.

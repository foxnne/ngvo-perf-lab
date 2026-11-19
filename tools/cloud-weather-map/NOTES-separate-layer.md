# Separate-layer local cloud mode - working notes (2026-11-18)

Worktree `C:\Users\foxnn\dev\cs-wt-locallayer`, branch `foxnne/local-cloud-separate-layer` (from foxnne/nr-pr6 f9e0f038d).
NOT tested in game; nothing was launched and the plugin was not built.
`SH` = `features\Physical Sky\Shaders\PhysicalSky`, `SRC` = `src\Features\PhysicalSky`, `V` = `SH\Volumetrics.cs.hlsl`.

## 1. Facts found before editing
- Every active local state already owns one slice in each of three atlas arrays (Height, Modeling, Maximum; all
  RGBA16F, SRC\LocalNdf.cpp CreateLocalTexture / targets[slice][map]). No new texture or slice is needed.
- `LocalNdfWeights[i]` was (endpoint weight, modelingBlend, 0, 0): z/w free.
- `localNdfAltitude` = (window bottom m, window span m, active flag 1, state count). `.z` is only ever tested
  `> 0` / `<= 0` (HLSL, CloudBoundary.hlsl, VolumetricClouds.cpp:1667), so it can carry "1 + number of Separate
  states" with no cbuffer layout change. No struct sizes or static_asserts changed.
- sampleNDF has ONE caller (sampleWeatherCloudDensity in V). View march, cubemap/reflection, shadow volume /
  columns / mean, ambient density, voxel view, lightning view all reach it through sampleCloudDensity.
- Trace range (VolumetricClouds.cpp:1122-1123), boundary mesh (CloudBoundary.hlsl), the TexCloudHeightBounds tightening
  for probes (V RenderVolumetricCloudRay), the ambient grid range (CloudAmbient.hlsli CurrentGrid) and the shadow
  volume range already include the local altitude window whenever `localNdfAltitude.y > 0`. The reflection
  empty-interval skip and the weather-bounds reduction are already disabled on rays that cross the local atlas.
- buildCloudAmbientDensity (CloudAmbient.hlsli) clamps each cell to SampleCloudHeights() = the GLOBAL slab, so it
  needed an explicit extension or a bank below the global base would get no ambient-transport density.

## 2. What was built
### Settings / C++
- `LocalNdfBlendMode::Separate = 2` (SRC\Ndf.h). JSON is the plain integer (`"modelingBlend": 2`), same macro as before.
- New state key `flatAltitude` (bool, default true, only used by Separate): heights are terrain altitudes, not
  altitudes on the curved cloud shell. Old JSON without the key loads with the default.
- SRC\LocalNdf.cpp: mode 2 is passed to the bake (`data.modelingBlend = 2`); for a Separate state the height weight is
  forced to 1 when strength*modelingWeight > 0 (Height.dds is always loaded/validated; "Height influence" is ignored and
  greyed out); `LocalNdfWeights[i]` = (endpoint weight, blend mode, flatAltitude ? 1 : 0, 0);
  `altitude.z = 1 + separateCount`; flatAltitude is part of the rebuild key.
- UI: combo entry "Separate layer" (`feature.physical_sky.local_ndf_separate`), checkbox "Terrain altitude (ignore cloud
  curvature)" (`local_ndf_flat_altitude`), hint (`local_ndf_separate_hint`). en.json only; other languages fall back
  to the inline English default.

### Bake (SH\LocalNdf.cs.hlsl)
For mode 2 the state's own slices hold:
- Height slice: unchanged code, `(normalizedBottom*w, normalizedTop*w, w, 0)` with `w = mask*alpha` (heightWeight is 1).
- Maximum slice: `(model.rgb * k, k)` with `k = mask * alpha * strength * modelingWeight`. (Mode 1 writes A = 0 there.)
- Modeling slice: stays 0.
Modes 0 and 1 produce exactly the same texels as before (the new branch is tested first, the old two are unchanged).

### March (V)
- `ApplyLocalNdfModel`, `HasLocalNdfInfluence`, `LocalNdfHeight`, `LocalNdfMotionWeight` skip endpoints with
  `LocalNdfWeights[i].y > 1.5` => the global slab (heights AND modeling) is bit-for-bit what it is without the state.
- The old `sampleNDF` body is now `sampleWeatherNDF` (unchanged). New `sampleNDF` = `sampleWeatherNDF`, then, only if
  `localNdfAltitude.z > 1.5`, `ApplyLocalNdfLayers`. Because the wrapper runs after the weather function returned,
  all its early-outs (outside the global slab, zero coverage) still reach the local check.
- `ApplyLocalNdfLayers(ndf, anchoredXY, profileAltitude)`: reject if the altitude is outside the atlas window (+ curvature)
  or XY outside the atlas; per Separate endpoint: bottom/top = `height.rg / height.b * span + window bottom` (metres ->
  game units), plus `endpoint.z * d^2/R` so a flat (terrain-altitude) slab is compared in profile-altitude space;
  skip unless bottom < altitude < top; read the Maximum slice; coverage = `rgb.r * endpointWeight`,
  types = `rgb.gb / a` (un-weighted); build an NDFInfo (height_fraction, shaping_start from the same top-type remap
  as the weather path, top_type * saturate(coverage*10), CloudNdfProfile) and keep it if the weather sample is empty
  or its `dimension_profile` is larger. No wind shear / upstream sample for the local slab.
- `IncludeLocalNdfLayerHeights` widens a column's bottom/top by the separate slabs; used by buildCloudAmbientDensity.
- `LocalNdfLayerMotionWeight` + CloudTemporal.hlsli: a pixel whose resolved mean cloud depth lies inside a separate
  slab is treated as world-anchored (same treatment as existing local clouds).

### Curvature
`CloudProfileAltitude = z + d^2/R`. With `flatAltitude` true (default) the slab test uses `z` (terrain altitude), so a
bank authored at 500 m sits at 500 m at any distance. Limit: the TRACE shell is still curved, so a flat bank is clipped
where `bankTop + d^2/R` exceeds the trace top = max(global top, local window top). With global top 2100 m and bank tops
<= 832 m that is beyond 9.7 km (the province is 7 km wide); with a thin low weather (top 1200 m) it would be 5.2 km.
Set `flatAltitude` false to get the old behaviour (bank follows the curved shell and sinks with distance).

## 3. Which passes show the separate slab
Shows it (shared density function, range already covers the window):
- main view (csVolMainWithoutStorm; csVolMainView / volcanic variants on storm tiles), voxel view NDF part
- cubemap / reflection (`CLOUD_REFLECTION` renderCubemap) - one jittered sample per stratum, so thin banks are noisy there
- cloud self-shadow light march (CloudLightOpticalDepth) - the global deck shadows the bank and vice versa
- shadow volume, shadow columns, shadow mean (renderShadowVolume / renderShadowColumns / buildCloudShadowMean)
- ambient transport density (buildCloudAmbientDensity, via IncludeLocalNdfLayerHeights)
- lightning VIEW mask (LightningView.hlsli march uses sampleCloudDensity)
- temporal reprojection treats it as stationary (approximation, see risks)
Does NOT show / is not aware of it:
- csVolMainWeather (`NO_LOCAL_NDF`): only used when no local state is active, so not a gap in practice.
- Supercell storm composition (CloudStorm.hlsli sampleSupercellWeatherDensity): inside a non-volcanic storm footprint
  the storm NDF replaces the column and the local slab is not drawn.
- Lightning SOURCE placement (findLightningSource uses SampleCloudHeights): strikes never start in a mist bank (wanted).
- Cloud boundary mesh, TexCloudHeightBounds / tiles, TexCloudWeatherBounds: built from the global field only; they
  already fall back to the whole local window inside the atlas rectangle, so nothing is clipped, but nothing is
  tightened to the banks either.
- Cloud cross-section debug view (CloudCrossSection.cs.hlsl) and the weather-map previews.
- Middle / upper (cirrus) layers: unrelated.
- The separate "Cloud Shadows" feature's own layers were not checked.

## 4. Cost
- No Separate state active: one float compare per sampleNDF, one extra compare per endpoint in the four global loops.
- Separate active: per density sample inside the atlas rectangle and the window altitudes, one Height-slice tap per
  Separate endpoint; only inside that endpoint's bottom..top one Maximum-slice tap + the profile LUT taps.
- NOT solved (inherent, NOTES.md P2.2): any local state with heights widens the trace range for every ray that crosses
  the ATLAS RECTANGLE (= the whole province for this asset) from global base..top to window bottom..global top, and the
  main pass uses the variant without the weather-bounds reduction. The window is now tight (192..832 m) but still
  below the global base, so the extra march distance is about the same as in pass 2 (+2-3 ms measured there).
  A real fix needs a conservative per-ray occupancy test for the banks (e.g. a coarse max-mip of the Maximum slice).

## 5. Verification done (no game, no plugin build)
- fxc 10.0.26100 `/T cs_5_0 /O3 /Ges`, defines COMPUTESHADER WINPC DX11 + the variant's own (as Util::CompileShader
  adds them; REVERSE_Z / feature common defines not added), include root = package\Shaders merged with all
  features\*\Shaders. All compiled without errors:
  LocalNdf.cs.hlsl main; Volumetrics.cs.hlsl main {CLOUD_AP_SHADOW, CLOUD_MAIN_DISPATCH, NO_CLOUD_STORMS} (the main
  pass while a local state is active), main {+ NO_LOCAL_NDF}, main {CLOUD_AP_SHADOW, CLOUD_MAIN_DISPATCH} (storm),
  renderCubemap {CLOUD_REFLECTION}, renderShadowVolume / renderShadowColumns / buildCloudShadowMean {NO_CLOUD_STORMS},
  buildCloudAmbientDensity, reproject, reprojectCubemap, renderVoxelView {CLOUD_AP_SHADOW, CLOUD_VOXELS,
  CLOUD_VOXEL_VIEW, NO_CLOUD_STORMS}, findLightningSource {CLOUD_VOXELS}, buildCloudHeightBounds.
  Not compiled: the volcanic / single-storm / voxel shadow+ambient+cubemap variants, upper/middle cloud entries, filters.
- MSVC 14.51 `cl /Zs` (full front end, no code generation) on SRC\LocalNdf.cpp with the include dirs / defines /
  options of the main checkout's build\PR\CommunityShaders.vcxproj (Release) and the worktree's PCH.h force-included:
  exit 0, only two pre-existing warnings. PhysicalSky.cpp / VolumetricClouds.cpp were not re-checked (they only see the
  Ndf.h change, which LocalNdf.cpp also includes).
- The main checkout's uncommitted detile diff to V (`git diff` there, read only) passes `git apply --check` on top of
  this branch (hunks at lines 154 and ~890; mine end at ~905 of the new file / 776 of the old).
- en.json parses.

## 6. Asset: `out\tamriel-mist-separate` (build_map.py `--mode mist-separate`)
- Same candidate picking as `--mode mist` (placed statics + terrain lattice scored as face base / ridge crest / saddle,
  greedy, >= 340 m apart), plus the 5-bank Throat ring at ground ~560 m and a second ring of 3 at ground ~680 m.
  48 banks: 8 Throat, 8 face, 19 ridge, 13 saddle (the face quota of 27 does not fill: few candidates pass the score).
- Modeling.dds (RGBA16 UNORM, 952x752, mips): R 0.55, G 0.70, B 0.10 CONSTANT over the map; A = the soft bank outline
  (fully feathered ellipse, irregular edge from noise). Effective coverage = R*A. No clearing zones, no collar.
- Height.dds (RG16 UNORM): one smooth field, inverse-distance mix of the per-bank bottom/top, blurred 24 m.
  Bottom 30-50 m under the 35 m-smoothed ground at the bank centre, top 120-210 m above it, capped at 900 m.
  Bottoms 200..617 m, tops 357..817 m; window altitude 192, heightSpan 640.
- Radii 205-290 x 105-130 m (1.5x the pass-2 banks). A > 0.02 on 8.8 % of the map, A > 0.5 on 2.9 %.
- Narrowest full alpha ramp 56 m => >= 2 atlas texels needs localTexelSize <= 28 m; the default 32 m is borderline,
  16 m is comfortable (atlas ~440 texels).
- Height slope inside banks: median 0.02 m/m; 1577 of 33013 texels with A > 0.3 are steeper than 1 m/m, all in the
  Throat cluster where neighbouring banks sit at 374..642 m on the flank (the slab follows the mountain side there).
- `--bank-coverage` / `--bank-type` defaults are now per mode (mist 0.6 / 0.4 as before, mist-separate 0.55 / 0.7);
  other modes are unchanged (orographic / mist / diag-* code paths untouched apart from that default resolution).
- Previews: preview\overlay_banks_on_relief.png (white = R*A, dots = class), modeling_A_bank_outline.png,
  effective_coverage_R_x_A.png, height_R_bottom.png, height_G_top.png, bank_vs_ground.png (red = top above ground,
  green = outline, blue = bottom below ground).

State JSON (one element of `cloudMap.localCloud.states`):
```json
{"value": {"altitude": 192.0, "asset": "tamriel-mist-separate", "center": [146.227, 233.964], "enabled": true,
  "feather": 0.0, "flatAltitude": true, "heightSpan": 640.0, "heightWeight": 1.0, "modelingAlpha": true,
  "modelingBlend": 2, "modelingWeight": 1.0, "rotation": 0.0, "size": [6960.415, 5498.143], "strength": 1.0,
  "worldspace": "Tamriel"}, "weight": 1.0}
```
Install: `<mod>\textures\PhysicalSky\LocalNdf\tamriel-mist-separate\{Height,Modeling}.dds`.
In this mode strength / modelingWeight below 1 really are "a fainter bank" (they only scale coverage).

## 7. Risks / unknowns
- Nothing ran on a GPU. The standalone fxc compile proves syntax and types only.
- A plugin built from an older commit ignores mode 2 (falls back to Interpolate) and would blend this asset's heights
  into the global slab = curtains again. The new shaders need the new plugin too (weights buffer z, altitude.z).
- Look of the bank is a guess: coverage 0.55 / type 0.7 through the weather's coverage exponent, erosion noise (which
  drifts with the wind while the bank stays put) and ShapeCloudBaseDensity (density is 0 at the very bottom of a slab).
  The bank may come out too thin, too solid, or mostly underground on crests.
- Where a bank and the global slab overlap in altitude the denser profile wins per sample (hard switch, no blend).
- Temporal: the stationary/moving decision uses the pixel's mean cloud depth; a bank seen in front of moving global
  cloud can smear or lag slightly.
- Cubemap: thin banks get 1 sample per stratum -> noisy reflections / probe lighting.
- Trace cost as in section 4.
- Mode 2 with `modelingAlpha` false and no Mask.dds fills the whole map rectangle with the slab (by design).

## 8. Commit
- `4d781391e` on `foxnne/local-cloud-separate-layer` (parent f9e0f038d): Ndf.h, LocalNdf.cpp, LocalNdf.cs.hlsl,
  Volumetrics.cs.hlsl, CloudAmbient.hlsli, CloudTemporal.hlsli, en.json, docs\physical-sky\local-ndf.md.
- Baseline comparison (same fxc run on the parent's shaders): warning counts per variant are identical, and the
  `NO_LOCAL_NDF` main-pass bytecode is byte-identical to the parent (the new code compiles out completely there).
  With local NDF compiled in, the main pass grows 109108 -> 115072 bytes.
- build_map.py: `--mode mist`, `diag-one-blob` and `orographic` re-run into a temp folder give byte-identical
  Height.dds / Modeling.dds / localcloud_state.json to the existing `out\` folders.

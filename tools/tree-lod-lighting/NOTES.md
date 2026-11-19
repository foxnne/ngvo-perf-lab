# Tree LOD lighting investigation (offline, read-only)

2026-11-18. Nothing launched, nothing modified under `C:\Modlists` or the fork. Scripts are in this folder; extracted/decoded
temp files are in the session scratchpad only. Labels: **[read]** = read from a file/code, **[measured]** = computed by a script
here, **[inferred]** = conclusion not read literally.

Fork paths are relative to `C:\Users\foxnn\dev\skyrim-community-shaders` (branch `foxnne/nr-pr6`). Deployed
`Lighting.hlsl`, `Utility.hlsl`, `Common/LightingEval.hlsli` in `mods\Bottled Shaders - foxnne\Shaders` are byte-identical to the fork **[measured, cmp]**.

## 1. How tree LOD is built

- **No traditional tree LOD.** `mods\NGVO - DynDOLOD Output\Meshes\terrain\Tamriel\Trees\` holds only `Tamriel.lst` (4 zero bytes); no `.btt`,
  no tree atlas. `DistantTree.hlsl` draws nothing in Tamriel. Preset `Edit Scripts\DynDOLOD\Presets\DynDOLOD_SSE_Default.ini`:
  `DoTreeLOD=0`, `UltraTreeLOD=1`, `Level32=0`, `TreeLODBrightness=0`, `ObjectLODBrightness=0` **[read]**.
- **All trees are in object LOD** (693 `.bto`, 5.4 GB), drawn by the Lighting shader. Tree rule (preset line 745):
  `tree,Level0,Billboard1,Billboard1,None,FarLOD` = 3D model at LOD4, Billboard1 at LOD8/LOD16. `DynDOLOD_SSE.ini:27 TreeFullFallBack=1`
  (billboard when a species has no 3D LOD model), `:33 TreeBillboard1=Internal` (2-plane X) **[read]**.
- Tamriel references (`export_ref_counts.py` on `Edit Scripts\Export\LODGen_SSE_Export_Tamriel.txt`) **[measured]**: 50,453 tree refs;
  **76.6 %** use a 3D hybrid `*passthru_lod.nif` at LOD4 and a billboard at LOD8/16; **23.2 %** are billboards at every level
  (e.g. aspen_dwarf*, spruce_common_low01, conifer_young_cluster03, pine_forest_big01, all elm/beech/oak/hornbeam, most alder);
  Whiterun-area box: 1776 3D-at-LOD4 vs 361 billboard. By species (`tree_report_species.py` on `Logs\DynDOLOD_SSE_Tree_Report.txt`):
  127 tree base records have a 3D LOD model (pine_common*, spruce_forest*, scots_pine*, birch*, aspen_forest*, some alder/oak), 379 do not.
- LOD4 reaches `fBlockLevel0Distance=100000` units, LOD8 to 180500 (`profiles\foxnne-nsfw\skyrimprefs.ini:176-177`) **[read]**. So the
  conifers in the plains frame are almost certainly LOD4 3D crowns, not billboards **[inferred]**.
- What is actually in the `.bto` files (`bto_shapes.py`, all Tamriel blocks aggregated) **[measured]**:

| Class | Level | Verts | Shader flags (SLSF2) | SLSF1 | Vertex colour | Normals | Textures |
|---|---|---|---|---|---|---|---|
| A. 3D crowns | LOD4 | 136.6 M | Double_Sided, Vertex_Colors | none (no Cast/Receive_Shadows) | 0.788 flat | mesh (bent, 12 % point down) | atlas `DynDOLOD_Tamriel_Alpha` + `_n` |
| A'. 3D trunks | LOD4 | 2.5 M | Vertex_Colors | none | 0.788 | mesh | `DynDOLOD_Tamriel` |
| B. flat trunk cards of hybrids | LOD4 | 0.6 M | Vertex_Colors | none | 0.549 | card | atlas alpha |
| C. X billboards | LOD4 (23 % species) 94 k, LOD8 403 k, LOD16 403 k | | Double_Sided, Soft_Lighting, Rim_Lighting, Vertex_Colors; LE1=2.0 LE2=1.0 | none | 0.40-0.55, mean 0.473 | all (0,0,1) + normal map | atlas alpha, `_n`, slot 3 = the atlas diffuse again |

  None carry LOD_Objects, HD_LOD_Objects or Tree_Anim, and the `.bto` has no NiAlphaProperty blocks. Shape name is `passthru`
  (not `treepassthru`).
- Source LOD model (`Nature of the Wild Lands.bsa`, `meshes\dyndolod\lod\trees\pine_common_big03_summer_9545d40fpassthru_lod.nif`) **[measured]**:
  crown = Double_Sided + Tree_Anim + Vertex_Colors, **no Soft_Lighting, no third texture**, LE1=1, vc 0.788; 4 `DoNothing FlatTrunk` cards, vc 0.549.
  Full model `meshes\landscape\trees\pine_common_big03_summer.nif` leaves = Double_Sided + Tree_Anim + **Soft_Lighting (LE1=5.0)** + Specular +
  Cast/Receive_Shadows, slot 3 `pine02_sk.dds`, vc 0.788, normals 70 % horizontal and none pointing down.
- DynDOLOD ini lighting values **[read]** `Edit Scripts\DynDOLOD\DynDOLOD_SSE.ini`: `CrownBrightness=1`, `TrunkBrightness=1`, `FlatTrunkBrightness=1` (:15-17),
  `FlatLODLightingEffect=0.0` (:61), `FlatLODGlowMap=textures\white.dds` (:64), `FlatLODVertexColor=0.55` (:68),
  `FlatLODWithNormalMapVertexColor=0.50` (:72), `FlatLODColorVariance=0.1` (:75), `FlatLODLevelLODFlag=0` (:83), `TreeLODComplexAtlas=0` (:93).
  Note the files show LE1=2.0 and slot 3 = atlas on billboards, not the ini's 0.0 / white.dds; why is not determined.
- TexGen (`Presets\DynDOLOD_SSE_TexGen.ini`) **[read]**: `TreeBillboards Direct=135 Ambient=55`, `TreeHDBillboards Direct=135 Ambient=55 Glow=100 Back=100`,
  `RenderBillboards (3D trunk cards) Direct=50 Ambient=150`, top-down light (`DirectTB=-100`), `BillboardPBRScale=0.7`.
  Normal-map billboards exist: 1400 `_n.dds` of 3309 dds under `mods\NGVO - TexGen Output\textures\terrain\lodgen`; HD `_1/_2` + `_n` are what the atlas uses.
  (`TexGen_SSE.INI:34 TreeNormalMaps=0` only concerns standard tree LOD.) `TexGen_SSE_log.txt` does not print the light values.

## 2. Measured gap in the frames (`measure_frames.py`, display-linear Rec.709 Y, hand-picked boxes; crops in `crops\`)

Plains noon (`01_mist_removed_height_fog_on__h12.png`; note the weather in `log.json` is `CloudyPF`):

| Region | sRGB mean | Y | Y / nearby sunlit ground |
|---|---|---|---|
| Distant conifer mass, centre | 77 79 82 | 0.078 | 0.48 (ground 0.164) |
| Distant conifers, right slope | 92 95 98 | 0.114 | 0.55 (ground 0.206) |
| Near pines, foreground | 82 83 79 | 0.089 | 0.71 (ground 0.124) |

Distant trees sit at about half the luminance of the ground at the same distance, near trees at about 0.7; distant masses are neutral
blue-grey (no green), near pines are olive. Haze adds light to both distant values, so the underlying ratio is lower than 0.48 **[inferred]**.
Ilinalta: far forest band Y 0.094 (h9.5) / 0.109 (h14) vs near full-model conifer 0.074 / 0.078 and sunlit grass 0.125 / 0.147:
there the far band is not darker by number (haze lifts it); the deficit is flatness/hue, not mean luminance. Not separable from haze offline.

## 3. How the fork shades each class (file:line)

No LOD/tree define applies: flags above give the plain Lighting technique with `VC` (+ `SOFT_LIGHTING`/`RIM_LIGHTING` for class C).
The code itself says so: `package/Shaders/Lighting.hlsl:2621` "should only match object lod trees (ultra trees), they have no special define".
Full-model NotWL trees are `TREE_ANIM`, and with PGLite (runtime PBR patcher, active; `mods\Nature of the Wild Lands - PBR\PBRNifPatcher\nature_of_the_wild_lands\pine\pine02_summer.json`
has `"subsurface": true`) they are `TRUE_PBR` foliage **[inferred: PGLite log does not list meshes]**.

| Light term | Full-model tree (TREE_ANIM + TRUE_PBR subsurface) | LOD4 crown (class A) | Billboard (class C) |
|---|---|---|---|
| Sun colour chain | `Lighting.hlsl:2845-2870` | same | same |
| Direct diffuse | thin-surface foliage: `PBRMath.hlsli:43-52` (TREE_ANIM + Subsurface = foliage), wrap on both faces `PBRMath.hlsli:166-170`, back transmission `Lighting.hlsl:3025-3026`, `PBR.hlsli:355-362` | plain `saturate(NdotL)` only, `Common/LightingEval.hlsli:176-179`; no soft/rim/back term because the flags are absent (`:183-190`) | Lambert on an up normal + soft/rim terms, but their colour is the leaf texture decoded to linear (`Lighting.hlsl:2011`, `:2378`), about 0.05, so they add almost nothing |
| Shadowing of the sun | softened: `GetFoliageShadowVisibility` `Lighting.hlsl:2996-3000`, `PBRMath.hlsli:212-215` (never below 1 - thickness); thin-surface SSS variant `:2914-2918` | full-strength screen-space shadow `Lighting.hlsl:2922-2927` (bend SSS has no distance fade parameter, `src/Features/ScreenSpaceShadows.h:29-36`); no cascades beyond `fShadowDistance=10000` | same as A |
| Normal | face-oriented thin-surface normal `Lighting.hlsl:1167-1168`, `PBRMath.hlsli:121-133` | stored vertex normal; the double-sided back-face flip only runs within ~5000 units (`Lighting.hlsl:1146-1157`, `nearFactor` `:1143`) so far back faces keep the front normal | (0,0,1) from the mesh + normal map |
| Sky ambient / IBL | `Lighting.hlsl:3369`, `:3427` plus ambient transmitted through both faces `:3530-3551` | same DALC + sky SH call, single-sided, using the stored normal | same, normal up |
| Vertex colour | PBR: normalised/AO path `Lighting.hlsl:2284-2295` (0.788 -> x0.58 at `VertexAOStrength` 1.0 default) | `SRGBToWorking(0.788)` = x0.58, `Lighting.hlsl:3401`, `:3557` | `SRGBToWorking(0.47)` = x0.19 |
| LOD Blending brightness/gamma | n/a | not applied: only under `LODOBJECTS/LODOBJECTSHD`, `Lighting.hlsl:1728-1730` | not applied |
| Cloud / terrain shadows, SSGI, skylighting | `GetWorldShadow` `Lighting.hlsl:2869-2870` | same (not a difference) | same |
| Albedo texture | `textures\pbr\...\pine02_summer.dds` | atlas copy of the non-PBR `textures\nature_of_the_wild_lands\pine\pine02_summer.dds` at 256 px | TexGen render of the non-PBR textures |

Places where LOD trees get less light or a worse normal:
1. **No foliage light model on LOD crowns** (largest, [read]): Lambert only, versus two-sided wrap + transmission on full models. Any crown side
   not facing the sun gets zero direct light. Even without PBR the full model has Soft_Lighting LE1=5 (`Lighting.hlsl:685-693`) and the LOD crown nif does not.
2. **Darker albedo** ([measured], `tex_stats.py`, opaque texels, linear Y): PBR leaf albedo 0.095, non-PBR leaf 0.043, atlas leaf tile 0.049, billboard 0.054;
   bark PBR 0.126 vs non-PBR 0.061. Atlas/billboard textures are faithful copies of the non-PBR source (ratio 1.1-1.2), so TexGen/atlas did not darken them;
   the LOD was simply built from textures about half as bright as what the loaded trees use. After Linear Lighting's diffuse curve
   (`Common/ColorManagement.hlsli:161-169`, `src/Features/LinearLighting.cpp:228-230`) the LOD/loaded albedo ratio is about 0.58 **[computed, inferred]**.
3. **Unsoftened screen-space shadows** on dense LOD card masses ([read] code, magnitude unknown offline).
4. **Back faces of far double-sided cards keep the front normal**, and LOD crown normals include 12 % downward ones (full model 0 %) ([read]/[measured]); affects both sun and sky ambient.
5. **Billboards**: vertex colour 0.47 (x0.19 linear) and soft/rim light that collapses in linear space; by DynDOLOD design they rely on the up normal. Relevant beyond 100 k units and for the 23 % billboard-only species.
6. Snow Cover's LOD-tree detection (`src/Features/SnowCover.cpp:33-51`) expects `treepassthru`/`obj*` names; these crowns are named `passthru`, so that path does not see them ([read], side note).

## 4. Windswept and Tree Wind

- **Windswept mod (ticked, modlist.txt line 515)**: live files are only `SKSE\Plugins\K747_LodWind.ini` (`bEnabled=0`) plus readme/licences. The DLL is
  `K747_LodWind.dll.disabled-20261108` and its shaders are in `Shaders.disabled-20261108\`, so neither loads; `Documents\My Games\Skyrim Special Edition\SKSE\K747_LodWind.log`
  was last written 2026-11-08 22:12. It contributes nothing at runtime **[read]**. Risk if its files were ever renamed back: it sits above
  `Bottled Shaders - foxnne` (line 607), so its CS 1.9.1 `Lighting.hlsl`/`Utility.hlsl` would replace the fork's, and Tree Wind stands down when the DLL is loaded
  (`src/Features/TreeWind.cpp:233-241`). Safe to untick. Its own description also says full 3D LOD models stay still under Windswept.
- **Fork Tree Wind**: vertex-shader only. `TREE_WIND` adds an XY position offset in `Lighting.hlsl:172-175, 218-223, 246-247` and `Utility.hlsl:102-107,142`
  (and `DistantTree.hlsl`, unused here); C++ binds VS cbuffer b3 and SRV t120 per draw (`src/Features/TreeWind.cpp:340-364`) and classifies shapes by reading flags
  (`src/Features/TreeWind/TreeShapes.cpp:285-321`). It does not touch normals, the pixel shader, material flags or the deferred/forward choice **[read]**.
  Its classifier confirms the build: "Tree-mod crowns: two-sided without rim or soft lighting ... only in the LOD4 ring" (`TreeShapes.cpp:315-318`).

## 5. Not determined offline

- Whether PGLite really converts the NotWL tree shapes to PBR at runtime, and that it leaves `.bto` shapes alone (RenderDoc or the PGLite menu would show it).
- That LOD draws take the `DEFERRED` permutation (`src/ShaderCache.cpp:193-195`) like loaded statics; assumed.
- Actual strength of screen-space shadows / SSGI AO on LOD tree masses; how much of the measured gap is haze.
- How alpha test is enabled for `.bto` shapes without NiAlphaProperty; why billboards have LE1=2.0 with the ini at 0.0.
- Only one species (pine_common_big03_summer) had textures and nifs decoded; other species assumed similar.
- Decoding: texconv (`tools\DynDOLOD\Edit Scripts\Texconvx64.exe`) decoded everything tried, including BC7 and the 8192 atlas. BSA read with `bsa_extract.py` (pure-Python LZ4).

## 6. Fixes, ranked (benefit vs effort/risk)

### (a) Shader side
1. **LOD-tree foliage lighting flag** (high benefit, ~1 day, low risk). Add `ExtraShaderDescriptors::LODTree` (`src/State.h:~440`), set it per draw where
   Tree Wind already knows the answer (`TreeWind::BeginDraw`, `src/Features/TreeWind.cpp:243-250`, kind == Crown) or by fixing `IsObjectLODTree` to accept `passthru`.
   In `Common/LightingEval.hlsli:176-179` (non-PBR branch of `EvaluateLighting`), when the flag is set replace `saturate(NdotL)` with the thin-surface pair already in
   `PBRMath.hlsli:166-170`: front `saturate((NdotL + w) / (1+w)^2)` plus back `saturate((w - NdotL) / (1+w)^2) * transmissionTint * softShadow`, w about 0.5.
   Test: Tree Wind page debug toggle or a new checkbox; compare a pine at the loaded/LOD4 boundary and the plains frame at h12 and h17.
2. **Soften screen-space shadow for LOD trees** (medium, 1 hour): at `Lighting.hlsl:2926-2927` use `lerp(1, screenSpaceShadows.x, 0.3)` or `PBR::GetFoliageShadowVisibility` when the flag is set.
   Test first with setting C1.
3. **Rounded/up-biased normal for LOD crowns** (medium, 1 hour): before lighting (`Lighting.hlsl` after `:2236`) `worldNormal = normalize(worldNormal + float3(0,0,k))`, k 0.5-1,
   and use `0.5 * (ambient(n) + ambient(-n))` at `:3427`. Same trick Snow Cover uses at `:2667`.
4. **Brightness matching knob** (medium, 30 min, purely cosmetic): under the flag multiply `baseColor` at `Lighting.hlsl:1728-1730` by a `LODTreeBrightness` setting
   (about 1.7 matches the PBR albedo), or extend `LODObjectBrightness/Gamma` to flagged draws.

### (b) Regeneration (LOD is due anyway)
1. **`CrownBrightness=1.27`** (`DynDOLOD_SSE.ini:15`; raises crown vertex colour 0.788 -> 1.0 = x1.71 linear, which is almost exactly the measured albedo deficit) and `TrunkBrightness` likewise. Zero code, low risk. Test: regenerate, compare same frames.
2. **Billboards**: `FlatLODWithNormalMapVertexColor` 0.50 -> 0.65-0.70 (x1.8-2.1 linear) (`:72`), `FlatTrunkBrightness` up (`:17`), and/or TexGen `TreeHDBillboardsAmbient` 55 -> 90-100.
   Needed for the 23 % billboard-only species and everything past 100 k units.
3. **Give NotWL LOD crowns foliage flags**: the 3D crown shapes pass flags through; adding Soft_Lighting + a light slot-3 texture to the `*passthru_lod.nif` crowns would enable
   `LightingEval.hlsli:183-184`. Low value under Linear Lighting unless the texture is near white (soft colour is decoded to linear). Higher effort (127 nifs in a BSA).
4. More species with 3D LOD models (or `Level32`) do not address brightness.

### (c) Settings only
1. Toggle **Screen Space Shadows** off in the CS menu and compare distant conifers: confirms cause 3.
2. Toggle **SSGI** (or AOPower 2.0 -> 1.0): isolates AO on LOD masses.
3. Open the **PGLite** menu / disable PGLite for one launch: if loaded trees drop toward LOD brightness, cause 2 and the PBR foliage model are confirmed.
4. LOD Blending `LODObjectBrightness` will not affect trees (cause table); moving it and seeing no change on trees confirms the classification.
5. Untick Windswept (no runtime effect today; removes the risk in section 4).
`tll` in the console hides LOD and shows exactly which trees are LOD in a frame.

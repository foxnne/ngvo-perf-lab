# LOD tree lighting patch notes

Worktree: C:\Usersoxnn\dev\cs-wt-lodtree, branch foxnne/lod-tree-lighting (from foxnne/nr-pr6 f9e0f038d). Started 2026-11-18.

## Design (decided after reading the code)
- Per-draw flag: new bit `State::ExtraShaderDescriptors::LODTreeCrown = 1 << 24` / `Permutation::ExtraFlags::LODTreeCrown`
  (PerShader cbuffer b4, same path as SnowLODTree; no new shader permutations).
- Set in `TreeWind::BeginDraw` (Lighting SetupGeometry hook only), cleared in `EndDraw`. Condition: setting on, Classify == Crown,
  and shape name is passthru / treepassthru / objpassthru (optional -LargeRef). Now runs even when sway is off or the map is open.
- Settings owned by Tree Wind (short name `TreeWind`), JSON keys LODTreeLighting, LODTreeWrap, LODTreeTransmission,
  LODTreeShadowSoftening, LODTreeNormalUpBias, LODTreeBrightness.
- To the pixel shader through the shared FeatureData cbuffer (b6): new 32-byte `LODTreeLightingSettings lodTreeLightingSettings`
  appended last (FeatureBuffer.cpp + SharedData.hlsli). Tree Wind's own cbuffer is VS-only (b3) so it was not usable.
- TreeWind.ini version NOT bumped (a bump makes the DLL reject an un-updated deployed ini and would switch Tree Wind off).
- SnowCover::IsObjectLODTree left alone (changing it would switch on snow tint for these crowns = visual change outside this task).

## Result (commit 60bc46ce3 on foxnne/lod-tree-lighting)
Files: src/State.h, src/Features/TreeWind.{h,cpp}, src/Features/TreeWind/TreeShapes.{h,cpp}, src/FeatureBuffer.cpp,
package/Shaders/Common/{Permutation,SharedData,LightingEval}.hlsli, package/Shaders/Lighting.hlsl, Translations/en.json.

Shader (all under `LOD_TREE_LIGHTING` = PSHADER && TREE_WIND && VC && !TRUE_PBR && !TREE_ANIM && !LOD && !LODLANDSCAPE &&
!LANDSCAPE && !SKINNED && !SKIN && !EYE && !HAIR, and at runtime only when the LODTreeCrown bit is set):
- Lighting.hlsl: brightness multiply after the LOD_BLENDING block; normal up-bias before vertexNormal/screenSpaceNormal
  (so the G-buffer normal is raised too); screen-space shadow lerp toward 1; two-sided DALC and two-sided GetDiffuseIBL.
- LightingEval.hlsli EvaluateLighting (non-PBR branch): PBR::GetThinSurfaceDiffuseCosines(NdotL, Wrap); diffuse =
  cos.x * light * detailedShadow + cos.y * Transmission * light * softShadow. Applies to every light, not just the sun.
- Skylighting left as is: GetSkylightingDiffuse already clamps the normal's z to >= 0.
- WORLD_MAP defines LOD, so the map is not affected.

Settings (Tree Wind, short name TreeWind): LODTreeLighting=true, LODTreeLightBillboards=true, LODTreeWrap=0.5,
LODTreeTransmission=0.5, LODTreeShadowSoftening=0.7, LODTreeNormalUpBias=0.3, LODTreeBrightness=1.7.
The two bools only decide whether the flag is set (C++); the five floats are in FeatureData.lodTreeLightingSettings
(offset 3312, size 32 in the compiled shader reflection).

Checked offline:
- fxc 10.0.26100 ps_5_0 /O3 /Ges, merged package+features shader tree, base vs patched, 20 Lighting PS permutations + 1 VS:
  all compile, same warnings as base. Bytecode identical to base for no-TREE_WIND, PBR, TREE_ANIM (non-PBR), SKINNED,
  LODOBJECTS, LANDSCAPE, no-VC, HAIR, VS. PBR+TREE_ANIM differs by 3 instructions (fxc moves one `1 - x`; caused by the
  new unused constant in Permutation.hlsli alone, same arithmetic).
- cl /Zs (VS 18, flags from build/PR/CommunityShaders.vcxproj Release, PCH.h force-included): TreeWind.cpp, TreeShapes.cpp,
  FeatureBuffer.cpp, State.cpp, SnowCover.cpp pass. No link, no full build, nothing run in game.
- Shape names read from 3 .bto files: crowns and billboards are BSSubIndexTriShape 'passthru'.

Not done / open:
- TreeWind.ini version not bumped; SnowCover::IsObjectLODTree unchanged; yaml shader-validation config not regenerated.
- Billboards (two-sided + soft/rim) are flagged too by default; LODTreeLightBillboards=false limits it to tree-mod crowns.
- Crown detection for NotWL needs TreeModSupport on (Classify) and world scale < 6 (LOD4 only).
- With SSGI ReplaceAmbient on, ambient comes from the composite and the two-sided ambient here does nothing.
- Without Linear Lighting the 1.7 multiplier is applied in gamma space and will be stronger.

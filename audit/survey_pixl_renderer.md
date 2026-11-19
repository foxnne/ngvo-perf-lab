# Survey: PIXL Renderer (pixlmusic/PIXL-Renderer) vs our Community Shaders fork

Status: COMPLETE (survey date 2026-11-18). Read-only; nothing built, nothing run in game.

- Clone: `C:\Users\foxnn\dev\_survey\pixl-renderer` (blobless clone, 962 MB on disk, no local changes; safe to delete)
- PIXL HEAD surveyed: `50805342` (2026-11-17, "Fix hair cache and improve local shadow discovery"), branch `main`
- Our fork: `C:\Users\foxnn\dev\skyrim-community-shaders`, branch `foxnne/nr-pr6`, HEAD `753ce4ae` (read in place, not modified)
- Paths below are relative to the PIXL clone unless prefixed with OURS.
- Evidence labels: unlabelled = read in code; **(inferred)** = from names, comments or commit messages only.
- No GPU timings exist anywhere in this report. Cost hints are sample counts and resolutions read from code.

## Bottom line

PIXL is still a Community Shaders fork (forked 2026-08-05, roughly v1.8.3), renamed wholesale and extended by one author in large "release checkpoint" commits. Our fork is ahead of it in almost every priority area: physical sky, clouds, froxel fog, tone mapping, neural rendering, grass/Hi-Z culling, engine fixes, shader cache and profiler.

The one substantial thing PIXL has that we lack is **native DLSS Frame Generation (2x/3x/4x) with Reflex and PCL markers on a DX12 sidecar**. Everything else worth taking is small shader-level hardening (fog and skin), plus two tooling ideas.

PIXL has **nothing** for our dense-forest problem: no shadow cascade throttling, no caster culling, no tree/LOD draw-call work, no render-thread offloading.

## Top 10 worth porting

| # | Item | Source | Effort | Expected benefit |
|---|---|---|---|---|
| 1 | Native DLSS-G (multi-frame) on a second Streamline DX12 instance, with Reflex + PCL markers and input-completion fence | `engine/Modules/ImageReconstruction/DX12SwapChain.cpp`, `Streamline.cpp`, `docs/ImageReconstruction/DLSSG_SM86_INTEGRATION.md`; commit `c60814cc` (2026-09-09) | M-L | We only have FSR3 FG. On the 5080 this gives native DLSS-G up to 4x and NR-before-FG ordering in one command list. Upstream calls it "candidate, not release-certified". |
| 2 | Froxel fog temporal hardening: extinction-delta history rejection, history radiance clamp, conservative-depth interval rejection | `pipeline/Atmosphere/Kernels/Atmosphere/VolumetricFogLightScatteringCS.hlsl`; `fd3b6055` | S | Less shaft smear and ghosting around trees on camera motion. About 30 lines. |
| 3 | Skin transmission and curvature fixes (world-footprint curvature, authored thickness, back-light gate, dual-lobe IBL) | `pipeline/SkinOptics/Kernels/SkinOptics/SkinOptics.hlsli` | S-M | Less waxy faces; fits a neutral baseline. |
| 4 | SSS robustness (firefly clamp, normal/depth agreement weights, NaN guards, optional frame-stable rotation) | `pipeline/Tissue Diffusion/Kernels/TissueDiffusion/Burley.hlsli` | S | Less facial crawl under DLSS/NR. |
| 5 | Auto-exposure EV deadband, asymmetric stops-per-second slew limit, median anchoring | `pipeline/Camera Suite/Kernels/CameraSuite/PhysicalCameraExposureCS.hlsl`; `427cf4ca` | S | Less exposure pumping. Idea only; our pipeline is otherwise ahead. |
| 6 | Scene-table benchmark: per-scene coc/time/weather, per-pass avg/p95/p99, fixed marker captures | `engine/Renderer/WorldBenchmark.cpp` (`kScenes[20]`, schema `PIXL.WorldBenchmark.Sample.v2`) | S-M | Matches our reference-shot-set plan. Best re-implemented as a route type over RemoteControl, not ported in-DLL. |
| 7 | Camera spline path model and evaluator | `engine/Director/DirectorCameraPath.{h,cpp}` (899 lines, no game deps), `tools/TestDirectorCameraPath.cpp` | S (model), M (drive from RemoteControl) | Deterministic fly-throughs for flybench instead of held keys. |
| 8 | Vanilla volumetric-lighting fixes: proper HG phase; temporal weight = depth x motion x radiance confidence; sky never takes history | `distribution/PIXL-Shaders/ISVolumetricLightingGenerateCS.hlsl`, `ISApplyVolumetricLighting.hlsl`; `fd3b6055` | S | Drop-in, only relevant where vanilla VL still runs alongside our froxel fog. |
| 9 | Eye cornea F0 (IOR 1.376) and footprint-driven roughness; pupil warp optional | `distribution/PIXL-Shaders/EyeRendering/EyeRendering.hlsli` | S | Small close-up gain; we have no eye path. Pupil warp assumes vanilla eye UVs. |
| 10 | Once-per-froxel shading on history miss (hoist shadow/sky/local lights out of the miss-sample loop) | same fog shader as #2 | S-M | Cheaper disocclusion frames in fog. |

Runner-up ideas, lower value: expanded caustics (`WaterCaustics.hlsli`, M); world-anchored grass gust field with previous-frame evaluation for exact motion vectors (`FoliageWind.hlsli`, `WorldWind.hlsli`, M); bent-normal specular occlusion output from SSGI (we have none); WARP-based offline shader test harness pattern (`tools/Test*GPU.cpp`, `cmake/PIXLTests.cmake`); grass frustum guard band and 2-frame Hi-Z suppression on camera change (`FoliageOptimizer.cpp:300`, `:393-420`).

Watch, do not port: the world irradiance cache in HybridGI (upstream's own README says its flicker is unresolved).

---

## 1. What PIXL is today

**Architecture.** A fork structure, not a rewrite. `src/` became `engine/`, features became "modules" (`engine/Modules/`), shaders moved to `pipeline/<Module>/Kernels/` and `distribution/PIXL-Shaders/`. `ATTRIBUTION.md` states core loading, D3D hooks, shader cache, settings, weather, menu and engine fixes "remain derived from or byte-identical to Community Shaders v1.8.3", and gives a full rename table (TruePBR -> MaterialForge, Screen-Space GI -> HybridGI, Upscaling -> ImageReconstruction, HDR Display -> CameraSuite, Light Limit Fix -> RadiantGrid, and so on). Feature short names, register assignments and cbuffer layouts are deliberately kept stable (`docs/PIXL-RENDERER-ARCHITECTURE.md`).

Added on top: a shared-services layer in `engine/Renderer/` (`RenderPassScheduler`, `GPUResourceServices`, `GPUWorkloadBudgeter`, `QualityProfiles`, `TemporalContext`, `VolumetricContext`, `ReflectionContext`, `VisibilityContext`, `RenderOrigin`, `WorldBenchmark`). Most of it is bookkeeping (see 2c).

Removed relative to upstream: Effects11, CS Editor, Remote Control and RenderDoc integrations are "not active PIXL rendering modules" (`ATTRIBUTION.md`).

**Common ancestor.**
- PIXL's first own commit is `c5ce2a0c` (2026-08-25, "PIXL Renderer v1.0 private development checkpoint"). Its parent is upstream `dcea14b6` (2026-08-05, "fix(build): delete stale feature folders from dist (#2609)").
- `ATTRIBUTION.md` names the baseline as v1.8.3, commit `2f2919a7` (release commit dated 2026-08-07 in our repo).
- Our repo is a shallow clone on upstream's dev line, so hashes do not match and `git merge-base` returns nothing. The same change (#2609) is `6866e3c74` in our history; we are 2448 commits past it (439 first-parent).
- PIXL since the fork point: 134 commits, all by `pixlmusic`, `1389 files changed, 213150 insertions(+), 111997 deletions(-)`.
- Shared layout survives under renames; file-level diffing needs the rename table. Several upstream features newer than v1.8.3 were back-ported by PIXL by hand (grass optimizations from "Community Shaders 1.9.1", LOD blend ring fix from "PR #2894"), so some PIXL files are older copies of ours.

**Activity.** Commits per month since the fork: Aug 32 (PIXL portion), Sep 86, Oct 29, Nov 8. Commits are large squashed checkpoints, so hashes identify releases, not individual changes.

**Last two months by theme (2026-09-18 to 2026-11-17).**
- Release engineering dominates: 1.0.2 -> 1.0.3 -> 1.0.4 -> 1.0.5 -> 1.0.6 -> 1.0.7 -> 1.0.8 -> 1.0.9 (`cb3f123a`, 2026-10-30) -> 1.1.0 (`5e43047c`, 2026-11-15), plus FOMOD, package manifests, provenance/licence audits and portable CI fixes.
- Ground Response (snow/mud terrain deformation): `198ca93d`..`0134a79d` (2026-09-24).
- Director / Photo / Video capture tooling: `3dee8bec`, `10c489a1`, `3721c891` (2026-09-25).
- "Shared renderer architecture phases 1-6": `3f9ce5c7` (2026-10-03).
- Camera exposure and motion blur stabilisation: `427cf4ca` (2026-10-07); Auto-DOF: `25ec782c`.
- Volumetric clouds first appear in `f315e06a` (2026-10-12).
- HybridGI world cache updates: `d9ce5a5d`, `cb3f123a`.
- Preset library: `56bc56bd` (2026-10-30).
- Hair fixes after 1.1.0, Strand Shading disabled in release defaults: `f698d558`, `92b65ebc`, `14cb8946`, `50805342` (2026-11-16/17).

**Release state.** README announces 1.1.0.0, targeting Steam SE 1.6.1170, with a shipped precompiled shader cache (3,741 stages). The only git tag is `v1.0.9.0`. README carries a live-test note that irradiance-cache flicker "is under investigation". GitHub Releases and Nexus pages were not checked.

**Licence.** `COPYING` is GPL v3; README and `ATTRIBUTION.md` say GPL-3.0-or-later with the retained CS Modding Exception and Linking Exception (`EXCEPTIONS.md`). Compatible with our GPL-3 fork. Two caveats:
- `pipeline/Camera Suite/Kernels/CameraSuite/Looks/PROVENANCE.md` says redistribution terms for six LUTs are unconfirmed. Do not copy the Looks LUTs.
- Bundled NVIDIA Streamline/NGX binaries carry their own licences.

**Quality signal.** Docs repeatedly state that validation is static (build + regex/WARP tests) and that in-game validation is pending. Many features are default-off, "Beta", "Unreleased" or "Retired". Treat defaults as untuned and claims as unverified until tested on our side.

---

## 2. Findings per priority

### a. Frame generation and frame pacing

**PIXL has real work we lack.**

- **DLSS-G backend.** Selector `ImageReconstruction.frameGenerationBackend` (FSR3 or DLSSG), fixed at swap-chain creation. DLSS-G uses a three-buffer native D3D12 swap chain upgraded by a *second* Streamline instance (DX12) while the DX11 Streamline instance keeps doing DLSS SR. Files: `engine/Modules/ImageReconstruction/DX12SwapChain.cpp` (968 lines; ours is 560), `Streamline.cpp` (`ConfigureDLSSG`, `TagDX12Resources`, `EnsureFrameToken`, `CheckFrameConstants`, `SetD3DDevice12`, `EmitPCLMarker`), runtime DLLs in `pipeline/ImageReconstruction/Kernels/ImageReconstruction/StreamlineDX12/` (Streamline 2.10.3: `sl.dlss_g.dll`, `nvngx_dlssg.dll`, `sl.reflex.dll`, `sl.pcl.dll`).
- **Multi-frame.** `ConfigureDLSSG` sets `numFramesToGenerate` from `settings.dlssgGeneratedFrames`, clamped to 1..3 and to the SDK-reported `numFramesToGenerateMax` (so 2x/3x/4x).
- **Guides.** Tags depth, motion vectors and a separate UI colour+alpha buffer (`kBufferTypeUIColorAndAlpha`) with `eValidUntilPresent`; FG keeps its own raw pre-upscale guide pair, separate from the NR guide pair.
- **Sync.** After `Present`, it reads `slDLSSGGetState` and waits on `inputsProcessingCompletionFence` before signalling the shared fence that releases the next D3D11 frame (`DX12SwapChain.cpp` ~588-600). Failed tags disable interpolation for that frame.
- **Latency markers.** PCL markers on the DX12 instance around present: `eSimulationEnd`, `eRenderSubmitStart`, `eRenderSubmitEnd`, `ePresentStart`, `ePresentEnd`; `eSimulationStart` in `Streamline.cpp:934`. DX11 Reflex is suppressed while DLSS-G is active so two instances do not pace the same frame.
- **Reflex controls.** `reflexLowLatencyMode`, `reflexLowLatencyBoost`, `reflexUseMarkersToOptimize`, `reflexUseFPSLimit`, `reflexFPSLimit` (`ImageReconstruction.h:106-110`); DLSS-G forces Reflex on while generating. The Reflex cap is in rendered FPS.
- **30-series proxy.** The "SM86" part is an optional third-party `version.dll` proxy (`sdli1995/dlssg_for_sm86`, not examined) for RTX 30 cards. UI text in `ImageReconstruction.cpp:2341` says 40-series or newer uses native DLSS-G without it, so it should not matter for a 5080 **(inferred from UI strings; not tested)**.
- **Frame limiter.** `ImageReconstruction::FrameLimiter()` (`ImageReconstruction.cpp:1872`) waits on the frame-latency waitable object, then sleeps to a user FPS target (`frameLimitFPS`, 20-360). It halves the target when FG is on regardless of multiplier, which looks wrong for 3x/4x, and uses "last frame + interval" pacing. OURS (`src/Features/Upscaling.cpp:1327`) already has a fixed-cadence limiter with catch-up and a bounded wait, which is better. Nothing to take.
- **Interaction with final-image stages.** Order is DLSS SR -> NR (Feature 18) -> copy to real swap chain -> frame generation -> present, all in the sidecar's command list. UI is kept in a separate wrapped buffer and passed as a hint. PIXL's HDR path is excluded when NR is on (SDR only).
- **Anti-Lag:** nothing found.

**Ours today:** `src/Features/Upscaling/Streamline.h` has Reflex and PCL on the DX11 instance and FSR3 FG via `FidelityFX.cpp`; no `DLSSG` symbol anywhere in `src`.

**Maturity:** doc header says "candidate integration, not release-certified"; tested by the author on an RTX 3060 Ti; long-session, latency and wider hardware validation open. `tools/SidecarSmoke.cpp` is a standalone dual-instance init/present smoke test.

**Port difficulty:** moderate to large. Our `DX12SwapChain`/`Streamline` classes share ancestry with theirs, so the diff is readable, but our NR backend (`OURS src/Features/NeuralRendering/D3D12Interop.cpp`) has its own DX12 interop that must coexist with the sidecar. A Streamline version mismatch between the two instances was the cause of their startup crash; all five DLLs must match.

### b. Neural rendering / final-image ML stage

**PIXL has it; ours is more developed.**

- `engine/Modules/ImageReconstruction/NeuralRendering.{h,cpp}` (579 + 110 lines) drives NGX Feature 18 (`kFeatureDLSSNR`) on the sidecar's D3D12 command list. Runtime allowlist is 310.8.x and exactly 310.9.16. It patches the loaded module's `GetModuleFileNameW` import slot for the duration of vendor calls, and latches faults for the session.
- Placement is fixed: post-DLSS display-resolution colour, render-resolution depth/motion guides, before FG. A pre-DLSS placement is explicitly rejected in `docs/ImageReconstruction/DLSS_NEURAL_RENDERING.md`.
- Guides come from `pipeline/ImageReconstruction/Kernels/ImageReconstruction/EncodeTexturesCS.hlsl`: linear-depth silhouette velocity dilation restricted to geometry samples, one-pixel disocclusion coverage expansion.
- Double-buffered NR output textures alternate with the back-buffer index so D3D11 can read the last completed result while D3D12 writes the next.
- "Photo Finish" (`engine/Modules/PixelCapture.cpp`, `docs/ImageReconstruction/PHOTO_FINISH_OFFLINE_NEURAL_PIPELINE.md`): collects 8/16/24/32 fresh jittered NR frames with locked camera and resolves a Native/2x/4x still with outlier rejection, never re-feeding model output.
- Cost: one model evaluation plus guide copies; no measurements. The doc says cost and quality "remain runtime-test items".
- Gates: SDR only, mutually exclusive with `renodx-dlss.addon64`, 310.9.16 "not yet validated in-game".

**Ours:** `OURS src/Features/NeuralRendering.cpp` (2371 lines) plus `NeuralRendering/Backend.cpp` (1539), `Runtime.cpp`, `D3D12Interop.cpp`, with multiple placements (`Placement::kFinishedImage` default), colour domains, material categories and presets. A comparison of NGX parameter-name strings shows PIXL sets a few extent/scale names we do not (`DLSSNR.InputWidth/Height`, `DLSSNR.OutputWidth/Height`, `DLSSNR.Output.Width/Height`, `DLSSNR.Scale`, `DLSSNR.ScalingRatio`, `DLSSNR.Upscaling`, `PerfQualityValue`); whether they matter is untested.

**Worth taking:** the NR -> FG ordering comes for free with item 1. The multi-frame neural still is a nice-to-have (L, tied to their capture/Director code). Other ML post stages: none found.

### c. Dense-forest performance

**Nothing to port. Ours is a superset.**

- **Engine fixes.** `engine/EngineFixes/ShadowmapCascadeCullingFix`, `ShadowmapCascadeRasterizerFix`, `LODBlendRingFix`, `EffectShaderNoDecalsFix` all exist in `OURS src/EngineFixes/` with identical headers and the same relocation IDs (`101499/108496`, `101495/108489`, `527641/414593`). PIXL only adds defensive guards. Ours additionally has `CullPoolExhaustionFix`, `LightListSearchFix`, `SunShadowMaskFix`, `SunOcclusionPollFix`, `EmptyOverlayCullFix`, `AlphaGeometryGroupCeilingFix`, `WaterReflectionCubemapFix`.
- **Shadow cascade throttling / caster culling / shadow distance:** nothing found.
- **Foliage Optimizer.** `engine/Modules/FoliageOptimizer/*` states "Derived from Community Shaders 1.9.1 Grass Optimizations". `pipeline/Foliage Optimizer/Module.ini` has `Pipeline = Retired`, `Beta = True`; disabled by default since 1.0.6. Our `src/Features/GrassOptimizations/*` is newer and larger. Two small PIXL-only deltas: `FrustumGuardBand` (128 units) and Hi-Z disabled for 2 frames on cull-camera change (`cameraTransitionFrames`). Whether ours handles the camera-change case differently was not checked.
- **Hi-Z.** `HiZPyramid.{h,cpp}` is the same SPD pyramid as `OURS src/HiZPyramid.*`. PIXL has no equivalent of our `src/Features/HiZOcclusion.cpp`.
- **Renderer services.** `RenderPassScheduler` (421 lines) orders passes by declared reads/writes inside three existing hook points and records CPU ms; it has no interval/skip/amortisation logic. `VisibilityContext` (67 lines) wraps one Hi-Z pyramid. `GPUResourceServices` is a transient pool used almost only by `DistantLife`.
- **`GPUWorkloadBudgeter`** is the one real mechanism: a hysteretic 4-level scaler (0.50/0.67/0.84/1.0, 120-frame hold) triggered when a domain exceeds 28% of target frame time. Off by default, labelled experimental, and consumed only by `Atmosphere.cpp:516` (froxel grid) and `HybridGI.cpp:2638` (slices/steps). It does not touch CPU-bound cost.
- **Trees / LOD / instancing.** "Future: PIXL Distant World" in `docs/PIXL-RENDERER-ARCHITECTURE.md` is a 7-step plan for GPU-driven instanced distant geometry that says itself it "is not enabled"; no code matches it. `DistantLife` is distant lights, default off.
- **Render-thread offloading:** only the shader cache, screenshots, `Waterbody/WaterCache` and one `std::async` in OceanDynamics.

### d. Sky and clouds

**Nothing to port. Ours is ahead on every axis.**

- **Physical sky / sun disc / aerial perspective / twilight colour:** none. No Rayleigh/ozone/transmittance-LUT code anywhere. Sky is vanilla `Sky.hlsl` plus a grade. Twilight handling is `AtmosphereWeather::DirectionalFogScale` (`engine/Modules/AtmosphereWeather.h`), a smoothstep that scales directional fog inscatter down to 0.05 at night.
- **Volumetric clouds** exist: `engine/Modules/VolumetricClouds.{h,cpp}` (1311 lines) and one shader, `pipeline/VolumetricClouds/Kernels/VolumetricClouds/VolumetricCloudsCS.hlsl` (1147 lines; `WeatherMapCS`, `RaymarchCS`, `TemporalCS`, `CompositeCS`). First seen `f315e06a` (2026-10-12), about five weeks old, enabled by default.
  - Noise: fully procedural hashed value noise (`Noise3Periodic`, 3-octave FBM + warp + detail erosion), no baked textures; tiling via integer periods with CPU double-precision wind phase.
  - Weather map: 512x512 RGBA16F, world-anchored, refreshed every 0.20 s.
  - Cost: default quality = half resolution, 80 primary steps, 5 light steps, with procedural density re-evaluated per light step. Four compute passes.
  - Lighting: dual HG blended toward isotropic, powder term, 3-order multi-scatter loop, SH DC ambient only.
  - Temporal: world-space reprojection with per-deck wind displacement, previous-ray-distance depth validation, 3x3 clamp, coverage rejection, foreground/sky mixed-pixel cap.
  - Cloud shadows: no shadow volume or map. `CompositeCS` multiplies finished scene colour by the weather-map alpha (capped 38%); the comment admits it cannot separate direct from ambient.
  - Per-weather: `BuildWeatherProfile` reads `TESWeather::cloudAlpha` per layer plus a per-class preset table (`GetCloudWeatherPreset`).
  - Tests: `tools/TestVolumetricContext.ps1` regex-matches source only.
- **Ours** (`OURS src/Features/PhysicalSky*`, `features/Physical Sky/Shaders/PhysicalSky/`) has baked noise, a real 3D cloud shadow volume, multi-scatter LUT, cirrus/mid layers and storms.
- Possibly useful cloud temporal tricks (coverage-envelope rejection, mixed-pixel history cap, `PreviousRayDistance` validation) only if our `CloudTemporal.hlsli` lacks them; that file was not opened.

### e. Volumetric lighting, god rays, fog

**Small shader fixes worth taking (items 2, 8, 10).**

- **God rays (`LightVolumes`)** are stock CS Volumetric Lighting with two fixes in `fd3b6055`: proper HG phase in `ISVolumetricLightingGenerateCS.hlsl` (ours at `OURS package/Shaders/ISVolumetricLightingGenerateCS.hlsl:94` still uses the vanilla form) and depth x motion x radiance temporal confidence with sky exclusion in `ISApplyVolumetricLighting.hlsl` (ours, line 61, is depth-only).
- **Shafts through volumetric clouds:** none. Fog and vanilla VL see only cascades, terrain occlusion and the SkyVeil cubemap. Ours already feeds PhysicalSky cloud shadows and transmittance into fog (`VolumetricFogLighting.hlsli`).
- **Shafts through trees:** plain cascade shadow sampling, nothing special.
- **Froxel fog (`Atmosphere`)** is upstream's Exponential Height Fog volumetric path, hardened. `engine/Modules/Atmosphere.{h,cpp}`, `pipeline/Atmosphere/Kernels/Atmosphere/VolumetricFog{Material,ConservativeDepth,LightScattering,Integration}CS.hlsl`.
  - Grid: 24 px froxels, 64 exponential slices, RGBA16F, single grid (ours has near + far in RGBA32F).
  - PIXL-only additions: `historyAlpha *= exp2(-8*extinctionDelta)`; conservative-depth interval rejection (`volumetricHistoryDepthRejection=16`, needs min/max depth); `volumetricHistoryRadianceClamp=2.5`; shadow/sky/local lights evaluated once per froxel with only sun phase supersampled on a history miss; `PIXLPhaseFunction` (dual HG with isotropic share) and `PIXLMultipleScatteringCompensation` in `VolumetricFogCommon.hlsli`; thin-fog series expansion in `HomogeneousScatteringWeight`; depth-aware 2x2 bilateral apply (`AccumulateDepthAwareVolumeSample` in `Atmosphere.hlsli`).
  - Ours rescales history by extinction ratio and has no radiance clamp. Whether our `ViewAtmosphere` composite already has a depth-aware upsample was not checked.
- **Ground/height fog:** same analytic exponential fog as upstream.
- **`VolumetricContext`** (88 lines) only publishes froxel SRVs. The single fog-to-cloud coupling is `SampleIntegratedCloudFog` in the cloud composite.
- **1.0.9 changelog items located** (`fd3b6055`, `cb3f123a`): cloud direct light `* lerp(0.16, 1, sunVisibility)`; fog phase `lerp(1/4pi, directional, 0.72)`; fog history fallback 0.82 -> 0.65. The cloud history cap was tightened to 0.84 in 1.0.9 and is back at 0.96 at HEAD (deliberate walk-back is **inferred**).
- **Weather mapping:** `Atmosphere::ResolveRuntimeSettings` adapts density, range and phase g by weather class from live `sky->fogNear/fogFar` and reduces history weight mid-transition. `engine/WeatherManager.cpp::ClassifyWeather` classifies by flags plus name tokens.
- **Microclimates** (`engine/Modules/Microclimates.*`): a 384x384 advected 2D humidity/fog/precipitation field; default off, labelled experimental. Prototype.

### f. Tone mapping and colour pipeline

**Nothing principled to take; ours is well ahead.**

- `engine/Modules/CameraSuite.cpp` (2822 lines) with one output compute pass, `pipeline/Camera Suite/Kernels/CameraSuite/HDROutputCS.hlsl` (948 lines): motion blur, DOF composite, exposure, tonemap, LUT, UI composite, sRGB or BT.2020 PQ. Keeps the CS 1.8.3 HDR Display design. `enableHDR` defaults false.
- **Tonemap:** one custom luminance operator `CameraMapLuminance` (rational shoulder normalised at 0.18, toe, shadow lift, contrast). No ACES/AgX/OpenDRT, no gamut mapping. In SDR it is lerped with the vanilla ISHDR image by `cameraInfluence`, so not scene-referred end to end.
- **Auto exposure:** `PhysicalCameraHistogramCS.hlsl` (256-bin log2 histogram over +-12 stops) and `PhysicalCameraExposureCS.hlsl` (2%/98% trimmed log mean blended 42% toward median, key 0.22, highlight protection from the 95th percentile capped at 0.55 stops, 0.06 EV deadband, slew -0.65/+1.25 stops/s). Not EV100-calibrated; "physical" is naming.
- **Local exposure:** `PhysicalCameraLocalExposureCS.hlsl`, quarter-res sparse log-luminance bilateral, gain clamped +-0.5 EV. The 1.1.0 ghosting fix was to drop the temporal history of the gain field.
- **Looks:** 32-cubed strip LUTs after the tonemap, display-referred. Licence unconfirmed for six of them.
- **Auto-DOF** (`DOFCoCCS`, `DOFFocusResolveCS`, `DOFTileClassifyCS`, `DOFBlurCS`; `docs/PIXL_AUTO_DOF.md`) and inline camera-only motion blur (default off).
- **ENB translator / ReShade:** `engine/Renderer/ExternalPostProcessing.cpp` maps a few `enbseries.ini` scalars into camera settings and registers as a ReShade add-on for preset switching only. Our Effects11 route is stronger.
- **Ours** (`OURS src/Features/PostProcessing/*`) has OpenDRT/GT7/RenoDX tonemappers, EV100-calibrated histogram exposure, bilateral-grid local exposure, LookGrade and LUT stages.
- **Liftable ideas:** the EV deadband + asymmetric slew + median anchor (our `CS_Average` in `HistogramAutoExposure/histogram.cs.hlsl` is a plain lerp), and skipping re-exposure in main/loading menus.

### g. Skin, SSS, hair, eyes

**Several small, worthwhile shader deltas (items 3, 4, 9).**

- **SkinOptics** (`pipeline/SkinOptics/Kernels/SkinOptics/SkinOptics.hlsli`, 353 lines vs our `Skin.hlsli` 270): `CalculateCurvature(N, worldPosition)` normalised by world footprint; `SSSSTransmittance` using the FaceGen soft-light map for thickness with a back-light gate instead of a constant floor; curvature-broadened lobe roughness; dual-lobe IBL with `GGXMultiScatterCompensation`; grazing-weighted peach fuzz; transmission visibility `min(detailedShadow, softShadow)`. Enabled by default.
- **TissueDiffusion** (`Burley.hlsli`, `SeparableSSS.hlsli`) is the same code as our SubsurfaceScattering, plus `USE_PIXL_STABLE_SSS`, normal/depth agreement weights, `min(sampleWeight, 16)` firefly clamp and NaN guards. Ours is structurally newer (profile array, working-gamut MFP, stratified R1 sampling).
- **Eyes** (`distribution/PIXL-Shaders/EyeRendering/EyeRendering.hlsli`, 194 lines): cornea F0 from IOR 1.376, UV-footprint roughness (0.072 near, 0.150 far), `WarpPupilUV` light-driven iris remap with no temporal adaptation. Ours has no eye path.
- **StrandShading** (`pipeline/Strand Shading/Kernels/Hair/Hair.hlsli`, 420 vs ours 301): same Kajiya-Kay/Marschner base plus tangent fallbacks, pigment-tinted R lobe, a d'Eon-style multiple-scatter term. Disabled in release defaults on 2026-11-16 (`f698d558`) with fixes still landing the next day. Uncertain value.
- **HairReconstruction:** `Module.ini` says "Retired ABI Stub". No documented reason. Skip.
- **ThinSurface:** our ExtendedTranslucency plus Beer-Lambert path length. Trivial.
- **FurShells:** 344 lines vs ours 1010. Nothing.
- `docs/DIRECTIONAL_SSS.md` is about sun/moon screen-space shadows, not subsurface scattering.

### h. Screen-space effects

**Watch the world cache; otherwise nothing better than ours.**

- **HybridGI screen-space part:** active kernel `gi106.cs.hlsl` (compile list `HybridGI.cpp:2385-2398`), same XeGTAO/visibility-bitmask lineage as our `diffuseGI.cs.hlsl`. Full resolution only (`ResolutionMode = 0`), 4 slices x 8 steps. In-house denoiser (`radianceDisocc.cs.hlsl`, `MaxAccumFrames 24`, plus `blur.cs.hlsl`). Outputs include a bent normal with specular occlusion; ours has no bent-normal output.
- **World irradiance cache** (new vs ours): `worldCache.hlsli`, `worldCacheInject/Decay/Mark/Evidence.cs.hlsl`. Two toroidal 32-cubed cascades in a 1024x64 atlas, L2 luminance SH in three RGBA16F textures plus chroma, fed from on-screen G-buffer radiance at a fixed 30 Hz with an 8 Hz ageing clock (`engine/Modules/HybridGI/TemporalPolicy.cpp`), optional emitter injection, read back via short traces (`SampleWorldCache`) as off-screen fallback and second bounce. `CacheBudget.h` throttles injection toward a 0.15 ms target.
  - Maturity: on by default in 1.1.0 but the README flags unresolved flicker; `docs/SSGI_LIVE_TEST.md` shows it toggled off and on within November with no in-game validation claims.
  - Port: large, tied to their temporal and metadata ABI.
- **Scene voxelizer** (`SceneVoxelizer.*`): dormant; `sceneVoxelDimension = 0` with a comment citing a 2026-11-04 crash.
- **Reflections:** `hybridReflection.cs.hlsl` (672 lines), GGX VNDF + min/max Hi-Z trace with world-cache fallback on miss. Ours already has Hi-Z SSR.
- **ContactShadows:** same Bend port as our ScreenSpaceShadows with reversed-Z handling, `IgnoreEdgePixels = false`, distance falloff. Ours adds denoise and mask-filter passes.
- **Local-light screen-space shadows:** `RadiantGrid::GetScreenSpaceLocalShadow` (10 depth taps, up to 4 lights per pixel). Our Light Limit Fix already has contact shadows (`OURS features/Light Limit Fix/Shaders/LightLimitFix/LightLimitFix.hlsli`); not compared in detail.
- **Ours** is cheaper (half-res default) and has the better denoiser (NRD ReBLUR).

### i. Stutter and hitch avoidance

**Nothing to port.**

- `engine/ShaderCache.cpp` (4112 lines) carries the same upstream scheduler we have (`ComputePriority`, hardest-first, background threads = P-cores/2, below-normal priority). Ours additionally has the demand queue and admission budget.
- `engine/ShaderCache/CompilationArtifact.h` (584 lines): SHA-256 content key, an include-revalidating fast index, in-flight request coalescing and a preprocess-failure latch. `OURS src/ShaderDDC.*` is already a content-addressed cache; how the two key includes was not compared. The coalescing and failure latch are the only PIXL-only ideas (M effort, small benefit unless we see duplicate or repeated failing compiles).
- "Precompiled pipeline library" is the renamed disk cache shipped in the FOMOD, with selective invalidation per changed module (`ValidateDiskCache()`, `ShaderCache.cpp:2583`). Irrelevant for a single-machine private fork.
- Texture streaming / residency: nothing. `engine/PipelineHealth.*` is our `FeatureIssues.*` renamed.

### j. Wind, snow, wetness, water

**A few ideas, mostly not worth the coupling.**

- **Grass wind:** `FoliageWind.hlsli` / `WorldWind.hlsli` define a world-anchored advected gust field evaluated at current and previous wind time for exact motion vectors, used by `RunGrass.hlsl`.
- **Tree wind:** `GetTreeShiftVector` in `distribution/PIXL-Shaders/Lighting.hlsl` adds trunk/branch/leaf frequencies, but `USE_PIXL_MULTI_FREQUENCY_TREE_WIND` is defined 0 and never enabled. Untested upstream. PIXL has no equivalent of our TreeWind.
- **GroundResponse** (`engine/Modules/GroundResponse.cpp`, 8818 lines; `TerrainSurface.hlsl`, 1867 lines): tessellated snow/mud deformation with a 1024x1024 field, mud gated by wetness, spell/projectile stamps, weather accumulation. `ForceLegacyTerrainSurface = true` by default, i.e. the newer path is not trusted. We already have tessellated SnowDeformation; only mud and stamps are new and they are bound to PIXL's classifier.
- **ActorSurfaceEffects:** analytical per-actor snow/mud/wetness lobes, depends on GroundResponse contacts. We have no equivalent.
- **RainResponse:** our WetnessEffects plus rain clumping/gust layers, rain mist, and a four-pass screen-space roof-runoff system (`RoofRunoffDetect/Generate/Resolve/CompositeCS`). Cosmetic and screen-space fragile.
- **WaterOptics:** `WaterCaustics.hlsli` is 396 lines vs our 78: dispersion, Beer-Lambert extinction, reflected caustics on nearby walls, local-light caustics. Shader-only, M effort.
- **OceanDynamics:** four 128x128 FFT cascades, hull tessellation, shoaling/breakers/spray. `Module.ini` says `Beta = true, Unreleased = true`, disabled at boot. Deeply coupled to their `Water.hlsl`.
- **Snow cover:** nothing beyond the above.

### k. Tooling

**Two ideas worth taking (items 6, 7); the rest we already have.**

- **`engine/Renderer/WorldBenchmark.*`** (913 lines): compile-time `kScenes[20]` table `{label, coc, fallbackCoc, hour, weather formID, condition, features, CameraRig}`; a state machine that runs `coc`, sets time and weather, settles 8 s, then flies 12 s of free camera on 5-keyframe rigs; captures at markers 0.20/0.55/0.88; writes per-scene JSON with frame ms avg/p50/p95/p99 and per-pass avg/p95/p99, plus a settings snapshot. Scene-relative only, no cell-crossing flights, so it complements rather than replaces our flybench.
- **`engine/Director/DirectorCameraPath.*`** (899 lines): up to 512 points with position, orientation/look-at/follow-tangent, FOV, speed, hold, easing, roll; arc-length parameterisation; allocation-free evaluation; JSON schema v2; `RunDeterministicSelfTest`. The editor UI lives in the 9802-line `engine/Menu/TuningWorkspaceRenderer.cpp` and is not portable. We have no camera-path code.
- **`engine/Modules/PixelCapture.*`** (3612 lines): base is our ScreenshotFeature (ours also has AVIF). PIXL-only "Photo Finish" multi-frame jittered supersampled stills.
- **PulseProfiler + ABTesting** = our PerformanceOverlay renamed. `engine/Profiler.*`: ours is ahead. `engine/FrameAnnotations.cpp`: same file.
- **Presets:** `engine/Presets/RenderPresetLibrary.*` (`.pixlpreset.json` overlays). We have `src/Presets/*`.
- **`QualityProfiles.*`** (526 lines): four tiers across seven groups writing live settings. We have no cross-feature tier system, but it is tied to their module settings and of little use on one machine.
- **GPU unit tests** (`tools/Test*GPU.cpp`, `tools/HybridGIGPUTestSupport.h`, `cmake/PIXLTests.cmake`): standalone exes on a WARP device that `D3DCompile` the shipped HLSL, fill cbuffers via reflection, dispatch and assert on readback; some string-patch a "legacy control" variant to prove the test catches the old bug. We use the same pattern once (`OURS tools/test-neural-temporal.cpp`).
- **`tools/CompareLiveShaders.ps1`:** SHA-256 diff of the deployed shader tree vs the repo. Useful against MO2 drift, trivial to rewrite.
- No remote automation bridge comparable to our RemoteControl / DevBenchBridge; no in-game editor comparable to CS Editor (both removed from PIXL).

---

## 3. Other notable things we do not have

- **WindowLife** (`engine/Modules/WindowLife.cpp`, 1379 lines; `pipeline/WindowLife/`): interior-mapped windows with room atlases and occupants. Realism gain for towns at night; PIXL-specific and sizeable. Not examined in depth.
- **ContainedLiquids** (potion liquid rendering) and **DistantLife** (distant settlement lights, default off). Cosmetic. Not examined in depth.
- **RenderOrigin** (`engine/Renderer/RenderOrigin.*`, `docs/PIXL_RENDER_ORIGIN.md`, 270 lines): camera-relative origin work. Not examined.
- **ReactiveFX** (`engine/Modules/ReactiveFX.cpp`, 1987 lines, `docs/PIXL_REACTIVE_FX.md`). Not examined.
- **Native Seasons integration** (`engine/SeasonIntegration.*`, `docs/SEASONS_COMPATIBILITY.md`). Not examined.

None of these bears on our stated priorities; listed for completeness.

---

## Looked and found nothing

- Shadow cascade update throttling, caster culling, shadow distance work.
- Tree or LOD draw-call reduction, static instancing, GPU-driven distant geometry (plan only).
- Real multi-frame pass amortisation.
- Moving render work off the render thread; texture streaming or residency.
- Physical sky, atmosphere LUTs, sun disc, twilight colour, aerial perspective.
- Cloud shadow volumes or maps; light shafts through volumetric clouds; baked cloud noise.
- ACES/AgX/OpenDRT, scene-referred grading, EV100 calibration.
- AMD Anti-Lag.
- ML post stages other than DLSS SR / NR / FG.
- A working tree-wind implementation (compiled out).
- An active scene voxelizer (disabled after a crash).
- Remote control / automation bridge; in-game editor.
- Engine fixes beyond ours; compile-policy features beyond ours.

## Uncertainty and gaps

- No part of PIXL was built or run; maturity judgements come from code defaults, Module.ini flags and PIXL's own docs.
- Sections c through k rest on three delegated code-reading passes; a few claims were spot-checked (LLF contact shadows present in ours, no bent-normal in our SSGI, `GetScreenSpaceLocalShadow` location), most were not independently re-verified.
- Per-change commit attribution is coarse because PIXL commits are squashed checkpoints.
- Common ancestor is established by matching PR #2609 across two different hash lines (PIXL `dcea14b6`, ours `6866e3c74`), because our repo is shallow; a true `git merge-base` could not be computed.
- "5080 does not need the SM86 proxy" is inferred from PIXL UI strings.
- Not opened on our side: `CloudTemporal.hlsli`, the `ViewAtmosphere` composite, how our grass culling handles camera changes, how `ShaderDDC` keys includes, details of our LLF contact shadows.
- Not examined on PIXL's side: `VolumeOcclusion`, `SkyContinuity`, `SkyBounce` internals, `TemporalContext`, `LightTransportWorld`, ReactiveFX, ContainedLiquids, WindowLife, DistantLife, RenderOrigin, SeasonIntegration, `tools/TestHybridReflectionHiZ.cpp`.
- GitHub Releases / Nexus state not checked (only the git tag `v1.0.9.0` and README).

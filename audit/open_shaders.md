# open-shaders audit: perf/memory items we could port

Date: 2026-11-17. Read-only audit, nothing built or run.

- open-shaders: `alandtse/open-shaders`, branch `dev`, tip `5eb8662e` (2026-11-17, release 2.22.1).
  Cloned blobless/no-checkout to `C:\Users\foxnn\dev\ngvo-perf-lab\ref\open-shaders`.
- Ours: `C:\Users\foxnn\dev\skyrim-community-shaders`, `foxnne/on-bottled-20261116`, tip `c4dcdf297`.
  It already has an `openshaders` remote fetched at the same tip, so all comparisons below were done
  with read-only `git log/show/grep/diff` between `HEAD` and `openshaders/dev`.

## Divergence (verified)

- Ours contains upstream CS `dev` up to `038a0a04c` (2026-11-15, grass batching #3162); only 5 upstream commits missing.
- open-shaders last merged upstream on 2026-11-07 (`1343e16dc`), so it does NOT have #3162. On grass we are ahead.
- `git merge-base HEAD openshaders/dev` = `95e1f69d3` (2026-11-10) but that is misleading: open-shaders carries
  its own non-shared history. `rev-list` counts: 2097 ours-only, 4182 theirs-only.
- By commit subject (PR number stripped), about 2570 of 3954 open-shaders non-merge commits have no match in ours;
  about 1090 of those are dated 2026-05 or later (open-shaders' own PRs, numbered #24..#1171).
- Tree diff `HEAD..openshaders/dev` over src + shaders: 1348 files, +150k/-102k lines.
- Hot files all differ heavily: ShaderCache.cpp (+2761/-704), State.cpp (+1705/-787), LightLimitFix.cpp (+1461/-1639),
  Streamline.cpp (+786/-201), DX12SwapChain.cpp (+488/-58), ScreenSpaceGI.cpp (+793/-731), Skylighting.cpp (+536/-382).
- Conclusion: `git cherry-pick` will rarely apply cleanly. Small single-file commits can be hand-ported; large ones
  (DLSS-G, shadow manager) are re-implementation guided by their diff.
- Bottled/ours already hand-ported several open-shaders items: NR (a84b8aa13, 2026-11-02), NR crop, FSR4 runtime,
  Anti-Lag 2, active shader key cache (#1014), Tracy zone name formatting (#1013), LLF cluster batch, reverse-Z, NvPerf, A/B testing.
- Ours has things open-shaders lacks: TreeWind, HiZOcclusion feature, SSR feature file, NRD, PhysicalSky, VramTracker, SSGI HalfRes flag.

## Candidates, ranked

### 1. NR "Model Every Nth Frame" frame reuse  (#1108, a22e2b4e9, 2026-11-11)
- Files: `src/Features/Upscaling/NeuralRendering/Cadence.h`, `Tuning.h`, `EyeMode.h`, `NeuralRendering.cpp`, tests `test_nr_cadence.cpp`.
- Runs the NR model once per N frames (1-4) on flat, reprojects its tone gain to in-between frames; forces a model run
  when camera turns >1 degree or moves >12 units.
- Their measurement (commit message): NR evaluate 3.66 ms -> 2.18 ms at N=2 -> 1.65 ms at N=3.
- Ours: NOT present (no `interval` in our Cadence.h/Tuning.h; our Cadence.h differs by 45 lines). Our NR port predates it.
- Related NR commits also missing in ours: #1089 keep history when crop moves (0f15bc277), #935 bilinear taps for reused gain
  (34ac74792 - check), #1067 capability/memory report (165e9cf4c), #993 reuse interop D3D11 objects (5ede64eb7 - check).
- Benefit (inference): our NR costs ~9.5 ms; if the same ratio holds, N=2 saves roughly 3-4 ms, N=3 about 5 ms. Largest single GPU win found.
  Unknown: interaction with our final-image placement / replace composite fork switches (73e53137b) and with FSR frame generation.
- Effort: small-medium. Mostly NR-local; our NeuralRendering.cpp differs by +295/-169.

### 2. DLSS-G frame generation + Dynamic MFG  (#445 0deec7f21, #864 30d150fba, #747 bf52e305a, #832 d62f8a8c9, #1102 20ea52057, #1110 2bd02571d, #1111 5846ac17a)
- Files: `Upscaling.cpp/.h`, `Upscaling/Streamline.cpp/.h`, `Upscaling/DX12SwapChain.cpp/.h`, `DLSSGDynamic.h`, `DLSSGInputFence.h`,
  `DLSSGPreset.h`, `Utils/NvApiDrs.h`, Streamline DLLs (sl.dlss_g, sl.reflex, sl.pcl, nvngx_dlssg), `tools/dlssg-repro`.
- Streamline submodule: theirs `625db07d`, ours `2122257e` (different pins).
- #1110: waits on DLSS-G `inputsProcessingCompletionFence` (100 ms cap) before overwriting shared depth/MV; fixes judder with NR + DLSS-G.
- #902 (74af89ecd): bounded frame-fence wait in DX12SwapChain (ours calls `SetEventOnCompletion(value, nullptr)`, an unbounded block).
- Ours: no DLSS-G. Bottled added it 2026-10-05 (`3f11431d3`) and removed it 2026-10-09 (`5969d9c4d`, -1269 lines) - reason not recorded in the subject.
- Benefit (inference): does not raise real fps; MFG 3x/4x or Dynamic MFG would give more presented frames from 31-50 real fps on the 5080,
  and Reflex/PCL pacing. Costs VRAM (we are near the limit).
- Effort: large. Touches swap chain proxy, Streamline init, present path. Start by reading why Bottled removed it.

### 3. Draw annotations only while a capture tool is attached + cheaper per-draw events  (#842 295b0f1a8, #301 b6fd0db48, #1017 3dd18b979, #516 ad2e2e6d3)
- Files: `src/State.cpp/.h` (`RefreshDrawAnnotations`, `drawAnnotationsActive`), `src/FrameAnnotations.cpp`, `src/Utils/TracyZones.h`, `src/GpuPass.cpp`.
- #842: per-draw Begin/End events only when `frameAnnotations` AND (D3DPERF status or renderdoc.dll or WinPixGpuCapturer.dll loaded).
- #301: replaces per-draw `std::format` + fresh `std::wstring` with reused buffers; `BeginDrawEvent` skips Tracy.
- #1017: per-draw Tracy zones behind a runtime gate (`TracyZones::PerDrawZonesEnabled`).
- Ours: partly. We have `AnnotateDraws()` gate, `frameAnnotations` defaults false, but State.cpp:318 and FrameAnnotations.cpp still use
  `std::format` per draw when on; no TracyZones.h, no BeginDrawEvent.
- Benefit: zero in a normal run if Frame Annotations is off (verify our setting). Real when profiling with Tracy/RenderDoc: less distortion at 6,100 draws.
- Effort: small.

### 4. Generic per-render-pass / per-draw feature hooks  (#654 d76813c51, per-draw hook in #932 4470b8f95)
- Files: `src/Feature.h/.cpp` (`WantsRenderPassHook`, `OnRenderPassBegin`, `ShouldSkipRenderPass`, `WantsDrawHook`, `OnDraw`), `src/Hooks.cpp` ~1300-1420.
- Core owns the RenderPassImmediately thunks; features opt in through a list cached once; nothing runs when the list is empty.
  LightLimitFix no longer installs its own RenderPassImmediately thunk in open-shaders.
- Ours: no (`WantsRenderPassHook` absent). LLF, InteriorSun, FurShells, TerrainBlending each write their own thunk.
- Caveat (verified): open-shaders still keeps separate thunks for InteriorSun, FurShells and TerrainBlending, so it is a pattern, not a finished consolidation.
- Benefit (guess): small CPU per draw (one fewer indirect call x 6,100); main value is the place to finish our own consolidation.
- Effort: small for the API, medium to move four features onto it.

### 5. Skylighting performance controls  (#701-705, #707, #826; cbc7611ca, e36bfe9c8, 6a775a810, dd072317b, b6df85e67, d6765a99c, 48ed0ec73, #624 6cbe1c970)
- Settings in theirs: `ProbeGridQuality` (3 grid sizes), `EnableIncrementalProbeUpdates`, `StableSliceCount`, `EnableReducedUpdateFrequency`,
  `OcclusionUpdateInterval`, `ProbeUpdateInterval`, runtime enable toggle; probe textures owned by unique_ptr and reallocated on grid change.
- Ours: only `OcclusionUpdateInterval` (ms), distance culling and min radius (upstream #2767).
- Benefit (guess): fewer occlusion-capture draws per frame (CPU draw submission) and smaller probe volumes (some VRAM); size of win unmeasured.
- Effort: medium. Skylighting.cpp +536/-382, shader + SharedData changes.

### 6. SSGI AO-only resource profile + adaptive sampling  (#277, 6038eb801)
- Files: `ScreenSpaceGI.cpp/.h`, `gi.cs.hlsl`, `radianceDisocc.cs.hlsl`, `DeferredCompositeCS.hlsl`, `Deferred.cpp`.
- `ResourceProfile` AO-only does not allocate GI targets (`HasGIResources()`); `EnableAdaptiveSampling` adds an `ADAPTIVE_SAMPLING` define in gi.cs.
- Ours: neither (we do have `HalfRes`).
- Benefit (guess): VRAM saving only if we accept AO without GI; adaptive sampling GPU saving unmeasured. Written for VR.
- Effort: medium (SSGI file differs by ~790 lines each way).

### 7. DoF and motion blur before upscaling  (#811, 951220acc)
- 28 lines: `DoF::DrawBeforeUpscaling()` / `MotionBlur::DrawBeforeUpscaling()` overrides + PostProcessing.cpp.
- Ours: has the `DrawBeforeUpscaling()` virtual in PostProcessFeature.h but DoF/MotionBlur do not override it.
- Benefit: runs those passes at render resolution (DLSS Quality = 44% of pixels). Only matters if DoF/motion blur are enabled in our look.
- Effort: small. Risk: quality change, interaction with NR final-image placement.

### 8. Shader compile/cache stutter work
- #1170 d8448b2e6: Lighting pixel shaders compiled with real `D3DCOMPILE_SKIP_OPTIMIZATION` flag (`Utils/ShaderCompileFlags.h`); flags are part of cache keys.
  Ours only pushes it as a macro define (ShaderCache.cpp:1553, 2652).
- #117 021d7980b background compile on boot; #325 76684d794 content-digest validity; #854/#953 keep cache across feature flips / version bumps
  (`Utils/ShaderCacheManifest.h`, absent in ours); #825 67cac1314 cache synchronous standalone compiles; #960 bb951d72c hide VS inputs from PS compiles
  (more shared PS); #284 rollback slot; #154 prebuilt cache.
- Ours: has upstream's dedupe (#2836), merged permutations (#2829), utility shader disk cache (#2848), #1014. Not the items above.
- Benefit (guess): shorter cold compiles and fewer forced full recompiles. Helps cell-crossing stalls only if those are first-use compiles - not established.
- Effort: small for #1170 and #960; large for the cache-manifest series (ShaderCache.cpp +2761/-704).

### 9. Diagnostics worth borrowing
- Render target GPU table (#932, 4470b8f95): `PerformanceOverlay/RenderTargetStats.cpp/.h`, `Utils/GpuTimestamps.h` (`TimestampQueryBatch`);
  draw calls and GPU ms per engine render-target binding, shadow maps included. Directly answers "where do the 15 ms of unlabelled scene GPU go".
- A/B settings compare (#1028, 73479337f): `PerformanceOverlay/ABTesting/ABComparison.*`, `ABSettingActions.cpp`; benchmark repeat (#1062).
- `docs/development/nsight-perf.md`, devbench profiler tools (`ToolSpecs/ProfilerTool.h`, `InspectProfilerExt.h`), shader store stats on Home (#1104).
- Ours: has ABTesting base and NvPerf, VramTracker; not RenderTargetStats/TimestampQueryBatch.
- Effort: medium (needs the per-draw feature hook from item 4).

### 10. LLF shadow caster manager / shadow atlas  (#35 4e246fb21, #292 c350c84f8, #393 cf22c50ec, scm perf #928 #942 #943 #1020 #1021)
- Files: `src/Features/LightLimitFix/Shadow*.cpp`, `ShadowCasterManager.*` (5,400+ lines), `ShadowDemandCS.hlsl`, `ShadowDepthPyramidCS.hlsl`.
- Caches static shadow maps of local (point/spot) lights, redraws under a ms budget, GPU screen-demand scheduling.
- Ours: none of it. Scope is local lights, not the sun cascades (little directional handling in those files).
- Benefit (guess): interiors and towns with many shadow lights; little for the outdoor grass scene. Effort: very large. Not recommended now.

### 11. Small fixes
- #505 cd7f35a51: dedupes boot `Setup()`, plugs constant-buffer leaks.
- #1122 cd2b8de01: grass bucket draw restores engine CBs (correctness fix against our grass batching path; check applicability after #3162).
- #1141 f44511875: SSS skips DrawShadows with no sun light.

## Looked for, not found in open-shaders
- No grass LOD / distance simplification beyond what upstream has (we are ahead with #3162).
- No multithreaded or deferred command recording, no depth-prepass change, no sun-cascade shadow caching/culling.
  `LODShadows` (#1087, #1125) adds cached sun shadows from terrain/LOD: extra cost, default off.
- No flat-screen render-target shrinking or pooling. `Upscaling/PerfMode` allocates engine targets at render resolution but is hard-gated to VR
  (`if (!globals::game::isVR)` in PerfMode/Core.cpp:22, ResolutionHook.cpp:33). Same for foveated rendering.
- No texture streaming.

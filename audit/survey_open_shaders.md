# Open Shaders survey (deep pass)

Date: 2026-11-18. Read-only survey; nothing built, nothing run, our fork untouched.

- Open Shaders: https://github.com/alandtse/open-shaders, branch `dev`, tip `c89e4e62` (2026-11-18, "fix(effects): restore smoke utility controls (#1184)").
  Clone: `C:\Users\foxnn\dev\_survey\open-shaders` (blobless).
- Ours: `C:\Users\foxnn\dev\skyrim-community-shaders`, branch `foxnne/nr-pr6`.
- Supersedes/extends `open_shaders.md` (2026-11-17).

STATUS: complete (2026-11-18). Sections: top 10, 1 state and divergence, 2 per-priority findings, 3 other, 4 looked and found nothing, 5 uncertainty.

## Top 10 worth porting

Effort: S = hours, M = days, L = a week or more / re-implementation. No clean cherry-picks exist: the trees differ in every hot file, so everything is a hand port guided by their diff. Benefit numbers marked "claim" are theirs.

| # | Item | Where (OS) | Effort | Expected benefit for us |
|---|---|---|---|---|
| 1 | **NR model preset on the 310.9 runtime**: write `DLSSNR.Hint.Render.Preset` = 2 (newest, faster network) or 1 instead of our hard-coded 0 | `NeuralRendering/Runtime.cpp:506`, `Runtime.h:61`, `4f21680c0` #956 | S (a few lines in our `NeuralRendering/Runtime.cpp:553` + setting) | Claim: model 4.5 ms -> 2.6 ms (5090, 1080x1200). Our runtime is already 310.9.16.0. Look changes (weaker, finer gain), so it needs a visual A/B. Largest GPU win per line of code found. |
| 2 | **Frame pacing hygiene**: bounded frame-fence wait, limiter that scales with the FG multiplier and steps aside for the Streamline pacer, full PCL marker sequence | `DX12SwapChain.cpp:698` `SharedFence::CpuWaitOutcome` (`74af89ecd` #902), `Upscaling.cpp:2663`, `Streamline.cpp:969-1075` | S-M | Removes an unbounded render-thread block (`SetEventOnCompletion(..., nullptr)` in ours); correct Reflex marker set. Prerequisite for 3. |
| 3 | **DLSS-G frame generation with MFG, Dynamic MFG, model presets** | `Upscaling.cpp`, `Upscaling/Streamline.cpp`, `Upscaling/DX12SwapChain.cpp`, `DLSSG*.h`, `Utils/NvApiDrs.h`; #445 #864 #747 #832 #1102 #1110 #1111 | L | 3x/4x or dynamic MFG on the 5080 with Reflex pacing. Does not raise real fps; costs VRAM. Must keep their private input copies + input fence so our final-image stages (NR, LookGrade) do not race it. |
| 4 | **NR reuse refinements**: model every Nth frame (3, 4), forced model run on fast camera motion, real frame gap passed to the model | `NeuralRendering/Cadence.h`, `GainReuseCS.hlsl`, `a22e2b4e9` #1108 | S-M (adapt into our `Backend.cpp` skip logic) | Claim: 3.66 -> 2.18 (N=2) -> 1.65 ms (N=3). We already have N=2; N=3 plus the motion gate is the increment. |
| 5 | **Profiling tools**: per-render-target GPU table, A/B settings compare, benchmark repeat | `PerformanceOverlay/RenderTargetStats.*`, `Utils/GpuTimestamps.h`, `ABTesting/ABComparison.*`; #932 #1028 #1062 | M (needs their per-draw feature hook #654) | Attributes unlabelled scene GPU time (shadow maps included) and makes setting A/Bs repeatable for the forest work. |
| 6 | **Skip inactive shader work with runtime branches** (snow, wetness, tree bend, empty clustered-light grid, IBL) | branch `origin/refactor/runtime-shader-branches` (`d8e32c2d2`..`bd45d4ef8`), unmerged | M | GPU time on forest pixels; unmeasured. Their earlier compile-time version was reverted wholesale on 11-17, so wait for it to land or take only the simplest guards. |
| 7 | **Neutral-grade fast paths** + **DoF/motion blur before upscaling** | `colorgrading.hlsl`, `ColorGrading.cpp`: `cdd55a427` #1137, `1faa781df` #1138, `73e5cca45` #1128; `951220acc` #811 | S-M | Fits the neutral baseline: identity controls cost nothing, white balance leaves the pixel shader; DoF/blur at render resolution. Small GPU savings. |
| 8 | **LOD Shadows**: cached far sun/moon shadows from terrain, object LOD and tree LOD, also fed to the volumetric light | `src/Features/LODShadows.*`, `features/LOD Shadows`, `d66ccad74` #949 + #1029 #1087 | L | Realism: shadows and light shafts beyond the cascades at a 0.1 ms update budget (their default). Default off upstream of us, so treat as beta. |
| 9 | **Nearby volumetric mists** in the existing volumetric fog | `VolumetricMists.hlsli`, `docs/development/volumetric-mists.md`, `434a5d6c0` #959 | M | Wind-drifted ground mist pockets with no extra pass. Cost unmeasured by them. |
| 10 | **Skylighting cost controls** (grid size, incremental probe updates, update intervals) | `Skylighting.h:73-79`, #701-#705 #707 #826 #624 | M | Fewer occlusion-capture draws per frame in dense scenes (CPU). Size of win unmeasured. |

Also worth a look, smaller or less certain: shared shadow SRV bind cache (`bf670cf8d` #1160, S); rain composited after upscaling (`RainLayer.cpp`, `8571e8a58` #995, S-M); Lighting PS compiled without FXC optimisation for faster cold compiles (`d8448b2e6` #1170, S, needs a frame-time A/B); hide VS inputs from PS compiles (`bb951d72c` #960, S); screenshot frame sequences for temporal comparisons (#834 #981 #982, M); shared wind field with gust fronts (`src/Features/Wind`, L).

## 1. What Open Shaders is today (verified from the clone, 2026-11-18)

- Fork of Community Shaders by alandtse (VR-first, heavy use of AI-assisted PRs; many commits co-authored by Claude). One long-lived branch, `dev` (default). `main` = last release commit (`5eb8662e`, "chore(release): 2.22.1", 2026-11-17).
- Releases: tags `v2.20.0` (10-29), `v2.21.0` (11-11), `v2.22.0` (11-15), `v2.22.1` (11-17), plus `dev-latest` and per-PR prerelease tags (`v2.22.1-pr1161`). Roughly one release a week.
- Activity: 820 non-merge commits on `dev` since 2026-09-18. Rough themes by commit scope (count): effects11 40, upscaling/NR/DLSS-G 57, UI/menu 46, upstream "sync" fixes 22, skylighting 22, LLF + shadow caster manager (scm) 31, shader cache 30, grass 11, snow (cover + deformation) 14, wind/rain 10, VR 7+, devbench/profiler/screenshot 25.
- 707 remote branches; only `dev` matters. Notable side branches: `sync/upstream-dev-20261115` (57 commits ahead of dev, not merged: brings upstream Tree Wind #2991, Procedural Aurora #2936, grass batching #3162, physical lens #3171, camera fx #3155, skin editor #3154, wetness surface rain flow #2912), `refactor/runtime-shader-branches` (11-18, replacing compile-time permutations by runtime branches after the 11-17 mass revert, see 2i), `feat/nr-flat-cadence`, `perf/sun-passless-filter`.
- Relation to upstream CS: OS merges upstream `dev` in batches ("sync" branches). Last upstream PR in OS `dev` is #3140 (2026-11-10). OS `dev` does NOT have upstream #3157 (Physical Sky), #3162 (grass batching), #2991 (Tree Wind), #3171 (physical lens), #3178 (GGX energy compensation). We have all of those. So for sky/clouds, grass and tree wind we are ahead of OS.
- Relation to our fork (`foxnne/nr-pr6`, HEAD `753ce4ae2`): `git merge-base` = `95e1f69d3` (2026-11-10, upstream #3135). Commit-graph counts: 3844 theirs-only (3581 non-merge), 1378 ours-only. By subject match (PR suffix stripped) 999 of the 3581 have no counterpart in ours; 446 of those are dated 2026-09-18 or later. Monthly: 05:37, 06:110, 07:108, 08:192, 09:221, 10:197, 11:134.
- Their own PR numbers are #1..#1184; upstream PRs appear as #2xxx/#3xxx. That is the quickest way to tell an OS-original commit from a synced one.
- The 2026-11-17 note is still right on divergence and on the candidate list, with these corrections:
  1. Our NR is no longer the hand-ported OS one. `foxnne/nr-pr6` replaced it with the cavy8 feature (`src/Features/NeuralRendering.cpp`, `NeuralRendering/Backend.cpp`, `Runtime.cpp`; commits `b03edd328`, `639c6ba83`). It already has "alternate frames" reuse (`Settings::alternateFrames`, `Backend.cpp:1025 skipFrame`). So old candidate #1 (OS #1108 cadence) is now "compare ideas", not "port".
  2. Anti-Lag 2 is NOT in our tree (no `antilag` match in `src/Features/Upscaling*`; `extern/AntiLag2-SDK/` is an untracked folder). The old note listed it as already ported.
  3. OS tip moved 5eb8662e -> c89e4e62 (8 fix commits, none relevant to our priorities).

### OS-only work not in our fork, grouped (hashes are OS `dev`)

| Group | Commits (PR) | In ours? |
|---|---|---|
| DLSS-G frame generation, MFG, Dynamic MFG, presets | `0deec7f21` (#445), `30d150fba` (#864), `20ea52057` (#1102), `2bd02571d` (#1110), `5846ac17a` (#1111), `74af89ecd` (#902) | No |
| AMD Anti-Lag 2 | `c1b1ef1e8` (#991) + `docs/development/antilag2.md` | No |
| NR (OS variant): crop, material strength, dialogue profile, 310.9 presets, model scale, cadence, colour strength, capability report | `386bb211f` #723, `0d169a2a1` #831, `6feeaf39e` #866, `5c4073db4` #870, `4f21680c0` #956, `1ec966e28` #889, `a22e2b4e9` #1108, `87a087f53` #1088, `0f15bc277` #1089, `165e9cf4c` #1067, `3caae9cb5` #1061 | Different implementation |
| LLF shadow caster manager / shadow atlas / contact shadows | `4e246fb21` #35, `c350c84f8` #292, `cf22c50ec` #393, `c37cea357` #823, scm perf #928 #942 #943 #1020 #1021 | No (upstream has its own #2757 local shadow cache, which we have) |
| LOD Shadows feature | `d66ccad74` #949, `a973fb2e4` #1029, `bb327f2d4` #1087, `503b5a161` #1125 | No |
| Shared wind field + wind for grass/trees/rain/fog/fur | `7acc8d70a` #634, `3aa48d435` #767, `b6a02fc1e` #799, `2ac27bd99` #794, `fa373f4ca` #1075, `79f0cb8c9` #1077, `434a5d6c0` #959 | No (we have upstream Tree Wind instead) |
| Snow Cover / Snow Deformation with physics | `c3e0662e7` #989, `de960167d` #1050, #1076 #1082-1084 #1112 | We have Bottled/upstream variants; OS ones are separate code |
| Fur shells for armor, inertia, wet fur, touch | #964 #972 #975 #976 #978 #984 | Base feature yes, these extensions no |
| Volumetric mists, local-light fog shadows, distance haze | `434a5d6c0` #959, `ddec37223` #931, `2cedaa978` #753, `405b59488` #635 | No |
| Skylighting perf controls and interior probes | #701-705, #707, #826, `6cbe1c970` #624, `9293a75c7` #596 | No |
| Cloud Relight, Foliage Lighting, CS/OS Utility, Vanilla Fresnel | `5c8d229a6` #342, `1aaed89d0` #486, `09442614a` #453, `c5ebf27c5` #225 | Cloud Relight/Foliage Lighting/Utility: no |
| Shader cache: manifest, flips, version bumps, rollback, prebuilt cache, background compile, -Od Lighting PS | #117 #154 #157 #284 #325 #346 #825 #854 #953 #960 #961 #1064 #1170 | No |
| Profiling/tooling: render target GPU table, A/B settings compare, benchmark repeat, draw-annotation gating, per-pass hooks, devbench notices, screenshot sequences/bursts | #932 #1028 #1062 #842 #654 #1086 #834 #981 #982 | Partly (ABTesting base, NvPerf, FrameRecorder) |
| Wetness: character rain drops, tree wetness, grass wetness, wall droplets | #604 #614 #470 #1101 | No (upstream #2912 surface rain flow is ours) |
| VR: PerfMode, foveated DLSS/FSR, eye gaze | many | Not relevant (flat screen) |

## 2. Findings per priority

Legend: [V] = I opened the file/commit; [I] = inferred from commit message or names only. "Claim" = number taken from their commit message/doc, not measured by us.

### 2a. Frame generation and frame pacing

OS has the most complete frame-gen stack seen so far. All of it is absent from ours (we have FSR FG + DX11 Reflex only; Bottled added DLSS-G on 10-05 and removed it on 10-09, `5969d9c4d` "remove dlssg", no reason recorded).

- **DLSS-G with MFG and Dynamic MFG** [V]
  - `src/Features/Upscaling.h` Settings: `enableDLSSFrameGen`, `dlssgFramesToGenerate` (clamped to `DLSSGState::numFramesToGenerateMax`), `dlssgDynamic`, `dlssgDynamicTargetFPS` (0 = display refresh), `dlssgPreset` (Default/A/B/C; C needs nvngx_dlssg 310.9.16), `frameGenerationAllowInMenus`, `streamlineLogLevel`.
  - `src/Features/Upscaling/DX12SwapChain.cpp` `PresentImpl<WithAntiLag2>` (line 408): copies depth, motion vectors, HUD-less colour (the fake swap-chain buffer) and UI colour+alpha into private D3D12 copies (`CopyDLSSGInputs`, line 904), tags them (`Streamline::TagDX12Resources`), calls `ConfigureDLSSG`, queues a GPU-side wait on the DLSS-G input fence (`QueueWaitForDLSSGInputs`), then Present.
  - `src/Features/Upscaling/Streamline.cpp`: `ConfigureDLSSG` (line 1077; `sl::DLSSGMode::eOn/eOff/eDynamic`, `eRetainResourcesWhenOff`, `slFreeResources` when FG is turned off), `TrackDLSSGInputFence` / `QueueWaitForDLSSGInputs` (1161-1190; reads `state.inputsProcessingCompletionFence` and `lastPresentInputsProcessingCompletionFenceValue`), `EnsureDriverProfileAllowsDLSSG`, `IsSmoothMotionEnabledForProfile`, `ApplyDLSSGPresetToDriverProfile` (NvAPI DRS, `src/Utils/NvApiDrs.h`).
  - Small pure helpers with Catch2 tests: `DLSSGDynamic.h` (29 lines), `DLSSGInputFence.h` (39), `DLSSGPreset.h` (43); tests `tests/cpp/test_dlssg_*.cpp`. Repro tool `tools/dlssg-repro`.
  - Commits: `0deec7f21` #445 (base), `30d150fba` #864 (opt-in), `bf52e305a` #747, `d62f8a8c9` #832, `74af89ecd` #902 (bounded frame fence), `20ea52057` #1102 (Dynamic MFG), `2bd02571d` #1110 (input fence), `5846ac17a` #1111 (Preset C). Streamline submodule pin `625db07d` (ours `2122257e` per the 11-17 note).
- **Latency markers / Reflex** [V]
  - With DLSS-G active, DX11 Reflex is switched off and the DX12 Streamline instance owns Reflex (`Streamline::UpdateReflex`, line 969: forces at least `eLowLatency` while FG is prepared).
  - Full PCL marker sequence per frame: `eSimulationStart` right after `slReflexSleep`, then in `PresentImpl`: `eSimulationEnd`, `eRenderSubmitStart`, `eRenderSubmitEnd`, `ePresentStart`, `ePresentEnd`. Their comment: "The full per-frame PCL marker sequence is structural for interpolation". Ours only emits `eRenderSubmitStart/End` around the DLSS evaluate (`src/Features/Upscaling/Streamline.cpp:538-540`), which is not a complete marker set for Reflex "use markers to optimize".
  - Generic input-poll hook: `Feature::OnBeforeInputPoll()` + `Hooks::InstallBeforeInputPoll` (`src/Hooks.cpp:761-777`, `BSInputDeviceManager`, id 67315/68617). They use it for Anti-Lag 2.
- **Frame limiter** [V] `Upscaling::FrameLimiter` (`Upscaling.cpp:2663`):
  - returns immediately when DLSS-G is active ("The SL pacer owns presentation when DLSS-G is active; host-side blocking here starves its flip queue and every interpolated frame gets dropped");
  - real-frame target scales with the active multiplier (`GetFrameGenerationMultiplier()`); ours hard-codes 0.5 (`kFrameGenerationRateScale`, our `Upscaling.cpp:1344`). Otherwise identical to ours (same upstream #3041 sleep+spin code).
- **Bounded fence wait** [V] `SharedFence::CpuWaitOutcome` (`DX12SwapChain.cpp:698`): event wait in slices, polls `GetDeviceRemovedReason`, `PresentImpl` returns `DXGI_ERROR_WAS_STILL_DRAWING` on timeout. Ours: `d3d12Fence->SetEventOnCompletion(value, nullptr)` at `DX12SwapChain.cpp:245`, an unbounded block on the render thread. Small, self-contained port.
- **Anti-Lag 2** [V] `c1b1ef1e8` #991, `Upscaling/antilag2sdk.h`, `docs/development/antilag2.md`. AMD-only; not relevant to an NVIDIA-only fork.
- **Interaction with final-image post stages** [V]:
  - OS's HUD-less colour for DLSS-G is the wrapped fake swap-chain buffer after all scene post (and after HDR encode); UI is rendered to a separate `uiBufferWrapped` and passed as `UIColorAndAlpha`. So anything composited into the final image before the UI is interpolated; the UI is not.
  - `Upscaling::Main_PostProcessing::thunk` (`Upscaling.cpp`, about line 3620) order: `postProcessing.DrawBeforeUpscaling()` -> NR `DrawBeforeUpscaling` (render resolution, before DLSS) -> `ClearBorderMotionVectorsForFrameGen` + `CopySharedD3D12Resources` (FG depth/MV capture) -> upscale -> sharpen -> rain layer composite -> engine ISHDR.
  - #1110 exists because the next frame overwrote the shared depth/MV while DLSS-G was still reading them (the 11-17 note records it as fixing judder with NR + DLSS-G). Any final-image stage we add (our NR final-image placement, LookGrade) has the same hazard if we port DLSS-G without the private copies + fence.
  - NR crop calibration "refuses to run with frame generation on, since frame generation paces the frame and skews the GPU zones"; the VR eye stagger is switched off while FG is active (`docs/development/neural-rendering.md`).
- Maturity: shipped in releases since August, opt-in, many follow-up fixes, unit tests for the decision logic. All testing is theirs.
- Port effort: **large, re-implementation**. Our `DX12SwapChain.cpp` is 560 lines vs 990, `Streamline.cpp` 664 vs 1247, `Upscaling.cpp` 1917 vs 3718. No cherry-pick will apply. The three helper headers and their tests copy over unchanged; the bounded fence wait and the multiplier-aware limiter are small independent ports.

### 2b. Neural rendering / ML final-image stage

OS NR (`src/Features/Upscaling/NeuralRendering.cpp` 2837 lines + `NeuralRendering/*`, shaders `features/Upscaling/Shaders/Upscaling/NeuralRendering/*`, doc `docs/development/neural-rendering.md` 776 lines) and our NR (cavy8 PR #6: `src/Features/NeuralRendering.cpp`, `NeuralRendering/Backend.cpp`, `Runtime.cpp`) are now two separate implementations of the same NGX Feature 18 (`nvngx_dlssnr.dll`).

- **Placement** [V]: OS evaluates at render resolution inside `Main_PostProcessing`, before DLSS/FSR and before FG input capture; it treats the model as a per-pixel luminance gain applied to the untouched HDR frame (`ColorTransferCS.hlsl`), optionally plus a colour shift (`colorStrength`, `87a087f53` #1088). Ours has selectable seams including final-image.
- **Model preset on the 310.9 runtime: concrete, cheap experiment** [V]
  - OS `NeuralRendering/Runtime.cpp:506`: `DLSSNR.Hint.Render.Preset` = `kRuntimeModelPreset[tuning.modelPreset]` = `{1, 2}` (`Runtime.h:61`) when the runtime is 310.9 or newer (`kNewerRuntimeMinor = 9`), else 0. Doc: "The runtime ships two networks chosen at feature creation ... 1 (the original 310.8 network, the default) or 2 (the newest, faster one)".
  - Their measurement (claim; VR 1080x1200 per eye, RTX 5090): preset 1 about 4.5 ms, preset 2 about 2.6 ms; preset 2 applies a weaker, finer gain (mean 0.167 vs 0.236 stops).
  - Ours: `src/Features/NeuralRendering/Runtime.cpp:553` hard-codes `parameters->Set("DLSSNR.Hint.Render.Preset", 0u)`. The runtime installed in `C:\Modlists\NGVO 8.0 Beta\mods\Bottled Shaders - foxnne\Shaders\Upscaling\Streamline\nvngx_dlssnr.dll` is **310.9.16.0** (file version read). What preset 0 selects on 310.9 is not stated anywhere I read: unknown.
  - Port: expose a setting and write 1 or 2 at creation; changing it recreates the feature. A few lines plus UI. Commit `4f21680c0` #956.
- **Frame reuse** [V]: OS `Cadence.h` + `GainReuseCS.hlsl` + `MotionOffsetCS.hlsl`, `a22e2b4e9` #1108: model every N frames (1-4); in between, reproject the stored log-gain with 4 bilinear taps, each rejected on depth (`kReuseDepthTolerance`) or luma (`kReuseLumaTolerance`) mismatch; force a model run on camera turn > 1 degree or move > 12 units (`Cadence::IsHighMotion`); tell the model the real frame gap (`GapScale`). Claim: 3.66 -> 2.18 (N=2) -> 1.65 ms (N=3), SE Dragonsreach replay, reuse error 0.03 stops against a model effect of about 0.11.
  - Ours already has every-other-frame reuse (`Settings::alternateFrames`, `Backend.cpp:1017-1030`, `TemporalReprojection.hlsli`). Ideas we may lack: N = 3/4, the high-motion forced run, reporting the real gap to the model (I did not check our decode shader for luma rejection).
- **Run the model at reduced size** [V]: OS `ModelScale.h` (0.25-1.0, 8-px aligned) + `LowResCS.hlsl`, dev-only, `1ec966e28` #889. Ours has `resolutionScale` / per-axis scale + `depthAwareResolve`: equivalent exists.
- **Tracked-actor crop** [V]: `ActorRegion.h`, `CropCalibration.h`, `src/Utils/Region.h`: evaluate only a stabilised crop around the most prominent actor, keep history when the crop moves (`0f15bc277` #1089), built-in calibration that times `Upscaling::NREvaluate` per crop size. Dialogue profile (`ContextProfile.h`, `5c4073db4` #870): run NR only while `DialogueMenu` is open, or change scope/crop in dialogue. Real cost levers for a face-focused use of NR. I did not find an actor crop in our NR (not exhaustively checked).
- **Material lanes** [V]: `MaterialMap.h`, `MaterialStrength.h`, `CategoryAlphaCS.hlsl` (skin/hair/eyes/foliage/landscape/cloth/metal/else). Ours has `categoryStrengths`.
- **Runtime hygiene** [V]: SHA-256 pinning of validated runtime builds (`NR::kValidatedRuntimeSha256`), several runtime builds side by side in subfolders with a picker (`Tuning::runtimeVariant`), capability + memory report (`165e9cf4c` #1067).
- Maturity: heavily documented and instrumented; the doc itself flags single-run measurements and test scenes without characters.
- Port effort: preset switch = trivial. Cadence ideas = small to moderate adaptation into our Backend. Actor crop = moderate to large (needs `Util::Region`, actor scoring on the main thread, subrect plumbing).

### 2c. Dense-forest performance

OS has **no** work on sun cascade caching/throttling, generic occlusion or Hi-Z culling of trees, tree LOD, or draw-call reduction beyond upstream. We are ahead here (HiZOcclusion feature, grass batching #3162, budgeted TreeWind builds). What exists:

- **LOD Shadows** [V] `src/Features/LODShadows.cpp` (1349 lines), `LODShadowSettings.h`, `LODShadowUpdateBudget.h`, shaders `features/LOD Shadows/Shaders/LODShadows/{Caster.hlsl, FilterMask.cs.hlsl, LODShadows.hlsli}`. Author Dlizzio, `d66ccad74` #949 (10-22); perf follow-ups `a973fb2e4` #1029, `bb327f2d4` #1087; default off since `503b5a161` #1125.
  - 3 nested cached directional depth maps, 2048 px (`kMapCount = 3`, `kResolution = 2048`, minimum half extents 18432 / 55296 / 165888 units), filled from terrain, distant objects and trees under a GPU-time budget (`UpdateBudgetMs = 0.1`; triangle budget adapts from measured batches), history blending (600/1500/2500 ms) and a filtered receiver mask.
  - Consumers: `package/Shaders/Common/ShadowSampling.hlsli`, `Effect.hlsl`, and `ISVolumetricLightingGenerateCS.hlsl` (line 123, through `ShadowSampling::GetWorldShadow`), so far shadows also cut the vanilla volumetric light.
  - `ReplacesTerrainShadows()`: complete maps can replace heightmap terrain shadows.
  - For us this is a realism item (mountain and forest LOD shadows past the cascades, far shafts) with a bounded cost, not a speed-up. Needs their per-draw feature hook (`WantsDrawHook/OnDraw`). Effort: large (new feature, texture slots 117/118/127/61, engine geometry walk).
- **Sun caster filtering** [V] `21118225b` #1098 (`LightLimitFix/ShadowCasterClassifier.cpp`): drops casters that register no shadow-map pass from the sun cascade cull append. Their measurement: about 50 us/frame, "a refactor, not a perf change". Tied to their shadow caster manager. Not worth porting.
- **Redundant shadow SRV bind** [V] `bf670cf8d` #1160 `src/Features/VolumetricShadows.cpp` (+20 lines): cache the SRV bound to slot 18 per frame instead of rebinding on every draw. Claim 0.1-0.2 ms, within their noise. Small port; at about 6,100 draws it removes one `PSSetShaderResources` per draw.
- **Draw annotation gating, per-pass/per-draw hook consolidation** (#842, #301, #1017, #654): unchanged from the 11-17 note; still absent in ours (`WantsRenderPassHook` / `WantsDrawHook`: 0 matches in our `src/Feature.h`).
- **Skylighting cost controls** [V] OS `src/Features/Skylighting.h:73-79`: `ProbeGridQuality`, `EnableIncrementalProbeUpdates`, `StableSliceCount`, `EnableReducedUpdateFrequency`, `ProbeUpdateInterval`; `855d3889e` #1136 / `023fb4030` #1135 reuse probe offsets. Ours only has `OcclusionUpdateInterval`. Skylighting's occlusion capture re-draws geometry, which in a forest is CPU draw submission. Medium port.
- **Runtime-branch shader work** [V, unmerged branch] `origin/refactor/runtime-shader-branches` (11-18, 6 commits `d8e32c2d2`..`bd45d4ef8`): `[branch]` guards so inactive snow, wetness, tree bend, clustered-light grid (publishes the clustered light count so shaders skip cluster index math and grid reads when it is zero), IBL and effect lighting are skipped without new permutations. It replaces the #1129-#1149 compile-time "specialize" series that was mass-reverted on 11-17 (12 revert commits, `2e063d83c` .. `fbb5046c8`; revert bodies give no reason). No measurements quoted. Worth watching; the ideas apply directly to forest pixels.
- **PCF taps as dynamic loops** [I] `10669f941` #409, `857cbbf15` #417 (`LightLimitFix.hlsli`).
- Grass: OS is behind us (no #3162). `cd2b8de01` #1122 "restore engine CBs after bucket draw" is a correctness fix on the older bucket path; check whether it still applies after #3162.

### 2d. Sky and clouds

OS has no physical sky, no atmosphere LUTs, no volumetric clouds, no aerial perspective. We are far ahead (upstream #3157 Physical Sky plus our fixes). OS-only items:

- **Cloud Relight** [V] `src/Features/CloudRelight.cpp/.h` (149 lines), `features/Cloud Relight/Shaders/CloudRelight/{CloudRelight.hlsli (220 lines), Draine.hlsli}`; `5c8d229a6` #342, `1aaed89d0` #486. Relights vanilla 2D cloud textures with the active sun/moon: self-shadowing and silver-lining / forward-scattering phase (Draine). Only useful where we still draw vanilla clouds. We already use a Draine phase (`features/Physical Sky/Shaders/PhysicalSky/CloudLighting.hlsli`).
- **Sun glare occlusion** [V] `ad261d852` #819: `GetSunGlareVisibility` in `package/Shaders/Sky.hlsl` (16 Poisson depth taps around the sun in the vertex shader fade the glare sprite), plus sunset light occlusion through SkySync/TerrainShadows. Small.
- Procedural Sun (#3098, #2822), sky dither animation (#3104), sky-sync smoothing (#3132) are upstream commits that are in our history.

### 2e. Volumetric lighting, god rays, fog

- Same upstream volumetric fog base on both sides (`features/Exponential Height Fog/Shaders/ExponentialHeightFog/VolumetricFog*CS.hlsl`). Ours additionally has `ViewAtmosphere` ("Atmosphere and Fog"), `FogIBLColorCS.hlsl`, `VolumetricFogLighting.hlsli`.
- **Nearby volumetric mists** [V] `434a5d6c0` #959, `VolumetricMists.hlsli`, `docs/development/volumetric-mists.md`: world-positioned, wind-drifted noise pockets added to extinction and scattering inside the existing material pass (no new dispatch or texture); strength calibrated from the weather fog optical depth over 8192 units; pockets stretched 2.5x along drift and half height; resolution-aware fade so coarse far cells do not alias. Off by default; the doc says "No GPU cost or visual quality claim has been measured yet". Closest thing to ground-fog patches. Port: moderate (one hlsli, settings, cbuffer fields; our EHF .cpp differs by about 100 lines in size and has its own additions).
- **Far shadows in the vanilla volumetric light**: via LOD Shadows (2c).
- Local light shadows in fog `ddec37223` #931: upstream equivalent #2899 is in ours.
- Distance haze controls `2cedaa978` #753, "match vanilla weather visibility" `405b59488` #635 [I].
- Nothing on shafts through volumetric clouds (they have none) and nothing tree-specific.

### 2f. Tone mapping and colour pipeline

Same upstream post-processing stack (OpenDRT, PsychoV v30, histogram auto exposure, local exposure, LUT). OS lacks our LookGrade, PhysicalLens, ImageSpaceModifiers. OS-only:

- **Grading fast paths** [V] (Dlizzio, 11-13/14, not among the reverts): `cdd55a427` #1137 white balance matrix computed in the vertex shader and passed down (ours calls `WhiteBalance()` per pixel, `colorgrading.hlsl:829`); `1faa781df` #1138 `NeutralGrading` bit mask computed in the vertex shader so neutral input gamma/cinematic controls, CDL, contrast, tint/fade and OKLCH controls are skipped with `[branch]`; `73e5cca45` #1128 grading writes the engine target directly. Good fit for a neutral baseline where most controls sit at identity. Port: moderate adaptation (same file; ours diverged).
- **DoF and motion blur before upscaling** `951220acc` #811: still absent in ours (0 `DrawBeforeUpscaling` overrides in our `DoF.h` / `MotionBlur.h`).
- `69c87160d` #809 tonemapping settings exposed to Scene Manager [I].
- No new tonemapper, no new exposure method, no new HDR output work beyond upstream.

### 2g. Skin, SSS, hair, eyes

Nothing new. We have the upstream skin editor (#3154, #3175) that OS `dev` lacks. OS-only fixes [I, subjects only]: `fa0b7cc5c` #940 skin keeps wetness when leaving water, `026984d1d` #1018 hair sun-lit with the deferred shadow in LLF, `1bdf8aab3` #820 ACEScg skin tint, `f44511875` #1141 SSS `DrawShadows` null-sun guard.

### 2h. Screen-space effects

- **SSGI AO-only resource profile + adaptive sampling** `6038eb801` #277 [V: OS `ScreenSpaceGI.h:99-115`]: unchanged from the 11-17 note; ours has `HalfRes` instead.
- LLF depth-raymarched contact shadows `c37cea357` #823 [I].
- No denoiser work (we have NRD; they do not). No SSR feature (we have one).

### 2i. Stutter / hitch avoidance

All on the shader-cache side; nothing on streaming or on moving engine work off the render thread.

- **Lighting pixel shaders compiled with `D3DCOMPILE_SKIP_OPTIMIZATION`** [V] `d8448b2e6` #1170: `src/Utils/ShaderCompileFlags.h` (16 lines) + 6 lines in `ShaderCache.cpp`; the flags are part of the dedupe and content-store keys. Their rationale: Lighting PS dominates cold compile time and "the driver re-optimizes the bytecode ... without a measurable runtime cost". The runtime-cost statement is theirs; in a GPU-bound forest scene it must be A/B tested before adoption. Ours only passes `D3DCOMPILE_SKIP_OPTIMIZATION` as a macro define in debug compiles (`ShaderCache.cpp:1553`, `2652`).
- **Hide VS inputs from PS compiles** [V] `bb951d72c` #960 (8 shader files, +80/-62): more pixel shaders dedupe to the same bytecode.
- Keep cache across feature flips and version bumps `2efcd7218` #854, `6c20a55e3` #953 (`Utils/ShaderCacheManifest.h`, `Utils/CacheInvalidation.h`); cache synchronous standalone compiles `67cac1314` #825; content-digest validity `76684d794` #325; rollback slot `48c23e05b` #284; prebuilt cache distribution `a33b653cc` #154; background compile on boot `021d7980b` #117; wrong-runtime cache flag `34b4b8288` #1064; compile impact of toggles in the menu `567d872f8` #858.
- Ours has upstream's content store (#3008), dedupe, demand compile in background (#3077) and our own `Utils/AsyncShaderSet`, `HitchSampler`. `ShaderCache.cpp` is 4173 lines (ours) vs 6230 (theirs): the manifest series is a large port.
- `src/Utils/RenderTaskQueue.h` is a plain hand-off queue to the render thread, not a job system.

### 2j. Wind, snow, wetness, water

- **Shared wind field** [V] `src/Features/Wind/*` (2911 lines in the top folder, more in subfolders); `7acc8d70a` #634, `3aa48d435` #767 (tiered sampling API), `2ac27bd99` #794, `b6a02fc1e` #799, `2ce1aa469` #1005. One procedural gust-front field (`WindField::SampleField`; tuning: gust scale 2048, front aspect 4, advection 384 u/s, turbulence 0.24) evaluated identically in C++ and HLSL (parity test `tests/cpp/test_windfield.cpp` with `package/Shaders/Tests/WindFieldParitySamples.hlsli`), driving grass flutter, tree bending (`TreeWindSpringCS.hlsl`), rain (`fa373f4ca` #1075, curtains `79f0cb8c9` #1077), fog mists and fur. `WindEffects/*`: transient impulses from shouts, dragons, explosions, projectiles and heavy impacts.
  - We have upstream Tree Wind (#2991) instead; OS's pending sync branch imports that too (`34311b462` "ship Procedural Sun and Tree Wind"). Coherent gust fronts across grass, trees and rain are a visible realism gain. Port: large, and it overlaps our TreeWind hooks.
- **Rain layer** [V] `src/Features/Upscaling/RainLayer.cpp` (186 lines), `CompositeRainCS.hlsl`, `8571e8a58` #995: header says it "Keeps lit rain out of temporal reconstruction and composites it at display resolution". Small to moderate port; relevant to DLSS quality in rain.
- **Wetness** [I]: character rain drops `7ae52a554` #604 (`CharacterRainSurfaces.cpp`), simple tree wetness `a50bbf9e0` #614, grass wetness `e14e95123` #470, wall droplets `72441aa92` #1101 (their sync branch drops these for upstream surface rain flow: `1a5c48402`).
- **Snow**: OS Snow Cover `c3e0662e7` #989 and Snow Deformation `de960167d` #1050 with object physics (#1076, #1082-#1084, #1112). Different code from ours (`SnowCover.cpp` 802 lines vs our 1259). Not compared in depth.
- **Water**: same Unified Water layout (`Flowmap`, `WaterCache`). Nothing new found.
- Fur shells for armor with inertia, wetness, touch (#964-#984): outside the listed priorities.

### 2k. Tooling

- **Render target GPU table** `4470b8f95` #932 (`PerformanceOverlay/RenderTargetStats.cpp`, `Utils/GpuTimestamps.h`); **A/B settings compare** `73479337f` #1028 (`ABTesting/ABComparison.*`, `ABCompositorStats.*`, `ABSettingActions.cpp`, `PrerequisiteChain.h`); benchmark repeat `e92a22ff3` #1062; dropdowns can join benchmarks `7fc79c287` #1057. Ours has only `ABTesting.*` + `ABTestAggregator.*`.
- **Screenshot sequences and bursts** `3570cc1f9` #834, `5a89d6e3e` #981, `f028ff6a6` #982 (`src/Features/Screenshot/*`: `SequenceCapture`, `BurstAdapter`, `WorkerThread.h`, AVIF, HDR PNG metadata; doc `docs/development/screenshot-frame-sequences.md`): bounded lossless frame sequences with manifests for temporal comparisons, driven by the devbench `capture` tool's `burst` action. Useful for our shot-set comparisons and for judging NR/FG temporal stability.
- **DevBench tool specs** `src/Features/RemoteControl/ToolSpecs/*.h` (17 headers: Capture, Profiler, NvPerf, Settings, Shadercache, LightHighlight, InspectLlfShadows ...), renderer state notices `e2ef72e6d` #1086 (`Utils/DevBenchNotices.h`), per-feature runtime-only flags (`Feature::GetRuntimeFlags/SetRuntimeFlag`). Their `DevBenchBridge.cpp` is 2163 lines vs our 1600.
- **Shader refactor verification**: `tools/verify-shader-refactor.ps1/.sh` (offline check that a refactor is bytecode-identical), `tools/validate_changed_shaders.py`, `docs/development/shader-runtime-ab.md` + `tools/taa-renderdoc-ab.py` (swap one shader on a captured RenderDoc frame and diff, for refactors that change bytecode).
- **Tests/CI**: `tests/cpp` has about 80 Catch2 files over pure-logic headers, `tests/shaders` HLSL tests, Python tests for build tooling, `tests/test_architecture_lints.py`. Ours has 2 Python tests. The habit worth copying: decision logic in small headers (`Cadence.h`, `DLSSGDynamic.h`, `LODShadowUpdateBudget.h`) testable without the game.
- Scene settings framework doc (`docs/development/scene-settings-framework.md`, 482 lines), Scene Manager restore controls `eb4c9676b` #1100, NR tuning in scene settings `3caae9cb5` #1061. We have Bottled's Scene Manager; not diffed.
- `docs/development/upstream-sync.md`: their process for merging upstream in batches with explicit "re-apply fork divergences" commits; a usable template for our own merges. `docs/development/nsight-perf.md`.

## 3. Other notable things we do not have

- **Fur shell extensions**: we have the base Fur Shells feature (`src/Features/FurShells.cpp`, 1010 lines; theirs 1470 plus `FurShells/{AssetScan,InertiaSpring.h,Interactors}`). OS adds shell fur for armor, inertia, wind thinning, wet fur and touch deformation (#964 #972 #975 #976 #978 #984). Cost not looked at.
- **Foliage Lighting** (`src/Features/FoliageLighting.*`, `09442614a` #453, kevdevrev): "inexpensive transmission and ambient controls for animated foliage" (view-dependent transmission, backside ambient). Upstream later added PBR foliage shading (#2863, in ours), so check overlap before porting.
- **Improved grass transparency** `faa83083e` #754 (`package/Shaders/Common/GrassAlphaCoverage.hlsli`, 51 lines; not present in our `package/Shaders/Common`).
- **SKSE plugin API** (`API.md`, `include/`, `d5ff1571d` #280): other plugins can query Open Shaders at runtime (revision 4). Only matters if we want external tools to talk to the renderer without devbench.
- **Mod conflict handling** `a1a5b4460` #1003 and compat blocks (`dac5f7bff` #1152 blocks `reversed_z.dll`).
- **Shadow caster manager for local lights** (LLF shadow atlas, demand scheduling; `LightLimitFix/Shadow*.cpp`): unchanged assessment from the 11-17 note: very large, interiors/towns only.
- VR-only work (PerfMode render-target shrinking, foveated DLSS/FSR, eye gaze, dynamic near clip) is not applicable to flat screen; PerfMode is still hard-gated to VR per the 11-17 note (not re-checked).

## 4. Looked and found nothing

- Sun shadow cascades: no caster culling beyond #1098 (50 us), no cascade update throttling or caching, no shadow-distance work.
- Occlusion / Hi-Z culling of world geometry or trees: none (their `GrassOptimizations/HiZPyramid.cpp` is the upstream grass one). Tree LOD handling, draw-call merging/instancing, multithreaded or deferred command recording: none.
- Physical sky, atmosphere, volumetric clouds (noise, shadow volumes, temporal reconstruction, multi-scattering, cloud types per weather), aerial perspective, twilight colour: none. OS `dev` does not even carry upstream #3157 yet.
- God rays through clouds or trees beyond the vanilla volumetric light reading the world shadow term: none.
- New tonemappers, exposure methods or an HDR pipeline beyond upstream: none.
- Skin/eyes/hair shading beyond upstream: none (they are behind us on skin).
- Denoisers, SSR: none.
- Texture/geometry streaming, cell-load hitch work, moving engine work off the render thread: none. Stutter work is limited to the shader cache.
- Water rendering beyond upstream Unified Water: none found.
- ML post stages other than NVIDIA NR (Feature 18): none.

## 5. Uncertainty and method notes

- Everything marked "claim" is a number from their commit messages or docs, mostly single runs on VR or the Dragonsreach replay with an RTX 5090. None of it was measured here; nothing was built or run.
- "In ours?" checks were done by reading our working tree in place (grep for identifiers, file presence) and by `git log --grep` for upstream PR numbers in our repo. Subject matching between the two histories undercounts renamed ports and overcounts when Bottled re-implemented something under another title (Scene Manager, Snow Cover/Deformation, Effects11 were not diffed).
- NR: I compared settings and the creation/evaluate parameter writes, not the shaders line by line. Whether our decode already rejects reused taps on luma change, and whether our NR has an actor crop under another name, is unchecked.
- What `DLSSNR.Hint.Render.Preset = 0` selects on a 310.9 runtime is unknown; OS never sends 0 to a 310.9 runtime.
- The 11-17 mass revert of the shader "specialize" series has no stated reason in the revert commits; the replacement branch suggests the permutation count or compile impact was the problem (inferred).
- The clone at `C:\Users\foxnn\dev\_survey\open-shaders` is about 1.1 GB (blobless plus lazily fetched blobs) and has our fork added as remote `ours` (push URL disabled, only `foxnne/nr-pr6` fetched). Do not run `git diff`/`git show` on our commits inside that clone: missing blobs trigger per-object lazy fetches against our repo. Delete the clone when the survey is no longer needed.


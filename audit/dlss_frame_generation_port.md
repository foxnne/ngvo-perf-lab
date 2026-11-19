# DLSS Frame Generation (DLSS-G / MFG) port: scoping study

Date: 2026-11-17. Read-only study of `C:\Users\foxnn\dev\skyrim-community-shaders` (branch `foxnne/nr-pr6`). Nothing was built or run.

Tags used below: **[source]** = read in this repo's working tree or git history. **[docs]** = stated in NVIDIA documentation (mostly the Streamline 2.14.1 guides vendored at `extern/Streamline-DX12/docs/`). **[inferred]** = my reasoning, not stated anywhere I read. **[unverified]** = needs a run to know.

## 0. Verdict

**Feasible: yes, with one qualification.**

- DLSS-G cannot run on the game's D3D11 device. NVIDIA: "DirectX 12 is required for DLSS Frame Generation" (https://developer.nvidia.com/rtx/streamline/get-started). The DLSS-G guide only ever names D3D12 and Vulkan (`ProgrammingGuideDLSS_G.md` sections 2.0 and 3.1), and `ProgrammingGuide.md:132` warns that a feature can be supported on the adapter "but only when using a D3D12 device". **[docs]**
- It can run on a D3D12 device and swap chain that the plugin owns, with the D3D11 frame copied in through shared textures. That is exactly the layout this fork already uses for FSR. NVIDIA does not document this hybrid, so there is no official statement that it is supported. **[inferred]**
- The evidence that it works is code, not documentation:
  - This fork's own history had a complete implementation: added in `3f11431d3` (2026-10-05, "dlss g"), removed in `5969d9c4d` (2026-10-09, "remove dlssg", -1269 lines). The reason for removal is not recorded. **[source]**
  - `openshaders/dev` (remote already configured, tip `5eb8662ec`, 2026-11-17) still carries and maintains the same design, including Dynamic MFG and a fix for judder with Neural Rendering. **[source]**
- I did not run either version, so "it works well on this machine" is **[unverified]**.

The most important consequence: this is a hand-port of existing code onto drifted files, not a from-scratch integration.

## 1. What exists today

### 1.1 Deployed runtime

`C:\Modlists\NGVO 8.0 Beta\mods\Bottled Shaders - foxnne\Shaders\Upscaling\Streamline\` **[source: file versions]**

| File | Version |
|---|---|
| `sl.interposer.dll`, `sl.common.dll`, `sl.dlss.dll`, `sl.reflex.dll`, `sl.pcl.dll` | 2.10.3.0 |
| `nvngx_dlss.dll` | 310.9.16.0 (backup of 310.5.2 alongside) |
| `nvngx_dlssnr.dll` | 310.9.16.0 (backups of 310.8.0 and a 310.9.16 "compat" build alongside) |
| `sl.dlss_g.dll`, `nvngx_dlssg.dll` | **absent** |

- The source headers are Streamline **2.14.1** (`extern/Streamline-DX12/include/sl_version.h`, submodule at `2122257e`). The plugin passes that `kSDKVersion` to a 2.10.3 interposer (`Streamline.cpp:161`). It works today, but headers and DLLs disagree. **[source]**
- A different mod in the same modlist, `SkyrimUpscalerAIOBuild18\UpscalerBasePlugin\Streamline\`, ships `sl.dlss_g.dll` 2.13.0 and `nvngx_dlssg.dll` 310.8.0. I did not check whether that mod is enabled. **[source]**

### 1.2 Streamline initialisation and features

- One Streamline instance, `renderAPI = eD3D11`, `eUseManualHooking` (`Streamline.cpp:135-140`). **[source]**
- Features requested: `kFeatureDLSS`, `kFeatureReflex`, `kFeaturePCL` (`Streamline.cpp:103`). **[source]**
- `kFeatureDLSS_G` is not referenced anywhere in `src`. `sl_dlss_g.h` is not included. **[source]**
- Device binding: `slUpgradeInterface` on the D3D11 device, then `slSetD3DDevice`, `CheckFeatures`, `PostDevice` (`Upscaling.cpp:159-170`). **[source]**

### 1.3 Resource tags and constants

Tags set in `Streamline::EvaluateDLSS` (`Streamline.cpp:520-529`), all D3D11 resources, through the deprecated `slSetTag`: **[source]**

| Tag | Present | Lifecycle |
|---|---|---|
| `kBufferTypeScalingInputColor` / `ScalingOutputColor` | yes | `eOnlyValidNow` |
| `kBufferTypeDepth` | yes | `eValidUntilPresent` |
| `kBufferTypeMotionVectors` | yes | `eValidUntilPresent` |
| `kBufferTypeBiasCurrentColorHint`, `kBufferTypeTransparencyHint` | yes | `eValidUntilPresent` |
| `kBufferTypeHUDLessColor`, `kBufferTypeUIColorAndAlpha` / `UIAlpha`, `kBufferTypeBackbuffer` | **no** | |

Common constants in `Streamline::CheckFrameConstants` (`Streamline.cpp:327-377`): aspect, FOV, near/far, camera basis and position, unjittered `cameraViewToClip`, `depthInverted` from ReverseZ, `jitterOffset`, `mvecScale = {1,1}`, `motionVectorsDilated = false`, `motionVectorsJittered = false`, `reset`. `recalculateCameraMatrices` fills the rest. **[source]**

These are the constants DLSS-G needs. They are currently sent to the D3D11 instance only, and only when DLSS upscaling evaluates.

- One viewport handle `{0}` (`Streamline.h:42`). **[source]**
- Frame tokens come from `slGetNewFrameToken` keyed on `globals::state->frameCount` (`Streamline.cpp:307-325`). **[source]**

### 1.4 D3D12 device, queue and swap chain

- `DX12SwapChain::CreateD3D12Device` calls raw `D3D12CreateDevice` and raw `CreateCommandQueue` (`DX12SwapChain.cpp:18-26`). Not upgraded through Streamline. **[source]**
- The swap chain is created by FidelityFX (`ffx::CreateContextDescFrameGenerationSwapChainForHwndDX12`, `DX12SwapChain.cpp:76-89`). The factory is raw. Buffer count is 2 and `ResizeBuffers` rejects anything else (`DX12SwapChain.cpp:190-193`). **[source]**
- Streamline is deliberately not wrapped around the swap chain; the comment at `Upscaling.cpp:161-166` says the hand-written `DXGISwapChainProxy` must stay outermost so `GetDevice(IID_ID3D11Device)` keeps working for other SKSE plugins. **[source]**
- The game renders into a shared D3D11/D3D12 texture (`swapChainBufferWrapped`), which `DX12SwapChain::Present` copies into the real back buffer (`DX12SwapChain.cpp:249-270`). Depth (R32F) and motion vectors are copied into shared textures by `Upscaling::CopySharedD3D12Resources` (`Upscaling.cpp:1195-1266`). **[source]**
- A UI-only shared texture already exists: `uiBufferWrapped`, R8G8B8A8_UNORM, premultiplied, filled by redirecting the game's UI render target in `HDRDisplay::SetUIBuffer` (`HDRDisplay.cpp:885-915`) and handed to FSR at `FidelityFX.cpp:287-297`. **[source]**

### 1.5 Reflex: what is actually implemented

| Setting | Implemented? | Where |
|---|---|---|
| `reflexLowLatencyMode`, `reflexLowLatencyBoost` | yes, maps to `ReflexMode` | `Streamline.cpp:612-617` |
| `reflexUseFPSLimit` + `reflexFPSLimit` | yes, `frameLimitUs`, clamped 20-240 | `Streamline.cpp:619-627` |
| `reflexUseMarkersToOptimize` | partly | `Streamline.cpp:628`, `498-516` |
| `slReflexSleep` | yes, once per frame from the input-poll hook | `Hooks.cpp:771`, `Streamline.cpp:647` |

Gaps: **[source]**

- The only PCL markers ever sent are `eRenderSubmitStart` / `eRenderSubmitEnd`, and they bracket the DLSS evaluate call only, and only when marker optimisation is on (`Streamline.cpp:538-540`). No simulation start/end, no present start/end, no latency ping.
- **Reflex is forced off whenever the D3D12 proxy is active** (`Streamline.cpp:600-608`). So with frame generation on today, Reflex does nothing, and the Reflex frame limit does nothing.

### 1.6 Neural Rendering interop

- NR creates its **own** D3D12 device and queue (`NeuralRendering/D3D12Interop.cpp:31-36`), separate from the swap-chain D3D12 device. Today the process has three devices: D3D11, D3D12 for presentation, D3D12 for NR. **[source]**
- NR calls NGX directly (`NVSDK_NGX_D3D12_*`, `NeuralRendering/Runtime.cpp:42-46`) with the same project ID as Streamline, because "both use the process-wide core" (`Runtime.cpp:38`). **[source]**
- NR output is copied back to D3D11 and feeds DLSS upscaling (`Upscaling.cpp:1615`, `NeuralRendering::PrepareUpscaleInput`). The final image reaches presentation through the normal D3D11 path, so frame generation already sees post-NR colour. **[source]**

## 2. What is missing: work breakdown

The reference for every item is the fork's own pre-removal tree (`git show 5969d9c4d^:<path>`) and `openshaders/dev`. Files have drifted since the removal: +839 / -655 lines across the eight touched files. **[source]**

| # | Work item | Where | Reference |
|---|---|---|---|
| A | Second Streamline instance in D3D12 mode. Fields `renderAPI`, `pluginDir`, `instanceTag`; features `{DLSS_G, Reflex, PCL}`; `eUseFrameBasedResourceTagging`; a second copy of the interposer loaded from `Shaders\Upscaling\StreamlineDX12\` | `Streamline.h`, `Streamline::LoadInterposer`, `Upscaling::LoadUpscalingSDKs` | pre-removal `Streamline.cpp:95-153`, `Upscaling.cpp:1505-1509` |
| B | Bind the D3D12 device: `slSetD3DDevice(d3d12)`, `CheckFeatures`, `PostDevice`, then `slUpgradeInterface` on the device, bind `slDLSSGSetOptions` / `slDLSSGGetState`, read `numFramesToGenerateMax` | `hk_D3D11CreateDeviceAndSwapChain` (`Upscaling.cpp:134-173`), `Streamline::PostDevice` | pre-removal `Upscaling.cpp:158-205`, `Streamline.cpp:308-340` |
| C | Swap chain through Streamline: upgrade the DXGI factory, plain `CreateSwapChainForHwnd`, 3+ back buffers sized from the max multiplier, no `FRAME_LATENCY_WAITABLE_OBJECT` flag, tearing flag; relax the buffer-count check in `ResizeBuffers` | `DX12SwapChain::CreateSwapChain`, `ResizeBuffers`, `DX12SwapChain.h` (buffer arrays are size 2) | pre-removal `DX12SwapChain::CreateSwapChainDirect` |
| D | Per-frame present path: constants to the D3D12 instance, `slSetTagForFrame` with D3D12 depth / motion vectors / HUD-less / UI, `slDLSSGSetOptions`, `slDLSSGGetState` | `DX12SwapChain::Present` (`DX12SwapChain.cpp:222-302`) | pre-removal `DX12SwapChain.cpp:394-451`, `Streamline::TagDX12Resources`, `ConfigureDLSSG` |
| E | Full Reflex/PCL marker chain on the D3D12 instance (table below); stop forcing Reflex off; Reflex mode at least `eLowLatency` while DLSS-G is on | `Streamline::UpdateReflex`, `Hooks.cpp:771`, `DX12SwapChain::Present` | pre-removal `Streamline.cpp:747-810` |
| F | Skip `Upscaling::FrameLimiter` while DLSS-G is active; move any cap to `ReflexOptions::frameLimitUs` | `Upscaling.cpp:1327` | pre-removal `Upscaling.cpp:1364` |
| G | HUD-less colour buffer (new shared texture, copy before UI) and UI colour+alpha tag | `DX12SwapChain::RecreateWrappedResources`, `MenuManagerDrawInterfaceStartHook` (`Upscaling.cpp:1849`), `HDRDisplay::SetUIBuffer`, `HandleSwapChainPresent` | pre-removal `Upscaling::CaptureHudLessColor`; openshaders `CopyDLSSGInputs` |
| H | Driver-profile helper (`Utils/NvApiDrs.h`, deleted here): clears a "DLSS-G disabled" profile key, detects Smooth Motion | new file | pre-removal `Streamline::EnsureDriverProfileAllowsDLSSG`; openshaders `Utils/NvApiDrs.h` |
| I | Settings, menu, diagnostics: backend choice, multiplier, dynamic target, status readout | `Upscaling.h` settings struct, `DrawSettings`, `PerformanceOverlay.cpp`, `DevBenchBridge.cpp`, translations | pre-removal `Upscaling.cpp:430-520` |
| J | Runtime packaging: stage a `StreamlineDX12` folder with matching-version DLLs | `cmake/`, package folder | openshaders `cmake/Streamline-Runtime.cmake` (pins 2.14.16) |
| K | Input lifetime with NR: wait on `DLSSGState::inputsProcessingCompletionFence` before overwriting shared depth / motion vectors | `Upscaling::CopySharedD3D12Resources`, `DX12SwapChain` | openshaders `DLSSGInputFence.h`, PR #1110 |
| L | Dynamic MFG | `Streamline::ConfigureDLSSG` | openshaders `DLSSGDynamic.h` |

### Marker points (item E)

DLSS-G requires Streamline Reflex, and the present markers must carry the same frame index as the constants (`ProgrammingGuideDLSS_G.md` section 8.0). **[docs]** Where they go in this codebase: **[source for locations, pre-removal code for the pattern]**

| Marker | Hook point |
|---|---|
| `slReflexSleep`, then `eSimulationStart` | `BSInputDeviceManager_PollInputDevices::thunk` (`Hooks.cpp:765-771`), already the sleep site |
| `eSimulationEnd`, `eRenderSubmitStart` | start of `DX12SwapChain::Present`, after the D3D11 to D3D12 fence wait. A truer render-start would be the first render hook of the frame; `Main_Update` (`Hooks.cpp:1125`) bounds the whole frame |
| `eRenderSubmitEnd`, `ePresentStart` | after `ExecuteCommandLists`, before `swapChain->Present` (`DX12SwapChain.cpp:277-280`) |
| `ePresentEnd` | right after `swapChain->Present` returns |
| `ePCLatencyPing` | not implemented anywhere; optional, needs a window-message hook |

The pre-removal code fetched the D3D12 frame token as `frameCount + 1` at the sleep site (`Streamline.cpp:796`). That index bookkeeping is fragile and is the usual cause of the "common constants cannot be found for frame N" warning. **[inferred]**

### Options, buffers, formats

- `sl::DLSSGOptions`: `mode` (`eOff` / `eOn` / `eAuto` / `eDynamic`), `numFramesToGenerate` (1 = 2x, 3 = 4x, bounded by `DLSSGState::numFramesToGenerateMax`), `flags` (`eRetainResourcesWhenOff`, `eDynamicResolutionEnabled`, `eEnableFullscreenMenuDetection`), `enableUserInterfaceRecomposition`, `dynamicTargetFrameRate` (`sl_dlss_g.h`, struct version 5). **[docs]**
- Required inputs: back buffer (taken from the wrapped swap chain), depth, motion vectors. Strongly recommended: HUD-less plus UI alpha or UI colour+alpha, both the size of the back buffer (section 5.1). **[docs]**
- Depth and motion vectors may be render resolution with extents; the pre-removal code tagged them with the render extent. With fixed-ratio DLSS do **not** set the dynamic-resolution flag (section 10.0). **[docs]**
- HDR: back buffer must be R10G10B10A2 with HDR10 colour space (already the case, `DX12SwapChain.cpp:43`). The UI colour+alpha buffer must not be R10G10B10A2 because its alpha is too coarse (section 11.0). `uiBufferWrapped` is R8G8B8A8, which is fine. **[docs + source]**
- UI must satisfy `Final = UI.rgb + (1 - UI.a) * Hudless.rgb`, premultiplied, and HUD-less must be in the same colour space as the back buffer (section 5.1 table). **[docs]** With HDR on, this fork PQ-scales the UI and composites it in `HDROutputCS`, so that identity may not hold. The pre-removal code simply disabled HUD-less capture when HDR Display was loaded. **[source]** This is the hard part of the UI stage.
- Menus: turn DLSS-G off in full-screen menus with `eRetainResourcesWhenOff` to avoid a stutter on resume (section 6.4). The existing `ShouldPrepareFrameGeneration` menu logic (`Upscaling.cpp:1436`) maps directly onto this. **[docs + source]**
- Resizes and fullscreen switches: DLSS-G must be off during them or Present can deadlock (section 12.0). **[docs]**

### DLLs, versions, driver, OS

- Needed in the D3D12 instance's folder: `sl.interposer.dll`, `sl.common.dll`, `sl.dlss_g.dll`, `sl.reflex.dll`, `sl.pcl.dll`, `nvngx_dlssg.dll`. `sl.dlss_g.dll` is binary-only, from the Streamline SDK release archive (`README.md:9`). **[docs]**
- Multi Frame Generation arrived in Streamline 2.7.2 (`changelog.txt:461`). The deployed 2.10.3 is new enough for fixed 3x/4x. Dynamic MFG, UI recomposition and VSync-with-FG arrived in 2.11.0; many DLSS-G pacing fixes are in 2.12 and 2.14. **[docs]**
- Recommendation: use one matching 2.14.x set for the D3D12 folder (headers are already 2.14.1). Mixing a 2.13 `sl.dlss_g.dll` with 2.10.3 common/interposer is not something the docs endorse. **[inferred]**
- Driver: Dynamic MFG needs 595.41 or newer (section 6.3). **[docs]** Windows reports driver `32.0.16.1692`, which reads as 616.92. **[source for the string, inferred for the mapping]**
- OS: Windows 10 20H1 or newer and **Hardware-accelerated GPU Scheduling must be on** (section 1.0). **[docs]**
- **Check before starting:** the registry value `HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\HwSchMode` reads `1` on this machine. `2` is on, `1` is off. If that reading is right, DLSS-G will refuse to load until HAGS is enabled in Settings > Display > Graphics and the machine is rebooted. Confirm in the Settings UI. **[source for the value, inferred for its meaning]**
- Cost on an RTX 5080: about 2.0 ms for 2x and 3.6 ms for 4x at 1440p; about 489 MB VRAM at 1440p, more at 3440x1440 (section 1.1). **[docs]** Earlier notes say this modlist is already near the VRAM limit.

## 3. Frame pacing compared with FSR + the custom limiter

Today (FSR): **[source]**

- `DX12SwapChain::Present` calls `Upscaling::FrameLimiter` after every present when the game's sync interval is 0 (`DX12SwapChain.cpp:295`).
- `FrameLimiter` first blocks on the swap chain's frame-latency waitable object (`Upscaling.cpp:1332-1340`), then sleeps to a fixed cadence of `refreshRate * 0.5` when `frameLimitMode` is on (`Upscaling.cpp:1342-1362`).
- So real frames are capped at half the refresh rate on a fixed schedule. A cheaper alternate NR frame cannot start earlier; the limiter absorbs it. That matches the observed symptom.

With DLSS-G: **[docs unless marked]**

- Presentation becomes asynchronous. The "SL pacer" owns the real swap chain and schedules real and generated frames; the host's `Present` returns in about 0.2 ms instead of blocking (section 13.0).
- Streamline's internal swap chain always uses the frame-latency waitable object. If the app did not request that flag, the app **must not** call `GetFrameLatencyWaitableObject` or `SetMaximumFrameLatency`; doing so competes with the pacer for signals (section 12.1). The pre-removal code comment records the practical effect: "the SL pacer drop[s] every interpolated frame". **[docs + source]**
- So the custom limiter must be skipped entirely. The documented replacement is `slReflexSleep` for frame start and `ReflexOptions::frameLimitUs` for a fixed cap (section 12.1).
- Dynamic MFG "is designed to work with the Reflex frame rate limiter"; other limiters "may not work or may produce unexpected results" (section 6.3).

Would alternating NR load still be a problem?

- The specific mechanism (limiter wait swallowing the fast frames) goes away, because the limiter is gone and Present no longer blocks. **[inferred from docs]**
- The docs say nothing about how the pacer behaves when real frame times alternate short/long. Generated frames are placed between two real frames, so an alternating cadence may show as uneven motion. **[unverified]**
- If a Reflex frame limit, G-SYNC cap or VSync is the binding constraint, the saving is again absorbed, by design. The saving only shows as higher output when the GPU is the limit. **[inferred]**
- openshaders PR #1110 exists specifically because NR plus DLSS-G juddered until inputs were protected by the DLSS-G input fence. Expect to need item K. **[source]**
- Measure with FrameView's `MsBetweenDisplayChange`; `MsBetweenPresents` is misleading under DLSS-G (section 13.1). **[docs]**

## 4. Interaction with Neural Rendering and DLSS upscaling

- **Ordering is already right.** NR runs before DLSS upscaling; frame generation consumes the final back buffer after tonemap/HDR. No reordering is needed. **[source]**
- **Devices.** DLSS upscaling stays on the D3D11 Streamline instance. DLSS-G would sit on the presentation D3D12 device. NR stays on its own third D3D12 device. Nothing forces a merge. **[source + inferred]**
- **NGX sharing is the open question.** NR initialises NGX directly on its own device. A D3D12 Streamline instance would initialise NGX again for DLSS-G on a different D3D12 device in the same process, alongside the D3D11 instance's NGX use for DLSS. The pre-removal DLSS-G code in this fork never coexisted with NR (`src/Features/NeuralRendering*` did not exist at `5969d9c4d^`). openshaders runs both, but its NR code differs from this fork's. **[source for the facts; whether this fork's NR survives it is unverified]**
- **Two interposers.** Running two Streamline instances means loading `sl.interposer.dll` twice from two folders. Streamline's docs do not describe or bless this. It is the design both prior implementations used. **[source + inferred]**
- **Shared inputs.** DLSS-G reads the tagged depth and motion vectors during the asynchronous present, after the game has started the next frame. Section 15.1 says the host must wait on `inputsProcessingCompletionFence` before modifying inputs from another queue. This fork writes them from D3D11, so the wait applies. NR's alternate-frame mode changes when those buffers are rewritten, which is where the judder came from upstream. **[docs + source + inferred]**
- **GPU contention.** NR on a separate queue and DLSS-G's own queue both compete with the D3D11 frame. `eBlockNoClientQueues` is Vulkan-only, so there is no parallelism lever on D3D12. **[docs]**

## 5. Risks, unknowns and staged plan

### Risks, highest first

1. **Why it was removed.** Bottled deleted a working-looking implementation after four days with no explanation. It may have been quality, crashes, or just maintenance. Ask or diff before investing. **[source]**
2. **HAGS appears to be off** on this machine (see section 2). Cheap to check, blocks everything if true.
3. **NGX/Streamline coexistence with this fork's NR** (three devices, two interposers, direct NGX). Could be a non-issue or a crash at device creation. **[unverified]**
4. **Frame-index and marker synchronisation** between the sleep site, constants and present. Wrong here means DLSS-G silently presents no generated frames. **[inferred]**
5. **HDR UI composition** not matching the required blend identity; HUD-less in PQ space. **[inferred]**
6. **Drift.** The eight files changed by +839 / -655 lines since the removal; `HDRDisplay::HandleSwapChainPresent` and the present hooks were reworked. A mechanical revert will not apply.
7. **Alternate-frame NR cadence under the SL pacer.** **[unverified]**
8. **VRAM**: roughly +0.5 GB on a setup already near the limit.
9. **Other SKSE plugins and overlays** that call `GetDevice` or hook Present on the swap chain. The fork's own proxy stays outermost, which is what protected them before. **[source]**
10. **Hair slivers may persist**: DLSS-G consumes the same undilated depth and motion vectors (see section 6).

### Staged plan

Sizes: small = about a day, medium = several days, large = a week or more. These assume hand-porting from the two references.

| Stage | Content | Size | Main files | What it proves |
|---|---|---|---|---|
| Pre | Confirm HAGS; find out why DLSS-G was removed; read `5969d9c4d` and openshaders PRs #445, #864, #1110 | small | none | Whether to proceed |
| 0 | D3D12 Streamline instance with Reflex + PCL only (items A, B without DLSS-G, E, J). FSR stays the generator. | small-medium | `Streamline.cpp/.h`, `Upscaling.cpp`, `Hooks.cpp`, `DX12SwapChain.cpp`, cmake | Two instances load next to NR without crashing; Streamline log shows markers; `slReflexGetState` and the NVIDIA overlay show latency stats. Whether Reflex pacing is healthy with FSR's own swap chain in the way is uncertain. |
| 1 | DLSS-G 2x with existing depth / motion vectors and the back buffer as HUD-less (items B, C, D, F, H, I minimal) | medium | `DX12SwapChain.cpp/.h`, `Streamline.cpp/.h`, `Upscaling.cpp/.h`, `Utils/NvApiDrs.h` | `DLSSGState::status == eOk`, `numFramesActuallyPresented == 2`, FrameView display cadence. Problem (1) can be measured here. |
| 2 | HUD-less capture and UI colour+alpha, UI recomposition, SDR first then HDR (item G) | medium; HDR part may be large | `HDRDisplay.cpp`, `Upscaling.cpp`, `DX12SwapChain.cpp`, HDR output shader | HUD and subtitles stable on generated frames in SDR and HDR. |
| 3 | Fixed 3x/4x, then Dynamic MFG with the Reflex limiter (items I, L) | small, plus small-medium for dynamic | `Streamline.cpp`, `Upscaling.cpp`, `DLSSGDynamic.h` | `numFramesToGenerateMax` on the 5080; `bIsDynamicMFGSupported`; output tracks the target rate. |
| 4 | NR hardening: input fence, alternate-frame cadence (item K) | medium | `DX12SwapChain.cpp`, `Upscaling.cpp`, `DLSSGInputFence.h` | No judder with NR on, with and without alternate frames. |

Total: roughly two to three weeks if nothing in the risk list bites.

Where this could be badly wrong:

- If the removal reason was a fundamental quality or stability problem on this renderer, no stage estimate holds.
- If this fork's NR cannot share the process with a D3D12 Streamline instance, stage 0 becomes large (moving NR onto the presentation device, or DLSS-G off Streamline is not possible since `sl.dlss_g` is the only route).
- HDR UI could need a rewrite of how the UI is encoded, not a tweak.
- Stage 0 with FSR still owning the swap chain may not be meaningful; it may have to be folded into stage 1.

## 6. The cheaper alternative: keep FSR and fix two things

(a) Frame-limiter wait: stop waiting on the frame-latency waitable object and/or stop pacing to a fixed half-refresh cadence when FSR is generating (`Upscaling.cpp:1327-1362`). Small. Caveat: FSR's swap chain does its own pacing, so the saving may still be absorbed there. **[inferred]**

(b) FG-specific depth for hair: in `Upscaling::CopySharedD3D12Resources`, write a dilated/nearest depth at hair-category pixels (already scoped as P1 in `frame_generation_inputs.md`). Small to medium.

| Problem | FSR + fixes (a), (b) | DLSS-G port |
|---|---|---|
| 1. Alternate-frame NR saving disappears | (a) targets it directly; may be only partly effective | The limiter is removed by necessity, so the known cause goes away. Cadence under the SL pacer is unverified; needs the input fence. |
| 2. Hair-edge slivers | (b) targets the suspected cause directly | Not fixed by the port itself. DLSS-G reads the same depth and motion vectors, so (b) is needed either way if the diagnosis is right. DLSS-G's model may hide it better; unverified. |
| 3. UI updates at real frame rate only | Not addressed | Partly. No interpolation method produces new UI states; UI recomposition interpolates UI motion separately and stops HUD distortion. HDR makes this the hardest stage. |
| Extra | None | Reflex latency reduction (currently disabled with FG on), 3x/4x and Dynamic MFG, better generated-frame quality on NVIDIA hardware |
| Cost | Days | Two to three weeks plus real risk |

Suggested order: do (a) and (b) first. They are cheap, (b) is required for DLSS-G too, and (a) tells you how much of problem 1 is the limiter. Run the "Pre" checks in parallel. Commit to the port only if you want MFG or Reflex, or if (a) fails to recover the NR saving.

## Sources

- `extern/Streamline-DX12/docs/ProgrammingGuideDLSS_G.md`, `ProgrammingGuide.md`, `ProgrammingGuideReflex.md`, `ProgrammingGuidePCL.md`, `ProgrammingGuideManualHooking.md`, `changelog.txt`, `README.md`, `include/sl_dlss_g.h` (Streamline 2.14.1)
- https://developer.nvidia.com/rtx/streamline/get-started ("DirectX 12 is required for DLSS Frame Generation")
- https://github.com/NVIDIA-RTX/Streamline
- Git history of this repo: `375696e5e`, `961463d67`, `3f11431d3`, `5969d9c4d`; remote branch `openshaders/dev` at `5eb8662ec`
- Earlier notes: `audit/frame_generation_inputs.md`, `audit/open_shaders.md`

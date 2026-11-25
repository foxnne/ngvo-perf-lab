# DXVK / Vulkan backend feasibility study for NGVO (2026-11-24)

Scope: web research + read-only reading of the CS fork (branch foxnne/merge-rc2-1123). Nothing was
downloaded, installed, run or changed. Labels used: **[measured]** = published number,
**[maintainer]** = statement by a project maintainer, **[source]** = read in source code,
**[inference]** = my reasoning, not tested, **[anecdote]** = forum claim.

## Verdict

**Not viable for the real setup; at most a low-value diagnostic.**

1. The best available evidence is directly on point and negative: in Sept 2026 doodlum (Community
   Shaders author) tested DXVK on Windows with Skyrim SE on an RTX 4080 and filed DXVK issue #5885
   reporting a "30% performance hit" versus native D3D11. The DXVK maintainer replied that "DXVK is
   significantly slower than Nvidia's driver when CPU-bound". The fix that followed (DXVK 3.1.1,
   cached dynamic resources on by default for Skyrim SE) recovered 147.4 -> 180.3 fps inside DXVK, at
   a maintainer-estimated 5-10 % GPU-bound cost; no figure shows DXVK beating NVIDIA's native D3D11.
2. The fork's frame generation and DLSS NR both create shared textures on the D3D11 device and open
   them on a real D3D12 device. Under DXVK on Windows that is the one direction of sharing the
   author of DXVK's shared-resource code says does not work (create+export; import "should").
3. DLSS SR, Reflex and PCL through Streamline on a D3D11 device rely on NVIDIA's D3D11 driver /
   NVAPI. DXVK's vendor-extension path needs dxvk-nvapi, whose README says "Usage on Windows is
   discouraged"; DXVK release notes say vendor extensions do "not work on Windows".
4. The heavy village view is GPU-bound (94-98 %); DXVK can only cost there.

So the realistic DXVK configuration is: no FG, no NR, probably no DLSS, no Reflex, and slower or equal
CPU-side. That is not the user's game.

## 1. DXVK on Windows + Skyrim SE, 2025-2026

- DXVK current: v3.1.1 (15 Sep 2026); 3.0 (Jun 2026) needs Vulkan 1.4, new dxbc-spirv compiler,
  descriptor heaps (NVIDIA driver >= 595.84). https://github.com/doitsujin/dxvk/releases
- Windows is officially unsupported: "may generally work"; overlays, RTSS, OBS and "some mods" can
  interfere; vendor libraries (NVAPI/AGS) "may crash or fail" on non-native D3D11 resources; games
  using both D3D11 and D3D12 need vkd3d-proton next to DXVK. https://github.com/doitsujin/dxvk/wiki/Windows
- Issue #5885 "Skyrim Special Edition performance hit (Windows, DX11)", opened by doodlum 7 Sep 2026,
  RTX 4080. https://github.com/doitsujin/dxvk/issues/5885
  - [anecdote/measured by reporter] 30 % hit vs native; no native baseline number published.
  - [measured] inside DXVK: default 147.4 fps, cachedDynamicResources "c" 160.4, "a" 180.3.
  - [maintainer] "DXVK is significantly slower than Nvidia's driver when CPU-bound and
    catastrophically slow on AMD's Vulkan driver when GPU-bound"; cached buffers trade
    "~5-10% GPU perf" for CPU perf.
  - doodlum: ~20k constant-buffer maps per frame; "A lot of CPU time lives in the Nvidia driver";
    said he would raise it with NVIDIA.
  - Second reporter (RTX 3060) had 30-40 fps under DXVK with GPU headroom; native D3D11 fine.
  - Press summary: https://www.pcgameshardware.de/Linux-Software-26761/News/DXVK-3-1-1-Skyrim-SE-Rayman-3-Fixes-1554384/
- Older positive reports are for Skyrim LE (D3D9) or AMD/Intel GPUs, i.e. replacing a weak driver;
  [anecdote] Nexus wrapper guide for SSE says it "may work nice for some or does not change
  performance for others" (nexusmods SSE 48566). No published NVIDIA-on-Windows SSE win found.
- Shader stutter: DXVK uses graphics pipeline library (dxvk.enableGraphicsPipelineLibrary = Auto)
  so first-use hitching is small, but CS already precompiles its DXBC to disk; D3D11 on NVIDIA has
  no pipeline-link stutter problem to fix here. [inference]
- Memory: DXVK 2.7+ enforces the driver VRAM budget on discrete GPUs and evicts unused resources to
  system memory; "Temporary slowdowns and stutters are still expected when exceeding VRAM capacity".
  On Windows this sits on top of WDDM's own VidMM. No measurement vs NVIDIA D3D11 found.
  https://github.com/doitsujin/dxvk/releases/tag/v2.7

## 2. Community Shaders and DXVK

- No official support statement found in the CS repo/wiki/FAQ or the Open Shaders FAQ
  (https://github.com/alandtse/open-shaders/wiki/FAQ); neither mentions DXVK/Vulkan/Proton.
- CS runs under DXVK on Linux in practice (it is D3D11 FL 11_1, compute + UAVs, which DXVK covers);
  the #5885 report shows upstream CS's author running Skyrim on DXVK/Windows himself.
- No specific failing CS feature (typed UAV loads, Hi-Z, texture arrays) documented. Unverified.
- The fork source has no DXVK/Wine handling at all (grep of src/: zero hits).

## 3. NVIDIA stack and the fork's interop (the crux)

Read: src/Features/Upscaling.cpp (device-creation hook), Upscaling/DX12SwapChain.cpp,
Upscaling/Streamline.cpp, NeuralRendering/D3D12Interop.cpp, NeuralRendering/Runtime.cpp.

| Dependency in the fork | Where | Under DXVK on Windows |
|---|---|---|
| IAT hook of `d3d11.dll!D3D11CreateDeviceAndSwapChain`; FG path calls `D3D11CreateDevice` | Upscaling.cpp:71-203, :609 | Works with any DLL named d3d11.dll [inference] |
| QI `ID3D11Device5`, `ID3D11DeviceContext4` (Signal/Wait) | DX12SwapChain.cpp:153-161; D3D12Interop.cpp:27-30 | DXVK implements D3D11.4 device/context and ID3D11Fence [source: d3d11_fence.cpp] |
| `D3D12CreateDevice(adapter, FL12_0)` with the game's IDXGIAdapter | DX12SwapChain.cpp:18; D3D12Interop.cpp:31 | With DXVK's dxgi.dll the adapter is a DXVK object; Microsoft d3d12.dll is expected to reject it [inference]. With DXVK d3d11.dll only + system DXGI, DXVK finds its adapter by LUID [source: d3d11_main.cpp] and D3D12 gets a real adapter, but then the non-FG `CreateDeviceAndSwapChain` path cannot make a native DXGI swap chain on a DXVK device |
| D3D12 shared fence -> `ID3D11Device5::OpenSharedFence` | DX12SwapChain.cpp:108-110; D3D12Interop.cpp:49-54; FidelityFX RuntimeUpscaler.cpp:884-886 | DXVK imports as VK D3D11/D3D12 fence semaphore; plausible on NVIDIA's Windows Vulkan driver. Untested |
| **D3D11 `CreateTexture2D(SHARED \| SHARED_NTHANDLE)` -> `IDXGIResource1::CreateSharedHandle` -> `ID3D12Device::OpenSharedHandle`** | DX12SwapChain.cpp:321-335 (swap-chain copy, UI, depth, motion vectors); D3D12Interop.cpp:102-125 ("D3D11First") | **Expected to fail.** DXVK PR #5257 author: on Windows "creating and exporting resources would not work, but importing should"; export needs a Wine-only D3DKMTEscape (NVIDIA "may" produce a descriptor - unconfirmed) |
| FG proxy swap chain (FidelityFX DX12 FG swap chain / DLSS-G on a D3D12 queue), `DXGISwapChainProxy` returned to the game | DX12SwapChain.cpp:35-103, 407+ | Native D3D12, fine in itself, but fed only by the shared textures above. Failures are `DX::ThrowIfFailed` => crash at startup if FG is enabled |
| Streamline `slUpgradeInterface` / `slSetD3DDevice` on the D3D11 device; DLSS SR via `slEvaluateFeature` on the D3D11 context; Reflex + PCL | Upscaling.cpp:159-200, 1483-1495; Streamline.cpp:103, 207-287, 539 | Needs NVIDIA D3D11 driver internals/NVAPI. On Linux that is dxvk-nvapi + CUDA interop; dxvk-nvapi: "Usage on Windows is discouraged". Expect DLSS/Reflex reported unavailable or a crash. Untested |
| NGX DLSS NR via `NVSDK_NGX_D3D12_Init_Ext` / `_EvaluateFeature` on the interop D3D12 device | Runtime.cpp:42-44, 449-530 | Native D3D12; blocked only by the shared-texture export. Fails soft (RecordFailure) |
| `IDXGIAdapter3::QueryVideoMemoryInfo` | VramTracker.cpp, PerformanceOverlay.cpp:598 | Implemented by DXVK (reports the Vulkan budget) |
| D3D11On12, keyed mutexes | not used by the fork | n/a (DXVK's ID3D11On12Device1 only pairs with vkd3d-proton) |

Could it be made to work? Reversing the sharing direction (create on D3D12, `OpenSharedResource1` in
DXVK) is the direction the PR author says "should" work on Windows, and the fork's comment shows it
once did it that way. That is real engineering on an unsupported platform, for a backend that is
measured slower. Replacing d3d12.dll with vkd3d-proton as well would make interop DXVK<->vkd3d but
then DLSS FG/NR/Streamline lose the native D3D12 they need. Not recommended.

Sources: https://github.com/doitsujin/dxvk/pull/5257 , https://github.com/jp7677/dxvk-nvapi ,
https://github.com/doitsujin/dxvk/releases/tag/v2.6 , DXVK src/d3d11/d3d11_fence.cpp, d3d11_main.cpp.

## 4. Other breakage risks

- DXVK wiki names overlays/hook software and "some mods" as interference sources on Windows.
- ImGui D3D11 backends (CS menu, SKSE Menu Framework, Apocrypha) are plain D3D11 and normally fine.
- Hitch Hunter wraps the D3D11 device: unknown; switch off for a trial.
- SSE Display Tweaks: flip-model/tearing/latency settings act on DXGI swap-chain flags that DXVK
  largely ignores or maps to Vulkan present modes; frame limiter still works. Unverified.
- MO2/usvfs: DXVK DLLs must sit beside SkyrimSE.exe (`Stock Game`), which is outside the VFS; no
  existing d3d11.dll/dxgi.dll proxy is present there today (checked). No conflict expected.
- Sunshine: captures the desktop/DXGI output, should be unaffected; NVENC + Vulkan share VRAM.
- HDR: DXVK supports HDR10 swap chains (dxgi.enableHDR); user is SDR. Exclusive fullscreen is
  blocked by default (dxvk.allowFse = False); borderless is the supported mode.

## 5. What a Vulkan backend would actually buy here

| Their cost | Driver/translation-bound? | Expected under DXVK |
|---|---|---|
| Village: 27 ms, GPU 94-98 % | No (shading, NR, deferred passes) | Worse: 5-10 % GPU-bound penalty with cached dynamic resources [maintainer] |
| 8-12k draws, 11-14 ms CPU submission | Partly: game traversal + CS per-draw hooks + ~20k CB maps + driver | DXVK moves translation to its CS thread, but maintainer and doodlum's test say NVIDIA native is faster when CPU-bound |
| Plains, CPU-bound | Same as above | Same; this is the only view where a test says anything |
| 1.1-1.6 GB VB/IB creation per cell crossing | Mostly engine + upload | DXVK initialises resources on an async transfer queue (2.6); could smooth or not. Unmeasured |
| VRAM 12-14.7/16 GB, overcommit collapse | Allocation policy | DXVK budget enforcement + eviction is a different policy, but DXVK adds its own overhead and the D3D12 side would not exist. Unmeasured |
| DLSS NR, FG | No | Lost |

Useful DXVK knobs if anyone does test: `d3d11.cachedDynamicResources = a` (default for Skyrim SE in
3.1.1), `dxvk.enableGraphicsPipelineLibrary`, `dxvk.maxMemoryBudget`, `dxgi.maxDeviceMemory`,
`dxvk.numCompilerThreads`, and `dxvk.hud = fps,frametimes,drawcalls,submissions,pipelines,memory,allocations,gpuload,cs,compiler`
(the `cs` item shows how much work is queued to DXVK's command-stream thread; `drawcalls`,
`memory` and `allocations` are an independent cross-check of the harness numbers).

The more promising lead from #5885 is native: the CPU time is in NVIDIA's D3D11 driver handling
constant-buffer map/discard churn. Cutting CB updates per draw in the fork (or batching them) attacks
the same cost without leaving D3D11.

## 6. Alternatives

- "RAW": a GitHub project HarperZ9/RAW describes itself as "a D3D11 proxy for Skyrim SE", not a
  Vulkan/D3D12 renderer; native renderer is stated direction only. Nexus page 200344 returned 403,
  so the link between the two is unverified. https://github.com/HarperZ9/RAW
- No native Vulkan or D3D12 renderer replacement for Skyrim SE found. PIXL / Open Shaders are D3D11.
- Nothing found that moves the game's submission onto D3D11 deferred contexts; the engine renders
  on one immediate context. NVIDIA's D3D11 driver already threads internally. [inference]

## 7. Minimal reversible trial (only if curiosity outweighs the evidence)

Informative question: "is draw submission cheaper under DXVK in a CPU-bound plains view, like for
like?" It cannot test the real configuration.

1. Baseline first, native D3D11, same reduced features on both sides: frame generation OFF, DLSS NR
   OFF, upscaler = TAA/none (DLSS is expected unavailable under DXVK), Reflex OFF, Hitch Hunter
   disabled, SSE Display Tweaks borderless with no tearing overrides. Record plains + village +
   one flybench cell-crossing run: frame time, draw-call CPU time, GPU %, VRAM.
   Frame generation must be off before the DXVK launch or device creation will throw.
2. With MO2 and the game closed, place DXVK 3.1.1 x64 `d3d11.dll` + `dxgi.dll` in
   `C:\Modlists\NGVO 8.0 Beta\Stock Game\` beside SkyrimSE.exe (not in a mod/Data), plus a
   `dxvk.conf` there with the `dxvk.hud` line above. No existing file is overwritten.
3. Launch through MO2 as usual. Confirm the HUD shows; discard the first run (pipeline warm-up).
   Repeat the three captures. Read `SkyrimSE_d3d11.log` / `_dxgi.log` beside the exe for errors.
4. Back out: delete d3d11.dll, dxgi.dll, dxvk.conf, the two `SkyrimSE_*.log` files and any
   `*.dxvk-cache` in `Stock Game`; re-enable Hitch Hunter, FG, NR, DLSS, Reflex.

Pass criterion to even discuss further work: >= 20 % lower draw-submission CPU time in the plains
view. Expected result on the evidence: equal or worse.

## Not verified

- No hands-on test; all DXVK-on-Windows behaviour is from docs, source and issue threads.
- Whether Microsoft's D3D12CreateDevice accepts a DXVK adapter; whether NVIDIA's Windows Vulkan
  driver exports D3D11-openable texture handles; whether Streamline/NGX D3D11 initialises on a DXVK
  device on Windows.
- Native-vs-DXVK numbers for #5885 (only the 30 % claim and in-DXVK numbers are published).
- Nexus 200344 page content; CS Discord discussions; any r/skyrimmods 2026 threads (search returned none).
- Hitch Hunter, SSE Display Tweaks, Sunshine behaviour under DXVK.

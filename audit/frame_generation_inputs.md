# Frame generation input audit: sky-coloured sliver on hair edges

Scope: read-only audit of `C:\Users\foxnn\dev\skyrim-community-shaders` (branch `foxnne/nr-pr6`, HEAD `5451c7e0a`), the deployed mod `C:\Modlists\NGVO 8.0 Beta\mods\Bottled Shaders - foxnne`, and the last `BottledShaders.log`. Nothing was built or run. Paths below are relative to the repo unless absolute.

## Summary

- No convention mismatch was found in the values handed to FSR frame generation for the current configuration (Reverse-Z on, DLSS Quality, 3440x1440, HDR off). Depth inversion, motion vector scale, sign, resolution, jitter and frame pairing are all consistent with the SDK headers and with the DLSS path.
- The most likely cause is in the content of the inputs, not the parameters: the alpha-blended (forward) hair layer writes a full-strength motion vector but its presence in depth depends on the mesh's z-write flag. Where it is absent from depth, FSR sees the hair fringe as far-plane background and lets the fast-moving sky win.
- The fork exposes none of the FSR debug views, so this cannot be confirmed from code. Adding the debug-view flag is a few lines and is the first step.

## 1. What is passed to FSR frame generation

API: FidelityFX "ffx_api" DX12 (`include/FidelityFX/framegeneration/include/ffx_framegeneration.h`, header version 4.0.1), loaded through `amd_fidelityfx_loader_dx12.dll`. Structs used: `ffxCreateContextDescFrameGenerationSwapChainForHwndDX12`, `ffxCreateContextDescFrameGeneration` + `ffxCreateBackendDX12Desc`, `ffxConfigureDescFrameGeneration`, `ffxConfigureDescFrameGenerationSwapChainRegisterUiResourceDX12`, `ffxDispatchDescFrameGenerationPrepare` + linked `ffxDispatchDescFrameGenerationPrepareCameraInfo`, and `ffxDispatchDescFrameGeneration` (filled by the SDK, patched in the callback).

### Context creation (`src/Features/Upscaling/FidelityFX.cpp:164-181`, called once from `DX12SwapChain.cpp:102`)

| Field | Value | Line |
|---|---|---|
| `displaySize` | swap chain size (3440x1440) | 169 |
| `maxRenderSize` | = displaySize | 170 |
| `flags` | `ENABLE_ASYNC_WORKLOAD_SUPPORT`, plus `ENABLE_DEPTH_INVERTED` if `reverseZ.IsActive()` | 171-173 |
| not set | `DEPTH_INFINITE`, `HIGH_DYNAMIC_RANGE`, `DISPLAY_RESOLUTION_MOTION_VECTORS`, `MOTION_VECTORS_JITTER_CANCELLATION`, `DEBUG_CHECKING` | - |
| `backBufferFormat` | R10G10B10A2_UNORM (negotiated, `DX12SwapChain.cpp:43-69`) | 174 |

Swap chain: 2 buffers, proxy D3D12 swap chain created by FFX (`DX12SwapChain.cpp:66-89`). Colour space SDR sRGB (log line 379).

### Configure, every present (`FidelityFX.cpp:218-283`)

| Field | Value | Line |
|---|---|---|
| `frameGenerationEnabled` | `frameGenerationPrepared` (true only if depth/MV were copied this frame) | 221, `Upscaling.cpp:1874` |
| `frameGenerationCallback` | lambda: sets `backbufferTransferFunction` = SRGB (PQ + `minMaxLuminance` when HDR), sets `reset` if `needsReset`, then `ffxModule.Dispatch` | 223-241 |
| `presentCallback` | null | 254 |
| `HUDLessColor` | empty | 252 |
| `frameID` | static counter, +1 per present, +2 on reset | 257-266, 360 |
| `onlyPresentGenerated` | false | 268 |
| `flags` | 0 (no debug view, tear lines, reset indicators, pacing lines) | 269 |
| `allowAsyncWorkloads` | true | 270 |
| `generationRect` | full back buffer (0,0,W,H) | 274-277 |

UI: `uiBufferWrapped` (R8G8B8A8_UNORM, display size) registered with `USE_PREMUL_ALPHA | ENABLE_INTERNAL_UI_DOUBLE_BUFFERING` (`FidelityFX.cpp:287-292`). With FG active the vanilla UI is routed to that buffer, so the colour FSR interpolates is HUD-less.

### Prepare dispatch (`FidelityFX.cpp:305-357`)

| Field | Value | Line |
|---|---|---|
| `commandList` | proxy swap chain's per-frame list, executed before `Present` | 308, `DX12SwapChain.cpp:272-280` |
| `renderSize` | screen x `resolutionScale` = 2293x960 (float32 round trip checked, no off-by-one at this resolution) | 272, 312-313 |
| `motionVectorScale` | (renderW, renderH) | 310-311 |
| `jitterOffset` | (-jitter.x, -jitter.y), render pixels | 315-316 |
| `frameTimeDelta` | `RE::GetSecondsSinceLastFrame() * 1000` | 318 |
| `cameraNear` / `cameraFar` | game globals, not swapped | 320-321 |
| `cameraFovAngleVertical` | derived from the world FOV setting and screen aspect (`src/Utils/Game.cpp:227-235`) | 323 |
| `viewSpaceToMetersFactor` | 0.01428222656 | 324 |
| `depth` | `depthBufferShared12`, R32_FLOAT, allocated at kMAIN (display) size, content in the top-left 2293x960 | 328, `DX12SwapChain.cpp:550-554` |
| `motionVectors` | `motionVectorBufferShared12`, same format/size as kMOTION_VECTOR, straight `CopyResource` | 329, `DX12SwapChain.cpp:557-559`, `Upscaling.cpp:1211` |
| `flags` | 0 (never assigned) | - |
| camera info | right/up/forward from transposed `CameraViewInverse`, position = `CameraPosAdjust` | 331-351 |

Depth source: kMAIN depth-stencil, copied 1:1 with `Load` by `features/Upscaling/Shaders/Upscaling/CopyDepthToSharedBufferPS.hlsl` (`Upscaling.cpp:1213-1253`). It is the raw device depth: reversed-Z when ReverseZ is on (finite far, `z' = w - z`, `src/Features/ReverseZ.cpp:162-171`), jittered, render resolution, not dilated, not upscaled. The copy runs in `Main_PostProcessing` before `PerformUpscaling` (`Upscaling.cpp:1871-1877`), so it is taken before the depth-upscale pass overwrites kMAIN depth.

Motion vectors: `prevUV - curUV` in viewport UV units, computed from the unjittered view-projection matrices (`package/Shaders/Common/MotionBlur.hlsli:8-15`). Render resolution, no jitter baked in, not dilated.

Reset handling: `needsReset` and a frameID skip are triggered by an HDR state change or `State::ShouldResetHistory()` (`FidelityFX.cpp:204-216, 262-264`). `RequestHistoryReset()` is only called from the LinearLighting toggle (`src/Features/LinearLighting.cpp:187`; the NeuralRendering one is its own). There is no reset on camera cuts, teleports or load screens.

Debug: the header offers `FFX_FRAMEGENERATION_FLAG_DRAW_DEBUG_VIEW`, `..._DRAW_DEBUG_TEAR_LINES`, `..._DRAW_DEBUG_RESET_INDICATORS`, `..._DRAW_DEBUG_PACING_LINES` (`ffx_framegeneration.h:51-60`), `FFX_FRAMEGENERATION_ENABLE_DEBUG_CHECKING` (line 48) and `ffxConfigureDescGlobalDebug1` (`include/FidelityFX/api/include/ffx_api.h:80`). None is used anywhere in `src`.

## 2. Checks against the SDK

| Check | Result | Evidence |
|---|---|---|
| (a) Depth inversion flag vs Reverse-Z | Consistent this boot. The flag is fixed at context creation, which is acceptable because ReverseZ is boot-latched (restart-gated). Log confirms order: `ReverseZ: enabled` at 17:28:55, FG context at 17:29:40, `converted 3 depth targets` at 17:29:42. | `FidelityFX.cpp:172`, `ReverseZ.cpp:288-295, 945-953`, `BottledShaders.log` lines 336, 377, 391 |
| (a) near/far swap | Not needed. The SDK takes min/max of the two and swaps on the inverted flag itself. | `extern/FidelityFX-SDK/sdk/src/components/frameinterpolation/ffx_frameinterpolation.cpp:648-662` (older SDK source, same contract in the header comment) |
| (a) `DEPTH_INFINITE` | Correctly unset; the reversed projection keeps a finite far plane. | `ReverseZ.cpp:162-171` |
| (a) edge case | The flag follows `IsActive()` (the setting), not "depth targets actually converted". If conversion ever failed, the projection would stay standard while FSR is told inverted. Not the case in the current log. | `FidelityFX.cpp:172` vs `ReverseZ.cpp:509` |
| (b) MV scale / resolution flag | Consistent. UV-space vectors x render size = render pixels; target is render resolution in the top-left region, so `DISPLAY_RESOLUTION_MOTION_VECTORS` is correctly unset. Sign matches FSR (current to previous). | `MotionBlur.hlsli:15`, `FidelityFX.cpp:310-313` |
| (c) jitter | Consistent with DLSS and FSR upscaling: all three pass `-upscaling.jitter`. MVs are unjittered, so `JITTER_CANCELLATION` is correctly unset (DLSS path says `motionVectorsJittered = eFalse`). | `FidelityFX.cpp:315-316`, `Streamline.cpp:358-359, 369`, `RuntimeUpscaler.cpp:1881-1882` |
| (d) same frame as colour | Yes. Depth/MV are copied in `Main_PostProcessing` of frame N and dispatched in the `Present` of frame N with the same `frameID`; `frameGenerationPrepared` gates FG when the copy did not happen. | `Upscaling.cpp:1874`, `DX12SwapChain.cpp:272, 299` |
| (e) blended geometry in depth/MV | Inconsistent by construction, see below. | `src/Deferred.cpp:569-595`, `package/Shaders/Lighting.hlsl:3856-3866, 3983` |
| HDR flag / transfer function | Correct for HDR off: SDR 10-bit back buffer, sRGB transfer, no `HIGH_DYNAMIC_RANGE`. | `FidelityFX.cpp:227-235` |
| API generation | The tree's header has neither `ffxDispatchDescFrameGenerationPrepareV2` nor a frame generation version descriptor. The SDK 2.1.0 release notes say the camera-info prepare path is deprecated in favour of PrepareV2 and that a version descriptor should be linked at context creation. The fork drives a 4.0.1 DLL through the older call pattern. No errors appear in the log, so it is accepted, but which provider and code path the DLL selects is not visible. | `include/FidelityFX/framegeneration/include/ffx_framegeneration.h` (no V2), release notes |

### (e) in detail: hair in depth and motion vectors

- Deferred (opaque, alpha-tested) hair writes depth and motion vectors normally; `MotionVectors.w` carries the diffuse alpha (`Lighting.hlsl:3856-3866`).
- Forward (alpha-blended) lighting draws write `MotionVectors = float4(mv, 0, 1)` (`Lighting.hlsl:3983`). The fork forces render targets 1-2 (motion vectors, normals) to `SRC_ALPHA / INV_SRC_ALPHA` blending with their own output alpha (`Deferred.cpp:585-595`). With alpha fixed at 1, every non-discarded pixel of a blended hair card overwrites the motion vector with the hair's motion, however faint the hair is in colour.
- Whether that same pixel writes depth is decided per mesh by its z-write flag, which the code does not override. For blended cards without z-write, depth stays at whatever is behind: the sky, at far plane (0.0 in reversed Z).
- Frame generation receives the raw depth and raw motion vectors. The DLSS path gets extra help that FG does not: a 5x5 dilated motion vector copy plus reactive and transparency masks (`Upscaling.cpp:1576-1583`, `Streamline.cpp:520-527`).

## 3. Versions and `fsr4RuntimeEnable`

Deployed DLLs in `C:\Modlists\NGVO 8.0 Beta\mods\Bottled Shaders - foxnne\Shaders\Upscaling\FidelityFX`:

| DLL | File version |
|---|---|
| `amd_fidelityfx_framegeneration_dx12.dll` | 4.0.1.2740 |
| `amd_fidelityfx_loader_dx12.dll` | 2.3.0.2740 |
| `amd_fidelityfx_upscaler_dx12.dll` | 4.1.1.2740 |

This matches FidelityFX SDK 2.3.0 (per the GitHub release list, dated 24 Jun). Its frame generation notes: fixed motion vector pre-processing for the generation rectangle, fixed binding of camera data for motion vector pre-processing, shutdown race fixes.

A newer SDK exists: 2.4.0 (28 Oct) with Frame Generation 4.0.2 and Frame Generation Swapchain 4.0.0. Its notes list refactoring and stability, Vulkan parity, PresentMon integration and driver-assisted frame pacing on RX 9000. Nothing in the 2.3.0 or 2.4.0 notes mentions disocclusion, thin geometry or halo handling, so a DLL swap is unlikely to change this artifact. Frame Generation 4.0.0 (SDK 2.1.0) introduced ML-based interpolation; my understanding is that it needs supported Radeon hardware and that other GPUs get the analytical 3.1.x interpolator from the same DLL. The fork never queries which provider is active, so this is unconfirmed for this machine.

`fsr4RuntimeEnable` (`src/Features/Upscaling.h:75-90`, `Upscaling.cpp:300-303, 1114`, `RuntimeUpscaler.cpp:830, 842-846`): restart-gated opt-in that routes FSR upscaling through the runtime `amd_fidelityfx_upscaler_dx12.dll` (FSR4) instead of the host-linked FSR 3.1 SDK. It only takes effect on an AMD adapter and only for the FSR upscale method. It has no influence on frame generation or on the DLSS path.

Side note: Streamline headers in `extern/Streamline-DX12/include/sl_version.h` are 2.14.1 while the deployed Streamline DLLs are 2.10.3.

## 4. Ranked causes

### Verified (code clearly does this)

1. No wrong or inconsistent parameter value was found for the current configuration. This is a negative result worth stating: depth convention, MV scale/sign/resolution, jitter and frame pairing are all correct.
2. Forward-blended geometry gets a full-strength motion vector while its depth is left to the mesh's z-write flag (`Lighting.hlsl:3983`, `Deferred.cpp:585-595`). Verified as a structural inconsistency; whether the player's hair hits it is not determinable from code.
3. FG receives raw render-resolution depth and motion vectors with no dilation or masks, unlike DLSS (`Upscaling.cpp:1211-1253` vs `1576-1583`).
4. No debug view, debug checking or message callback is wired (`FidelityFX.cpp:171, 269`).
5. No FG history reset on camera cuts or teleports (`State.h:564`, `LinearLighting.cpp:187`). Not related to the hair artifact.
6. Depth-inverted flag keyed to the setting rather than to the converted state (`FidelityFX.cpp:172`). Correct this boot.
7. `frameTimeDelta` uses the game delta and FOV uses the configured world FOV, not the live camera (`FidelityFX.cpp:318, 323`). Minor.

### Plausible (need the game to confirm)

| # | Cause | Confidence |
|---|---|---|
| P1 | Blended hair fringe is missing from depth. FSR sees those pixels at far-plane depth, equal to the sky, so they get no foreground priority when the fast sky vectors are reprojected and dilated; the fringe is filled from sky colour in the generated frame. Fits "crown or one side", "single frames", and a camera orbit where the head is screen-static and the sky moves fast. | Medium-high, about 50% |
| P2 | Thin alpha-tested strands in jittered 2293x960 depth versus DLSS-resolved 3440x1440 colour. Strand coverage in depth flickers frame to frame with jitter, producing false disocclusion at the silhouette that is filled with background. Inherent to the technique. | Medium, about 30% |
| P3 | Sky motion vectors are wrong or underestimated: the sky writes its vector with `Color.w * alphaTransmittance` as blend alpha onto the target (`package/Shaders/Sky.hlsl:598-600`), and any sky/cloud layer drawn without vectors leaves zeros. FSR then falls back on optical flow, which is weak on low-texture sky next to a high-contrast edge. | Low-medium, about 15% |
| P4 | Post effects applied after the depth copy (motion blur, depth of field, lens effects) spread hair/sky colour across the silhouette that depth and vectors still describe as sharp. | Low |
| P5 | Camera basis vectors or position convention wrong in the linked camera info (`FidelityFX.cpp:333-351`); same values are given to Streamline (`Streamline.cpp:343-350`). | Low |

The report that the artifact "mostly" disappears with FG off, rather than fully, fits P1/P2: DLSS consumes the same depth and vectors and would show a weaker version of the same error.

## 5. Fixes

| Target | Change | Risk | Verification |
|---|---|---|---|
| All (do first) | Add a debug setting. In `FidelityFX::Present` set `configParameters.flags` (`FidelityFX.cpp:269`) and `dispatchParameters.flags` to `FFX_FRAMEGENERATION_FLAG_DRAW_DEBUG_VIEW` (optionally reset indicators and tear lines). In `SetupFrameGeneration` (`FidelityFX.cpp:171`) add `FFX_FRAMEGENERATION_ENABLE_DEBUG_CHECKING` under the same setting and register `ffxConfigureDescGlobalDebug1` to log SDK messages. | None when off | The debug view tiles the game motion vector field, optical flow field, disocclusion masks and the generated frame. Orbit the camera and look at the hair silhouette in the motion vector and disocclusion tiles. |
| P1 | In `Upscaling::CopySharedD3D12Resources` (`Upscaling.cpp:1195-1266`) replace the plain depth copy with an FG-only depth: where a pixel is flagged hair (the fork already writes a hair category for forward-sorted hair into Masks2, `Lighting.hlsl:3920-3958`) and its depth is at far plane, take the nearest depth of the 3x3 or 5x5 neighbourhood. Alternative: force depth write for the forward hair pass. | Low for the FG-only depth (does not touch scene depth). Forcing z-write risks hair sorting artifacts. | Debug view: fringe pixels move with the head in the motion vector tile and leave the disocclusion mask. |
| P2 | No parameter fixes this. Options: feed FG a depth dilated toward the camera at hair-category pixels (same pass as P1), or test at DLAA/native to confirm. | Low | Sliver disappears at native resolution but persists at Quality. |
| P3 | Make sky layers write motion vectors with blend alpha 1 (`Sky.hlsl:600`), and ensure custom sky/cloud passes write camera-motion vectors. | Low-medium (affects DLSS and motion blur inputs too) | Motion vector tile shows uniform sky motion right up to the hair edge. |
| P4 | Temporarily disable motion blur and depth of field. | None | Artifact changes or disappears. |
| Hygiene | Call `RequestHistoryReset()` on camera cuts/teleports; key the inverted flag to the converted state; consider SDK 2.4.0 headers with PrepareV2. | Low | Reset indicators debug flag. |

## 6. DLSS Frame Generation as an alternative

A DLSS-G port would be a larger effort than fixing the FSR path. What exists: Streamline is initialised with only `kFeatureDLSS`, `kFeatureReflex` and `kFeaturePCL` (`Streamline.cpp:103`), common constants (camera, matrices, `depthInverted`, jitter, `mvecScale`) are already set per frame (`Streamline.cpp:327-372`), and depth and motion vectors are already tagged `eValidUntilPresent` (`Streamline.cpp:523-524`). What is missing: there is no `kFeatureDLSS_G` reference in `src` (only the constant in `extern/Streamline-DX12/include/sl_core_types.h:244` and the `sl_dlss_g.h` header), no HUD-less colour or UI colour/alpha tags, the swap chain is deliberately not wrapped by Streamline when the D3D12 proxy is active (`Upscaling.cpp:160-166`), Reflex is force-disabled whenever the FG DX12 path is active (`Streamline.cpp:600-606`), the deployed mod ships no `sl.dlss_g.dll` or `nvngx_dlssg.dll`, and headers (2.14.1) and DLLs (2.10.3) disagree. It would also consume the same depth and motion vectors, so if P1 or P3 is the cause the input fix is needed either way.

## Cannot be determined without running the game

- Whether the player's hair meshes have a blended pass, and whether that pass writes depth.
- What the sky's motion vectors look like at the silhouette.
- Which frame generation provider the 4.0.1 DLL selects on this GPU.
- Whether the sliver appears only on generated frames, and on which side relative to the orbit direction (leading side points to P1/P3, both sides to P2).

## Sources

- https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK/releases
- https://www.digitalcitizen.life/amd-releases-fsr-redstone-sdk-2-4-with-vulkan-support-and-improved-frame-generation/ (search snippet only; page returned 403)

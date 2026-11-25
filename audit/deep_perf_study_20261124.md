# Deep perf study: CPU-side render cost (2026-11-24)

Analysis and design only. Nothing was launched, deployed, committed or pushed. The game bridge was not called.

Evidence labels used throughout:
- **[V-src]** read in source (our fork, SPS 1.0.63 public source, Nukem9 SkyrimSETest for SE 1.5.x, CommonLibSSE-NG).
- **[V-log]** read in a crash log, SPS/Faster Objects log, or a saved result file of ours.
- **[I]** inferred. The reasoning is given; treat as a hypothesis.

## 0. Limits of this study (read first)

1. **No disassembly was possible.** `Stock Game\SkyrimSE.exe` has an encrypted `.text` on disk (Steam DRM). `dumpbin /DISASM` at 0x1414F3DC0 returns garbage (`mov bh,70h / rcl dword ptr ...`). There is no memory dump on the machine (`crashDumps\SkyrimSE.exe-45380.dmp` is 0 bytes). Every statement about instructions inside a function comes from crash-log register/stack lines plus the SE 1.5.x reimplementation, not from 1.6.1170 bytes. `harness\exe_peek.py` reads decrypted bytes from the *running* process; I did not use it because the game was off limits. Running `python exe_peek.py 107644+0x0:0x140 107642+0x270:0x40 106437+0x0:0x90 106436+0x0:0xA0` once the game is free would settle section B.
2. **The public SPS source is 1.0.63; the installed DLL is 1.0.74** (`SPS.log` line 1). The Bottled Shaders detection (`bAllowWithBottledShaders`, `bAllowWithBottledHiZ`) is not in the public source at all. The only module probe there is `GetModuleHandleW(L"CommunityShaders.dll")` in `EngineTimers.cpp:91`. The stated reasons below come from the installed `SPS.ini` comments and `SPS.log`.
3. **The rename database is thin for the render path.** Almost everything there is `Class::sub_*` or `FuncN_*`. Real names below come from CommonLibSSE-NG, our fork's hook names, SPS comments and Nukem9's source, cross-checked against call stacks.
4. The 2026-11-17 crash log is not on disk (oldest is 11-18). The address 14F3E4A appears in two logs: `crash-2026-11-22-21-03-42.log` and `crash-2026-11-24-13-45-24.log`.

Clone sizes: AddressLibraryDatabase 155 MB, SkyrimSETest 61 MB, skyrimPerformanceSolution 1.8 MB, total 217 MB in `C:\Users\foxnn\dev\re-refs\`. None over 300 MB. Nothing from them was executed.

---

## A. Names

| AE ID | RVA | SE ID | Name | Basis |
|---|---|---|---|---|
| 106583 | 0x14B2D90 | 99938 | `BSShaderAccumulator::FinishAccumulating_Standard_PreResolveDepth` (main-view opaque submission; our `Main_RenderWorld_Start` thunk replaces its first `RenderBatches` call at +0x84, `BlendedDecals` at +0x308) | rename: `BSShaderAccumulator::sub_*` only. Name is **[I]** from Nukem9 `BSShaderAccumulator.cpp:176` + our `Deferred.h:212-213` + the 11-22 stack (`106583+0x89` returns from 106609). |
| 106436 | 0x14A90F0 | ? | Scene render helper `(NiCamera*, BSShaderAccumulator*, uint32 flags)`; called once per shadow map from 107604+0x167 | rename: **no entry**. Signature **[V-src]** SPS `LightShadowCache.cpp:518,641-642`. A Fallout 4 style name would be `BSShaderUtil::RenderScene`; that name is **[I]**. |
| 106437 | 0x14A9190 | ? | Sibling of 106436, same shape; called by `Main::RenderDepth` (107139+0x180) and `Main::RenderWorld` (107142+0x124); calls the accumulator's FinishAccumulating function (106592 or 106583) at +0x72 | rename: `NiCamera::sub_*` (class guess only). Role **[V-log]** from both crash stacks; a name such as `BSShaderUtil::RenderScenePreResolveDepth` is **[I]**. |
| 107564 | 0x14ED920 | ? | `BSCubeMapCamera::sub_*`, 1056 bytes | rename gives the class only. Not referenced in our fork, CommonLib or SPS. Likely the six-face cubemap render that calls 106436/106437 per face: **[I]**, unverified. |
| 107142 | 0x14CDAA0 | 100424 | `Main::RenderWorld(bool)` | rename: **no entry**. **[V-src]** our `FrameAnnotations.cpp:947`. |
| 107644 | 0x14F3DC0 | 100854 | `BSBatchRenderer::RenderPassImmediately(BSRenderPass*, uint32 technique, bool alphaTest, uint32 renderFlags)`; CommonLib-NG calls it `SetupAndDrawPass`. **Contains RVA 0x14F3E4A (+0x8A).** | rename: **no entry**. **[V-src]** CommonLib `BSBatchRenderer.h:52`, Nukem9 `BSBatchRenderer.cpp:371`, Engine Fixes symbol in the stack. |

Callers and neighbours of the crash function (from the two stacks, innermost first):

| AE ID | SE ID | Name | Basis |
|---|---|---|---|
| 107642 | 100852 | `BSBatchRenderer::RenderBatches(uint32& technique, uint32& groupIndex, list*&, uint32 flags)`; the call to 107644 is at +0x28F, the loop step `mov rbx,[rbx+0x30]` (= `pass->passGroupNext`) at +0x294 | rename `sub_*`; **[V-src]** Nukem9 :231-324, our hooks, **[V-log]** stack line 5 |
| 106609 | 99963 | `BSShaderAccumulator::RenderBatches(start, end, flags, group)` | rename `sub_*`; **[V-src]** our `FrameAnnotations.cpp:951`, Nukem9 :510 |
| 106592 | ? | `BSShaderAccumulator::FinishAccumulating_ShadowMapOrMask` | rename `sub_*`; **[I]**, strong: the instruction after the return at +0x5C is `mov edx, 0x5C000030` (= `BSSM_GRASS_DIRONLY_LF`), which is the second `RenderGeometryGroup` call in Nukem9 :417-418 |
| 107139 | 100421 | `Main::RenderDepth(bool, bool)` (depth pre-pass) | **[V-src]** our `SnowDeformation.cpp:3123`, SPS `ShadowCulling.cpp:1253` |
| 36559 | 35560 | `Main::RenderPlayerView` (rename: `Main::Draw_*`). Call sites on 1.6.1170: +0x30A shadow maps, +0x3B3 RenderDepth, +0x3BF precipitation occlusion, +0x85E RenderWorld, +0x971 first person | **[V-src]** `Deferred.h:209-215`, `TerrainBlending.h:127`, `Skylighting.cpp:364` |
| 107604 | ? | Per-shadow-map render: allocate slot, clear, draw (106436 at +0x167), compute matrix. Used for sun cascades as well as local lights | rename `BSShadowParabolicLight::sub_*` is misleading; **[V-src]** SPS `LightShadowCache.h:13`, `ShadowCulling.cpp:1606-1624` |
| 108488 / 108489 / 108496 | 101494? / 101495 / 101499 | `BSShadowDirectionalLight` vfunc 0x9 `Accumulate`, 0xA `RenderShadowmaps`, 0x10 `UpdateCamera`/`SetFrameCamera` | rename `Func9_/Func10_/Func16_`; **[V-src]** SPS `InstancingAnalysis.cpp:777-780`, our `ShadowmapCascade*Fix.cpp` |
| 106567 | 99923 | `BSShaderAccumulator::RegisterObject` dispatch | **[V-src]** our `Hooks.cpp:1446`, SPS `LightShadowCache.h:10` |
| 107637 | 100847 | `BSBatchRenderer::Draw` | **[V-src]** our `GrassOptimizations.cpp:680` |
| 107630 | 100840 | `RenderPersistentPassList` | **[V-src]** our `LightLimitFix.cpp:1107` |
| 107137 / 107140 | 100419 / 100422 | `CalculateActiveShadowCasterLights` / `Main::RenderShadowmasks` | **[V-src]** our fork |

---

## B. The crash at SkyrimSE.exe+14F3E4A

### What is dereferenced

`BSBatchRenderer::RenderPassImmediately` begins (Nukem9 :371-388) by deciding whether the technique is already set up and, if not, calling `BeginPass(Pass->m_Shader, Technique)`, whose first act is the virtual `Shader->SetupTechnique(Technique)`. `BSShader` derives from `NiRefObject`, so its vtable is: 0x00 destructor, 0x08 `DeleteThis`, **0x10 `SetupTechnique`**, 0x18 `RestoreTechnique`, 0x20 `SetupMaterial`, 0x30 `SetupGeometry`, 0x38 `RestoreGeometry`. `call [rax+0x10]` with `rax = 0` is therefore `pass->shader->SetupTechnique(technique)` where **the object `pass->shader` points at has a null vtable pointer**. It is not a null `shader` pointer (that would fault reading address 0 one instruction earlier).

Register evidence **[V-log]**, both crashes:

| | 11-24 13:45 | 11-22 21:03 |
|---|---|---|
| Path | `Main::RenderDepth` → 106437 → 106592 → 106609 → 107642 | `Main::RenderWorld` → 106437 → 106583 → 106609 → 107642 |
| `RDX`/`RBX` (technique) | 0x20C6 = Utility 0x2B + `RenderDepth\|AlphaTest\|BinormalTangent\|Normals\|Texture\|Vc` | 0x48006036 (Lighting) |
| `RSI` (the pass; also the saved first argument in every thunk frame) | 0x16514DA5530 | 0x1FE6BB897B0 |
| `RCX`=`RDI` (`pass->shader`) | 0x16514DA4A90 = pass **− 0xAA0** | 0x1FE6BB8B510 = pass **+ 0x1D60** |
| `R14` | BSTriShape "Precombined", parent BSFadeNode "SkyrimPrecombines" with **kHidden** set | same |
| `R8` | 1 | a real `BSLightingShader*` ("Lighting") |

Two things stand out.

- `pass->shader` is not one of the engine's shader singletons. In the 11-22 crash the real `BSLightingShader` is sitting in `R8` at 0x1F121CAF700, while the pass's shader field points 0x1D60 bytes from the pass itself. In both crashes the field points into the same small heap region as the pass.
- Both distances are whole multiples of 0xA0 (0xAA0 = 17 × 0xA0, 0x1D60 = 47 × 0xA0). **[I]** That is what a freed pool entry looks like when its first 8 bytes are reused as the free-list link to another free entry of the same pool, whose own first qword is zero. I could not confirm the pool stride or the free-list layout without disassembly.

So the best-supported reading: **the batch renderer is drawing a `BSRenderPass` that has already been returned to the render-pass pool** (a use-after-free of the pass, not of the shader). `RenderBatches` only zeroes its list heads after drawing; "the memory is freed elsewhere" (Nukem9 :310), by the owning `BSShaderProperty` when its pass list is rebuilt or the geometry dies.

### What state could leave a pass pointing at freed memory **[I]**

Ranked by how well each fits the evidence (always "Precombined" geometry, parent node hidden at crash time, only after many rapid cell jumps, seen in both the depth pre-pass and the world pass):

1. **A precombined chunk is retired between accumulation and submission.** Faster Objects swaps chunks in and out on cell attach/detach. Its log says the swap happens "on the main thread before the frame's jobs start (Main::Update+82F)". The parent node being `kHidden` in the crash dump while one of its shapes is still in a draw list means the list is older than the hide. If the pass list of that shape's shader property was cleared (shape destroyed, or passes rebuilt) after the batch renderer took the pointer, this crash follows. A pass list can outlive its frame if a frame accumulated but did not submit that accumulator (load fade, a skipped `RenderDepth`), which rapid cell jumps make more likely.
2. **Two geometries sharing one `BSShaderProperty`.** `GetRenderPasses` frees and rebuilds the property's own pass list on every call. If a merged shape shares its property with another shape (a shallow clone), registering the second frees the first's passes in the same accumulation. This would normally crash far more often than once per session, so it would need to be a rare path (for example a chunk attached twice during a fast re-attach).
3. **A bake worker touching live scene objects.** The log shows bake work on other threads (thread 1864). If a worker releases the last reference to a shape or property that the render lists still use, the result is the same. Their log claims scene changes are main-thread only, so this ranks last.

None of these is in our fork's code. SPS and five of our thunks are on the stack only because they all wrap the same call site. I found no place where our fork or SPS 1.0.63 frees or rewrites a `BSRenderPass`.

Worth knowing: `TerrainBlending` keeps raw `BSRenderPass*` in `terrainRenderPasses` / `renderPasses` and replays them later in the frame (`TerrainBlending.cpp:343-350, 407, 420`). That is a similar hazard in principle but it is not this crash: the faulting call comes straight from the engine loop at 107642+0x294.

### Smallest defensive fix

Sketch: `C:\Users\foxnn\dev\ngvo-perf-lab\audit\deep_perf_patch_sketch_stale_pass_guard.cpp` (new file, not in the tree).

- **Hook site: ID 107642 + 0x28F** (SE 100852 + 0x29E), the `call RenderPassImmediately` inside `BSBatchRenderer::RenderBatches`. Our fork already installs five thunks there (`FurShells.cpp:1006`, `LightLimitFix.cpp:2225`, `InteriorSun.cpp:60`, `TerrainBlending.h:130`, `NeuralRendering.cpp:1374`); install the guard last so it is the outermost of ours.
- **Test:** under SEH, read `pass->shader`, read its first qword, and require it to lie inside the SkyrimSE.exe image (every `BSShader` vtable does). Otherwise return without drawing and log the pass, technique and geometry name. Cost per draw: two loads and two compares.
- **Second layer (recommended, behind a setting):** a detour of 107642 that walks `renderPass[renderPassMap[technique]]->passes[groupIndex]` before the original runs and cuts the list at the first invalid pass. Without it the engine still executes `mov rbx,[rbx+0x30]` on the stale pass and follows whatever it links to.

Confidence:
- That the faulting instruction is `pass->shader->SetupTechnique` with a readable but vtable-less target: **high** (two logs, consistent registers, matches SE source and the vtable slot).
- That the layer-1 guard would have avoided both logged crashes: **moderate to high** (in both, the pass and the bogus shader were readable).
- That the game stays healthy afterwards: **low to moderate**. The guard hides a use-after-free whose owner is Faster Objects or the engine. The same stale pass may carry a stale geometry pointer. Treat the guard as a crash-to-log converter that names the geometry and cell, then take the evidence to the Faster Objects side (test: `bEnabled=0` in `SkyrimPrecombines.ini` and repeat the cell-jump run).
- Root-cause ranking above: **low**, it is reasoning without disassembly.

---

## C. The shadow and depth draw path

### Frame order **[V-src]** for sites, **[I]** where marked

`Main::RenderPlayerView` (36559):
1. +0x30A: shadow maps. `CalculateActiveShadowCasterLights` (107137) picks lights; each `BSShadowLight` then runs its virtuals.
2. +0x3B3: `Main::RenderDepth` (107139), the depth pre-pass into kMAIN.
3. +0x3BF: precipitation occlusion map (also Skylighting's occlusion render).
4. +0x85E: `Main::RenderWorld` (107142). `Main::RenderShadowmasks` is 107140.

### Sun cascades

1. **Cameras:** `BSShadowDirectionalLight` vfunc 0x10 (108496) rebuilds every cascade camera every frame: orientation follows the sun, the ortho window follows the view, the depth range follows the objects **[V-src]** SPS `ShadowCulling.cpp:1282-1287`. Culling planes per cascade are built at 108496+0x1C12, which our `ShadowmapCascadeCullingFix` wraps. `DirShadowLightCulling` is 108492 (our `InteriorSun.cpp:68`).
2. **Collect:** vfunc 0x9 (108488) culls the scene once per cascade with a `BSCullingProcess` (`Process` = vfunc 0x16, `AppendVirtual` = vfunc 0x18). Each accepted geometry goes through `BSShaderAccumulator::RegisterObject` (106567) in render mode 14, which asks the shader property for its passes and registers them with the accumulator's `BSBatchRenderer` (`RegisterPass`, vfunc 0x2).
   **Side effect that matters for every caching design [V-src]** Nukem9 `BSShaderAccumulator.cpp:108-124`: registering a geometry in a shadow accumulator ORs that accumulator's flag into `shaderProperty->pLightData->uiShadowAccumFlags`. Collection is also how the engine records *which geometry belongs to which shadow light*. This is very likely why SPS found that filtering at collection "took the far shadows off ground and paths" and made interior lights go out (`LightShadowCache.h:7-10`, `ShadowCulling.cpp:1606-1609`), and why SPS now filters only at the single draw.
3. **Submit:** vfunc 0xA (108489) loops the cascades (per-cascade call at +0xC6, wrapped by our `ShadowmapCascadeRasterizerFix`). Each map goes through 107604: allocate slice in kSHADOWMAPS_ESRAM, clear, draw via 106436 at +0x167, compute matrix. 106436 → `FinishAccumulating_ShadowMapOrMask` (106592) → `BSShaderAccumulator::RenderBatches` (106609) over the Utility technique range 0x2B..0x4000002B, then grass → `BSBatchRenderer::RenderBatches` (107642) per technique and bucket → +0x28F → `RenderPassImmediately` (107644) → `BSUtilityShader::SetupGeometry` (vfunc 0x6) → `Draw` (107637).

### Depth pre-pass

`Main::RenderDepth` (107139) runs **its own scene traversal and its own pass generation** with a separate accumulator (global ID 415008, render mode 12; our HiZ code calls it "Sun Shadow Mask (12)"), then 107139+0x180 → 106437 → 106592 → 106609 → 107642 → 107644, the same submission code as the cascades **[V-log]** (11-24 stack). The main pass then draws with a depth-equal test wherever a pre-pass ran (Nukem9 :199-200; our `TerrainBlending.cpp:415` restores `kTestEqual`).

### Measured split of Utility draws **[V-log]**

`results\profile-prof-64gb.json` (11-21, forest segment, 6,845 Utility draws per frame, 5,746 of them itemised):

| Target | Draws | Opaque | Alpha test | Tree anim | LOD |
|---|---|---|---|---|---|
| kMAIN (depth pre-pass) | 3,356 (58 %) | 1,428 | 878 | 864 | 187 |
| kSHADOWMAPS_ESRAM (sun cascades) | 1,956 (34 %) | 1,006 | 349 | 601 | 0 |
| kSHADOWMAPS (local lights) | 246 | | | | |
| precipitation occlusion | 181 | | | | |

**The depth pre-pass, not the cascades, is the larger half of Utility.** Per-draw CPU from the same file: Utility 7.30 ms / 6,845 = 1.07 µs; Lighting 6.54 ms / 3,338 = 1.96 µs. There is no per-cascade split anywhere yet (see D, first steps).

### Where the three techniques attach

| Technique | Draw-time attach (safe) | Collect-time attach (saves traversal too, but see the flag side effect) |
|---|---|---|
| (1) Cache static casters per cascade | Wrap the per-map draw at **107604+0x167** (save/restore the depth slice) and filter single draws at **107642+0x28F**. This is exactly SPS. | vfunc 0x9 (108488) per cascade, plus freezing that cascade's camera in vfunc 0x10 (108496). Must keep `uiShadowAccumFlags` alive. |
| (2) Instance identical static meshes | Detour **107642** for batch boundaries, collect at +0x28F, flush with an own vertex shader (SPS). | Group at `RegisterPass` or build engine instance nodes at cell attach. |
| (3) Skip casters by occlusion or size | Same per-draw filter at 107642+0x28F. | `BSCullingProcess::AppendVirtual` vfunc 0x18 (SPS size rule) or the `RegisterObject` call at **76558+0xD3** (our HiZ hook, `Hooks.cpp:1445-1448`). |

### How SPS implements each **[V-src]** (1.0.63)

- **Far shadow cache** (`ShadowCulling.cpp:1280-1820`, `FarShadowGpu.cpp`). Only the last cascade. `StabilizeFarCascade` runs after the engine's `UpdateCamera`: it holds a reference frame and an ortho window that encloses the engine's, re-anchors when the sun turns by more than a step (0.05° in the installed config) or the window grows past 1.15× area, and snaps the centre to texels. `FarDecide` picks a mode per frame: Wait (draw everything, save the full slice), Build (draw statics only, save as "static", show the saved full slice), Cached (restore "static" after the clear, draw only dynamic or unknown geometry). The per-draw filter `FarSkipDraw` keys a hash map on `BSGeometry*` plus a quantised pose. A cached frame with more than 400 unknown draws, or one moved static, forces a rebuild. Everything is still collected.
- **Static-light shadow cache** (`LightShadowCache.cpp`). Same three modes per local light, one shared "previous" copy, keyed on the bound depth slice. A light whose maps land in different slices, or whose slice is shared with another light, is marked unsupported (`:497-513, 566-572`).
- **Shadow instancing** (`InstancingAnalysis.cpp:201-390, 601-644`, `InstancedDraw.cpp`). Sun shadow pass only, call site 1 only, opaque single-sided plain tri-shapes of the configured techniques (installed: C046, C045). Draws are withheld and flushed at the end of each `RenderBatches` call with an own vertex shader that reads `CameraViewProj` from constant buffer b12, "the same camera matrix the Community Shaders utility shader uses".
- **Sun shadow culling** (`ShadowCulling.cpp`, vfunc 0x18 and 0x16): size/distance rule from cascade 1 outward, plus subtree pruning.
- **Hide occluded objects** (`Occlusion.cpp`, vfunc 0x2A on `BSLightingShaderProperty`): previous-frame depth reduced to 256x144 tiles, read back, main view only.
- **Depth pre-pass culling** exists but is a developer test: "whole objects (not only small ones) disappeared from the main scene" (`SPS.ini`). **[I]** That is the depth-equal test: whatever is left out of the pre-pass fails the main pass.

### Why SPS stands down under Bottled / our fork

Stated reasons **[V-log]** (installed `SPS.ini` 1.0.74):
- Static-light cache: "Bottled Shaders installed: interior shadows flickered with this cache."
- Far shadow cache: "Bottled has its own shadow optimizations."
- Hide occluded objects: "Bottled Shaders has its own HiZ Occlusion Culling."

The detection code itself could not be read (not in the public 1.0.63 source). **[I]** for the static-light flicker: our Light Limit Fix re-chooses shadow-casting lights per frame (`CalculateActiveShadowCasterLights` detour on 107137, `UpdateCamera` vfunc 0x10 on parabolic and frustum lights, and its own settings-keyed local shadow cache at `LightLimitFix.cpp:1813`). SPS's cache assumes a light keeps its slice.

### Concrete overlaps with our fork's hooks **[V-src]**

| Engine point | SPS | Our fork | Verdict |
|---|---|---|---|
| 107642+0x28F (`RenderPassImmediately` call) | draw filter + instancing collect | FurShells, LightLimitFix `RenderPass2`, InteriorSun, TerrainBlending, NeuralRendering | Chain works (visible in the crash stack). Every draw passes up to six thunks plus Engine Fixes' inline hook. TerrainBlending re-issues and defers passes behind SPS's back. |
| 107667+0xED | call site 2 | LightLimitFix `RenderPass3` | Same site, chained. |
| 107642 detour | only when instancing is on at startup; source comment says older Community Shaders builds crash at the main menu with it | `FrameAnnotations.cpp:945` detour | Two detours on one function when both are on. |
| `BSUtilityShader` vfunc 0x6 | per-draw counters | TreeWind, SnowDeformation, FrameAnnotations (0x6 and 0x7) | Chained. Every Utility draw pays all of them. |
| `BSCullingProcess` vfunc 0x18 / 0x16 | size culling, pruning | `CullPoolExhaustionFix`, PhysicalSky (0x18) | Chained. |
| `BSLightingShaderProperty` vfunc 0x2A / 0x2D | occlusion, micro culling, skylighting culling | EmptyOverlayCullFix, SunShadowMaskFix, LandscapeSeams, SubsurfaceScattering, TruePBR (0x2A); Skylighting (0x2D) | Order depends on install time. SPS installs late on purpose (`ShadowCulling.h`: "must be installed AFTER Community Shaders"). |
| `Main::RenderDepth` 107139 | detour | SnowDeformation detour, FrameAnnotations detour, TerrainBlending call-site thunk | Chained (11-24 stack). |
| Sun light vfunc 0x9 / 0xA / 0x10 | accumulate, render, camera | FrameAnnotations vtable hooks | Chained. |
| 108496 internals | changes the far cascade camera after the engine | `ShadowmapCascadeCullingFix` (+0x1C12), InteriorSun patch (+0xE9C) | Composes, but SPS enlarges the far cascade window (up to 1.15× area plus margin 48 and step 64), so far-cascade texel density drops a little under our fix. |
| 108489+0xC6 | none | `ShadowmapCascadeRasterizerFix` counts cascades with a static counter | Safe today. A design that skips a cascade render must still advance this counter. |
| kSHADOWMAPS_ESRAM contents | copies slices with its own textures | Skylighting `CaptureShadowCascadeSRV`, VolumetricShadows `CopyShadowLightData`, `Deferred::CaptureDirectionalShadowMap` (`State.cpp:248-254`) | A Build frame shows the previous frame's full slice, so our captures read a one-frame-old far cascade on those frames. |
| Tree wind | 1.0.74 treats trees beyond `fTreesStillFrom = 2000` as static | `TREE_WIND` moves vertices in Utility for depth and shadow | Far-cascade tree shadows freeze between rebuilds and jump to a new sway phase at each rebuild. |
| Occlusion | pauses itself | HiZ registration hook at 76558+0xD3 | No conflict while SPS stays paused. |

Two facts about our own HiZ that matter for D **[V-src]**:
- `HiZOcclusion.h:150`: `cullRenderMode = { true }` enables only index 0 (world). The deployed `SettingsUser.json` overrides only `conservativeBias` and `motionMarginFrames`. **So HiZ currently culls the world pass only. The depth pre-pass (mode 12) and the sun cascades (mode 14) are not culled**, although the code path, the UI rows and a shadow-caster test with a sun sweep (`shadowSweepDistance`, default 2048) already exist.
- `Hooks.cpp:1158-1161`: geometry without a `TESObjectREFR` user data pointer is never tested. LOD has none. Whether Faster Objects' "Precombined" shapes carry one is unknown; if not, every merged chunk is exempt from HiZ.

Faster Objects also has its own "Hi-Z sun-shadow culling" (casters whose shadow cannot reach the view), but its Hi-Z is off because ours is on (`SkyrimPrecombines.log`).

---

## D. Ranked candidate projects

Reference numbers **[V-log]** from `results\perf40\sps_opts_locked\rows.jsonl` (Riverwood, locked camera, today):

| Variant | When | Frame ms | Total draws | CPU ms | Utility | Lighting |
|---|---|---|---|---|---|---|
| A baseline | day | 27.4 | 11,930 | 14.1 | 7,151 | 3,819 |
| C far shadow cache | day | 26.9 | 9,576 | 13.5 | 4,798 | 3,818 |
| D shadow instancing | day | 27.8 | 11,311 | 15.2 | 6,537 | 3,814 |
| A baseline | night | 28.1 | 8,369 | 10.7 | 5,000 | 2,583 |
| C far shadow cache | night | 27.2 | 8,262 | 12.2 | 4,027 | 3,346 |
| F B+C+D | night | 26.9 | 6,123 | 9.9 | 2,882 | 2,473 |

Reading these honestly:
- The far cache removed **2,353 Utility draws by day and bought 0.5 ms of frame time and 0.6 ms of CPU**. That is about 0.25 µs per removed draw, a quarter of the average Utility draw. Cascade draws are the cheap ones.
- Instancing removed 614 draws and **cost** 1.1 ms of CPU.
- Night rows are noisy (Lighting moves by 700 between variants), and row F shows a flicker score of 7.19 against 0.91 at baseline, which the measuring agent should explain before anything is adopted.
- Whether the 27 to 28 ms frame is limited by draw submission at all is **not established**. Removing 20 % of all draws moved the frame by 2 %.

Consequence: draw count is a weak proxy here. The expensive draws are Lighting (about 2 µs each) and, by elimination, the kMAIN pre-pass draws, both of which run through our own per-draw hooks. The ranking weights expected milliseconds, not draws.

### 1. Turn on HiZ for the depth pre-pass, then for cascade casters (existing code)

- **Saves:** every object HiZ already hides in the world pass is still collected, pass-built and drawn in the pre-pass today. Upper bound is the 3,356 pre-pass draws; the real figure equals the current world-pass cull count, which the feature already counts (`stats.earlyCulledCount`, per-mode call counters). No number exists yet. **[I]** 10 to 30 % in a village, so 300 to 1,000 draws, and these are the costlier main-view Utility draws plus their traversal and pass building. Cascade casters (mode 14): unknown, has a known popping risk.
- **Change:** nothing to build for a first test. Settings → HiZ Occlusion Culling → advanced render-mode table: enable "Sun Shadow Mask (12)", later "Sun Shadow Cascades (14)". Code: `HiZOcclusion.cpp:2014-2030`, `Hooks.cpp:1141-1205`.
- **Visual risk:** mode 12 must cull exactly the set mode 0 culls, or an object drawn in the main pass without pre-pass depth fails the depth-equal test and vanishes for a frame. Both accumulations read the same `cameraOcclusion` set and both run before `Deferred::StartDeferred`. I did not trace where the readback swaps the set, so **verify that the swap cannot land between `RenderDepth` and `RenderWorld`**. Mode 14: missing or late shadows when turning; the feature text says so itself.
- **Frame generation:** a late-appearing object is a one-frame disocclusion, which interpolation smears. Same exposure as today's world-pass culling.
- **Tree wind:** none (bounds-based).
- **Effort:** 0.5 day to measure; 1 to 2 days if the set swap needs pinning or precombined shapes need a user-data exemption path.
- **First step:** locked camera, toggle mode 12, compare Utility draws on kMAIN and the flicker score.

### 2. Per-draw hook diet (no draws removed; targets the 2 µs Lighting draw)

- **Saves:** **[I]** 1 to 3 ms of CPU per frame. Basis: 3,300 to 3,800 Lighting draws at 1.96 µs, and the following per-draw work in our own code, all **[V-src]**:
  - `Skin/Runtime/Renderer.cpp:315-365`: for **every** Lighting draw, skin or not, two recursive-mutex locks, `MakeData(Resolve(...))`, an unconditional `PerGeometryCB->Update` (Map/Unmap) and `PSSetConstantBuffers`. `:369` locks again from `State::Draw`.
  - `State.cpp:180-270`: `State::Draw` runs on every dirty-state flush and fans out to up to eight features.
  - Six chained thunks at 107642+0x28F and three or four on `BSUtilityShader::SetupGeometry`.
  - The rest of the list is in section E, part 3 (SnowCover name hashing per draw, ShaderCache mutexes per technique, LLF room-node walk, NightEye lookups).
- **Change:** start with Skin: compute the default-profile block once per frame, bind it once, and only Map when the pass is a skin material or the previous draw changed the buffer. Then give `State::Draw` a per-shader-type early-out.
- **Visual risk:** none if the cached block is invalidated correctly; a stale wetness or profile value on skin if not.
- **Frame generation / tree wind:** none.
- **Effort:** 2 to 4 days in slices, each measurable.
- **First step:** Tracy capture of the locked view; the zones already exist (`ZoneScopedN` in `State::Draw`). Add one zone to `Skin::BSLightingShader_SetupGeometry` and read its total.

### 3. Adopt SPS far shadow cache under our fork (measured)

- **Saves:** measured −2,353 Utility draws by day, −973 at night; −0.5 ms frame, −0.6 ms CPU by day. SPS's own claim is 1,000 to 1,500 draws and about 0.4 ms.
- **Change:** `bAllowWithBottledShaders = true` under `[FarShadowCache]` (already done for the test). No fork code needed unless the interplay below shows.
- **Visual risk:** far shadows follow the sun in steps; far tree shadows freeze and re-phase at rebuilds (tree wind); one-frame-old far cascade in our Skylighting, volumetric shadow and directional shadow captures on Build frames; slightly coarser far cascade. Rapid camera turns force rebuilds (more than 400 new draws), so the gain shrinks while moving. The locked-camera number is the best case.
- **Frame generation:** none direct; shadow maps carry no motion vectors.
- **Effort:** 1 to 2 days of soak and view tests.
- **First step:** repeat the measurement on a walk (flybench), not a locked camera, and read the `[FarShadowCache]` line with analysis logging on (share of frames served from cache, rebuild reasons).

### 4. Cascade sleep with collection skipped (own fork)

- **Idea:** update the middle cascade every 2nd frame and the far one every 3rd or 4th, skipping **both** collection and submission on sleep frames. This is what the SPS cache cannot do, and collection is the part with real CPU weight.
- **Saves:** **[I]** about half of the middle cascade and two thirds or more of the far cascade, draws and traversal. Per-cascade counts are not measured; with 1,956 to 2,400 cascade draws in total, 800 to 1,400 draws per frame on average plus the matching traversal.
- **Change:** `BSShadowDirectionalLight` vfunc 0x10 (108496) to freeze a sleeping cascade's camera and matrices, vfunc 0x9 (108488) to skip its collection, and the per-cascade call at 108489+0xC6 (already ours, `ShadowmapCascadeRasterizerFix.cpp:6`) to skip its render so 107604 does not clear the slice. Keep that file's static cascade counter in step.
- **Visual risk:** high if done loosely. Sampling a stale slice with a fresh matrix makes shadows swim, so the camera must be frozen exactly. Skipping collection clears the receiver flags described in section C unless they are preserved. Characters in a sleeping cascade get shadows at a half or third rate. Tree shadows in sleeping cascades update at a lower rate, which with wind reads as stutter in the middle cascade; keep sleep to the far cascade where sway is below a texel.
- **Frame generation:** generated frames double the visible staleness of a sleeping cascade (a 1-in-3 update becomes 1-in-6 displayed frames).
- **Effort:** 4 to 7 days. Needs disassembly of 108488/108489 first (see section 0).
- **First step:** add the cascade index to the existing Utility draw statistics (`State.cpp:316`, keyed today by descriptor and target) so cascades 0/1/2 are counted separately. One hour, and it sizes projects 3, 4 and 5.

### 5. Hand the far cascade's job to LOD Shadows (own fork, already has the cache)

- **Idea:** our `LODShadows` feature already keeps cached, budgeted (0.2 ms), history-blended directional depth maps of terrain, distant objects, trees and loaded objects (`LODShadows.h:8-15`, `LODShadows.cpp:568, 981`). Drop the vanilla far cascade (`iNumSplits` 3 → 2, or a shorter shadow distance) and let those maps cover the range.
- **Saves:** the whole far cascade: its draws (at least the 2,353 the SPS cache skipped by day) and its collection, every frame, with no rebuild spikes.
- **Visual risk:** shadow quality in the hand-over band (LOD-resolution casters, softer edges), loss of character shadows at that range, and a visible seam where cascades end. Every shader that assumes three splits (`SHADOWSPLITCOUNT=3` is a compile define) recompiles.
- **Frame generation / tree wind:** none new; LOD Shadows already handles wind by softening.
- **Effort:** 3 to 6 days including a look pass against the clear-day benchmark shots.
- **First step:** a throwaway profile with two splits and LOD Shadows on; reference shots plus Utility draw count.

### 6. Pre-pass by projected size (lower priority)

- **Saves:** tunable; 1,742 of the 3,356 pre-pass draws are alpha-tested or wind-animated trees, the class that benefits least from early Z.
- **Blocker:** the main pass's depth-equal test. Skipped objects must have their main-pass depth mode switched to less-equal with depth write per draw. `TerrainBlending.cpp:403-416` shows the state plumbing.
- **Visual risk:** medium to high. Terrain blending, snow deformation, HiZ and screen-space shadows all read pre-pass depth; small objects would be missing from it. GPU overdraw of foliage rises.
- **Effort:** 5 to 8 days. **First step:** count pre-pass draws by bound radius over distance to see what a 0.02 rule would remove.

### 7. Instancing in the depth pre-pass (not recommended as specified)

- SPS's draw-time instancing was a net CPU loss in the sun pass here (−614 draws, +1.1 ms). The pre-pass adds jitter, reverse Z, tree wind, the double terrain draw and snow routing to the list of things an own vertex shader must reproduce. Faster Objects already merges the static repeats that instancing would target.
- If repeats still dominate after project 1, the place to act is scene level (more merge coverage, or engine instance nodes at cell attach), which removes the draws from the pre-pass, the cascades **and** Lighting. It is the only item on this list that cuts Lighting draws without culling.
- **First step:** SPS analysis logging already prints `[Instancing-v2]` groupable counts for the sun pass; read that before spending anything.

### Not a perf project but blocks soak testing: the stale-pass guard (section B), 0.5 to 1 day.

---

## E. Per-frame waste checklist (our fork)

Collected by a sub-agent that read each enclosing function and its callers at HEAD ea4ebc368 plus the working tree. Entries are marked as that pass marked them. I re-read and confirm the Skin, `State::Draw`, HiZ and ViewAtmosphere entries myself; the rest are not independently re-checked. Paths are under `C:\Users\foxnn\dev\skyrim-community-shaders\src\`.

**Headline: nothing creates GPU resources unconditionally every frame.** The risks are lazy creation inside per-draw hooks, resources keyed on the dynamic-resolution size, and plain CPU work per draw.

### 1. GPU-resource creation reachable from per-draw or per-frame paths (lazy, cached)

| File:line | What | When |
|---|---|---|
| `Features/SnowDeformation.cpp:2810-2822` | two synchronous `Util::CompileShader` (hull, domain) on the render thread | first sight of each decal vertex shader, from the `BSLightingShader::SetupGeometry` thunk (`:2987`) |
| `Features/TreeWind/TreeShapes.cpp:1429-1444`, `:381-398`, `:944-990` | immutable buffer + SRV per new tree shape | from `TreeWind::BeginDraw` in the Lighting and Utility `SetupGeometry` thunks; time-budgeted; rebuild when trunk-card generation changes (`:1057`) |
| `Features/GrassOptimizations.cpp:611-621` | vertex buffer per CPU-only instance group | first draw after optimized drawing is off |
| `Features/FurShells.cpp:774-777` | three depth-stencil states per new engine state | inside the `DrawIndexed` detour (`:863`) |
| `Features/HDRDisplay.cpp:1122` | blend state per new engine blend state; cache holds a reference to every original forever (`:1086`) | inside the `OMSetBlendState` detour |
| `Features/ReverseZ.cpp:475`, `:499` | rasterizer / depth-stencil state per new engine state; same never-freed growth | inside `RSSetState` / `OMSetDepthStencilState` detours |
| `Features/LODShadows.cpp:859` | input layout per new vertex descriptor | per caster in `RenderBatch` (`:1031`) |
| `Features/VolumetricShadows.cpp:99-171, 206-300` | texture created once, but the downsample and four blur dispatches rerun on every shadow-mask technique begin (`State.cpp:250`) | inferred: count of shadow-mask passes per frame not checked |
| `Features/SnowDeformation.cpp:2946-2967` | buffer only on size change, but 2 to 4 `GetDesc` and 2 `CopyResource` every frame | per frame |
| `Features/PhysicalSky/CloudNoiseGenerator.cpp:160-172` | SRV + UAV per mip on each regeneration | settings or source change |

### 2. Conditional recreation that can churn

| File:line | Trigger | Rebuilt |
|---|---|---|
| `Features/ViewAtmosphere.cpp:253, 292-324` | size from `Util::ConvertToDynamic` (confirmed) | four 3D volumes + views |
| `Features/ExponentialHeightFog.cpp:534, 562-565, 624-635`; released at `:849-866` | dynamic size; also freed whenever ViewAtmosphere is prepared, settings off, or range collapses, then rebuilt when that flips back | ten volumes |
| `Features/HiZOcclusion.cpp:947-1099` | dynamic size, checked every frame (confirmed). `HiZPyramid.cpp:147-154` avoids this on purpose | pyramid + SRV/UAV per mip |
| `Features/NRD.cpp:98-141`; followers `ScreenSpaceReflections.cpp:521`, `ScreenSpaceGI.cpp:862` | running maximum of the dynamic extent (grows, then settles) | guide textures, REBLUR re-init |
| `Features/ScreenSpaceGI.cpp:631-702, 863, 873` | SH toggle or size mismatch; rebuilds even when the size is unchanged | 2 to 4 full-res targets + REBLUR init |
| `Features/PhysicalSky/LocalNdf.cpp:202-251` | layer count changes at the start and end of each weather blend | weights buffer, three texture arrays, UAV per slice |
| `Features/PhysicalSky/Storm.cpp:274-289` | active storm count changes | two arrays, buffer, UAVs, a `std::format` name each |
| `Features/PhysicalSky/VoxelCloud.cpp:264-313` | cloud count changes | placements buffer, 256² × count×32 array |
| `Features/LandscapeSeams.cpp:467-788` | every land cell attach rebuilds that cell's quads and up to about 100 neighbours | textures per quad |
| `Features/GroundFog.cpp:277-327, 982-1094` | worldspace change (DDS read on the render thread); height-map SRV pointer change | water map, pyramid views, targets |
| `Features/TerrainShadows.cpp:472-518` | height-map load or worldspace change | precompute targets |
| `Features/NightEye.cpp:390-428` | `memcmp` of the output target description; inferred churn if two targets alternate | full-screen copy |
| `Features/NeuralRendering.cpp:2168-2214`; `NeuralRendering/Backend.cpp:393-452` | output or model raster size change; the backend path stalls the GPU (`WaitForIdle`) per change | shared D3D11/D3D12 textures |
| `Features/Upscaling/FidelityFX/RuntimeUpscaler.cpp:1431-1469` | any description change | shared wrapped resources |
| `Features/PostProcessing.cpp:628-690` | new (size, format, flags) key; old targets live 600 frames | scratch colour targets |
| `Features/PostProcessing/LensFlare.cpp:351-410, 637`; `PhysicalGlare.cpp:502` | FFT resolution slider | 4 and about 11 FFT textures |

With DLSS at a fixed ratio the dynamic-size entries are stable in play; they churn on a DLSS mode change or if vanilla dynamic resolution is ever enabled.

Created once and never resized (stale after a resolution change, inferred): `NeuralRendering.cpp:1449, 1693`, `DoF.cpp:597`, `PhysicalLens.cpp:731`, `SSS.cpp:437`.

### 3. Per-draw CPU work in hot hooks

| File:line | Cost per draw |
|---|---|
| `Features/Skin/Runtime/Renderer.cpp:315-365, 369, 306` | every Lighting draw: mutex ×2 to 3, profile resolve, Map/Unmap, constant-buffer bind (confirmed) |
| `Features/Skin/Runtime/Renderer.cpp:168` | `unordered_map` insert per compatible geometry |
| `State.cpp:180-270` via `Hooks.cpp:652-655` | fan-out to up to eight feature hooks per dirty-state flush (confirmed) |
| `ShaderCache.cpp:2022, 2072, 2094` | mutex per shader lookup, 2 to 5 lookups per technique begin (`Hooks.cpp:184-270`) |
| `Features/SnowCover.cpp:1084-1126, 1024-1081` | name hash, extra-data scan, list lookups per Lighting draw |
| `Features/LightLimitFix.cpp:443-461, 532-533` | room-node parent walk (interiors), strict-light buffer Map per draw |
| `Features/SnowDeformation.cpp:2836, 2879, 2687, 2760` | `VSGetShader`, set inserts and finds, a lock per decal draw |
| `Features/LandscapeSeams.cpp:191-229` | shared lock, two finds, `shared_ptr` copy per landscape draw |
| `Features/TreeWind.cpp:369-422, 617-624` | classify, parent walk, two hash finds per Lighting and Utility draw |
| `Features/NightEye.cpp:583-616, 759-806` | string-keyed finds and casts per Lighting/Effect draw while active |
| `Features/ReverseZ.cpp:460, 488`; `HDRDisplay.cpp:1056-1081` | lock + hash find per depth, raster and blend state set |
| `Features/FurShells.cpp:863-872, 803-825` | detour on every `DrawIndexed`; COM getters per fur draw |
| `Features/PhysicalSky.cpp:2842, 2807, 2866` | `PSGetSamplers` per grass draw, `VSGetConstantBuffers` per sky draw |
| `Features/TerrainHelper.cpp:244`; `ExtendedTranslucency.cpp:44`; `NeuralRendering.cpp:1651-1662` | lock + find; extra-data lookup; actor/race checks per draw |
| `Features/LODShadows.cpp:1012-1046` | Map + redundant shader and layout binds per caster |
| Debug only: `FrameAnnotations.cpp:33-41, 72-318`, `State.cpp:316-326, 1545-1566` | `std::format` per draw or pass; `BeginPerfEvent` does a COM status call and a `push_back` even with no consumer |

Per-frame (not per-draw) trims: `PhysicalSky/VoxelCloud.cpp:173, 282` (JSON dump to string and a vector copy every frame), `PhysicalSky/LocalNdf.cpp:115-217` (string building, JSON parse and `std::filesystem::exists` every frame per layer), `GroundFog.cpp:277, 1153-1186`, `ViewAtmosphere.cpp:723-729, 794`, `PhysicalLens.cpp:724-727`.

Tracker caveat: `Utils/VramTracker.cpp:69-189` allocates a tag, takes a mutex and captures a stack per tracked creation, and its slot counters are not atomic. It inflates the cost of any churn while it is on.

---

## What could not be determined

- The actual instructions of 107644, 107642, 106436, 106437, 107564, 108488, 108489 (encrypted on disk). Offsets inside them are taken from logs and hook sites only.
- The render-pass pool layout, so the "freed pass on a free list" reading is a hypothesis.
- Which component frees the pass. Faster Objects' source was not available to read.
- How SPS 1.0.74 detects Bottled Shaders, and its 1.0.64 to 1.0.74 changes.
- Draws per cascade, and how many pre-pass draws HiZ would remove.
- Whether the frame is limited by draw submission; today's numbers suggest only weakly.
- Whether "Precombined" shapes carry reference user data (decides whether HiZ can ever test them).
- SE IDs for 106436, 106437, 106592, 107564, 107604.

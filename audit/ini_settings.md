# Engine and plugin settings that drive cost - profile foxnne-nsfw (2026-11-17)

Read-only audit. "Verified" = value read from the file or a log line of the 11:40 session. "Inferred" = cost judged from what the setting does; not measured here.
Machine: i9-13900K (24C/32T), 3440x1440. GPU per nvidia-smi is an RTX 5080 with 16303 MiB (skyrimprefs.ini still says sD3DDevice="NVIDIA GeForce RTX 4090"); 13.5 GB in use and 97 % utilisation during the benchmark. Community Shaders VramTrack reports budgetMB=15209 and about 9.8 GB live in the game (SkyrimSE.exe geometry buffers 2.0 GB, 46 textures of 4K+ 1.56 GB, SPS-streamed textures 2.2 GB, CS targets 1.3 GB, Cinematic DoF Standalone 296 MB). SPS.log hitch lines show "VRAM 88-97 %, paged out 475-612 MB" while moving outdoors. Sunshine (stream host) and a QmlRenderer process are also running on the machine. Live process during the benchmark: priority High, affinity 0xFFF5, 768 threads, 31 GB private / 16 GB working set.

## Game INIs (`profiles\foxnne-nsfw\`)

skyrimcustom.ini overrides skyrim.ini where both set a key.

| Setting (file) | Value | Vanilla Ultra / usual | Cost (inferred) |
|---|---|---|---|
| fShadowDistance (prefs) | 10000 | 8000 | More casters per cascade; shadow passes are draw-call bound |
| iShadowMapResolution (prefs) | 2048 | 4096 ultra | Already low; with distance 10000 and 2 splits texel density is coarse |
| iNumSplits (prefs) | 2 | 2 | - |
| fInteriorShadowDistance | 3000 | 3000 | - |
| bDrawLandShadows / bTreesReceiveShadows | 1 / 1 | 0 / 0 on most presets | Land shadow pass renders terrain into the shadow map; terrain is 16x tessellated near the player by Smooth Terrain |
| fMaxHeightShadowCastingTrees (skyrim) | 5000 | - | All trees cast |
| bDisableHighTreeShadow | 1 | - | fine |
| fLODFadeOutMultObjects (prefs) | 30 | 15 | Statics with a fade distance stay drawn twice as far: direct draw-call count |
| fLODFadeOutMultActors | 30 | 15 | Actors (skinned, SMP, shadows) drawn twice as far |
| fLODFadeOutMultItems | 10 | 15 | below ultra |
| fMeshLODLevel1FadeDist / Level2 | 6144 / 10240 | 4096 / 3072 | Full-detail mesh LOD held longer |
| fMeshLODLevel1/2FadeTreeDistance | 6144 / 10240 | 2844 / 2048 | Trees keep LOD0 geometry much further |
| fTreesMidLODSwitchDist (custom) | 9999999 | 3600 | Never switches to mid LOD |
| bRenderSkinnedTrees / uiMaxSkinnedTreesToRender | 1 / 120 | 1 / 40 | 3x the animated (skinned, unbatched) trees |
| uGridsToLoad / uExterior Cell Buffer | 5 / 36 | 5 / 36 | vanilla |
| uLargeRefLODGridSize (prefs) | 9 | 11 ultra | Large refs loaded in a 9x9 block as full models |
| fBlockLevel0Distance / Level1 / Max | 100000 / 180500 / 327680 | 60000 / 90000 / 250000 | Known (DynDOLOD loader); LOD4 with 3D trees out to 100k |
| fTreeLoadDistance / fSkyCellRefFadeDistance | 233155 / 186275 | 75000 / 150000 | Tree LOD to 233k (set by `overwrite\MCM\Settings\DynDOLOD.ini`) |
| iMinGrassSize (skyrim) | 60 | 20 | Sparser than vanilla (good); real density comes from the cache (Only-load-from-cache) |
| iGrassCellRadius | 2 | 2 | Grass in the full 5x5 |
| bEnableGrassFade (skyrim) | 0 | 1 | No fade: grass is drawn to the edge of the 5x5 |
| fGrassStartFadeDistance (prefs) | 999999 | 7000 | With fade off, every grass cell in radius 2 is drawn at any distance (up to about 14k units in the corners) |
| fGrassFadeRange / fGrassMaxStartFadeDistance | 7000 / 7000 | 1000 / 7000 | - |
| iMaxGrassTypesPerTexure | 15 | 2 | More grass variety per landscape texture: more grass instances and shader variety |
| bUseWaterReflections + bReflectLODLand/Objects/Trees (skyrim) | 1 + 1/1/1 | 1 + 1/1/1 | Engine re-renders LOD land, LOD objects and tree LOD for the water reflection; with 81.6 M triangles in LOD4 this is a second LOD pass whenever reflective water is in view. bReflectSky=0 |
| iReflectionResolutionDivider | 2 | 2 | - |
| bScreenSpaceReflectionEnabled | 1 | 1 | CS replaces |
| bVolumetricLightingEnable / iVolumetricLightingQuality | 1 / 2 | 1 / 2 | CS Volumetric Lighting ExteriorQuality=1 |
| iMaxDesired (prefs, Particles) | 5000 | 750 | 6.7x particle budget; Particle Limit Uncapper also sets iMaxDesiredParticles=5000, fCap1Mult=3, iCap2=240 |
| uMaxDecals / uMaxSkinDecals / uMaxSkinDecalPerActor | 200 / 50 / 40 | 100-1000 / 35-100 / 20-60 | moderate |
| iMaxDecalsPerFrame / iMaxSkinDecalsPerFrame | 500 / 150 | 100 / 25 | Burst cost in fights only |
| fDecalLifetime / fDecalLOD0 | 300 / 10240 | 30 / 1000 | Decals live 10x longer and stay visible 10x further |
| fLightLODStartFade / fLightLODRange | 3500 / 24576 | 3500 / 25000 | - |
| fFlickeringLightDistance (custom) | 8192 | 1024 | Flicker animation runs 8x further (CPU, minor) |
| bSAOEnable / bUseTAA / bFXAAEnabled | 0 / 0 / 0 | - | correct for CS |
| bUse64bitsHDRRenderTarget | 1 | 0 | Needed for HDR pipeline; larger targets |
| iVSyncPresentInterval | 0 | 1 | but SSE Display Tweaks EnableVSync=true |
| bBackgroundLoadVMData (custom) | 1 | 0 | fine |
| [Papyrus] fPostLoadUpdateTimeMS / iMaxAllocatedMemoryBytes | 2000 / 500000 | 500 / 76800 | fine; fUpdateBudgetMS not set (1.2 default) |
| [Papyrus] logging/profiling/trace | 0 | 0 | off (good) |
| [HAVOK] fMaxTime | 0.01666667 | - | overridden by SSE Display Tweaks dynamic scaling |
| bLoadArchiveInMemory + sArchiveToLoadInMemoryList | Animations.bsa | - | fine |

## SSE Display Tweaks (`NGVO - MCM and INI Settings\SKSE\Plugins\SSEDisplayTweaks.ini`)

- EnableVSync=true, VSyncPresentInterval=1, EnableTearing=false, FramerateLimit=240, MaximumRefreshRate=240, MaxFrameLatency=0, SwapBufferCount=0. With frame generation presenting through Streamline, a VSync'd present can add wait time on the render thread (SPS installs a "Present - wait time" hook that can show this). Test: EnableVSync=false + EnableTearing=true.
- LogLevel=debug (tiny log, harmless).
- [HAVOK] DynamicMaxTimeScaling=true, 60-240. [Papyrus] DynamicUpdateBudget=false, UpdateBudgetBase=1.2.
- DisableActorFade=true, DisablePlayerFade=true.

## SSE Engine Fixes (`NGVO - MCM and INI Settings\SKSE\Plugins\EngineFixes.toml`, v7.0.20)

All MemoryManager overrides on (memory manager, scrap heap, Scaleform, render pass cache, Havok, replace imports; TBB). bFormCaching, bTreeLodReferenceCaching, bMaxStdIO on. iSaveGameMaxSize=256. Nothing unusual.

## SPS (`Skyrim Performance Solution (SPS) - AE SSE VR\SKSE\Plugins\SPS.ini` + `overwrite\SKSE\Plugins\SPS_User.ini`)

- Active (SPS.log): ShadowCulling (cascade >= 1, dist > 1500, radius < 150), PointLightShadowCulling, ActorShadowCulling (3500), ActorPartShadowCulling, SkylightingCulling, DecalCulling, LightGatherThrottle, SubtreePruning, TextureStream.
- Off: MainViewCulling, DepthPrepassCulling, ShadowInstancing ("Feature not used on this game version"), FarShadowCache.
- Auto-disabled because of Bottled Shaders: LightShadowCache and Occlusion ("Hide occluded objects stays off").
- TextureStream: ini says bBudgetMode=true, fReserveMB=1024, fMinEdge=1024; SPS_User.ini overrides bBudgetMode=false, bStreamClothing=true, bStreamCharacters=true, fMaxEdge=2048. So streaming is not driven by a VRAM budget; textures are reloaded to full/2048 as they are needed. Log: "[Hitch] 145 ms | SPS this frame: reloaded 19 (49 MB) | frame before: reloaded 151 (282 MB), released 67 (18 MB) | VRAM 51 %, paged out 519 MB", later "paged out 612 MB".
- Untested optional gains: MainViewCulling (dist > 3000, radius < 100, angular < 0.002) and DepthPrepassCulling are both off.

## Faster Textures (`Faster Textures\SKSE\Plugins\FasterTextures.ini`)

Mode=2, SkipMips=2, MinEdge=512, UploadMiBPerFrame=16, ReleasesPerFrame=4, UpgradeWorkers=2, cache 8421 textures / 2466 MiB in `Stock Game\FasterTextures Cache`. Log: "Skyrim Performance Solution's texture streaming is on: textures it can manage are handed to it after loading small", "handed to Skyrim Performance Solution: 436", hitches of 422 / 182 / 146 / 209 ms in the 5 s after the loading screen with "this plugin 0.0 ms".

## Faster Objects (`Faster Objects\SKSE\Plugins\SkyrimPrecombines.ini`)

bEnabled=1, bRuntimeBake=1, bHiZ=0. Log: 96 cached cells, "Runtime bake enabled: in-process baker (chunk size 4096 ...)", merges are small ("2 shapes -> 1", "11 shapes -> 1") because shapes only merge when lit by the same shadow lights. Cells not yet baked are baked in-process when first visited (worker threads) - first visit of a cell costs more than a revisit.

## Smooth Terrain (`Smooth Terrain\SKSE\plugins\SmoothTerrain.ini`)

iSubdivisions=2 (65x65 verts per quad = 16x vanilla triangles), iSmoothedQuads=3 (5x5 quads at full level), iGradientStep=2 (one level lost every 2 quads, so level 1 = 4x triangles covers most of the rest of the 5x5 cells). Log: "Hooked BuildQuadTriShape ... land quad build", "Terrain falloff player cell sink registered". Terrain is rebuilt at new levels when the player changes cell, and the denser terrain is also drawn into the depth, shadow (bDrawLandShadows=1) and reflection passes.

## Grass (NGIO `No Grass In Objects - Grass Control\SKSE\Plugins\GrassControl.ini`, `Grass Cache Helper NG`)

Use-grass-cache=true, Only-load-from-cache=true, Extend-grass-distance=true, Extend-grass-count=true, Super-dense-grass=false, Overwrite-grass-distance=-10000 (no override), Overwrite-min-grass-size=-1, DynDOLOD-Grass-Mode=0, Ray-cast-enabled=true (only used when generating), Threaded-grass-placement=false. Grass Cache Helper: UsingGrassLOD=1 while GrassControl has DynDOLOD-Grass-Mode=0 (mismatch; verify whether grass LOD exists in the DynDOLOD output), AutoGrassDistanceSettings=0. Grass Sampler Fix has no ini. Community Shaders GrassOptimizations feature is loaded.

## HDT-SMP (`foxnne - carried-over settings\SKSE\Plugins\hdtSkinnedMeshConfigs\configs.xml`, wins over NGVO copy; Faster HDT-SMP 4.1.1 AVX)

maximumActiveSkeletons=10, autoAdjustMaxSkeletons=false, budgetMs=3.5, sampleSize=5, minCullingDistance=750, numIterations=8, maxSubSteps=2, min-fps=60, erp=0.2, enableNPCFaceParts=false, disable1stPersonViewPhysics=true, wind enabled (strength 55.1), logLevel=0. With 31 real fps and min-fps=60 / maxSubSteps=2 the solver runs 2 substeps of 8 iterations every frame for up to 10 skeletons. Skeleton activation depends on what is in view, so fast camera turns switch skeletons on and off.

## CBPC (`GT Softbody (OStim)` config wins over `CBPC 1.7.3`)

`CBPC 1.7.3\SKSE\Plugins\CBPCSystem.ini`: SkipFrames=0, OutOfCombatActorCount=40, InCombatActorCount=20, ActorDistance=1024, ActorBounceDistance=2048, ActorAngle=360, Logging=0.

## Other plugin settings with a cost

- MuDynamicNormalMap: PlayerEnable/NPCEnable/HeadEnable=true, TextureWidth/Height=2048, UpdateDistance=3000, GPUEnable=true, ProcessingInLoadingWithMainGPU=true, AutoTaskQ=3, TextureCompress=1. Each actor entering 3000 units gets normal maps baked on the GPU (main GPU).
- Particle Limit Uncapper: fCap1Mult=3, iCap2=240, iMaxDesiredParticles=5000.
- PriorityMod.toml: priority=4 (High), affinity=0x000000000000FFF5 (P-core threads 0,2,4-15; logical 1 and 3 and all 16 E-cores excluded). Verified on the live process. 768 threads share 14 logical CPUs.
- Community Shaders `CS Settings\...\SettingsUser.json`: Compiler Threads=14, Background Compiler Threads=8, HiZ conservativeBias=0.02 / motionMarginFrames=5, Upscaling presetDLSS=4, neuralRenderingEnabled=true, frameGenerationForceEnable=1, Volumetric Lighting quality 1/1, "Throttle Water Cubemap"=true. `VramTrack.on` present -> `overwrite\SKSE\Plugins\CommunityShaders\VramTrack.jsonl` (13 MB, one record per second).
- Re Light `RELight - Official Light Addon\SKSE\Plugins\Relight.ini`: disableGameLights=true, enableLightMerging=true (max 12 lights), enableDebugLines=true.
- Feet of Skyrim: applyToNPCs=true, extraRaycasts=true, forceEnableWhileMoving=true.
- Audio Occlusion: bEnableExteriorOcclusion=1, fMaxOcclusionDistance=4096.
- CausticLight: fMaxDistance=3000, bFollowShadowDistance=1.
- Actor Limit Fix: morphLimit=128, moverLimit=256.
- Papyrus Tweaks: iMaxOpsPerFrame=500 (vanilla 100), bSpeedUpNativeCalls=false, bEnableDebugInformation=true.
- RaceMenu skee64.ini: iLogLevel=5 (debug), bParallelMorphing=1, bBodyMorphGPUCopy=1; SKSE.ini iTintTextureResolution=4096.
- Windswept `K747_LodWind.ini`: bEnabled=0 (plugin dll not present; ini only). DripSim: Enabled=false, DripSimRain Auto=false (both DLLs still load).

## Papyrus / AI load indicators (from modlist and plugin names; saves not opened)

- LLM stack, all native DLLs with game-thread hooks: SkyrimNet 1.2.0-rc2 (71 MB), SeverActions 4.9.0, IntelEngine 3.8.2, NarrativeEngine, OMind 0.8.0, PlayerSignals 0.2.1, Physical Letters 1.1.1, DragonSense 0.5.0, Ink and Quill 0.2.0, Battle Summaries 1.5.0, OStimNet 2.6.2, Hypnosis 1.2.0, BodyLanguage 2.1.1, Smart Talk, Dynamic Dialogue Framework 3.1. Cell-change work seen in logs: SeverActionsNative "FurnitureOccupancy ... markers read" bursts, NarrativeEngine "FineRoads: active graph rebuilt - 25 cell(s), 262 node(s)", Walk With Me "[Diag] scan: high actors=5".
- Script-driven mods usually named for polling or per-event scripts: Footprints (script per footstep on every actor), Conditional Expressions, Immersive Interactions, Dynamic Things Alternative, iWant Widgets, Wet/arousal set (ArousalBasedPussyWetting, OHorny, OCum, OInflation, sr_FillHerUp, NPCs Approach OStim, OStim NPCs), Warming Hands, Sleeping Expanded, Use Those Blankets, Simple Fishing Overhaul, Fire Cooks Food, Serana Dialogue Add-On, about 60 "DF"/"Intimacy" follower-dialogue plugins, Auri, Remiel, Nether's Maloria and other custom followers. No population/patrol mod (Immersive Patrols, Populated series, Immersive Citizens) is in the list.
- No Papyrus log exists to confirm (logging off); Papyrus Profiler is installed but disabled.

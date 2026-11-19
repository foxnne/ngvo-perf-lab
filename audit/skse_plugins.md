# SKSE plugin inventory - profile foxnne-nsfw (2026-11-17)

385 DLL files in 376 enabled mods; skse64.log of the 11:40 session shows 365 plugins "loaded correctly", 0 failures (18 files are shadowed duplicates, msdia140.dll and !ApocryphaMenuFramework-SMFName.dll are helpers).
Prio = position among enabled mods counted from the top of modlist.txt (1 = highest priority, wins conflicts). Ver = meta.ini version of the mod (not the DLL file version). Flags: a = hot-path hook, b = overlap, c = log issue, d = debug/dev. Flags come from each plugin's own log/ini where one is quoted in the report, otherwise from the plugin's known purpose (inference).

## Renderer / shaders / culling / streaming (30)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 7 | PGLite | PGLite.dll | 12194 | 2.4.0.0 | a: patches meshes/materials as they load (facegen streams), reloads Light Placer configs |
| 135 | Face Lighting SKSE - Player and dialogue NPC Lighting | FaceLighting.dll | 973 | 0.10.4.0 | a: per-frame light on player/dialogue NPC |
| 190 | MuDynamicNormalMap | MuDynamicNormalMap.dll | 4286 | 2.1.11.0 | a: GPU bakes 2048x2048 normal maps per actor within 3000 units (player+NPC, head too); task queue tick 100 ms |
| 436 | Cinematic DoF Standalone | CinematicDoFStandalone.dll | 912 | 1.0.12.0 | a: own DoF pass + 37.8 MB 4K+ texture (VramTrack); b: CS PostProcessing also has Depth of Field |
| 461 | Interior DALC Fix | InteriorDALCFix.dll | 586 | 1.0.0.0 |  |
| 462 | Underwater NG | UnderwaterNG.dll | 1590 | 1.0.0.0 | c: UnderwaterNG_snapshots.log 2.7 MB and growing (never truncated) |
| 463 | CausticLight - Water Caustics | CausticLight.dll | 1111 | 1.0.4.0 | a: caustic light within 3000 units of water |
| 473 | Skyrim Performance Solution (SPS) - AE SSE VR | SPS.dll | 1314 | 1.0.73.0 | a: cull process, shadow accumulate/render, GetRenderPasses, RenderWorld, DDS loader, CreateTexture, Present, VM::Update, Character::Update; b: texture streamer overlaps FasterTextures, occlusion overlaps CS HiZ (auto-off), shadow cache auto-off; c: logs [Hitch] lines |
| 478 | Leaf Animation Fix SKSE | LeafAnimProbe.dll | 1470 | 1.0.0.0 | a: per-frame leaf anim override; d: probe-named dev build (v0.0.1), logging off |
| 507 | No Grass In Objects | NGIO-NG.dll | 1280 | 2.0.2.0 | a: grass creation/cache load on cell attach; raycasts |
| 512 | Grass Cache Helper NG | GrassCacheHelperNG.dll | 562 | 1.0.2.0 | b: companion of NGIO (expected pair) |
| 516 | Bottled Shaders - foxnne | CommunityShaders.dll | 38546 |  | a: whole render pipeline; HiZ occlusion (active); SnowDeformation warns it gathers footprints on the render thread; VramTrack.on writes VramTrack.jsonl (13 MB) at 1 Hz -> d |
| 520 | Smooth Terrain | SmoothTerrain.dll | 3236 | 0.6.0.0 | a: land quad build (BuildQuadTriShape) + player-cell sink; level 2 = 16x terrain triangles in a 5x5 quad square |
| 522 | Dynamic Interior Fog | DynamicInteriorFog.dll | 518 | 0.0.6.0 |  |
| 542 | Particle Limit Uncapper | ParticleLimitUncapper.dll | 2340 | 1.0.0.0 | a: raises particle caps (iMaxDesired 5000, cap1 x3, cap2 240) |
| 543 | Rim Lighting Removed | RimLightingRemoved.dll | 602 | 1.1.1.0 |  |
| 709 | Faster Objects | SkyrimPrecombines.dll | 3098 | 1.0.3.0 | a: cell attach, runtime bake workers; b: its Hi-Z is the 3rd occlusion culler (off) |
| 710 | Faster Textures | FasterTextures.dll | 886 | 1.0.2.0 | a: DDS loader + Present hook; b: second texture streamer (hands 436 textures to SPS at load) |
| 812 | Decal Seam Fix (SKSE) | DecalSeamFix.dll | 584 | 1.1.0.0 |  |
| 1643 | XPMF - Extended Projected Materials Framework | XPMF.dll | 5538 | 0.9.0.0 | a: geometry pass on cell load (projected materials) |
| 1657 | FYX - Alpha Blood Blending Bug - NG | AlphaBloodBlendingBug-Fix-NG.dll | 582 | 1.0.1.0 |  |
| 1787 | DynDOLOD DLL NG and Scripts 3.00 | DynDOLOD.DLL | 1230 | Alpha-43 | a: LOD/large-ref activation on cell change; b: two copies (NG Alpha-43 wins over Resources copy) |
| 1788 | DynDOLOD Resources SE | DynDOLOD.DLL | 310 | Alpha-59 | SHADOWED - not loaded; copy in "DynDOLOD DLL NG and Scripts 3.00" wins. a: LOD/large-ref activation on cell change; b: two copies (NG Alpha-43 wins over Resources copy) |
| 1834 | Native Mesh Light Flicker Fix | NativeMeshLightFlickerFix.dll | 889 | 1.7.2.0 |  |
| 1835 | LOD Refresh Bug Fix | SkyrimLODFixes.dll | 612 | 1.0.3.0 |  |
| 1838 | Horizon Fix | HorizonFix.dll | 3426 | 0.9.0.0 | a: Atmosphere::Update, BSWaterShader/BSEffectShader SetupGeometry (per draw); b: CS also ships a HorizonFix feature |
| 1895 | ENB Light Inventory Fix (ELIF) | ELIF.dll | 48 | 1.2.1.0 |  |
| 1927 | Universal (SKSE) Rim Lighting Fix | RimLightingFix.dll | 368 | 1.1.0.0 |  |
| 1928 | Grass Sampler Fix | GrassSamplerFix.dll | 582 | 1.0.1.0 | a: grass shader sampler state (cheap) |
| 1934 | ENB Light Detection Fix | ENBLightDetectionFix.dll | 594 | 1.0.0.0 |  |

## Lights (placement / patching) (14)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 333 | Torch NG | TorchNG.dll | 1920 | 1.1.0.4 |  |
| 396 | SeverActions 4.9.0 | Magelight.dll | 2926 | 4.9.0 |  |
| 445 | Magelight UI | Magelight.dll | 2926 | 1.9.0.0 | SHADOWED - not loaded; copy in "SeverActions 4.9.0" wins. |
| 458 | Kindle - Light Fade Fix | Kindle.dll | 336 | 1.1.2.0 |  |
| 523 | Portal Strict Lights Patcher Framework (SKSE) | PortalLightsRuntimePatcher.dll | 2268 | 2.0.0.0 | c: EnableLogging=true LogLevel=3 |
| 525 | Illuminated - Spell Lighting NG | Illuminated.dll | 2164 | 1.8.0.0 | a: cell-change light re-registration; c: 364 KB log per start |
| 527 | Re Light | Relight.dll | 3822 | 7.7.0.0 | a: replaces game lights, merges lights on cell load; c: invalid mod names in config; d: enableDebugLines=true |
| 530 | Helios | Heliosphan.dll | 6265 | 2.0.0.0 | a: sun/window light tuning (Luma) |
| 530 | Helios | HeliosTuning.dll | 1496 | 2.0.0.0 |  |
| 533 | ISL Helper SKSE | SKSE_ISL.dll | 642 | 1.0.5.0 |  |
| 536 | Light Placer | po3_LightPlacer.dll | 1554 | 5.0.0.0 | a: attaches lights on 3D load; c: 339 KB log per start |
| 537 | XEMI Utility | XEMIUtil.dll | 752 | 1.7.0.0 |  |
| 538 | Mini's Micro-Systems Framework (MMSF) | 00_MMSF.dll | 1084 | 2.1.0.0 |  |
| 539 | Luma Utility | LumaUtil.dll | 1240 | 2.1.0.0 |  |

## Physics / collision (31)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 156 | GT Softbody (OStim) | SMPFixes.dll | 1198 |  | a: SMP hooks (GT Softbody) |
| 202 | Banner Physics HDT-SMP | BannerPhysics.dll | 916 | 1.3.0.0 |  |
| 205 | Dynamic Armor Physics | DynamicArmorPhysics.dll | 2218 | 1.0.3.0 | c: iVerboseMode=1 |
| 313 | Immersive Elemental Water Interactions | ElementallyReactiveWaters.dll | 1059 | 2.1.0.0 |  |
| 321 | Skyrim Delirium - GTA IV-style physical hit reactions | SkyrimDelirium.dll | 1421 | 2.1.1.0 |  |
| 340 | True Collision Damage and True Fall Damage | TrueCollisionDamage.dll | 572 | 1.2.0.0 |  |
| 357 | Ricochet - Arrow Physics Framework | RicochetFramework.dll | 2822 | 1.1.2.0 |  |
| 363 | Better Grabbing | BetterGrabbing.dll | 938 | 1.17.0.0 |  |
| 420 | PPA Penetration Physics | AccuratePenetration.dll | 2436 |  | a: per-frame collision (scene only) |
| 422 | CBPC 1.7.3 | cbp.dll | 1104 |  | a: per-frame bounce/collision; b: second body-physics solver next to SMP (40 actors out of combat) |
| 423 | DripSim 1.0.0 | DripSim.dll | 833 | 1.0.0 | off (Enabled=false) - still loaded |
| 423 | DripSim 1.0.0 | DripSimRain.dll | 610 | 1.0.0 | Auto=false - idle |
| 455 | Responsive Grounds | ResponsiveGrounds.dll | 990 | 3.0.0.0 | a: footstep/ground response |
| 456 | SLOPPY Interactive Spider Webs | SloppyWebsInteractive.dll | 814 | 1.6.1.0 |  |
| 460 | Ice is Slick | IceIsSlick.dll | 1044 | 1.0.3.2 |  |
| 465 | Skyrim Water Inertia | SkyrimWaterInertia.dll | 632 | 1.2.0.0 |  |
| 470 | Bone Limit Extender | skyrimbonelimitfix.dll | 594 |  |  |
| 485 | Variadic Collision Dynamics | VariadicCollisionDynamics.dll | 3726 | 1.3.4.0 | a: Havok collision callbacks |
| 490 | Furniture SMP Physics Smoother | TMS_PhysicsSmoother.dll | 375 | 1.0.0.0 | a: SMP smoothing |
| 491 | First Person (FP) Inertia - SKSE | FPInertia.dll | 921 | 1.3.0.0 |  |
| 515 | Better Body Deformation | BetterDeformation.dll | 822 |  |  |
| 579 | Auto Physics Reset | AutoPhysicsReset.dll | 871 | 1.3.0.0 |  |
| 708 | SMP-NPC crash fix | SMP-NPC crash fix.dll | 30 | 1.0.0.0 |  |
| 711 | Faster HDT-SMP | hdtsmp64.dll | 4160 | 4.1.1.0 | a: Bullet solver every frame, frustum-based skeleton activation |
| 729 | OStrands 0.8.0 | 0_OStrands.dll | 1136 |  |  |
| 753 | TongueLab | TongueLab.dll | 1014 | 1.2.0.0 |  |
| 1836 | Water Collision Crash Fix NG | WaterCollisionCrashFix.dll | 898 | 1.1.2.0 |  |
| 1845 | Collision Sentinel - Crash Fix | CollisionSentinel.dll | 381 | 2.2.0.0 |  |
| 1858 | Explosion Collision Fix | ExplosionCollisionFix.dll | 520 | 1.0.1.0 |  |
| 1859 | Inertia (Floating Gear Fix) | Inertia.dll | 602 | 1.1.1.0 |  |
| 2003 | Deep Snow Makes You Slow | DeepSnow.dll | 900 |  |  |

## Wind / weather / environment FX (10)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 326 | True Cone Shouts - Shout Cone Fix SKSE | ConeShoutRuntimeVisuals.dll | 498 | 1.3.1.0 |  |
| 919 | Dynamic Wind Framework - SKSE Plugin | DynamicWind.dll | 3424 | 1.5.0.0 | a: tree/anim/visibility handlers on cell change and weather; c: 85 KB log per start |
| 920 | Particle Wind - SKSE Plugin | ParticleWind.dll | 2448 | 4.1.1.0 | a: per-particle-system wind |
| 936 | Dynamic Bloodpool Framework | DynamicBloodpoolFramework.dll | 1036 | 1.1.1.0 |  |
| 938 | Sanguine Symphony | SanguineSymphony.dll | 800 | 1.3.5.0 |  |
| 939 | Core Impact Framework (CIF) | CoreImpactFramework.dll | 1318 | 2.0.9.0 |  |
| 1651 | Moons And Stars - Sky Overhaul SKSE | po3_MoonMod.dll | 928 | 2.1.0.0 |  |
| 1652 | Splashes of Storms | po3_SplashesOfStorms.dll | 1350 | 1.4.0.0 | a: rain splash particles |
| 1653 | Splashes Of Skyrim | po3_SplashesOfSkyrim.dll | 939 | 1.6.0.0 |  |
| 1756 | Unique Map Weather | UniqueMapWeather.dll | 584 | 1.1.1.0 |  |

## Animation / behavior / IK (40)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 27 | Hand Guard - Hand and Arm Clipping Fix for SexLab and OStim | SLHandGuard.dll | 1194 | 0.5.8.0 |  |
| 115 | Grey's HPM HairPresetManager | HairPresetManager.dll | 18 | 1.0.0.0 |  |
| 122 | HairPositioner | HairPositioner.dll | 955 | 2.0.0.0 |  |
| 131 | Modified Optimal Gaze NG | ModifiedOptimalGazeNG.dll | 566 | 1.2.0.0 | b: 4 gaze/headtracking plugins (with TrueGaze, FourthWall, OGaze) |
| 132 | TrueGaze - Biological NPC Gaze and Kinematics Engine | TrueGaze.dll | 710 | 1.0.0.0 | a: Actor update hook; c: "Frame budget exceeded" warning |
| 134 | The Fourth Wall - Eye Contact | FourthWall.dll | 740 | 1.1.2.0 | b: gaze overlap |
| 136 | Smooth Lip Sync NG | SmoothLipSyncNG.dll | 533 | 1.2.0.0 |  |
| 137 | Better Facial Animations | BetterFacialAnimations.dll | 1372 | 6.1.2.1 |  |
| 198 | Left Hand Rings SKSE | LeftHandRingsSKSE.dll | 1106 | 0.4.2.0 |  |
| 256 | Body In First Person 1.21.1 | BodyInFirstPerson.dll | 1600 | 1.21.1 |  |
| 259 | Open Animation Replacer - IED Conditions - OAR 3.x Update | OpenAnimationReplacer-IEDConditionExtensions.dll | 576 | f1.03 |  |
| 264 | Animation Pitch Control | AnimationPitchControl.dll | 575 | 0.1.4.0 |  |
| 277 | Horse Behaviour Improvements | HorsePoseCorrection.dll | 569 | 1.1.0.0 |  |
| 286 | Inverse Kinematics - Feet of Skyrim | FeetOfSkyrim.dll | 1062 | 6.0.0.0 | a: foot IK raycasts for player+NPCs every frame (extraRaycasts on) |
| 288 | Disable Turn Animation NG | DisableTurnAnimation.dll | 830 | 3.0.0.0 |  |
| 291 | Draw Fix - Move Equip Animation Fix | DrawFixSKSE.dll | 992 | 1.4.2.0 |  |
| 304 | Open Animation Replacer - RaySense | OpenAnimationReplacer-RaySense.dll | 1242 | 1.2.0.0 |  |
| 442 | First Person (FP) Camera Settle - SKSE | FPCameraSettle.dll | 851 | 2.33.0.0 |  |
| 471 | Behavior Node Slimmer 0.1.1 | BehaviorNodeSlimmer.dll | 613 | 0.1.1 |  |
| 476 | Animation Injector | AnimationInjector.dll | 3293 | 1.0.8.0 |  |
| 484 | Bobbing Framework - SKSE Plugin | BobbingFramework.dll | 1133 | 3.1.0.0 |  |
| 594 | Animation Queue Fix | AnimationQueueFix.dll | 372 | 1.0.1.0 |  |
| 598 | Auto Skeleton Patch - Universal Behaviour Runtime | SkeletonAutoPatch.dll | 526 | 1.0.4.0 |  |
| 599 | A-Pose Bug Fix - Universal Behavior Runtime | APoseFix.dll | 9854 | 1.1.0.0-a |  |
| 699 | Immersive Equipment Displays | ImmersiveEquipmentDisplays.dll | 5530 | 1.7.4.0 | a: per-actor node updates; own ImGui UI |
| 700 | Simple Dual Sheath | SimpleDualSheath.dll | 534 | 1.5.9.0 |  |
| 717 | OGaze 3.5.1 | OGaze.dll | 1074 |  |  |
| 728 | Hand Guard 0.5.6.2 | SLHandGuard.dll | 1176 |  | SHADOWED - not loaded; copy in "Hand Guard - Hand and Arm Clipping Fix for SexLab and OStim" wins. |
| 757 | Fabulous Poser - OStim n Sexlab Live Animation Editor | FabulousPoser.dll | 1257 |  |  |
| 771 | Open Animation Replacer - IED Conditions | OpenAnimationReplacer-IEDConditionExtensions.dll | 1086 | 1.0.2.0 | SHADOWED - not loaded; copy in "Open Animation Replacer - IED Conditions - OAR 3.x Update" wins. |
| 772 | Open Animation Replacer | OpenAnimationReplacer.dll | 3756 | 3.2.0.0 | a: animation clip selection hooks; 136 KB log |
| 1882 | Animated Static Reload Fix - NG | AnimatedStaticReload.dll | 338 | d2025.1.9.0 |  |
| 1889 | Player Eyes Blink Fix | PlayerEyesBlinkFix.dll | 179 | 1.4.0.0-AE |  |
| 1890 | Mfg Fix NG | mfgfix.dll | 694 | 1.0.9.0 |  |
| 1916 | Paired Animation Improvements | PairedAnimationImprovements.dll | 410 | 1.0.2.0 |  |
| 1940 | Behavior Data Injector Universal Support | BehaviorDataInjector.dll | 826 | 0.13.0.4 |  |
| 1941 | Behavior Data Injector | BehaviorDataInjector.dll | 1315 | 0.13.0.0 | SHADOWED - not loaded; copy in "Behavior Data Injector Universal Support" wins. |
| 1943 | Payload Interpreter | PayloadInterpreter.dll | 426 | 1.1.0.0 |  |
| 1967 | Animation Motion Revolution | AnimationMotionRevolution.dll | 1434 | d2025.1.9.0 |  |
| 1972 | AnimObject Swapper | po3_AnimObjectSwapper.dll | 1188 | 2.0.0.0 |  |

## Movement / combat gameplay (61)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 35 | Dynamic Simple Knock System SKSE | DynamicSimpleKnock.dll | 863 | 1.3.3.0 |  |
| 40 | Rin Daughter of the Nine | CD57KnightFollowerIdleTimer.dll | 644 | 1.0.0.0 |  |
| 70 | Dragonborns Cohort | DragonbornsCohort.dll | 598 | 1.1.0.0 |  |
| 260 | Standing Stealth | StandingStealth.dll | 641 | 1.0.0.0 |  |
| 261 | FreeClimb - Slippery Climbing Addon | FreeClimb.dll | 2100 | 1.0.0.0 |  |
| 266 | SlideThrough | Squeeze-through.dll | 704 | 1.0.0.0 |  |
| 275 | Wait Your Turn Redux - Enemy Circling Behavior | WaitYourTurn.dll | 989 | 1.0.3.0 |  |
| 276 | FreeClimb | FreeClimb.dll | 2090 | 0.5.0.0 | SHADOWED - not loaded; copy in "FreeClimb - Slippery Climbing Addon" wins. |
| 278 | Diagonal Sprint - First Person Free Sprint | DiagonalSprint.dll | 3626 | 1.0.8.0 |  |
| 281 | DMCO 1st Person Dodge | a1stpersondodgekeysync.dll | 3012 | 1.0.0.0 |  |
| 284 | Skyrim's Paraglider Anniversary Edition Update | Paraglider.dll | 652 | 1.11.0.0 |  |
| 285 | Skyrim's Paraglider | Paraglider.dll | 742 | 1.0.0.0 | SHADOWED - not loaded; copy in "Skyrim's Paraglider Anniversary Edition Update" wins. |
| 289 | Dynamic Animation Casting - NG | loki_DynamicAnimationCasting.dll | 1638 | 3.2.4.0 |  |
| 290 | Dynamic Animation Casting | loki_DynamicAnimationCasting.dll | 826 | 1.5.1.0 | SHADOWED - not loaded; copy in "Dynamic Animation Casting - NG" wins. |
| 297 | HorsePower - Modernized Horse Riding (Total Riding Overhaul) | HorsePower.dll | 712 | 1.3.0.0 |  |
| 298 | StepUpOnto SKSE | StepUpOntoSKSE.dll | 453 | 1.5.0.0 |  |
| 303 | RaySense - Cover Animation | CoverAnimation.dll | 870 | 1.5.0.0 |  |
| 305 | Dodge Framework | DodgeFramework.dll | 830 | 1.0.0.0 |  |
| 306 | Dodge MCO-DXP | DodgeFramework.dll | 384 | 2.1.21.0 | SHADOWED - not loaded; copy in "Dodge Framework" wins. |
| 307 | MCO Universal Support | MCO.dll | 508 | 1.0.0.0 |  |
| 308 | BFCO - Attack Behavior Framework 3.100.1 | BFCO.dll | 1002 | 3.100.8.0A |  |
| 309 | SkyParkour V3 - Parkour Framework | SkyParkourNG.dll | 780 | 3.6.7.0 |  |
| 310 | Walk With Me | Wayfarer.dll | 2862 | 0.3.1 | d: diagnostics build "followers-diag-20260914-r2", 1 Hz persistent log, 8 MB rotations; a: follower scan |
| 314 | ONWARD - Auto-Move Overhaul | Onward.dll | 976 | 1.2.0.0 |  |
| 315 | Animated Bound Weapons | AnimatedBoundWeapons.dll | 1012 | 1.2.0.0 |  |
| 316 | Spell Aim Marker | SpellAimMarker.dll | 618 | 1.0.0.0 |  |
| 318 | Apocrypha Tentacle Combat | TentacleCombat.dll | 706 | 1.2.0.0 |  |
| 322 | STB Projectile Control | STB_ProjectileControl.dll | 1094 | 1.0.0.0 |  |
| 323 | SkyPraxis - Spell learning | SkyPraxisNG.dll | 590 | 2.0.0.0 |  |
| 324 | Give me another fight - A nemesis system | PlayerNemesis.dll | 1016 | 1.0.1.0 |  |
| 325 | Trick Death - A checkpoint and respawn system | TrickDeath.dll | 1284 | 1.2.0.0 |  |
| 327 | Positional Spell Cast Sound (Hand-Attached) | HandPositionalSound.dll | 376 | 1.0.0.0 |  |
| 328 | Unpoisoned Blocking | UnpoisonedBlocking.dll | 1855 | 1.0.0.0 |  |
| 330 | Accuracy | Accuracy.dll | 2147 | 1.0.0.0 |  |
| 331 | Simple Offence Suppression | po3_SimpleOffenceSuppression.dll | 792 | 2.3.0.0 |  |
| 332 | NPC Spell Variance - Spell Variety AI | NPCSpellVariance.dll | 775 | 2.7.0.0 |  |
| 334 | Magic Organizer SKSE - Hide Spells Powers Active Effects | MagicOrganizer.dll | 982 | 1.2.0.0 |  |
| 335 | Manual Crossbow Reloading - SKSE | ManualCrossbowReloading.dll | 1377 | 1.1.0.0 |  |
| 342 | Headshots Kill SKSE | HeadshotsKill.dll | 872 | 1.41.0.0 |  |
| 344 | Precision - NPC Combat Fix | PrecisionNpcAimFix.dll | 2356 | 1.0.8.0 |  |
| 347 | Universal Arrow Spin - SKSE plugin | UniversalArrowSpin.dll | 721 | 1.1.0.0 |  |
| 354 | Perfectly Valid Wards | PerfectlyValidWards.dll | 796 | 3.0.0.0 |  |
| 355 | Dismembering Framework | DismemberingFramework.dll | 2636 | 1.2.2.0 |  |
| 356 | Next-Gen Decapitations | NextGenDecapitations.dll | 782 | 1.4.4.0 |  |
| 358 | Precision | Precision.dll | 1838 | 2.0.4.0 | a: weapon collision during attacks |
| 360 | Valhalla Combat | valhallaCombat.dll | 582 | 1.3.3.0 |  |
| 361 | Aggro Management in Skyrim | SmartNPCTargetSelector.dll | 625 | 1.3.2.0 |  |
| 368 | Cinematic Clash - Standoffs of Skyrim | CinematicClash.dll | 1322 | 1.0.2.0 |  |
| 370 | Paths of Empyrean | PathsOfEmpyrean.dll | 1302 |  |  |
| 580 | Sprint Stuttering Fix | SprintStutteringFix.dll | 536 | 1.0.0.0 |  |
| 1761 | True Directional Movement - Modernized Third Person Gameplay | TrueDirectionalMovement.dll | 997 | 2.2.7.0 |  |
| 1818 | Exit Sneak On Sprint | SprintCancelsSneak.dll | 802 | 1.2.1.0 |  |
| 1825 | Classic Sprinting Redone (SKSE64) | ClassicSprintingRedone.dll | 676 | 2.4.0.0 |  |
| 1830 | I'm walkin' here NG | ImWalkinHere.dll | 358 | 1.7.0.0 |  |
| 1860 | Death Drop Overhaul - Latest Version | DeathDropOverhaul.dll | 826 | 1.3.6.0 |  |
| 1911 | Shout Recovery Utilities | ShoutRecoveryOverhaul.dll | 346 | 1.1.0.0 |  |
| 1920 | IFrame Generator RE AE Support | MaxsuIFrame.dll | 1000 | 1.3.1.0 |  |
| 1932 | Better Combat Escape - NG | MaxsuCombatEscape.dll | 326 | 1.0.1.0 |  |
| 1933 | Better Combat Escape - SSE | MaxsuCombatEscape.dll | 292 | 0.83.0.0 | SHADOWED - not loaded; copy in "Better Combat Escape - NG" wins. |
| 1938 | Comprehensive Attack Rate Patch - SKSE | ComprehensiveAttackRatePatch.dll | 2288 | 1.1.5.1 |  |
| 1950 | Better Jumping SE | BetterJumpingSE.dll | 969 | 1.9.5.0 |  |

## AI / LLM (SkyrimNet family) (19)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 393 | NarrativeEngine | NarrativeEngine.dll | 3239 | d2026.11.11 | a: FineRoads graph rebuild per cell change; c: debug-level log |
| 394 | Battle Summaries 1.5.0 | BattleSummaries.dll | 1032 | 1.5.0 |  |
| 395 | Papyrus MessageBox 1.0.0 | SkyrimScripting.MessageBox.dll | 581 | 1.0.0 |  |
| 396 | SeverActions 4.9.0 | Phantasm.dll | 2838 | 4.9.0 |  |
| 396 | SeverActions 4.9.0 | SeverActionsNative.dll | 10564 | 4.9.0 | a: furniture occupancy scans on cell change; c: chatty |
| 397 | IntelEngine 3.8.2 | IntelEngine.dll | 6137 | 3.8.2 | c: 186 KB log per start |
| 398 | PlayerSignals 0.2.1 | PlayerSignals.dll | 846 | 0.2.1 |  |
| 399 | OMind 0.8.0 | OMind.dll | 1094 |  |  |
| 400 | Physical Letters 1.1.1 | PhysicalLetters.dll | 2949 |  |  |
| 401 | DragonSense 0.5.0 | DragonSense.dll | 2691 | 0.5.0 |  |
| 402 | Ink and Quill 0.2.0 | InkAndQuill.dll | 1198 |  |  |
| 405 | Smart Talk (Dialogue Menu Enhancer) | SmartTalk.dll | 2316 | 1.0.5.0 |  |
| 406 | Dragonborn ReVoiced | DBReV.dll | 1109 | 1.5.2.0 |  |
| 413 | Phantasm | Phantasm.dll | 2618 | 1.0.0.0 | SHADOWED - not loaded; copy in "SeverActions 4.9.0" wins. |
| 419 | Hypnosis 1.2.0 | HypnosisNative.dll | 1330 |  |  |
| 713 | Dynamic Dialogue Framework 3.1 | TMS_DynamicDialogue.dll | 2186 |  |  |
| 741 | OStimNet for SkyrimNet 2.6.2 | OStimNet.dll | 2292 | 2.6.2.0 |  |
| 744 | SkyrimNet 1.2.0-rc2 | SkyrimNet.dll | 71526 | 1.2.0-rc2 | a: 71 MB plugin, game-thread event/trigger polling, PrismaUI views; c: 180-680 KB log per session, BSA read warnings |
| 747 | BodyLanguage 2.1.1 | BodyLanguage.dll | 2474 | 2.1.1 |  |

## OStim / adult (16)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 424 | Cinematic OStim Camera (COC) 1.0.11 | CinematicOStimCamera.dll | 2073 | 1.0.11.0 |  |
| 425 | OCinema 0.9.14 | OCinema.dll | 1292 | 0.9.14 |  |
| 492 | OBody NG | OBody.dll | 1746 | 5.3.0.0 | distribution on actor load |
| 712 | Dynamic Moans 1.0 | TMS_DynamicMoans.dll | 538 |  |  |
| 716 | OSIS 2.0.0 | OSIS.dll | 1752 |  |  |
| 718 | Cinematic OStim Camera 1.0.5 | CinematicOStimCamera.dll | 2035 |  | SHADOWED - not loaded; copy in "Cinematic OStim Camera (COC) 1.0.11" wins. |
| 721 | Vampire Feed Proxy 1.3 | VampireFeedProxy.dll | 2165 |  |  |
| 723 | OStim NPCs 2.2.0 | OStimNPCs.dll | 574 |  |  |
| 725 | Stage Flow OStim 1.7 | TMS_StageFlow.dll | 661 |  |  |
| 742 | OStim Navigator 2.3.0 | OStimNavigator.dll | 1922 | 2.3.0 |  |
| 743 | OStim Hot Swap 1.0.0 | OStimHotSwap.dll | 986 | 1.0.0 |  |
| 745 | OStim Prism 1.0.0 | OStimPrism.dll | 1095 |  |  |
| 746 | OStim Scene Menu Paging 1.0 | OStimPagingSKSE.dll | 578 | 1.2.0.0 |  |
| 748 | OStim Restore SOS-TNG Faction | OStimRestoreSOSFaction.dll | 2241 |  |  |
| 770 | OStim Standalone 7.5.1c | OStim.dll | 8666 |  |  |
| 1114 | TNG 4.2.7 | TheNewGentleman.dll | 1225 |  |  |

## UI / HUD / overlay / camera (72)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 36 | Apocrypha Menu Framework | !ApocryphaMenuFramework-SMFName.dll | 12 | 2.4.1.0 |  |
| 36 | Apocrypha Menu Framework | !ApocryphaMenuFramework.dll | 4968 | 2.4.1.0 | b: overlay framework #2 |
| 57 | Risas All In One Menu 6.8 | RisaAllInOneMenu.dll | 3345 | 6.8 | b: ImGui overlay #3 |
| 57 | Risas All In One Menu 6.8 | RisaUI.dll | 1714 | 6.8 | b: ImGui overlay |
| 116 | RaceMenu Atelier | RaceMenuAtelier.dll | 1188 |  |  |
| 348 | Unsearched Corpse Indicator | UnsearchedCorpsesIndicator.dll | 388 | 1.3.2.0 |  |
| 349 | How many days passed - HMDP | DaysPassed.dll | 956 | 1.0.0.0 |  |
| 362 | Status Indicator Framework - Floating Icons | StatusIndicatorFramework.dll | 3212 | 1.0.2.0 | a: floating icons world-to-screen per frame |
| 374 | Dynamic Location Popups | po3_DynamicLocationPopups.dll | 855 | 1.0.2.0 |  |
| 430 | CINEMACAM - Camera Overhaul | Cinemacam.dll | 1726 | 2.2.3.0 |  |
| 432 | CROSSHAIR - Crosshair Overhaul 1.0 | CrosshairOverhaul.dll | 1260 | 1.2.0.0 |  |
| 433 | SpeedyUI | SpeedyUI.dll | 2982 | 0.2.1.0 | a: re-times Scaleform movies (interpolated, target 60 fps) - advances UI more often |
| 435 | HUD NG | HudNG.dll | 1852 | 1.0.5.0 | b: HUD framework next to TrueHUD/ImmersiveHUD/STB Widgets |
| 437 | Local Map Upgrade SKSE Menu Framework | LocalMapUpgrade.dll | 724 | 1.2.7.0 |  |
| 438 | TrueHUD Focus | TrueHUDFocus.dll | 611 | 1.0.0.0 |  |
| 439 | Cinematic Idle Camera | cinematicidlecamera.dll | 5776 | 1.3.1.0 |  |
| 440 | Cinematic Conversation Camera | SceneDirector.dll | 1679 | 1.5.5.0 |  |
| 441 | UI Parallax | SkyrimHudParallax.dll | 1908 | 3.0.0.0 |  |
| 443 | Kill Feed | po3_KillFeed.dll | 3034 | 1.2.0.0 |  |
| 444 | CINEMA - Dynamic Combat Letterboxes | Cinema.dll | 5429 | 1.0.5.0 | a: letterbox overlay |
| 446 | Floating Subtitles | po3_FloatingSubtitles.dll | 2537 | 3.3.5.0 |  |
| 447 | [NO DELETE] ImmersiveHUD SKSE | ImmersiveHUD.dll | 1140 | 3.2.2.0 |  |
| 449 | Grid Inventory | GridInventory.dll | 3257 | 1.6.6 |  |
| 469 | Inventory Interface Information Injector Improved | InventoryInjectorImproved.dll | 768 | 0.5.1.0 |  |
| 479 | Easy Goes It - A Scrolling Speed Mod | EasyGoesIt.dll | 803 | 0.2.4.0 |  |
| 488 | Fuzz's Legally Intelligible Core Kit | FUCK.dll | 4036 | 1.8.2.0 | b: ImGui kit overlay #4 |
| 503 | Flat World Map Framework | BakaWorldMapSpeed.dll | 570 | 1.9.990.0 |  |
| 503 | Flat World Map Framework | FlatMapMarkersSSE.dll | 576 | 1.9.990.0 |  |
| 508 | SearchUI - Get Any Item Instantly | SearchUI.dll | 876 | 1.2.0.0-license-fix |  |
| 511 | SKSE Menu Framework | SKSEMenuFramework.dll | 4476 | 3.18.0.0 | b: ImGui overlay #1 (Present hook) |
| 732 | Prisma UI 1.5.1 | PrismaUI.dll | 2022 |  | a/b: Ultralight web renderer composited every frame (views: SkyrimNet, TrickDeath, OStim Prism...) |
| 1713 | Compass Navigation Overhaul | CompassNavigationOverhaul.dll | 1836 | 2.2.0.0 | a: per-frame compass |
| 1719 | First Person FOV and Tween Menu Fix SKSE | FirstPersonFOV.dll | 623 | 1.0.11.0 |  |
| 1721 | Detection Meter - AE Support | MaxsuDetectionMeter.dll | 1053 | 1.11.0.0AE |  |
| 1722 | Detection Meter | MaxsuDetectionMeter.dll | 2019 | 1.11.0.0 | SHADOWED - not loaded; copy in "Detection Meter - AE Support" wins. |
| 1723 | Modern Wait Menu | Modern-Wait-Menu.dll | 554 | 2.1.1.0 |  |
| 1724 | Inventory Interface Information Injector (SE) | InventoryInjector.dll | 926 | 1.1.1.0 |  |
| 1726 | STB Widgets | STB_Widgets.dll | 1114 | 2.7.0.0 |  |
| 1728 | Desktop Splash Screen | _SplashScreen.dll | 313 | 1.0.1.0 |  |
| 1730 | Local Map Upgrade | LocalMapUpgrade.dll | 1782 | 3.1.0.0 | SHADOWED - not loaded; copy in "Local Map Upgrade SKSE Menu Framework" wins. |
| 1731 | Regular Quicksave for System Menu for 1.6.1170 | MenuRegularQuickSave.dll | 538 | 1.0.0.0 |  |
| 1733 | SkyUI - Fixed Note Icon | FixNotesForSkyUI.dll | 320 | 1.2.6.0 |  |
| 1735 | Casting Bar | CastingBar.dll | 602 | 4.0.0.0 |  |
| 1741 | SmoothCam | SmoothCam.dll | 1642 | 1.8.1.0 |  |
| 1742 | PhotoMode | po3_PhotoMode.dll | 4048 | 3.0.4.0 |  |
| 1744 | No Furniture Camera | NoFurnitureCamera.dll | 578 | 1.0.1.0 |  |
| 1746 | Infinity UI | InfinityUI.dll | 1374 | 2.0.3.0 | b: Scaleform injector |
| 1751 | More Informative Console | MoreInformativeConsole.dll | 1322 | 1.2.3.1 |  |
| 1754 | Oxygen Meter 2 | oxygenMeter2.dll | 872 | 1.0.7.0 |  |
| 1757 | HD Local Map | HDLocalMap.dll | 584 | 1.0.3.0 |  |
| 1762 | Better Third Person Selection - BTPS | BetterThirdPersonSelection.dll | 2667 | 0.8.9.0 | a: per-frame crosshair raycasts |
| 1763 | moreHUD Inventory Edition | AHZmoreHUDInventory.dll | 644 | 2.2.4.0 |  |
| 1764 | moreHUD SE | AHZmoreHUDPlugin.dll | 799 | 5.4.6.0 |  |
| 1765 | TrueHUD - Inventory Injector Patch | TrueHUD.dll | 2795 | 1.4.0.0 | a: per-frame world-to-screen bars; b: two copies |
| 1766 | TrueHUD - HUD Additions | TrueHUD.dll | 742 | 1.1.9.0 | SHADOWED - not loaded; copy in "TrueHUD - Inventory Injector Patch" wins. a: per-frame world-to-screen bars; b: two copies |
| 1772 | Security Overhaul SKSE - Lock Variations | po3_LockVariations.dll | 1082 | 4.1.0.0 |  |
| 1773 | MCM Memory - Settings Backup and Restore | MCMMemory.dll | 4458 | 1.6.0.0 |  |
| 1774 | MCM Unlocked | MCM-Unlocked.dll | 1110 | 2.1.6.0 |  |
| 1775 | MCM Helper | MCMHelper.dll | 1118 | 1.6.2.0 |  |
| 1776 | ShowRaceMenu - NG | ShowRaceMenu-NG.dll | 645 | 1.0.5.0 |  |
| 1777 | Race Menu Player Rotation | RaceMenuPlayerRotation.dll | 818 | d2025.1.9.0 |  |
| 1779 | RaceMenu | skee64.dll | 2462 | 0.4.20.0 | c: iLogLevel=5 (debug) logs every .tri load; 12 morph bind errors per start (Argonian HPH) |
| 1819 | Easy Console Commands | ECC_Utils.dll | 938 | 1.1.0.0 |  |
| 1921 | HelpExtender | HelpExtender.dll | 582 | 1.3.0.0 |  |
| 1922 | Console Commands Extender - Anniversary Edition Update | CCExtender.dll | 791 | 1.12.0.0 |  |
| 1948 | Whose Quest is it Anyway NG | WhoseQuestIsItAnyway.dll | 2901 | 1.6.0.0 |  |
| 1949 | Stay At The System Page NG | StayAtSystemPageSE.dll | 2198 | 1.7.0.0 |  |
| 1962 | Rogue's Gallery | RoguesGallery.dll | 2072 | 1.0.1.0 |  |
| 1963 | Widescreen Scale Removed for 1-6-1130 and higher | WidescreenScaleRemoved.dll | 604 | 1.0.4.0 |  |
| 1966 | ConsoleUtilSSE NG | ConsoleUtilSSE.dll | 2754 | 1.6.1.0 |  |
| 1975 | Scaleform Translation Plus Plus NG | ScaleformTranslationPP.dll | 2290 | 1.10.0.0 |  |
| 1976 | ConsolePlusPlus | po3_ConsolePlusPlus.dll | 854 | 1.5.0.0 |  |

## Engine fixes / loaders / memory (31)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 472 | Crash Fix Compendium | CrashFixCompendium.dll | 972 | 1.4.0.0 |  |
| 474 | Baked Goods - Skyrim Engine Fixes | BakedGoods.dll | 857 | 1.4.0.0 |  |
| 480 | Auto Output Switch - Redux | AutoAudioSwitch.dll | 988 | 1.0.0.0 |  |
| 1816 | AltTabFix 1.1.0 | AltTabFix.dll | 660 | 2.0.1.0 |  |
| 1821 | RemoveAllItems Freeze Fix | RemoveAllItemsFix.dll | 520 | 1.1.0.0 |  |
| 1827 | Media Keys Fix SKSE | MediaKeysFix.dll | 390 | 1.0.1.0 |  |
| 1828 | Kill Caps Lock NG | KillCapsLockNG.dll | 552 | 1.0.0.1 |  |
| 1832 | Better AltTab | BetterAltTab.dll | 636 | 1.0.1.0 |  |
| 1833 | Auto Input Switch | AutoInputSwitch.dll | 583 | 1.3.0.0 |  |
| 1837 | GC Bug Fix | GCBugFix.dll | 834 | 1.0.1.0 |  |
| 1856 | skyrim-freeze-fix | skyrim-freeze-fix.dll | 526 | 0.0.4.0 |  |
| 1870 | Script Effect Archetype Crash Fix | ScriptEffectArchetypeCrashFix.dll | 454 | 1.0.0.0 |  |
| 1884 | Actor Limit Fix | ActorLimitFix.dll | 550 | 9.0.0.0 |  |
| 1897 | Scrambled Bugs | ScrambledBugs.dll | 607 | 21.0.0.0 |  |
| 1898 | Bug Fixes SSE | BugFixesSSE.dll | 556 | 10.0.0.0 |  |
| 1899 | DPI Scaling Fix | DPIScalingFix.dll | 512 | d2025.1.9.0 |  |
| 1900 | Skyrim Priority SE AE - CPU Performance FPS Optimizer | PriorityMod.dll | 128 | 3.4.0.0 | process priority High + affinity 0xFFF5 (verified live) |
| 1906 | Save Unbaker | po3_SaveUnbaker.dll | 855 | 1.0.6.0 |  |
| 1909 | Native EditorID Fix | NativeEditorIDFix.dll | 308 | 1.2.3.0 |  |
| 1917 | MergeMapper | MergeMapper.dll | 895 | 1.6.2.0 |  |
| 1929 | Sound Fix for Large Sector Drives | large_sector_fix.dll | 12 | 4.0.0.0 |  |
| 1930 | Recursion Monitor | RecursionFPSFix.dll | 844 | 1.2.0.0 | Papyrus stack overflow hook |
| 1944 | Disk Cache Enabler | diskCacheEnabler.dll | 145 | 1.2.0.0 | b: file-cache flag (overlaps OS cache; harmless) |
| 1960 | Disabled Reference Integrity Fix (SKSE) | DisabledReferenceIntegrityFix.dll | 2324 | 1.5.0.0 |  |
| 1964 | LeveledList Crash Fix | LeveledListCrashPrevention.dll | 882 | 2.0.0.0 |  |
| 1977 | Papyrus Tweaks 4.1.1 | PapyrusTweaks.dll | 993 | 4.2.1.0 |  |
| 1978 | powerofthree's Tweaks | po3_Tweaks.dll | 1085 | 1.16.0.0 |  |
| 1985 | Crash Logger SSE AE VR - PDB support | CrashLogger.dll | 3250 | 1.27.0.0 | keep |
| 1985 | Crash Logger SSE AE VR - PDB support | msdia140.dll | 2637 | 1.27.0.0 |  |
| 1986 | SSE Display Tweaks | SSEDisplayTweaks.dll | 564 | 0.5.16.0 | a: Present hook, frame limiter 240, VSync on; c: LogLevel=debug |
| 1987 | EngineFixes | EngineFixes.dll | 2398 | 7.0.20.0 | a: allocator replacement (TBB) |

## Dev / debug tooling (1)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 415 | devbench | devbench.dll | 2988 | 1.32.0 | d: dev bridge, HTTP/MCP server on 127.0.0.1:8920, console hooks (needed by the benchmark) |

## Audio (6)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 477 | Audio Util | AudioUtil.dll | 1616 | 1.0.0.0 |  |
| 483 | Audio Occlusion | AudioOcclusion.dll | 1050 | 1.2.2.0 | a: raycasts per sound source up to 4096 units, exterior on |
| 810 | Sound Record Distributor | SoundRecordDistributor.dll | 904 | 1.5.3.0 |  |
| 811 | Music Type Distributor | MusicTypeDistributor.dll | 734 | 1.4.0.0 |  |
| 1913 | Fuz Ro D-oh - Silent Voice | Fuz Ro D'oh.dll | 337 | 2.5.0.0 |  |
| 1931 | Combat Music Fix NG | CombatMusicFixNG.dll | 596 | 2.0.0.0 |  |

## Frameworks / distributors / papyrus libs (28)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 468 | NPCs Names Distributor | NPCsNamesDistributor.dll | 1405 | 2.6.4.0 |  |
| 1804 | Alchemy XP Fix | po3_AlchemyXPFix.dll | 767 | 1.0.0.0 |  |
| 1822 | Dual Casting Fix | po3_DualCastingFix.dll | 568 | 1.0.0.0 |  |
| 1824 | Camera Persistence Fixes | po3_CameraPersistenceFixes.dll | 922 | 1.2.0.0 |  |
| 1831 | Favorite Misc Items | po3_FavoriteMiscItems.dll | 810 | 4.0.0.0 |  |
| 1912 | Papyrus Ini Manipulator | PapyrusIniManipulator.dll | 664 | 1.9.8.0 |  |
| 1914 | Container Distribution Framework | ContainerDistributionFramework.dll | 1076 | 3.1.0.0 |  |
| 1915 | Container Item Distributor | ContainerItemDistributor.dll | 658 | 2.1.3.0 |  |
| 1918 | MCU - 0.3.0 - Main files | aTweaks.dll | 2182 | 2.2.1.0 |  |
| 1923 | Actor Value Generator | ActorValueGenerator.dll | 3471 | 2.3.6.0 |  |
| 1924 | dTry Plugin Updates | DtryKeyUtil.dll | 370 | d2026.9.12.0 |  |
| 1926 | dTry's Key Utils | DtryKeyUtil.dll | 645 | 1.1.0.0 | SHADOWED - not loaded; copy in "dTry Plugin Updates" wins. |
| 1935 | FISSES patch for Skyrim AE 1.6.1130 (or later) | FISS.dll | 426 | 1.4.2.0 |  |
| 1936 | FileAccess Interface for Skyrim SE Scripts - FISSES | fiss.dll | 202 | 1.4.1.0 | SHADOWED - not loaded; copy in "FISSES patch for Skyrim AE 1.6.1130 (or later)" wins. |
| 1937 | SkyPatcher | SkyPatcher.dll | 2578 | 8.0.1.0 |  |
| 1939 | Perk Entry Point Extender | PerkEntryPointExtender.dll | 2636 | 2.3.7.0 |  |
| 1945 | Enhanced Invisibility | po3_EnhancedInvisibility.dll | 838 | 1.4.1.0 |  |
| 1946 | Enhanced Reanimation | po3_EnhancedReanimation.dll | 858 | 1.5.2.0 |  |
| 1952 | Essential Favorites | po3_EssentialFavorites.dll | 846 | 2.4.2.0 |  |
| 1961 | Lexicon SKSE | LexiconSKSE.dll | 6816 | 0.6.3.0 | c: trace-level log 400 KB per start |
| 1965 | PAPER | PAPER.dll | 441 | 2.2.4.0 |  |
| 1969 | Keyword Item Distributor (KID) | po3_KeywordItemDistributor.dll | 1710 | 4.1.0.0 |  |
| 1970 | Spell Perk Item Distributor (SPID) | po3_SpellPerkItemDistributor.dll | 1905 | 7.3.3.0 |  |
| 1971 | FormList Manipulator - FLM | FormListManipulator.dll | 938 | 1.8.1.0 |  |
| 1973 | Base Object Swapper | po3_BaseObjectSwapper.dll | 1198 | 3.5.0.0 |  |
| 1974 | JContainers SE | JContainers64.dll | 2946 | 4.3.2.0 |  |
| 1979 | powerofthree's Papyrus Extender | po3_PapyrusExtender.dll | 3134 | 6.4.2.0 |  |
| 1980 | PapyrusUtil SE - Modders Scripting Utility Functions | PapyrusUtil.dll | 1402 | 4.6.0.0 |  |

## Fixes / misc gameplay (26)

| Prio | Mod folder | DLL | KB | Ver | Flags / notes |
|---:|---|---|---:|---|---|
| 79 | NPC Fixer - Invisible and Naked NPC Fixer | NakedNPCFix.dll | 710 | 1.8.1.0 |  |
| 1820 | Bound Weapon Fix | BoundWeaponFix.dll | 762 | 1.0.0.0 |  |
| 1823 | Fix Toggle Walk Run (SKSE plugin) | FixToggleWalkRun.dll | 586 | 3.0.0.0 |  |
| 1829 | Instantly Skip Dialogue NG | InstantlySkipDialogueNG.dll | 639 | 1.1.1.0 |  |
| 1847 | Auto Follower Stuck Sneaking Fix SKSE | AutoSneakBugFix.dll | 522 | 1.5.0.0 |  |
| 1848 | Stuck on Screen Auto Load Door Fix SKSE | StuckDoor.dll | 2080 | 0.3.1.0 |  |
| 1849 | Project Combat Event Fixes - Fix NPCs Stuck in Combat | ProjectCombatEventFixes.dll | 584 | 2.0.0.0 |  |
| 1850 | Project Bro He's There - Fix followers not starting combat | ProjectBroHesThere.dll | 590 | 2.3.0.0 |  |
| 1852 | Keep Up - Follower Locomotion Fix | tesfankeepup.dll | 393 | 4.3.1.0 |  |
| 1853 | First Person Height Fix SKSE | FirstPersonScaleFix.dll | 578 | 2.0.0.0 |  |
| 1861 | Death Idle Fix | DeathIdleFix.dll | 623 | 1.0.2.0 |  |
| 1872 | Vendor Respawn Fix | VendorRespawnFix.dll | 460 | 1.0.0.0 |  |
| 1881 | Sprint Sneak Movement Speed Fix | SSMT_Fix.dll | 370 | 1.1.2.0 |  |
| 1883 | NPC AI Process Position Fix - NG | MaxsuAIProcessFix.dll | 391 | d2025.1.9.0 |  |
| 1885 | Zero Bounty Hostility Fix | ZeroBountyHostilityFix.dll | 1970 | 0.7.0.0 |  |
| 1891 | Beard Mask Fix | BeardMaskFix.dll | 362 | 1.0.1.0 |  |
| 1892 | Face Discoloration Fix | FaceGenFixes.dll | 368 | 1.0.3.0 |  |
| 1893 | Equip Enchantment Fix | EquipEnchantmentFix.dll | 423 | 1.3.7.0 |  |
| 1894 | Barter Limit Fix | BarterLimitFix.dll | 230 | d2025.1.9.0 |  |
| 1896 | Don't Stay in The Water | NPCWaterAIFix.dll | 450 | 5.1.0.0 |  |
| 1904 | Locked Empty Container Activate Text Fix | LockedEmptyContainerActivateTextFix.dll | 398 | 1.0.0.0 |  |
| 1908 | Unstack Stolen Items | UnstackStolenItems.dll | 879 | 2.0.4.0 |  |
| 1924 | dTry Plugin Updates | NoCrimeTeleportRE.dll | 520 | d2026.9.12.0 |  |
| 1925 | No Crime Teleport RE | NoCrimeTeleportRE.dll | 324 | 1.0.0.0 | SHADOWED - not loaded; copy in "dTry Plugin Updates" wins. |
| 1947 | To Your Face SE | ToYourFace.dll | 207 | 1.0.0.0u |  |
| 1951 | Considerate Followers - Followers are Silent During Dialogue | ConsiderateFollowers.dll | 969 | 1.3.0.0 |  |

## Duplicate DLL names (same file in two enabled mods)

- slhandguard.dll: wins "Hand Guard - Hand and Arm Clipping Fix for SexLab and OStim" (1194 KB); shadowed: "Hand Guard 0.5.6.2" (1176 KB)
- openanimationreplacer-iedconditionextensions.dll: wins "Open Animation Replacer - IED Conditions - OAR 3.x Update" (576 KB); shadowed: "Open Animation Replacer - IED Conditions" (1086 KB)
- freeclimb.dll: wins "FreeClimb - Slippery Climbing Addon" (2100 KB); shadowed: "FreeClimb" (2090 KB)
- paraglider.dll: wins "Skyrim's Paraglider Anniversary Edition Update" (652 KB); shadowed: "Skyrim's Paraglider" (742 KB)
- loki_dynamicanimationcasting.dll: wins "Dynamic Animation Casting - NG" (1638 KB); shadowed: "Dynamic Animation Casting" (826 KB)
- dodgeframework.dll: wins "Dodge Framework" (830 KB); shadowed: "Dodge MCO-DXP" (384 KB)
- magelight.dll: wins "SeverActions 4.9.0" (2926 KB); shadowed: "Magelight UI" (2926 KB)
- phantasm.dll: wins "SeverActions 4.9.0" (2838 KB); shadowed: "Phantasm" (2618 KB)
- cinematicostimcamera.dll: wins "Cinematic OStim Camera (COC) 1.0.11" (2073 KB); shadowed: "Cinematic OStim Camera 1.0.5" (2035 KB)
- localmapupgrade.dll: wins "Local Map Upgrade SKSE Menu Framework" (724 KB); shadowed: "Local Map Upgrade" (1782 KB)
- maxsudetectionmeter.dll: wins "Detection Meter - AE Support" (1053 KB); shadowed: "Detection Meter" (2019 KB)
- truehud.dll: wins "TrueHUD - Inventory Injector Patch" (2795 KB); shadowed: "TrueHUD - HUD Additions" (742 KB)
- dyndolod.dll: wins "DynDOLOD DLL NG and Scripts 3.00" (1230 KB); shadowed: "DynDOLOD Resources SE" (310 KB)
- dtrykeyutil.dll: wins "dTry Plugin Updates" (370 KB); shadowed: "dTry's Key Utils" (645 KB)
- nocrimeteleportre.dll: wins "dTry Plugin Updates" (520 KB); shadowed: "No Crime Teleport RE" (324 KB)
- maxsucombatescape.dll: wins "Better Combat Escape - NG" (326 KB); shadowed: "Better Combat Escape - SSE" (292 KB)
- fiss.dll: wins "FISSES patch for Skyrim AE 1.6.1130 (or later)" (426 KB); shadowed: "FileAccess Interface for Skyrim SE Scripts - FISSES" (202 KB)
- behaviordatainjector.dll: wins "Behavior Data Injector Universal Support" (826 KB); shadowed: "Behavior Data Injector" (1315 KB)

## Overlaps (verified from logs unless marked inferred)

- Occlusion culling, 3 implementations installed, 1 active: Bottled Shaders HiZ Occlusion (active); SPS "Hide occluded objects" stands down (`SPS.log`: "Bottled Shaders HiZ Occlusion Culling is active - SPS Hide occluded objects stays off"); Faster Objects Hi-Z off (`bHiZ=0`, log "Hi-Z occlusion OFF").
- Texture streaming, 2 active at once: Faster Textures (Mode=2, loads small first) and SPS TextureStream (`SPS_User.ini`: bBudgetMode=false, bStreamClothing=true, bStreamCharacters=true, fMaxEdge=2048). `FasterTextures.log`: "handed to Skyrim Performance Solution: 436"; `SPS.log`: "[Hitch] 145 ms | ... frame before: reloaded 151 (282 MB)".
- Texture Downscaler: the mod `Texture Downscaler` is DISABLED in modlist.txt and TextureDownscaler.dll is not in skse64.log; its last log is 11-16 11:34. Texture size is now governed by SPS (max edge 2048) + Faster Textures + the `foxnne - 2K Downscale (winning 4K textures)` asset mod.
- Shadow caches: SPS LightShadowCache auto-off with Bottled Shaders; FarShadowCache off.
- Body physics: Faster HDT-SMP + CBPC (40 actors out of combat) + GT Softbody SMPFixes + PPA + OStrands/TongueLab.
- Gaze / head tracking: ModifiedOptimalGazeNG, TrueGaze, FourthWall, OGaze (+ TDM head tracking).
- Overlay/UI layers drawing every frame: Community Shaders ImGui, SKSE Menu Framework, Apocrypha Menu Framework, Risa menu/RisaUI, FUCK, IED UI, devbench, PrismaUI (Ultralight web views), plus Scaleform HUD stacks TrueHUD / HudNG / ImmersiveHUD / STB Widgets / Status Indicator / Compass Navigation / Kill Feed / Floating Subtitles / Detection Meter / Casting Bar / Crosshair Overhaul / Cinema letterboxes, all re-timed by SpeedyUI.
- Frame limiters: SSE Display Tweaks (FramerateLimit=240, EnableVSync=true) together with CS frame generation; no second limiter plugin found.
- Loading / memory: Engine Fixes allocators (all on), Disk Cache Enabler, Sound Fix for Large Sector Drives, Faster Textures cache (2466 MiB), Faster Objects runtime bake. No duplicate allocator patch enabled (Faster Decompression / Faster File Copy / Faster Cell Lookup / Cached Recursive Directory Walk are disabled).
- Horizon: `Horizon Fix` plugin and the Community Shaders HorizonFix feature are both present.
- DoF: `Cinematic DoF Standalone` and CS Post Processing "Depth of Field".

## Log findings (11:26 and 11:40 sessions)

- Largest logs: Walk With Me-followers.1.log 8.2 MB (diagnostics build), UnderwaterNG_snapshots.log 2.7 MB (appends every start), SkyrimNet.*.log 0.4-0.7 MB per session, LexiconSKSE.log 0.4 MB (trace), Illuminated.log 0.36 MB, po3_LightPlacer.log 0.34 MB, FormListManipulator.log 0.26 MB (1608 duplicates skipped), IntelEngine.log 0.19 MB, skee64.log 0.18 MB (debug level), OpenAnimationReplacer.log 0.14 MB. None is per-frame; all are start-up or cell-change bursts.
- `Documents\My Games\Skyrim.INI\SKSE\SkyrimUpscaler.log` is 2.68 GB (dated 03-09, stale) - safe to delete, not from this install's current plugins.
- Errors/warnings: skee64 "Could not bind default morphs ... Vertex mismatch" (Argonian high poly head); Relight "Invalid mod name" for dynamiccandles.esp, jk's bee and barb.esp, alternate start reborn.esp; TrueDirectionalMovement "Failed to obtain Dodge Framework API"; SmoothCam "Failed to dispatch API message to 'hdtsmp64'"; BottledShaders "[EFFECTS11] Required effect file not found", "Unknown preset id 'fnenb Cabbage'", "Unmap vtable slot changed", "SnowDeformation Trampoline has 30 bytes free; gathering footprints on the render thread instead"; SkyrimNet "No animation tags found in triggers", "Failed to open BSA file: Scripts\TIF__*.pex"; TrueGaze "Frame budget exceeded: 553 us across 1 actors".
- No version-mismatch or failed-to-load plugin in skse64.log (365/365).

## Disabled mods that still hold SKSE DLLs (not loaded; disk leftovers)

zz HandleProbe (diagnostic), Papyrus Profiler, Debug Menu - In-Game Navmesh Viewer and More, Asset Doctor, Texture Downscaler, AnvilLOD Output, Bottled Shaders - foxnne (pre-merge), Bottled Shaders - foxnne (pre-merge 1111), SkyrimNet, SkyrimNet 1.1.1, SeverActions 4.8.0, IntelEngine 3.7.1, DragonSense 0.4.0, OStimNet 2.6.1, OStimNet for SkyrimNet, OStim Navigator, Cinematic OStim Camera (COC), Faster Decompression, Faster File Copy, Faster Cell Lookup, Cached Recursive Directory Walk, Lingering Subtitle - Engine Fix, Aurora Fix (both now covered by Baked Goods), and others. `Bottled Shaders - foxnne\SKSE\Plugins` also holds 30 `CommunityShaders.dll.bak-*` files (about 1.7 GB with PDB backups) that the VFS maps into Data.


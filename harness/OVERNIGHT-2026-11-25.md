# Overnight 2026-11-25 (user asleep; asked to press on)

Machine: RAM at BIOS defaults (4200 MT/s, 1.1 V) after two BSODs 0x4E at a hand-set 5600. User returns to XMP 6000 only if tonight stays crash-free.

User requests, in order of work:
1. Arc travel memory test (real fast travel, Sky Above arcs) -> NR after far travel, RAM, hitch per flight. `travel_ft.py arcs_4200` (results/travel_ft).
2. Views page server up (port 8930) and reshoot the views after the jumps.
3. Repeat reference shots (determinism): `shots.py repeat ...`, explain remaining diffs.
4. Sky Above: one smooth arc (no abrupt speed change above the character); long hitch at the top of the arc (destination load at the apex move).
5. Flying through clouds shows strange artifacts: "we need to be able to be inside clouds".
6. Fire: casting spells shows mismatched fire; get Embers XD working right (yellow install option?), more realistic embers.
7. Advanced Skin off/on turns Auri's body black (like the hands / new-character arms): textures lost on toggle? SSS / character lighting?
8. Rift foggy weather looks strange close up (very low volumetric clouds).

Log of what was done goes below.

## 02:25 log
- Arc test 1 (`results/travel_ft/arcs_4200.json`, RAM 4200, VRAM priority OFF, old Sky Above curve): 20 real fast-travel arcs between 6 places. NR 6.5-7.1 ms after every landing (answer: NR holds). Video 13.2-15.3 GB. RAM 35 -> 46 GB, never returned. Top-of-arc move frame 0.55-1.37 s every flight (Sky Above log `Move timing`; preload=0). Stalls per flight grew 1 -> 5 over the run. Flight 21: game crash in Havok broadphase (hkp3AxisSweep, ragdoll add for an Imperial Soldier) at 46 GB private: `crash-2026-11-25-02-19-28.log`. Machine stayed up (no BSOD at 4200).
- Bridge: new `world action=fasttravel name=<map marker name>` (Game.FastTravel; `list=true` lists names; walled-city markers are not in Tamriel's persistent cell, use stables etc.), `tmm` allowed. Sky Above `bScriptedFastTravel=1` so it flies these.
- Sky Above fork (C:\Users\foxnn\dev\sky-above-fast-travel, uncommitted): `bSmoothArc` (sine arc instead of sin^0.6 steep take-off; minimum-jerk progress in two halves, slowing to `fApexKeepSpeed`=0.15 of speed at the top, where the destination loads), `fSkyLook=0` (sun turn off), `bPreloadDestination=1`, `bStretchApproachForGrid=1`. Backups `*.bak-pre-smootharc-20261125`.
- Fire: Embers XD switched Burnt Orange -> Golden Yellow (32 meshes from the FOMOD's yellow folders; backup C:/Modlists/backups/embersxd-orange-20261125-022049). FYX Campfire Reacts to the Wind switched to its "3 EmbersXD Flames Yellow" file (downloaded with the user's yes; backup C:/Modlists/backups/fyx-crttw-xdflames-20261125-022258). Spell fire = KittyVFX - Fire (+ Conflagration textures), Embers Fire Magick add-on not installed: still to look at in game.

## 03:30 log
- Arc test 2 (`results/travel_ft/arcs_smooth.json`, smooth arc + preload + stretch): NR 5.8-6.4 ms at every landing again. Game crashed at the 14th flight, again right after Solitude Sawmill, identical crash to test 1 (SkyrimSE+BEF31E, id 64677+0x2DE, null write in Havok broadphase hkp3AxisSweep while adding an Imperial Soldier ragdoll; `crash-2026-11-25-02-36-43.log`, private 47.4 GB). Two identical crashes: something in the physics world builds up per trip.
- Preload loads all destination models ahead (355/355, 0 failed) but the move frame stays 0.6-1.2 s: the cost is not models.
- HitchSampler now samples the MAIN thread (it sampled the render thread, which only waits) and records SkyrimSE call chains (`exe < ...`). Move frames: 24-45% main thread waiting in Main::Update(36564) -> Main::sub(36581) -> 13641 -> bhkWorld::sub(77918) -> ... -> BSTaskManager(75633) wait; the rest scattered (TESFile::SeekCell 20456 -> BSFile reads, references). So the hitch is mostly the Havok world taking in / stepping the whole destination grid in one frame. Names from re-refs/AddressLibraryDatabase/skyrimae.rename.
- Repeat shots (`results/shots/rep_1125`): whiterun_plains 2.9 % (was 25 %), ilinalta_backlit 8.0 % (was 10 %). Two frames 3 s apart WITHOUT any reset differ 5.5 % at Ilinalta (back-to-back 0.75 %): the rest is real-time motion of the game's own tree animation (Dynamic Wind Framework drives vanilla tree anim) and water ripples, which the reference clock does not control. Our Tree Wind + clouds + shader timer are pinned. Repeatability itself: ~2.5 %.
- Views page: `snap common` reshot all 5 common views at clear noon, no holes.
- Cloud/fog close-up (Rift, RiftenOvercastFog, camera at ground+150): horizontal streaks / sideways-stretched copies of tree silhouettes in the fog. NOT removed by turning off (one at a time): GroundFog, ExponentialHeightFog, VolumetricLighting, PhysicalSky, NeuralRendering, ViewAtmosphere, ScreenSpaceGI, VolumetricShadows, CloudShadows, Skylighting, ScreenSpaceShadows, PostProcessing sub-effects Motion Blur / DoF / Local Exposure / COD Bloom / Composite / Look Grade / Lens Flare / cinematic_camera / Color Grading. Turning the WHOLE PostProcessing feature off removed the fog and the streaks. Next: camera parallax test (world-anchored vs screen-space), then PostProcessing's remaining parts (Fire, Histogram Auto Exposure) and the order of passes. Shots: scratchpad clouds/*.png (session cb71cf91).
- Cloud deck from above (8,000-45,000 units over the Rift): soft blurry blanket with terraced ledge shapes at distance; no hard artifacts captured in still frames.
- Advanced Skin toggle test: inconclusive (Auri not framed in the dark inn shot); needs a close-up camera on her.

## 04:25 log
- Plain teleports (`travel_leak.py cow_4200`, 24 cow jumps, started at 42.7 GB): no crash, RAM flat 42-44 GB, NR 5.7-6.0 ms.
- Arcs with Sky Above `fTimescale=20` (`travel_ft.py arcs_ts20`, 24 flights): NO crash, RAM rose 31 -> 44 GB and levelled off like the teleports, NR 5.8-6.1 ms. With the default `fTimescale=5000` the game crashed at flight 14 and 21 (Havok, respawning Imperial Soldier ragdoll at Solitude). Conclusion (one run vs two): the live world simulating ~20 game hours per flight at 5000x is what breaks Havok / grows RAM. ini restored to 5000 (user's design); fix to build: show time passing in the sky only during the flight, advance the game clock in one step at landing.
- Spell fire: KittyVFX - Fire meshes + Glorious Gradients colour ramps + Conflagration textures; world fire is now Embers XD Golden Yellow. Match option for the user: Embers XD "Fire Magick Add-On (Yellow)" from the archive in downloads (adds an ESP; replaces KittyVFX for fire spells).
- Legacy views: all 19 anchored (`shots.py anchor` now handles cell-only views and saved character spots). 14 outdoor + rift_wide_south + haafingar_wide_east reshot on the views page. plains_north/plains_west flagged (Treehouse platforms).
- Rift fog streaks: still present with LightShafts off (feature toggle AND its own Enabled setting); likely world light-ray effect meshes in that fog.

## 05:00 log: flying through clouds fixed (two changes in the CS fork, deployed)
- Captured flights through RiftenOvercastFog low cloud (scratchpad fly_* folders): radial streaks, tall stripes, scan-line streaks and hard blocks inside the cloud; heavy blur on the descent.
- Cause 1: our Motion Blur. A flight with Motion Blur off was clean of the stripes/radial streaks. Fix: `PostProcessing/MotionBlur.cpp` fades the blur out when the camera moves faster than 1500 units/s (off at 3000; sprint ~600, horse ~1000), back on over ~0.5 s. Normal play unchanged.
- Cause 2: Physical Sky cloud history reprojection at flight speed (crosshatch grids, block edges, speed lines with blur off). Fix: `PhysicalSky/VolumetricClouds.cpp` drops the cloud history when the camera moves faster than 6000 units/s. Result: billowing cloud tops seen from above, clean inside of the cloud, no streaks.
- Seen in passing: Windhelm's water looks flat lime-green from altitude (distant water colour); one flat dark-blue frame at the top of one flight (probably the destination-load frame).

## 05:15 wrap-up
- Advanced Skin: live setting `EnableSkin` was FALSE (user left it off). With a freshly spawned Auri (testbed spawn form 0x5C000D63) outdoors at noon, no black body in any order (feature toggle off/on; EnableSkin off->on->off->on). So the toggle alone does not blacken a newly loaded character; the black body needs a body loaded under some earlier condition (the user's Auri, the player's hands). Still open; next step: read the real Auri's body shape state (shader flags, bound textures) through a small bridge addition.
- Game and MO2 closed at 05:15. `VramTrack.on` moved to C:/Modlists/backups/VramTrack.on.removed-20261125 (tracker off from next start). Kept: `HitchSample.on` (diagnostics for the top-of-arc hitch), `VramPriority.off` (priority hook stays off).
- Deployed CS build (PR-Tracy, 04:51): bridge fasttravel + tmm, VRAM priority switch, HitchSampler main thread + exe chains, motion blur fast-camera fade, cloud history drop at speed. Sky Above: smooth arc build + ini (bSmoothArc, fApexKeepSpeed 0.15, fSkyLook 0, preload, stretch, bScriptedFastTravel; fTimescale back at 5000). All uncommitted.
- Images: results/overnight_20261125/ (clouds before/after, fog rays, Auri sequence, repeat diffs)

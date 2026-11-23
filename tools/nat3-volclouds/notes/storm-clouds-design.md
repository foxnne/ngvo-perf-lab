# Distant storm clouds, storm decks and cloud-terrain meeting: design notes

2026-11-22. Offline read of `C:\Users\foxnn\dev\skyrim-community-shaders` (HEAD 82f881db1). Nothing was built, launched
or seen in game by this pass; shapes were checked only with the weather-map emulator `C:\Users\foxnn\dev\cloud-storms\ndf_sim.py`
(no erosion, lighting or haze). Sweeps: `draft\sweeps-storm\` (generator `_tools\build_storm_sweeps.py`, emulator output `_sim\`).
Earlier notes this builds on: `C:\Users\foxnn\dev\cloud-storms\NOTES.md` (placed storms, tall-type finding).

Paths: `SRC` = `src\Features\PhysicalSky`, `SH` = `features\Physical Sky\Shaders\PhysicalSky`, `V` = `SH\Volumetrics.cs.hlsl`,
`VC` = `SRC\VolumetricClouds.cpp`. Settings keys are relative to the feature's "Physical Sky" object.

## 0. Facts that decide everything

- **Units.** All cloud altitudes are metres above the worldspace height zero `zBottom` (Tamriel -14500 game units,
  `src\Features\PhysicalSky.h:144`), and 1 m = 1 / 0.01428 game units (`GAME_UNIT_TO_M`, `package\Shaders\Common\Game.hlsli:13`).
  The march eye is `CameraPosAdjust - bottomZ` (`SH\CloudTemporal.hlsli:430`). So:
  `world z (game units) = altitude_m / 0.01428 - 14500`, and `altitude_m = (z + 14500) x 0.01428`.
  The world is small in these metres: the province is ~7 x 5.5 km, the Whiterun plain is at 155 m, the range west of
  the plains camera is 2.4-3.0 km away with crests at 466-514 m (z 18100-21500), the Throat is 770 m (terrain heightmap).
- **The layer bends down with distance.** Profile altitude = z + d^2 / R, d = horizontal distance from the camera,
  R = `cloudLayer.low.curvatureRadius` km (`SH\CloudGeometry.hlsli:4-12`; default 74.946, clamp 25..10000, `VC:296`).
  Note it is d^2 / R, not d^2 / 2R. With the default the whole layer is 53 m lower at 2 km, 120 m at 3 km, 334 m at
  5 km, 1.3 km at 10 km, 5.3 km at 20 km. A cloud top at height H is on the camera's horizon at d = sqrt(R x (H - 165 m)):
  12 km for the live 2.1 km top, 18 km for a 4.5 km top. Nothing ray-marched is visible beyond that, whatever `rayMarchRange` is.
- **Where cloud is** comes from one 512 x 512 weather map (`SRC\Ndf.h:189`) that repeats every `cloudLayer.low.ndfScale` km
  (live 24.66 x 16.7; clamp 1..50, `VC:1120-1121`): coverage = gain x max(primary, secondary), top type and bottom type
  from the `modeling` noise, bottom height = `baseHeight.x` + variation (+ base relief), top = `baseHeight.y` = 0.95
  (`SH\NdfGenerate.cs.hlsl:164-172, 189-215`; defaults `SRC\Ndf.h:90-116`). It is world-anchored and moves with the wind.
  There is **no camera-distance or direction term anywhere**: coverage cannot be made to grow towards the horizon.
- **How tall a cloud is** is the TOP TYPE, not the slab: the vertical profile LUT (`V:800-818`, `NubisVerticalProfile.dds`
  decoded) ends at 20 % of the slab for type 0.03-0.07, 40 % for 0.2, 65 % for 0.5, 97 % for 1.0. The lowest type still
  fills ~15-20 % of the slab. Live top types are (0..0.5)^1.6 = 0..0.33 (`Ndf.h:95`), typically 0.05-0.2.
  `topExpansionScale` (default 1, clamp 0..1, `VC:1224`) adds a second bulge above the cone: in the emulation the 90th
  percentile top of the tower variants is 830 m higher with it than without (variant 08).
- **What is solid.** density = saturate(noise x 0.975 - (1 - min(0.7, profile))), profile = top LUT x bottom LUT x coverage^k
  (`SH\CloudNoise.hlsli:54-70`, `V:813-817`). Coverage >= 0.7 is solid whatever the noise, 0.4-0.6 survives only in noise
  peaks, < 0.3 is nothing. Live coverage tops out at 0.65 (`primary.range.w`), so today's cumulus is never solid.
- **Detail noise is one fixed scale.** The 128^3 shape noise tiles every 230 m horizontally and 287 m vertically
  (`V:1038, 1054-1056`; `SRC\CloudNoiseGenerator.h:52`), with base lobes of 230 / 3 = 77 m (`CloudNoiseGenerator.h:32-35`).
  Between the weather-map cells (>= 1-2 km) and these 77 m lobes there is no intermediate scale.
- **Lighting.** Per view sample: a light march of 10 samples (4 beyond ~3 km view distance) over only 240 m, 120 m above
  30 % of the slab height (`SH\CloudLighting.hlsli:131-132`), shared across up to 4 view steps (`V:1551-1557`); direct =
  albedo x phase x exp(-depth x `sunExtinction`); a calibrated multiple-scattering term x `msStrength`
  (`CloudLighting.hlsli:329-344`); ambient from a 4-cascade 32 x 32 x 16 volume x `ambientStrength` (`V:1571-1589`,
  `src\Features\PhysicalSky.h:555-557`); optional deck light (section 3). There is no "powder" term; the nearest thing is
  the density gate `scatterDensityThreshold` / `scatterDensityPower` (`CloudLighting.hlsli:337-340`). The upper layers
  shadow the low clouds through a sun-depth map (`SH\MidCloud.hlsli:19-28`), but **low cloud does not shadow low cloud
  beyond those 120-240 m**: a tower's own far side goes dark (the probe ends inside the cloud), a tower standing in the
  shadow of another tower stays lit.
- **March cost.** Step = (3 m + 0.00366 x distance) x `marchStepScale` (live 0.5, clamp 0.0625..4; `V:744-753`, `VC:1174`),
  doubled where the profile is <= 0.05 (`V:1537`), stop at transmittance 0.1 (`V:1273`), traced at quarter resolution
  (`VC:1156-1157`). There is no step cap: cost follows the length of ray inside the slab. A horizontal ray is inside the
  live slab for 3.2 km (~160 steps), inside a 1.0-4.5 km slab for 10 km (~420 steps). `rayMarchRange` 32 km (clamp 1..64, `VC:1172`).
- **Scenes.** Floats and float vectors can be set per weather. Noise SLOT numbers of the map layers, the noise inputs
  (`cloudMap.procedural.noise`), `cloudNoise`, `rayMarchRange`, `marchStepScale` cannot (`draft\_generator\scene-catalog-pass4.json`
  policy list). Variants that need them are marked GLOBAL in the sweep files.

## 1. (a) An isolated towering cumulus / cumulonimbus like the reference

Three mechanisms exist; only the first is a pure setting.

### 1.1 Weather-map towers (settings; sweep `towering_day.json`)
| idea | keys | range to try | clamp / definition |
|---|---|---|---|
| room to grow | `cloudLayer.low.ndfAltitudeOffset`, `ndfAltitudeScale` | base 900-1200, span 3000-4500 | 0..20000 / 1..20000 m, `VC:289-290` |
| fill the slab | `cloudMap.procedural.parameters.modeling.range` z/w, `.exponent` | z 0.15-0.3, w 1.0, exponent 1.0 | range +-16, exponent 0.01..8, `SRC\Ndf.cpp:136-143, 478-486` |
| dome instead of random heights | `modeling.noise` = 3 (the coverage slot), `modeling.range` x/y just above the coverage threshold | [0.35, 0.95, 0.15, 1.0] | slot 0..4, `Ndf.cpp:479`. GLOBAL |
| few, steep, solid cells | `primary.range`, `primary.exponent`, `secondary.range` w | [0.35, 0.55, 0, 1.0], 1.0, w 0 | as above |
| larger cells | `cloudMap.procedural.noise[3].parameters.frequency` 12 -> 5 (GLOBAL), or `ndfScale` 50 x 33.9 | | 1..128, `Ndf.cpp:408-412`; 1..50 |
| flat dark base, wide foot | `low.bottomSpreadScale` 1.0, `bottomSpreadHeight` 0.15, `bottomSoftness` 0.15, `bottomSoftnessHeight` 0.12, `bottomTypeRange` w 0.05, `heightVariation.range` z = w = 0 | | `VC:1219-1223` |
| contrast | `cloudLayer.lighting.sunExtinction` 1.5-2, `ambientStrength` 0.4-0.7, `msAlbedo` 0.99-0.996, `low.densityScale` 1.0 | | >= 0, >= 0, 0..0.9999, >= 0; `VC:1218-1234` |
| lobe size | `cloudNoise.shape[i].frequency` 3,3,4,9 -> 1,2,3,6 (GLOBAL, experimental) | | `CloudNoiseGenerator.h:13-35` |

Why "core towers": with the default the top type reads noise slot 2 (770 x 520 m Perlin cells), unrelated to the
coverage cells, so tall slabs give columns of random height. Reading the same slot as coverage makes the type rise
towards the middle of each cell (emulation: rounded 1-1.5 km wide, 1.5-2.7 km deep domes with a wider foot;
`_sim\towering_day\04_few_large_cells.png`, `06_flat_dark_base.png`). Layer `frequency` must stay an integer (the noise
only tiles at whole multiples); slot 1 holds 2 repetitions, so 0.5 is also seamless for that slot only.

Limits: (1) the shape is a height field: one top per column, no overhang, no anvil spreading beyond the cell, no shelf
below the base; `topExpansionScale` only fattens the upper half inside the cell outline. (2) Surface detail is 77 m
"popcorn" on a smooth dome: the 300 m-1 km cauliflower lobes of the reference do not exist (section 0). (3) Fair cumulus
in the same slab get at least 15-20 % of the slab thick. (4) Aspect: the province is 7 km wide, so a believable tower is
1-2 km wide and 2-3 km deep, not 10 km. (5) Visibility: a 4.5 km top disappears below the horizon 18 km away; from the
plains the west ridge hides everything under 6-8 degrees. (6) Cost: the thick slab (section 0).

### 1.2 Placed supercell (file, not a setting): the only real cumulonimbus with an anvil
`Data\Textures\PhysicalSky\Storms\<ID>\Instance.json` (`SRC\Storm.cpp:18, 43-57`; keys `SRC\Storm.h:5-39`; clamps
`Storm.cpp:164-176`: radius 1..16000 m, altitude -24000..48000, height 1..24000, density 0..4, albedo 0..0.9999).
Mode "Supercell" replaces the weather column inside its footprint with a generated mesocyclone (`SH\StormNdf.cs.hlsl:71-97`,
`SH\CloudStorm.hlsli:283-375`); where the storm mask is > 0.15 the top profile is mirrored about mid height (`V:811-812`),
which is the anvil; its light march is strengthened (`SH\CloudNoise.hlsli:87`, `CloudLighting.hlsli:158-161`) and it has
its own density and albedo (`CloudLighting.hlsli:202-206, 231`). Details, a staged test mod and a test plan are in
`cloud-storms\NOTES.md` sections 1, 5b, 6. Limits: fixed in the world, on in every weather (no weather switch), costs
the storm-aware shader variants even off screen, noise bands are fixed sizes in metres.

### 1.3 Local cloud map, Separate layer (scene-blendable) and voxel "hero" clouds
- `cloudMap.localCloud.states[]` (`SRC\Ndf.h:146-164`; bake `SH\LocalNdf.cs.hlsl`; clamps `SRC\LocalNdf.cpp:167-171`:
  size 1..128000 m, altitude -24000..48000, heightSpan 1..24000) with `modelingBlend: 2` draws an authored cloud in its
  own slab at a fixed world position (`V:868-906`). This is the way to put ONE tower exactly where a view needs it and
  switch it per weather. It needs an authored Height.dds + Modeling.dds (the staged `tamriel-storm-cells` asset of
  `cloud-storms\NOTES.md` 5b is this). Ordinary cloud lighting, no anvil model, same 77 m detail.
- Voxel clouds (`voxelClouds` blend state, `SRC\VoxelCloud.h:6-37`; assets `Data\Textures\PhysicalSky\VoxelClouds\<ID>\`
  with `Instance.json`, 3D `Modeling.dds` and `Distance.dds`, `SRC\VoxelCloud.cpp:17, 100-131`; up to 8 assets) are the only
  path to true 3D shapes (overhangs, anvil, shelf, authored cauliflower). No asset is installed and the repo has no
  authoring tool: a hero cloud means modelling a volume + signed distance field offline. Out of reach by settings.

## 2. (b) A line or wall of storm cells on the horizon while the sky overhead is fair

Sweeps `front_horizon_day.json`, `front_horizon_sunset.json`.

### 2.1 Horizon band (cheap, beyond the marched range)
Two analytic shells around the camera at `distance` and `distance x farScale` (`SH\HorizonClouds.hlsli:139-217`), drawn
only on sky pixels behind the marched clouds (`HorizonClouds.hlsli:224-225`) at real-planet curvature. Keys under
`cloudLayer.horizon` (`SRC\Ndf.h:432-460`; clamps `VC:1116-1118, 1271-1274`):
`coverage` (x the weather class amount, result clamped 0..1, `src\Features\PhysicalSky.cpp:1411-1453`), `type` 0 towers ..
1 flat bank (0..1), `baseAltitude` 0..4000 m, `topAltitude` 500..12000 m, `distance` 45..150 km, `farScale` 1.2..3,
`density` 0..4, `brightness` 0..3, `sunlit` 0..0.6, `shade` 0..12, `seed` 0..64, class amounts `pleasantAmount` 0.6,
`cloudyAmount` 1.4, `rainyAmount` 0, `snowAmount` 0 (each clamped 0..4), `cloudyBank` 0..1, fog fade `fogHide` / `fogFull`.
For a storm line: type 0-0.55, top 7000-9000, distance 45 (9 km at 45 km = 11 degrees; the default 3.2 km at 60 km is
3 degrees and is hidden by terrain from both reference views), density 2, shade 6-9, sunlit 0.3, and set the class
amount of the weather to 1 so `coverage` is what you author.
Limits: a painted silhouette (value-noise outline, 4 octaves of lumps), light = depth-to-top estimate, no shadow from
or onto the marched clouds, no lightning, rain and snow classes have no band by default, tower spacing is fixed
(groups every 60 km of circumference, towers every 9 km: `HorizonClouds.hlsli:159-165`). `lumps` reaches 1.45 so towers
overshoot `topAltitude` by up to 45 % (cut at 150 %, `HorizonClouds.hlsli:149, 174-177`).

### 2.2 Ray-marched front: a storm REGION through the two gain layers (settings)
`coverageGain` and `modelingGain` multiply coverage and both types (`NdfGenerate.cs.hlsl:167-172`). Point both at a
low-frequency noise with the same frequency / offset and they become one regional mask:
- `coverageGain` = {noise 1, frequency 0.5, range [-0.25, 0.10, 0.65, 1.0]}, with `primary.range.w` raised to 1.0:
  outside the mask coverage is the live 0.65 x primary, inside it reaches 1 (solid).
- `modelingGain` = {noise 1, frequency 0.5, range [-0.25, 0.10, 0.03, 1.0]}, `modeling.range` [-0.5, 0.5, 0.25, 1.0]
  exponent 1: outside the mask the thinnest type, inside it tall types.
- slab 1000 + 4000 m. Mask cells are ~6 x 4 km; about 13 % of the map is fully "storm" (noise percentiles from the emulator).
The region is world-anchored and travels with the wind (`windOffset`, `NdfGenerate.cs.hlsl:157`); the layer `offset`
(tile fractions, +-10000, `Ndf.cpp:481-482`) places it, so a scene pair with different offsets is an approaching front
(variant 05 = +0.12 tile, about 3 km). The gain layers must read slot 1 globally (harmless while their output is 1..1).
Limits: fair cumulus thicken (lowest type in a 4 km slab); lighting settings are global, so "dark storm, bright fair
cumulus" cannot be had in one frame; the mask repeats every tile; where the region is relative to the player is not
controllable except through the offset; cost of the thick slab everywhere.
- `curvatureRadius` 300 keeps far cells above the horizon (they stack into a wall); the price is a far deck that
  reads as a ceiling in every weather that uses it.
- The middle layer (`cloudLayer.middle`, altitude 100..16000 m, thickness 100..4000 m, `SRC\Ndf.cpp:635-641`) could give a
  pre-frontal altostratus shelf, but its weather map is independent of the low towers: not swept here.

## 3. (c) Rolling heavy low cloud with relief under a storm

Sweep `storm_overhead_day.json` (on the pass-4 StormPF recipe: closed deck 400-2400 m).
| mechanism | keys | clamp / definition |
|---|---|---|
| shelves and hollows in the base | `cloudMap.procedural.parameters.baseRelief` {noise, frequency, exponent, range: z..w = lift as slab fraction}, `baseReliefThickness` | `NdfGenerate.cs.hlsl:205-215`; lift only raises, limited to top - 0.05 |
| pouches under the base | `cloudLayer.low.baseBillowHeight` (m) | 0..400, `VC:1261`; `V:994-1001` |
| thin = bright, thick = dark | `cloudLayer.lighting.deckLight`, `deckHalfDepth`, `deckHorizonLight`, `deckGroundLight` | 0..4, 10..4000 m, 0..0.95, 0..4 (`VC:1259-1262`, `PhysicalSky.cpp:2161`); `CloudLighting.hlsli:300-327` |
| column contrast | `modeling.range` (type 0.1..1 over a narrow interval) | |
| structure from gaps | `primary.range` z..w = 0.55..1 instead of the constant 1 | constant when z == w, `NdfGenerate.cs.hlsl:160-162` |
| darkness | `sunExtinction`, `viewExtinction`, `msAlbedo`, `ambientStrength`, `low.densityScale` | `VC:1218-1234` |
| lean | `cloudLayer.wind.lowVelocity / highVelocity`, `development`, `disturbance` | shear = 3 x (high - low) x height share, capped 150 m, `VC:997-1000`, `V:843-855` |

Deck light adds exit radiance x 2^-(metres of cloud above / halfDepth) where the local light path is blocked; it only
adds light, so "dark base" = low `ambientStrength` + low `msAlbedo` + short `deckHalfDepth`, not a deck-light value.
Limits: relief is read two mips coarser than the map (broad shelves only); billows use the 77 m detail noise; the base
density ramp is a fraction of the slab (section 4), so a thick storm slab has a diffuse underside; no rain shafts / virga
and no light shafts through gaps in the cloud pass.

## 4. Low cloud meeting mountains

### 4.1 What the code does (answers to the five questions)
1. **Depth.** Each traced ray is cut at the opaque scene: sky pixels march the full range, others stop at the surface
   distance (`CloudTemporal.hlsli:426-432`, `V:1277-1283, 1335-1338`). The result (transmittance + premultiplied radiance)
   is laid over the scene for every pixel, not only the sky: `SH\Common.hlsli:614-621`, or, with Atmosphere and Fog,
   `package\Shaders\Common\ViewMedium.hlsli:60-83`. So cloud between the camera and a mountain IS drawn over it, and a
   mountain inside the slab is hidden by the cloud in front of it. There is no minimum start distance and no near fade
   in the march. Things at silhouettes:
   - the trace is quarter resolution, one ray per 4 x 4 (`VC:1156-1157`); the upsample, the history and the blur keep only
     taps whose scene depth is within 0.064 km = 64 m (`CloudTemporal.hlsli:213, 260, 311`; `SH\CloudBlur.hlsli:51`); a pixel
     with no matching tap in a 16-pixel neighbourhood falls back to a plain bilinear of the 2 x 2
     (`CloudTemporal.hlsli:250-290, 559-562`), i.e. to whatever is next to it, sky deck included;
   - with Atmosphere and Fog the cloud on a surface is faded in over the last 40 m in front of that surface
     (`ViewMedium.hlsli:77`: visibility = (surface distance - cloud mean distance) x 0.025 per metre);
   - `cloudBlurRadius` (default 1, 0..2 px, `PhysicalSky.cpp:564`).
   None of these has a setting except `cloudBlurRadius`. Which one makes the thin bright fringe on ridge lines could not
   be decided offline; a ray grazing a crest also runs a long way through the thin base haze (below), which by itself
   gives a pale line along the crest.
2. **Where the base really is.** `ndfAltitudeOffset` is metres above zBottom (section 0). Overhead: base 400 m = z 13500,
   500 m = z 20500, 600 m = z 27500, 800 m = z 41500 game units (the plain is z -3600, the west crests z 18100-21500).
   At the west ridge (3 km) the layer is another 120 m lower. So with the pass-4 storm (base 400 m) the nominal base at
   that ridge is 280 m and the crests are 190-230 m inside the slab; with base 600 m the base there is 480 m, level with
   the crests: the deck starts where the mountain ends and must read as a backdrop. Three things then keep even the
   400 m deck off the slopes:
   - base relief only LIFTS the base, by up to `baseRelief.range.w` x span = 0.18 x 2000 = 360 m in pass 4 (`NdfGenerate.cs.hlsl:213-214`);
   - the base density ramp is in slab fractions: density is multiplied by h^0.3 x saturate(h x width)^power with
     width <= 10 (`CloudNoise.hlsli:77-83`; `bottomSoftnessHeight` below 0.1 changes nothing because the width saturates),
     and by a factor that is ~0 at the very bottom of solid cloud (`CloudNoise.hlsli:77, 83`). Full density is reached
     10-20 % up the slab: 200-400 m in a 2000 m slab. A crest that pokes 200 m into the storm slab sits in thin haze;
   - the weather map knows nothing about terrain: no lift, no cap, no scud.
   Mid-slope for the plains-west range is ~330 m at the ridge, i.e. **`ndfAltitudeOffset` 350-450 with base relief off or
   <= 0.05**; 350 m also buries the top 420 m of the Throat. A shorter slab (900 m) shortens the ramp to ~90 m.
3. **Fog.** The froxel Atmosphere and Fog volume takes only cloud SHADOW and cloud-filtered sky light, never cloud
   density (`features\Atmosphere and Fog\Shaders\ViewAtmosphere\MediumLighting.hlsli:108-115`); exponential height fog is
   independent (`ViewMedium.hlsli:30-36`). Terrain inside the layer is covered only by the per-pixel cloud march above.
4. **Local cloud map.** `cloudMap.localCloud.states` is empty in the saved settings (no `localCloud` key in SettingsUser.json),
   so nothing terrain-anchored is active. It is enabled by adding states (UI: Clouds > weather map > local cloud; or a
   scene, it is a blend state; the bridge has `SetLocalCloudState`, `src\Features\PhysicalSky.h:427`). A state names an asset
   folder `Data\Textures\PhysicalSky\LocalNdf\<asset>\` (Height.dds, Modeling.dds, optional Mask.dds), a worldspace, centre,
   size, rotation, altitude + heightSpan (metres), strength and a blend mode (`SRC\LocalNdf.cpp:119-173`): 0 Interpolate and
   1 Maximum reshape the global deck inside the footprint (heights included, `V:315-331`), 2 Separate adds an independent
   slab whose heights are terrain altitudes when `flatAltitude` is true (`V:340-358, 868-906`). The mod
   `foxnne - Cloud Weather Map` holds `tamriel-orographic` (Interpolate, 0-1056 m), `tamriel-mist-separate` (Separate,
   192-832 m: 45 small banks on the Throat ring, face bases, ridge crests and saddles) and three `diag-*` test assets;
   it is ticked in the MO2 profile that `ModOrganizer.ini` selects. So yes: Separate states are the mechanism for caps and
   slope-hugging banks, at the price of authored maps (generator `C:\Users\foxnn\dev\cloud-weather-map\build_map.py`).
   Two cautions: `tamriel-orographic` in Interpolate mode gave tall striped curtains in game (`cloud-weather-map\NOTES.md`
   "In-game result", because it moves the one slab instead of adding one), so it is not used here; and a blend state's
   weights must total <= 1 (`src\Utils\SceneBlend.h:25`) while a Separate slab's coverage is multiplied by its weight
   (`V:888`), so only ONE Separate asset can be at full strength: banks and caps must be baked into one asset.
5. **Options.** (a) settings: sweep `cloud_terrain_meeting.json` (section 4.2). (b) code, section 5 items T1-T5.

### 4.2 The four targets from the two photos
Photos: alpine valley (deck base cutting across a ridge, summits fading into it, detached scud below the base on the
slopes, dark thick and bright thin deck, lit saturated ground) and a smooth cap cloud on a mountain shoulder with a
ragged bright lower fringe under a layered deck.

| target | reachable with settings? | how / what is missing | sweep variants |
|---|---|---|---|
| 1 summits fading into the base | Partly. The march already hides terrain behind cloud (4.1.1); it only needs the base BELOW the summits and a base that is dense soon. | base 350-450 m with relief off; a thin slab (900 m) so the ramp is 90 m, `densityScale` 1.5; or `curvatureRadius` 45 for far ranges. The fade is then the density ramp (gradual over 90-200 m of height). Missing: the base does not sag or thicken towards slopes, the cut is a level line at a fixed altitude (code T1), and the ramp length cannot be set in metres (T2). | 01, 02, 03, 04 |
| 2 detached scud and banks below the base, on the slopes | Yes, with an asset. Not with the weather map: one slab per column, base fixed, no terrain term. | A Separate local state (`tamriel-mist-separate`, or a regenerated one with bigger, lower-coverage ragged banks: coverage 0.45-0.6 gives the torn look, >= 0.7 gives solid lumps). A second low thin weather layer does not exist (the middle layer starts at 100 m but has its own untied weather map and no terrain anchoring, and is compiled without storms); voxel clouds would be the best-looking scud (true 3D wisps) but need authored volumes. Moving scud is not possible: local slabs are terrain-anchored, only their detail noise drifts. | 05, 09 |
| 3 cap / lenticular on a peak | A cap: yes, as an authored Separate disc on the peak (solid core because coverage >= 0.7 ignores the erosion noise, eroded ragged rim where coverage falls: the fringe of the photo). A true lens: no. | The slab profile is the stock cone LUT: flat bottom, tapered top, no convex lens underside, no stacked plates, no smooth laminar surface (the 77 m erosion noise appears wherever coverage < 0.7). A lens needs either a voxel cloud (authored volume, `SRC\VoxelCloud.h`) or a per-state "smooth" flag that skips erosion plus a symmetric profile (code, ~30 lines). The test uses `diag-one-blob`; a real cap asset should follow the peak outline and lean downwind. | 07, 08 |
| 4 deck with thick dark and thin bright regions | Yes. | coverage 0.5..1 instead of a constant (gaps and thin lanes erode), top type 0.08..1 over a narrow noise interval (column depth 150 m to 1900 m side by side), `deckLight` 3-4 with `deckHalfDepth` 220-300 m (thin = bright, thick = dark), `ambientStrength` 0.4-0.5. Highlights near white come from thin columns only; there is no direct-sun break-through look unless coverage really opens (then the sunlit tops behind show). The ground under such a deck is lit by `deckGroundLight` (0..4) and the cloud shadow volume; saturation of the ground is a grading / fog matter outside this feature. | 06, 09; `storm_overhead_day.json` 05, 06 |

Variant list of `cloud_terrain_meeting.json` (weather StormPF, on the pass-4 storm recipe): 00 reference; 01 flat base
420; 02 base 350 mid-slope; 03 thin 900 m slab, hard base; 04 curvature radius 45; 05 mist banks; 06 thick / thin deck;
07 cap on the west crest (plains_west); 08 cap on the Throat (plains_throat); 09 everything reachable together.
05, 07, 08, 09 need the Cloud Weather Map mod in the running profile and a build that has Separate-layer local clouds
(if they look identical to 02 one of the two is missing; the Clouds page lists rejected assets).

## 5. Not possible without code changes

| # | what | change | size / risk |
|---|---|---|---|
| C1 | approaching front (coverage by distance / direction) | a scene float4 `front` (direction xy, signed distance, width) multiplied into coverage and top type in `sampleWeatherNDF` (`V:855-859`) and the shadow / ambient paths that share it | ~40 lines + CB field + 2 settings; low risk, no extra fetch |
| C2 | anvil / shelf on weather towers | storms get it from the mirrored profile (`V:811-812`); expose a weather float that enables the same mirror above a type threshold, plus a height-dependent widening of the coverage lookup (sample coverage with a blurred mip above 70 % height) | ~30 lines; medium (changes silhouettes, needs bounds padding) |
| C3 | taller / other profiles | profile is a 64 x 64 LUT (`VC:339`): ship alternative `NubisVerticalProfile.dds` or add a second LUT selected per weather | asset work; low |
| C4 | mid-scale cauliflower | second fetch of the shape noise at 1/4 frequency (920 m lobes) displacing `profile` before erosion in `sampleCloudDensityFromContext` (`V:968-987`) | ~15 lines; one more 3D fetch per density sample = the main cost of the pass rises 20-40 % |
| C5 | tower-on-tower shadow, long self-shadow | a low-cloud sun optical-depth map like `TexUpperSunDepth` (`MidCloud.hlsli:19-28`, 256^2 over 2 x range) added to `ShadeCloudLighting` (`CloudLighting.hlsli:378-394`) | ~120 lines + one compute pass; medium |
| C6 | wind shear that leans towers | shear is capped at 150 m and tied to the slab / cirrus ratio (`VC:994-1000`); make the cap and factor settings | ~10 lines; low |
| C7 | dome towers per weather | a float `modeling.coverageCoupling` blending the type noise with the coverage value (`NdfGenerate.cs.hlsl:168-172`) instead of the global slot switch | ~10 lines; low |
| C8 | weather-switched placed storms | scene float multiplied into each instance strength (`cloud-storms\NOTES.md` 5b.2) | ~20 lines; low |
| T1 | terrain-aware base (caps, scud, base sagging onto slopes) | sample the terrain height texture already bound for cloud terrain shadow (`CloudLighting.hlsli:355-375`) in the NDF sample: lower the base and raise coverage where altitude - terrain < a setting | ~60 lines + 3 settings; medium (one 2D fetch per NDF sample; coverage only inside the terrain-shadow map) |
| T2 | base ramp in metres | replace the fractional ramp in `ShapeCloudBaseDensity` (`CloudNoise.hlsli:77-83`) by a metre width setting | ~10 lines; low, but changes every sky unless defaulted off |
| T3 | soft terrain intersection | fade density over the last N metres before `sceneDistance` is physically wrong (cloud does not thin near rock) and would make the backdrop look worse; not recommended. Useful instead: T1 | - |
| T4 | silhouette fringe | when no depth-matching tap exists, use the nearest-depth tap instead of the bilinear 2 x 2 (`CloudTemporal.hlsli:559-562`); or trace mismatched pixels at full rate | ~20 lines; low |
| T5 | cloud in the froxel fog | only matters with the camera inside cloud (the march already covers distant terrain); inject low-cloud extinction into the nearest froxel grid | ~80 lines; medium |

## 6. Running the sweeps

From `C:\Users\foxnn\dev\ngvo-perf-lab\harness` (the harness launches and quits the game itself; `--stock` = variants on
the saved settings only, without the nat3 cloud draft; the weather of each variant is in its `weather` field and the
`--group` weather is the same one):
```
python sky_sweep.py storm_tower_plains  C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\towering_day.json --view plains_west   --group clear --hours 13 --stock
python sky_sweep.py storm_tower_throat  C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\towering_day.json --view plains_throat --group clear --hours 13 --stock
python sky_sweep.py storm_front_day     C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\front_horizon_day.json    --view plains_north  --group clear --hours 13 --stock
python sky_sweep.py storm_front_day_w   C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\front_horizon_day.json    --view plains_west   --group clear --hours 13 --stock
python sky_sweep.py storm_front_sunset  C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\front_horizon_sunset.json --view plains_west   --group clear --hours 18.25 --stock
python sky_sweep.py storm_front_sunset_i C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\front_horizon_sunset.json --view ilinalta_west --group clear --hours 18.25 --stock
python sky_sweep.py storm_overhead      C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\storm_overhead_day.json   --view plains_west   --group storm --hours 13 --stock
python sky_sweep.py storm_terrain       C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\cloud_terrain_meeting.json --view plains_west  --group storm --hours 13 --stock
python sky_sweep.py storm_terrain_thr   C:\Users\foxnn\dev\nat3-volclouds\draft\sweeps-storm\cloud_terrain_meeting.json --view plains_throat --group storm --hours 13 --stock
```
`plains_north` (yaw 0, pitch 12 up, fov 75) has the lowest terrain horizon (1.6 degrees) and is the best band view;
`plains_west` and `ilinalta_west` hide the first 6-8 degrees. Tower positions are random per view: if a tile shows no
tower, the emulator plan `_sim\towering_day\<name>.png` tells where they are (red ring = plains camera).
The storm files carry the whole pass-4 StormPF recipe (haze included) plus `lightning.rate 0`.
Each log has `frame_ms` per variant: compare with `00_*`. In the pass-4 runs of today the frame time was 29 ms for
every sky type including the 2000 m storm slab, so the cloud pass was not the limit there.

GPU cost risk: horizon band variants ~nil. Lighting / base / relief / billow / deck variants: none (same march).
Thick slabs (towering 01-09, front 04-08, overhead 08): the march is 2.5-4x longer on rays near the horizon; expect
the cloud pass (quarter-resolution trace + shadow volume + ambient density, which all cover the same slab) to cost
2-3x, more with `curvatureRadius` 300 (front 07). `noise[3]` / `cloudNoise` variants regenerate textures once.
Thin slab (terrain 03): cheaper than pass 4. Mist banks (terrain 05): local-layer shader variant + wider trace range.

## 7. Things in the code that look like bugs or missed opportunities

1. No long-range shadow between low clouds (section 0): the single biggest gap for big-cloud realism, most visible at
   low sun. The mechanism exists for the upper layers (`MidCloud.hlsli:19-28`); see C5.
2. One detail-noise scale (230 m tile, 77 m lobes) for everything from a 300 m puff to a 4 km tower: the "popcorn" look
   on large clouds. See C4.
3. `bottomSoftnessHeight` below 0.1 has no effect (`CloudNoise.hlsli:78`: the width saturates at 10), and the base ramp
   is a fraction of the slab, so thick slabs cannot have a crisp base (T2). Pass 4 uses 0.12-0.15, already at the limit.
4. Horizon towers overshoot `topAltitude` by up to 45 % (`HorizonClouds.hlsli:174-177`; the setting comment says the
   tallest towers reach it), and rain / snow weathers get no band at all by default (`Ndf.h:449-450`): a storm seen
   from inside has no distant cloud wall behind the deck edge.
5. The gain layers default to noise slot 2 (Perlin frequency 32, 770 m cells; `Ndf.h:78-87, 94, 96`), useless as a
   regional mask; slot 1 at frequency 0.5 makes them one (section 2.2). Their `exponent` is never read (`NdfGenerate.cs.hlsl:94-97`).
6. Top type is independent of coverage (section 1.1); a coupling float (C7) would give domed cumulus in every weather
   without the global slot switch.
7. `curvatureRadius` is used as d^2 / R (`CloudGeometry.hlsli:4-7`), i.e. the layer bends like a sphere of HALF that
   radius; with the default the marched sky ends 12 km out. Worth knowing when reading the setting, not a defect.
8. Blend-state weights scale a Separate slab's coverage (`V:888`), so two Separate assets cannot both be full: an
   unintended limit for combining scud banks with caps.
9. The depth-mismatch fallback at silhouettes (`CloudTemporal.hlsli`, "Rejected history still reconstructs the current
   cloud") can put the neighbouring sky's cloud on a ridge pixel (T4). Unverified as the cause of the ridge fringe.
10. Placed storms have no weather switch (C8) and the supercell is the only shape with an anvil (C2).

## Snow decisions (2026-11-22, user)
- snow_light group (SnowClear, SnowClear_Alt): sunny snow = broken cumulus, cloud brightness 2, +0.7 EV, sky IBL saturation 1.3, DALC 0 (blue shadows). Variant `snow_sunny` in draft/sweeps-storm/snow_realistic.json.
- snow and snowstorm groups: covered deck built on the overcast deck, bright (+1.0 EV). Open: thin spots show dark sky and grey streaks, cream horizon (R/B 1.06, not fog/ozone/horizon light). Trying solid decks `cov2_solid_070/085`.
- Live apply tool: harness/sky_apply.py VARIANTS.json NAME [--shot]; `restore` reloads saved settings.
- 12:34/12:57: SettingsUser.json got saved with live test values twice; harness/saved_fix.py restores sky/IBL/exposure from the baseline copy and sky_apply.py runs it before each load.
- Approved covered snow = `snow_overcast_approved` (overcast deck + cloud brightness 1.7 + exposure -2.5).
- snow_light: `snow_sunny` (own cloud map) was grey and heavy in Winterhold: rejected. New `snow_light_minimal` = saved fair sky + cloud brightness 2 + DALC 0 / SkyIBLSaturation 1.3 + vanillaFogStrength 0.02 (user chose 2%). The Winterhold haze is SnowClear's own record fog at vanillaFogStrength 0.1 (0 = crystal clear); height-fog density keys are unused while useVanillaFogSettings = 1.
- Sunlit snow clips near the camera in forest views (18-24% of frame) regardless of the EV boost: needs highlight roll-off, not exposure.

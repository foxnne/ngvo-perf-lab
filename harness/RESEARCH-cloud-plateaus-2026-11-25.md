# Flat plateaued cloud towers over the low deck (2026-11-25)

Evidence: `gallery/videos/20261125_1603_2_WhiterunStables_sdr.mp4`, 6-10 s (frames at 2 fps, brightened crops of
the far deck: `scratchpad/plat/crop_07..09.png`). At t≈8 s the far deck is made of box-like masses with flat tops
and near-vertical fronts, plus one long terrace (a raised flat shelf with a vertical front). At t≈9 s the far
deck goes dark and reads as a flat plane up to the horizon, with flat-topped lumps along its top edge.

Fork: `C:\Users\foxnn\dev\skyrim-community-shaders`, branch `foxnne/merge-rc2-1123`. Nothing built, deployed or run.
Changes are uncommitted. `S` = `features\Physical Sky\Shaders\PhysicalSky`.

## 1. Cause

Three things in the density shaping stack up. The first is ours and is the main one.

### 1a. The mid-scale lobes (main cause) - `S\Volumetrics.cs.hlsl`, CLOUD_LOBE block in `sampleCloudDensityFromContext`
Added in checkpoint `309ad1d52` (2026-11-25 14:45), before the 16:03 recording:
```hlsl
const float lobe = TexCloudShapeNoise.SampleLevel(..., noise_coordinates * 0.1 + ..., 0).g;
const float lift = saturate((height_fraction - 0.15) * 3.0);           // full from h = 0.48 up
profile = saturate(profile - 0.45 * lift * (1 - smoothstep(0.15, 0.5, lobe)));
```
- The lobe field's vertical period is 1 / (0.0034834 × 0.1) ≈ 2.9 km. Across the 900 m deck it barely
  changes with height, so the cut is almost columnar.
- Above h = 0.48 the cut doesn't depend on height. A turret core (lobe > 0.5) keeps the whole weather profile,
  and a gap loses 0.45 of profile at every height. The edge between them comes from a smoothstep in XY.
- Result: turrets with vertical walls and no shape of their own on top. Each top is the weather profile's top,
  which is one flat plane (1b). For a type-1 column the core top is at h≈0.95 and the gap top at h≈0.7. That
  is a cliff about 225 m high over a lobe edge of roughly 100-200 m: these are the "flat plateaued towers".

### 1b. Flat ceiling: map top constant + steep end of the top profile - `CloudNdfProfile`, `S\NdfGenerate.cs.hlsl`
- The procedural map writes the same top everywhere (`height = baseHeight`; `baseHeight.y` = 0.95). Variation
  only goes to the bottom (`height.x += variation`).
- `NubisVerticalProfile.dds` G (top profile), decoded with Pillow:

  | top type | h = 0.75 | 0.85 | 0.90 | 0.95 | 0.98 | 1.0 |
  |---|---|---|---|---|---|---|
  | 0.75 | 0.33 | 0.08 | 0 | 0 | 0 | 0 |
  | 0.95 | 0.60 | 0.45 | 0.40 | 0.21 | 0.04 | 0 |
  | 1.0 | 0.67 | 0.55 | 0.50 | 0.29 | 0.16 | 0.04 |

  High types hold 0.3-0.5 up to about 95 % of the column, then fall off. The adjustment LUT R (top expansion)
  is similar.
- 192 of the per-weather entries in the pass-5 pack set the modeling range to [-0.45, 0.45] → [0.25, 1.0].
  `Remap` saturates, so wherever the modeling noise is above 0.45 the top type is exactly 1.0, and coverage
  also saturates at the top of its range. Over those areas every column has the same profile, so the deck top
  is one flat shelf at about 0.9-0.95 of the window. That is the flat plane, and the shared top of every turret.

### 1c. Noise mip stepped by `floor(profile*3)` - `sampleCloudDensityFromContext` (upstream code)
- `biasedMip = floor(dimension_profile * 3)` switches the shape-noise mip in whole steps at profile 1/3 and 2/3.
- Where the map saturates, the profile depends only on height, so those iso-profile surfaces are flat planes.
  The noise sample, and therefore the density, jumps across them, which gives horizontal seams and terraces.

### Ruled out or minor
- **Local map `tamriel-mist-separate`** (Height.dds RG16 and Modeling.dds RGBA16, 952×752, 7.3 m/texel):
  - No saturation: 0 % of texels at either end of the window. Bottoms are 200-617 m and tops 357-817 m.
  - R, G and B are constant (0.55 / 0.70 / 0.10). A > 0.02 on 8.8 % of the map, A > 0.5 on 2.9 %.
  - Top slope inside the banks: median 0.014 m/m, p99 1.4. The narrowest alpha ramp is 56 m.
  - Banks are 157-209 m thick and sit below the 1.2-2.1 km deck, so they are not these shapes. The 56 m ramp
    against the default 32 m atlas texel is still borderline for their own edges.
  - No CS settings or Scene file references the asset, so it may not be active at all.
- **Ray-march range and step:** the medium default range is 10 km, and the step at 10 km is about 32 m (×0.8).
  It ends the deck but doesn't make walls. Nothing switches to a 2D layer within range.
- **Horizon clouds** (`S\HorizonClouds.hlsli`; on by default: coverage 0.5, distance 60/108 km, flat bank for
  cloudy weathers):
  - The band is azimuth-only: `GroupMask` and `TopHeight` depend on direction alone, so its groups have vertical
    side edges and near-flat tops.
  - It is composited behind the ray-marched result wherever that is translucent, within about 1° of the horizon.
  - It probably contributes the flat-topped lumps along the top edge at t≈9 s, but not the walls 5-13° below the
    horizon. Quick in-game check: Horizon Clouds coverage 0.
- **Dark far deck at t≈9 s:** a lighting change (time-lapse / sun), not geometry.

## 2. Fix (in `S\Volumetrics.cs.hlsl`; fxc cs_5_0 compiles main ±NO_CLOUD_STORMS ±NO_LOCAL_NDF, renderCubemap, renderShadowVolume)
1. **`CLOUD_LOBE_DOME 0.3` (new).** Both lobe thresholds climb by `0.3 × smoothstep(0.3, 1, h)`. Turrets now
   narrow upward, and each top height follows its own lobe value: rounded domes of different heights. Below
   h = 0.3 nothing changes, so the flat bases, the low deck and the billowing near tops stay. Set it to 0 to go
   back to the old turrets.
2. **`CLOUD_TOP_FADE 0.15` (new).** Non-storm `topProfile *= smoothstep(0, 0.15, 1 - h)`.
   - This removes the shelf at the ceiling.
   - Types up to about 0.85 already reach 0 below h = 0.85, so they are unchanged.
   - High-type tops come down about 5 % of the window (around 50 m).
   - Storm columns keep their mirrored top.
3. **`CLOUD_SMOOTH_PROFILE_MIP 1` (new).** Mip = `max(profile×3 − 1, 0) × 1.5`.
   - It is still mip 0 below profile 1/3 (the edges and billows), 3 at profile 1, and continuous in between.
   - The sampler is trilinear, so there is no extra cost.
   - The storm-blend weather erosion uses the same value. Storm and eruption mips are untouched.

Each one has a define, so it can be A/B'd. Not done: softening the generator's `Remap` saturation. A soft knee
doesn't restore variation inside the saturated area, and the dome now supplies it.

Things to watch in game:
- Is the upper deck visibly thinner? If so, lower CLOUD_LOBE_DOME to 0.2.
- The cellular `.g` value range was not measured. If cores rarely exceed 0.8, tops lose more.

## 3. Deck export (`src\Features\PhysicalSky\VolumetricClouds.cpp`)
"base 69534, top 132559" is the altitude window itself: `zBottom` −14500 + 1200 m and + 2100 m
(ndfAltitudeOffset 1200, ndfAltitudeScale 900; 1 unit = 1.428 cm). The arithmetic is right, but the number is
misleading in two ways:
- The map only fills `baseHeight.x..y` (0..0.95) of the window.
- The deck is a **camera-centred shell** with `CloudCurvatureOffset = d²/R`, R = 74.946 km. It sits 0.33 km lower
  at 5 km, 1.33 km lower at 10 km and 5.3 km lower at 20 km. So peaks 5-10 km away, whose terrain maximum is
  about 39 400 units (Sky Above height grid 40 896 including the 1500 tree margin), poke through a deck whose
  base above the camera is 69534.

Changes:
- `BottledShaders_GetCloudDeck` now reports the filled band directly under the camera:
  `base + span × baseHeight.x` and `base + span × baseHeight.y` for procedural maps. That is 69534 / 129408 with
  these settings. Imported and local height maps keep 0..1.
- New export `BottledShaders_GetCloudDeckCurvature(float* radius)` gives R in game units (5.25 M). At horizontal
  distance d from the camera the deck is d²/R lower.

For Sky Above: the deck right under the camera is truly above 129k, so "out of reach" was correct. To fly
through or above the deck seen around the route, use `deckTop − d²/R` at the viewing distance. Lowering
ndfAltitudeOffset for that weather is the other option.

## Uncommitted changes
- `features/Physical Sky/Shaders/PhysicalSky/Volumetrics.cs.hlsl`: 3 defines, lobe dome, top fade, smooth mip.
- `src/Features/PhysicalSky/VolumetricClouds.cpp`: deck band and the curvature export. The 3-line `elapsed`
  clamp in `UpdateCloudWind` was already in the tree and is not part of this change.

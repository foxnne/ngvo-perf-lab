# cloud-weather-map - working notes

Offline generator of a world-anchored "local cloud map" (Local NDF) asset for the Physical Sky
volumetric clouds of the private Community Shaders fork (`C:\Users\foxnn\dev\skyrim-community-shaders`,
branch foxnne/nr-pr6, read only). NOT tested in game.

Paths below: `SRC` = `src\Features\PhysicalSky`, `SH` = `features\Physical Sky\Shaders\PhysicalSky`.

## 1. Format facts read from the fork (file:line)

### Asset location
- `kAssetRoot = "Data/Textures/PhysicalSky/LocalNdf"` (SRC\LocalNdf.cpp:17). Relative to the game working
  directory, so inside an MO2 mod the folder is `<mod>\textures\PhysicalSky\LocalNdf\<asset id>\`.
- Asset id = sub-folder name; only `[A-Za-z0-9_-]` allowed, otherwise rejected (LocalNdf.cpp:39-46).
  `tamriel-orographic` is valid.
- Folder scan: every directory under kAssetRoot (LocalNdf.cpp:48-62); UI button "Scan asset folders" / "Reload Cloud Textures".
- Files: `Height.dds`, `Modeling.dds`, optional `Mask.dds` (LocalNdf.cpp:141-143). Height.dds is only loaded when
  `strength*heightWeight > 0` (LocalNdf.cpp:144-145, 155); Mask is used only if the file exists (148-154).
- Loaded with `DirectX::CreateDDSTextureFromFile(device, context, path, nullptr, &srv)` (SRC\Ndf.cpp:49-50).

### Accepted DDS formats
- Validation: Modeling must pass `IsTextureNdf(.., 3)`, Height + Modeling must pass `IsTexturePair`, Mask `IsTextureNdf(.., 1)`
  (LocalNdf.cpp:157). A failing asset is listed as "Rejected local cloud asset".
- `IsTextureNdf`: SRV must be a plain TEXTURE2D (no array/cube) with a "linear" format (Ndf.cpp:542-551).
- `IsLinearFormat` (Ndf.cpp:553-584):
  - 1 channel: R8_UNORM, R16_UNORM, R16_FLOAT, R32_FLOAT, BC4_UNORM
  - 2 channels: R8G8_UNORM, R16G16_UNORM, R16G16_FLOAT, R32G32_FLOAT, BC5_UNORM
  - 3 channels: R32G32B32_FLOAT, B8G8R8X8_UNORM
  - 4 channels (accepted for any count): R8G8B8A8_UNORM, B8G8R8A8_UNORM, R16G16B16A16_UNORM, R16G16B16A16_FLOAT,
    R32G32B32A32_FLOAT, BC1/BC2/BC3/BC7_UNORM. No sRGB formats.
- `IsTexturePair`: Height (>=2 ch) and Modeling (>=3 ch) must have IDENTICAL width and height (Ndf.cpp:586-600).
  Mask may be any size. No power-of-two or square requirement anywhere; the local shader only uses uv.
- Mips: the bake shader samples with `SampleLevel(uv, mip)`, `mip = log2(source texels per atlas texel)`
  (SH\LocalNdf.cs.hlsl:35-39, 51), sampler = trilinear CLAMP (LocalNdf.cpp:74-81). So a mip chain is used when present.
  build_map.py writes a full box-filtered chain.

### Channel meaning
- Height.dds: `Texture2D<float2>`, both saturated to 0..1 (LocalNdf.cs.hlsl:14, 51).
  R = cloud BOTTOM, G = cloud TOP, as fractions of the state's vertical window:
  altitude_m = `altitude + value * heightSpan` (LocalNdf.cs.hlsl:52, heightFeather.x/.y set at LocalNdf.cpp:166).
  UI names: "Height zero (m)" and "Height span (m)" (LocalNdf.cpp:402-403). Global hint text: "height RG = bottom/top,
  modeling RGB = coverage/top type/bottom type" (Ndf.cpp:190).
  A column only holds cloud where top > bottom (SH\Volumetrics.cs.hlsl:741-744).
- Modeling.dds: `Texture2D<float4>` saturated 0..1 (LocalNdf.cs.hlsl:15, 39).
  - R = coverage (`ndf.coverage = model.r`, Volumetrics.cs.hlsl:770; density profile = vertical profile * coverage^exp, 731-732;
    coverage < 1e-8 means no cloud, 771).
  - G = top type (`top_type = model.g * saturate(coverage*10)`, Volumetrics.cs.hlsl:774): u coordinate into
    `NubisVerticalProfile.dds` .g with v = height fraction inside [bottom, top] (718). Decoded that LUT: type 0 fills only the
    lowest ~10 % of the bottom..top span (flat stratus/fog sheet), 0.5 fills ~60 %, 1.0 fills the whole span (towering cumulus).
  - B = bottom type (775): u coordinate into the same LUT .r (722). 0 = dense base (0.58 at the very bottom), 1 = strongly
    eroded/wispy base (0.14). Global procedural default range for B is 0..0.25 (SRC\Ndf.h:99).
  - A = per-texel influence mask when `modelingAlpha` is true, else treated as 1 (LocalNdf.cs.hlsl:48).
    RGB is stored STRAIGHT (not premultiplied); the bake shader multiplies by the weight (57-60).
- Mask.dds (optional): single channel R, 0..1, multiplied into the influence (LocalNdf.cs.hlsl:16, 40-45). Not produced here
  (Modeling alpha does the same job).

### World mapping
- World position used by the cloud shader is absolute world XY in game units; local uv is computed from
  `worldXY * GAME_UNIT_TO_M` (Volumetrics.cs.hlsl:245-248). GAME_UNIT_TO_M = 1.428/100 = 0.01428 (src\Utils\Game.h:49-50).
  So `center` and `size` are METRES = world game units * 0.01428, origin = worldspace origin (0,0) (cell 0,0 SW corner).
  The UI fills centre with camera world XY * GAME_UNIT_TO_M (src\Features\PhysicalSky.cpp:1324-1326) and labels it
  "World X / Y (m)" / "Width / length (m)" (LocalNdf.cpp:398-399).
- Texture mapping (LocalNdf.cs.hlsl:29-34): `delta = world - center; local = (dot(delta,(cos,sin)), dot(delta,(-sin,cos)));
  uv = local / size + 0.5`. With rotation 0: u = 0 at the WEST edge (min X), u = 1 east; v = 0 at the SOUTH edge (min Y),
  v = 1 north. DDS row 0 is v = 0, so **the first image row is the SOUTH edge** (a north-up picture must be flipped
  vertically before saving). uv outside (0,1) contributes nothing.
- `rotation` is in degrees (LocalNdf.cpp:164); positive turns the texture's +u axis from east towards north (counter-clockwise
  seen from above).
- `size` = full width (X) and length (Y) in metres, clamped 1..128000 each; centre clamped +-1e7 (LocalNdf.cpp:162-163).
  size.x and size.y are independent, so non-square maps are fine.
- Vertical: cloud-space z is relative to zBottom ("Cloud-space z is relative to bottomZ", SH\CloudLighting.hlsli:344-345);
  default zBottom = -14500 (src\Features\PhysicalSky.h:113, per-worldspace whitelist). So
  altitude_m = (world z + 14500) * 0.01428. `altitude` clamped -24000..48000, `heightSpan` 1..24000 (LocalNdf.cpp:166).
- Global field for comparison: bottom/top = lerp(lowCloudBaseAltitude, lowCloudTopAltitude, TexCloudHeight.rg)
  (Volumetrics.cs.hlsl:705-711); defaults ndfAltitudeOffset 256 m, ndfAltitudeScale 1792 m (Ndf.h:244-245), procedural
  baseHeight = {0, 0.95} (Ndf.h:100) -> global clouds sit between 256 m and ~1958 m above zBottom by default.
  The trace range is automatically widened to include the local window (PhysicalSky.cpp:1860-1862, VolumetricClouds.cpp:1122-1123).

### How the state parameters combine with the global field
- modelWeight = strength * modelingWeight; heightWeight = strength * heightWeight (each clamped 0..1) (LocalNdf.cpp:131-133).
  Both zero -> state skipped.
- Per atlas texel, mask = Mask.r (if any) * edge feather; feather = smoothstep(0, feather_m, distance to nearest map edge in m),
  feather clamped to half the smaller side (LocalNdf.cs.hlsl:46-47, LocalNdf.cpp:167). alpha = Modeling.a if modelingAlpha else 1.
- Height (LocalNdf.cs.hlsl:49-54, Volumetrics.cs.hlsl:306-317): w = mask * alpha * heightWeight (times the state's endpoint weight);
  `bottom/top = global * (1 - w) + local_altitude * w`. Always alpha-driven, in both blend modes.
- Modeling, modelingBlend 0 = Interpolate (LocalNdf.cs.hlsl:58-61, Volumetrics.cs.hlsl:282-287):
  w = mask * alpha * modelWeight; `rgb = global.rgb * (1 - w) + local.rgb * w`. Alpha 0 keeps the global weather,
  alpha 1 replaces it (so local coverage 0 with alpha 1 CLEARS the sky). Result is then mixed by the endpoint weight.
- Modeling, modelingBlend 1 = Maximum (LocalNdf.cs.hlsl:55-57, Volumetrics.cs.hlsl:280-281): `rgb = max(global.rgb, local.rgb * mask * modelWeight)`
  per channel; alpha is ignored for RGB; can only add cloud, never clear.
- The global field drifts with wind; the local map is sampled at the un-advected world position ("anchoredXY",
  Volumetrics.cs.hlsl:735, 765-766, 886) so it stays fixed to the terrain. Erosion noise still moves.
- Top type from the blended model also re-derives the "shaping start" value inside the map when the global
  heightAuxiliaryRange is non-degenerate (Volumetrics.cs.hlsl:747-756).

### Atlas / texel limits
- All active states are baked into one square R16G16B16A16_FLOAT texture array ("atlas") covering the bounding box of the
  states (LocalNdf.cpp:24-36, 171-176, 214-223).
- `effectiveTexelSize = max(clamp(localTexelSize, 1, 512; default 32), extent / 2044)`; `dimension = clamp(ceil(extent/texel)+1, 1, 2048)`
  (LocalNdf.cpp:206, 215-219). `localTexelSize` lives at `cloudMap.localTexelSize` (PhysicalSky.cpp:71, 83), default 32 m
  (Ndf.h:167); it is a baseline-only setting (LocalNdf.cpp:347-349), not part of the state.
- For this map: extent = 6960.4 m -> at the default 32 m the atlas is ~220 x 220 texels (32 m per texel); the finest
  possible is 6960.4/2044 = 3.41 m per texel (2048 atlas). Detail finer than the effective texel is averaged away by the mip pick.

### Settings JSON
- `cloudMap` serialises as {version 3, type, texture, procedural, localCloud, localTexelSize} (PhysicalSky.cpp:71).
- `localCloud` is a SceneBlend: an object with exactly one key `states`, an array of `{ "value": {...}, "weight": number }`,
  weights >= 0 and summing to <= 1 (src\Utils\SceneBlend.h:11-27). Entries with weight <= 0, enabled false, or a worldspace
  different from the current one are skipped (LocalNdf.cpp:126-130).
- State keys (Ndf.h:138-159): asset, worldspace, enabled, center [x,y], size [x,y], rotation, altitude, heightSpan, strength,
  modelingWeight, heightWeight, feather, modelingAlpha, modelingBlend (0 Interpolate / 1 Maximum). Missing keys take defaults.

## 2. Not determined from code
- Which DDSTextureLoader build is linked (whether single-mip files get auto-generated mips). Irrelevant here because the
  tool writes its own mip chain, but not verified that the loader accepts DX10-header R16G16(B16A16)_UNORM files with mips
  (these are standard and in the accepted-format list).
- The user's actual `ndfAltitudeOffset/Scale`, zBottom and procedural coverage ranges in the live settings (no saved
  PhysicalSky JSON with these keys was found in the places checked); defaults from code were assumed.
- How the sizes of the placed cloud statics relate to their XSCL scale (mesh bounds not read); blob radius is a knob.
- Visual result in game: nothing here was launched or tested.

## 3. Source data
- Terrain: `C:\Users\foxnn\dev\terrain-heightmap\mod\textures\terrain\HeightMaps\Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds`.
  NOTE: it has a LEGACY 128-byte header (DDPF_LUMINANCE 16 bpp), not a DX10 header. 3808 x 3008, raw = z/8 + 32767,
  row 0 = north, col 0 = west, 128 game units per texel (terrain-heightmap\notes.md, steps 3-4). The loader handles both headers.
- Extent: cells -57..61 x -43..50 -> x -233472..253952, y -176128..208896 game units ->
  centre (146.227, 233.964) m, size 6960.415 x 5498.143 m. (Texels are cell vertices; treating them as texel centres is a
  0.9 m offset, ignored.)
- Sea level: z < -14000 (= 7.1 m above zBottom). The height histogram piles up at -14200..-13900 (shore) and -14000 is the
  WRLD default water height; 27.0 % of the map is sea. Inland lakes/rivers at other water heights are NOT detected as water.
- Heights in sky metres: Whiterun ~157, Riften ~359, Throat of the World summit 770, land median 221, 95 % 507.
  The default global cloud base (256 m) is therefore BELOW half of the land; terrain routinely sticks into the cloud window.
- Seeds: 811 REFRs under the Tamriel world group (0x3C) of the original NAT-ENB.esp: 776 cloud statics + 35 NAT_MistTamriel.
  Scale 0.2..8 (median 3.0); z median 2420 (= 242 m), 95 % 562 m. They line up with the mountain ranges.

## 4. build_map.py - what it does
Working grid 952 x 752 (7.31 m per texel, exactly 4 x 4 height-map texels), north-up internally, flipped on write.
Terms (each 0..1, combined as 1 - prod(1 - term), capped at --max-coverage):
- orographic: upslope = wind . grad(terrain blurred 50 m), carried downwind with a one-sided exponential kernel
  (--advect-length 220 m), /--slope-scale, ^1.4; reduced by moisture already spent on ranges upwind (--depletion).
- rain shadow ("lee"): decayed running maximum of terrain along the wind (--shadow-drop 0.22 m/m) minus local terrain, or
  advected descent; multiplies orographic (fully), fog and marine (partly) and sets alpha so the global field is thinned there.
- peaks: absolute height (380..640 m) + prominence (35 m blur minus 260 m blur); not suppressed by the lee term.
- fog: enclosed valley floors (220 m mean minus local, below ~260 m) and broad low wet ground (< 60 m above sea, in a
  neighbourhood that is mostly low land), where the 90 m-scale slope is gentle.
- marine: blurred sea mask.
- seeds: Gaussian blob per placed static, sigma = --seed-radius (16 m) x scale (clamped 0.5..6), amplitude 0.85; mist statics
  go to the fog class; cloud statics also set the local cloud base (their z - 110 m, at least ground + 10 m).
- deterministic band-limited noise (PCG64, --noise-seed) breaks up the smooth terms.
Channels written:
- Modeling.dds R16G16B16A16_UNORM, 10 mips: R coverage, G top type, B bottom type (coverage-weighted mean of the per-term
  values: orographic .55/.20, peaks .45/.15, fog .14/.05, marine .30/.15, seed cloud .60/.25, mist .14/.05),
  A influence = max(smoothstep(.04,.40,coverage) * alpha-max, lee * alpha-clear).
- Height.dds R16G16_UNORM, 10 mips: R/G = (base, top - altitude) / heightSpan; window computed from the data and written to JSON.
  Bases: orographic max(lcl, broad terrain + 90), peaks max(broad terrain + 30, local - 170), fog/mist ground - 12,
  marine --marine-base, seeds from their z; thickness 220..520 m (the top type decides how much of it is filled).
- `localcloud_state.json`: ONE element for the `cloudMap.localCloud.states` array (`{"value": {...}, "weight": 1.0}`).
  For a baseline with only this map the whole setting is `"localCloud": {"states": [ <that element> ]}`.
- `preview\`: north-up PNG of every channel, every term, `relief.png`, `overlay_clouds_on_relief.png` (white opacity =
  coverage x influence) and `overlay_diagnostic.png` (magenta = map asserts clear air, orange/cyan dots = cloud/mist statics,
  yellow arrow = wind). `build_report.txt` has the options and statistics.

Intended use: modelingBlend 0 (Interpolate) with modelingAlpha true, so the map adds cloud on windward slopes/peaks, thins
the global field in rain shadows, and leaves alpha-0 areas (Whiterun plains, the Rift floor) to the normal weather.
With modelingBlend 1 (Maximum) the same files only add cloud (R is near 0 where nothing is asserted) and the lee
suppression is lost. Mod layout: `<mod>\textures\PhysicalSky\LocalNdf\tamriel-orographic\{Height,Modeling}.dds`.

## 5. Result of the default run (previews inspected, NOT tested in game)
- Defaults: wind from 330 deg, orographic .70, peaks .55, rain-shadow .85, fog .60, marine .32, seeds .50, seed-radius 16,
  noise .35, max-coverage .85, alpha-max .90, alpha-clear .65, lcl 300, marine-base 150, feather 300, width 952.
- Output window: altitude 0 m, heightSpan 1056 m. Coverage: land median .23, 95 % .66, max .85; only 12 % of the map above .5,
  0.3 % above .8. Throat .81 (base 564, top 1044, summit 770); Whiterun .04 with alpha 0; Morthal fog .37 (base 43);
  north sea .28 (150..530 m, type .30).
- Two consecutive runs give byte-identical DDS/JSON. DDS re-read and sampled through the shader's uv formula: Throat,
  Whiterun, Morthal and the north sea land on the expected texels (confirms the vertical flip).

## 6. Weaknesses / things to check in game
- The blobs from individual statics are still visible as a "popcorn" texture in coverage where statics are sparse.
- Alpha is close to binary (0 or .9): inside cloud areas the drifting global field is almost fully replaced by a static
  coverage pattern; only the erosion noise moves. Lower strength / --alpha-max if the clouds look frozen.
- The window bottom is 0 m, so the low-cloud trace range is extended down from the global base while the state is active
  (PhysicalSky.cpp:1860-1862) - possible cost; fog and marine cloud sit far below the default 256 m global base.
- At the default localTexelSize (32 m) the atlas is only ~220 texels across; river-valley fog (10-30 m wide) will mostly
  average away unless `cloudMap.localTexelSize` is lowered (8 m -> ~870 texels).
- Large magenta "clear" areas lie south and east of the playable border (high out-of-bounds terrain); harmless but untuned.
- Sea mask is purely z < -14000; lakes (Ilinalta, Honrich, Yorgrim...) get no marine/wet treatment; Falkreath gets little fog.
- Blob size vs. XSCL, the wind direction (330) and all thresholds are judgement calls, tuned by eye on the previews only.
- Cloud bases can still dip into terrain around steep relief (bases follow 55-260 m blurred terrain).

# Pass 2 (2026-11-18) - why the first map made curtains, and how to author for this system

In-game result of `tamriel-orographic` (frames in `ngvo-perf-lab\results\sky_sweep\map-plains_west`, `map-ilinalta_west`):
tall vertical striped curtains from just above the terrain to the top of the sky, same at 32 m / 8 m texel and in Maximum,
much weaker at strength 0.6, +2-3 ms. Global layer in the test: ndfAltitudeOffset 1200, ndfAltitudeScale 900; all other
procedural values default (live SettingsUser.json only overrides `primary.range`), so global bottom = 1200..1218 m
(baseHeight.x 0 + heightVariation 0..0.02 of 900 m, Ndf.h:97,100, NdfGenerate.cs.hlsl:187-202) and top = 1200 + 0.95*900 = 2055 m.

## P2.1 Cause (file:line; `V` = SH\Volumetrics.cs.hlsl)
The cloud field is ONE slab per column: `sampleNDF` gets a single bottom/top pair and a single modeling triple
(V:735-777). A local map never adds a second slab; it moves the one slab:
- heights: `height.xy = global.xy*(1 - w) + local_altitude*w`, w = sum(endpointWeight * mask * alpha * strength*heightWeight)
  (LocalNdf.cs.hlsl:49-53, V:306-317). Global xy = lerp(lowCloudBase, lowCloudTop, TexCloudHeight.rg) (V:708-709).
- coverage/types (Interpolate): `rgb = global*(1 - a) + local*a` with the same alpha (LocalNdf.cs.hlsl:59-60, V:284-287).
So wherever 0 < w < 1 the slab is at an in-between altitude and still carries (1-a) of the GLOBAL coverage, and wherever
w changes horizontally the slab surface tilts. With global 1200..2055 m and local ~200..700 m, a change of alpha of 0.1
moves the slab by ~90 m. Measured on the shipped files (python, same uv maths as the shader):
- alpha > 0.02 on 93 % of the map, 0.05 < alpha < 0.85 on 65 %; within 3 km of the plains camera 91 % has alpha > 0.02.
- slope of the BLENDED slab bottom: median 0.95 m/m, 90th percentile 8 m/m, 99th 19 m/m; 49 % of the map is steeper
  than 45 degrees. Slope of the local height channel alone: median 0.26, 99th 1.4. => the walls come from alpha
  variation (coverage-driven smoothstep + "popcorn" seeds + lee term), NOT from steps in Height.dds.
- transect west of the plains camera: alpha 0 for 1.5 km (slab 1200..2055), then within 450 m alpha 0.50/0.81/0.90 and the
  slab bottom goes 1200 -> 708 -> 338 -> 221 m, top 2055 -> 1374 -> 775 -> 585 m, then back up to 827/1521 and down again.
The global cumulus (coverage up to 0.65, drifting) are rendered inside that corrugated slab: every alpha ramp is a
near-vertical sheet from the local bank up to 2055 m, with the vertical profile stretched along it = the striped curtains.
Candidates:
- (a) REJECTED as stated. The global slab is not stretched: lowCloudBase/TopAltitude stay 1200/2100 (VolumetricClouds.cpp:1116-1118,
  1172-1173). Only the TRACE range is widened to min(base, local altitude) .. max(top, local altitude+span) = 0..2100 m
  (VolumetricClouds.cpp:1122-1123, 1175-1176; V:188-190, 1139-1141). That costs time, see P2.2, but adds no cloud by itself.
- (b) CONFIRMED, main cause, with the correction that it is not "bottom from one source, top from the other": both
  are blended with the same weight, the slab is moved as a whole and tilts where the weight changes.
- (c) REJECTED for Height.dds (smooth, see slopes above); true for the alpha channel.
- (d) Minor. Types 0.45-0.60 fill ~60 % of the span; additionally `topExpansion` (default topExpansionScale 1, Ndf.h:252)
  takes max(top, TexCloudAdjustmentLUT) (V:719-725), which can fill more. Makes the sheets fuller, does not create them.
- (e) REJECTED. Files re-read: 952x752, 10 mips, sizes exact, formats 11 / 35, G >= R everywhere, R 0.007..0.54, G 0.22..0.99,
  probes land on the right texels.
- (f) Alpha 0 does pass the global field through untouched (weights are premultiplied in the atlas, LocalNdf.cs.hlsl:53,60).
  The plain looked covered because (1) only a ~1.5 km patch really has alpha 0 and the curtains start right behind it and
  stand 400-2000 m tall, filling the view; (2) NOTES section 5 judged "Whiterun alpha 0" from one probe point.
- Same in Maximum: Maximum only changes RGB; heights are still blended by alpha*heightWeight (LocalNdf.cs.hlsl:49-54; UI hint
  LocalNdf.cpp:421). Same at 8 m: the ramps are 50-300 m wide, far above either texel size.
- strength 0.6: every weight is x0.6 (LocalNdf.cpp:131-133), so alpha tops out at 0.54, the slab only comes halfway down and
  keeps >= 46 % global coverage: looks like a disturbed normal sky. Partial strength is never "a fainter bank".

## P2.2 Cost
`LocalNdfIntersectsRay` is true for every ray that crosses the atlas rectangle = the whole province (V:344-369), so all
rays march 0..2100 m instead of 1200..2100 m; while any local state is active the main pass uses the shader variant
without the weather-bounds reduction (VolumetricClouds.cpp:1667; V:197, 1173, 1228) and without the
CloudReflectionInterval skip (V:1346, 1353). Inherent to any full-map local state with height influence.

## P2.3 Other facts that matter for authoring
- Curvature applies to local clouds too: profile altitude = z + d^2/R, R = curvatureRadius 74.9 km (CloudGeometry.hlsli:4-12,
  V:881). A bank authored at 500 m renders 13 m low at 1 km, 53 m at 2 km, 120 m at 3 km, 334 m at 5 km from the camera,
  so distant low banks sink into the terrain. Not fixable from the asset.
- Upstream sample: for height fraction > 0.1 coverage = max(here, 60 x cloudShapeShear upwind) (V:758-770), shear =
  (highVel - lowVel) * 3 * span/(cirrus - mid) capped 150 m (VolumetricClouds.cpp:984-991). With the test wind (5 / 10 m/s)
  that is roughly 2 m shear -> ~110 m upwind (cirrus altitude not checked). Global coverage can leak ~110 m into a cleared
  area through this path.
- The atlas is sampled bilinearly (V:284, 313) and baked from the mip that matches the atlas texel (LocalNdf.cs.hlsl:37-39):
  any authored transition must be >= 2 atlas texels wide to survive.

## P2.4 Can the system show low banks under a higher global layer? Authoring rules
No, not in the same column: one bottom/top pair and one coverage value per column (V:735-777). A column is either the
global slab, the local slab, or a mix that sits in between. What the asset CAN do is take columns away from the global
layer completely. Rules that follow from the code:
1. strength 1, heightWeight 1, modelingWeight 1, Interpolate, modelingAlpha true. Any weight below 1 inside a bank is a
   slab at the wrong height holding global cloud. "Sparing / faint" is done with coverage (R) and bank count, never with
   strength or alpha.
2. Alpha is 0 or 1 wherever cloud can exist. Going outwards from a bank: core (a 1, cov > 0, bank heights) -> skirt
   (a 1, cov 0, bank heights) -> ramp (a 1, cov 0, heights bank -> global range) -> plateau (a 1, cov 0, heights = global
   range) -> fade (a 1 -> 0, cov 0, heights = global range). The slab only tilts where coverage is exactly 0, and alpha only
   changes where local heights equal the global heights. Each zone >= 2 atlas texels (rule P2.3) => use
   `cloudMap.localTexelSize` 8 for the province map (16/16/16/32 m zones); at 32 m the zones would need 64/64/64/128 m.
3. Height.dds must therefore span bank bottom .. GLOBAL top, and the map is tied to the weather's ndfAltitudeOffset /
   ndfAltitudeScale / baseHeight (here 1200 / 900 / 0.95 -> 1200..2055). With another global range the fade ring becomes a
   step of that difference; rebuild with --global-base / --global-thickness.
4. Price: every bank punches a hole in the global layer (bank + ~80 m collar at 8 m texels). Overcast above a bank is
   impossible. Keep banks few and small; spacing so that collars rarely merge.
5. Heights smooth inside a bank (flat per bank here); bottom at or slightly below the slope so the bank touches terrain.
6. Maximum blend + heightWeight 0 (the "stationary maximum" preset, LocalNdf.cpp:387-397) is the safe way to ADD cloud, but
   only inside the global slab (1200..2055 m here): cap clouds above chosen mountains, no holes, no trace widening
   (LocalNdf.cpp:177-180 leaves the altitude window empty), no curtains. It cannot make anything below the global base.
   The pass-2 Modeling.dds works in that mode too (G/B are 0 outside banks, so max() does not change global types).
7. Distant banks sink (curvature, P2.3); only banks within ~2 km of the camera sit where they were authored.

Smallest code change that would give real low banks (NOT made): a third blend mode "separate layer".
- Ndf.h LocalNdfBlendMode: add `Layer`; LocalNdf.cpp:170 pass 2; UI combo LocalNdf.cpp:406.
- LocalNdf.cs.hlsl: for mode 2 write MaximumOutput = float4(model.rgb * mask * alpha * modelWeight, 0) and HeightOutput as now.
- Volumetrics.cs.hlsl: in LocalNdfHeight (306) and ApplyLocalNdfModel (273) skip endpoints with LocalNdfWeights[i].y == 2, so
  the global slab is untouched. In sampleNDF (735), after the global `ndf` is built (also on its early-outs at 743/771):
  if InLocalNdf and profileAltitude is inside the local window, read the layer endpoint's height
  (`h = tex.rg / max(tex.b, 1e-4) * localNdfAltitude.y + localNdfAltitude.x`, un-premultiplied) and model; if
  bottom < profileAltitude < top build a second NDFInfo (height_fraction from h, coverage = model.r, types = model.gb,
  dimension_profile = CloudNdfProfile) and keep whichever of the two has the larger dimension_profile.
  The trace range is already widened (VolumetricClouds.cpp:1122-1123) and shadows use the same density function (V:1587).
  One extra pair of atlas samples per march step, only below the local window top inside the footprint.

## P2.5 build_map.py changes and outputs
`--mode orographic` (default) is the unchanged pass-1 generator. New: `--mode mist | diag-one-blob | diag-two-heights |
diag-flat-clear`, with `--global-base 1200 --global-thickness 900 --global-top-frac 0.95 --atlas-texel 8 --shear-margin 0
--banks 60 --bank-spacing 340 --bank-coverage 0.6 --bank-type 0.4`. Each run writes Height.dds, Modeling.dds,
localcloud_state.json, build_report.txt and preview\ (incl. `zones_cloud_hole_lowslab.png`: red cloud, green alpha, blue
slab below global base; mist also `overlay_banks_on_relief.png`: white banks, magenta cleared global sky, dots = class).
- `out\diag-one-blob`: 3840 m square centred on game units (0,-10000); disc radius 600 m (full coverage 0.8 inside 390 m),
  bottom 400, top 700, type 1.0; zones 64/64/64/128 m (works at the default 32 m texel). altitude 400, heightSpan 1664.
- `out\diag-two-heights`: same footprint; west disc centre game units (-35014,-10000) r 350 m 300..500 m; east disc centre
  (28011,-10000) r 350 m 600..900 m. altitude 288, heightSpan 1776.
- `out\diag-flat-clear`: whole province, A 1, RGB 0; state heightWeight 0, feather 0.
- `out\tamriel-mist-v2`: 45 banks (5 Throat ring, 8 face bases, 19 ridge crests, 13 saddles), ellipses ~120-190 x 55-80 m,
  bottoms 250..548, tops 390..718, coverage 0.6, type 0.4; cloud on 3.9 % of the map, global sky cleared/dimmed on 16.5 %.
  Candidates: the placed NAT statics inside the playable box scored by terrain (face = steep at 150 m scale + locally
  concave; ridge = above the 260 m mean + convex; saddle = Hessian eigenvalues of opposite sign), plus terrain-only
  lattice points at 0.6x score; greedy by score, round-robin over classes, >= 340 m apart. altitude 240, heightSpan 1824.
  REQUIRES cloudMap.localTexelSize 8 (emulated at 32 m: 6.5 % of the atlas is steep slab carrying coverage = curtains again).
Emulation of bake + blend on the written files (box mip, bilinear atlas, global 1200..2055): steep slab carrying
coverage = 0 texels for both diag assets at 32 m and for mist-v2 at 8 m; 39 % for tamriel-orographic.

## P2.6 Still uncertain (nothing tested in game)
- The upstream shear sample (P2.3) can put global coverage into the ramp ring on the upwind side (thin partial curtain).
  If seen: rebuild with `--shear-margin 150`, or test with equal low/high wind.
- How coverage 0.6 / type 0.4 looks after noise erosion at a 150-m bank size (the shape noise tiles at 230 m); bank size,
  coverage and type are guesses. topExpansion may fill more of the span than the type suggests.
- Whether the holes in the global deck are acceptable; whether far banks sinking by curvature look wrong.
- TransmittanceSampler assumed linear/clamp (not checked). Cirrus altitude (sets shear) not checked.
- Terrain classes are heuristics checked only on the preview; face bases are under-represented (8).

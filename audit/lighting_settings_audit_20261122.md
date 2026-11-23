# Lighting settings audit, 2026-11-22

Read-only audit. Nothing was edited, built or launched. Source: `C:\Users\foxnn\dev\skyrim-community-shaders` @ `foxnne/llf-shadowless-spots` (f684fc825). Paths below are relative to that repo unless absolute. Settings: `mods\CS Settings\SKSE\Plugins\CommunityShaders\SettingsUser.json` (user layer), `Presets\foxnne-look\Baseline\*.json` (baseline layer), `SceneSettings\SceneManager.json`.

Labels: **[read]** = read literally in code/settings. **[computed]** = arithmetic from settings and formulas, not a capture. **[inferred]** = conclusion not proven from code; needs the stated check.

## 0. Headlines

1. **The "everything is far too bright" root cause is an exposure-chain problem, not a light-unit problem.** Three parts:
   - (fixed 11-20) Histogram Auto Exposure read zero because SharedData (b5) was not bound on the compute stage (commit ae00ed0ee).
   - (**still open, [inferred], high confidence**) **Local Exposure has the same defect.** Its analysis pass decodes pre-exposed radiance with `SharedData::RcpPreExposure` (`features/Post Processing/Shaders/PostProcessing/LocalExposure/localexposure.cs.hlsl:54`) but `LocalExposure::Draw` binds only its own buffer at b1 (`src/Features/PostProcessing/LocalExposure.cpp:353`). It runs immediately *before* Auto Exposure in the pipeline (`src/Features/PostProcessing.h:112-131`), i.e. at the exact point where the histogram pass was found to read zero. If b5 is empty there, every pixel's base luminance is the floor (-13 log2) and Local Exposure stops being local: it becomes a **uniform gain of `Strength x 0.2 x (12 + log2(adapted luminance))` EV** [computed]: about **+0.7 EV on the plains, +0.6 EV in the Bannered Mare, +0.3 EV at night** at the current Strength 0.4, and +1.5 to +1.7 EV at the default Strength 1.0. That is "all lights, interior and exterior, too bright", and it appeared with the pre-exposure merge (11-15/17), exactly when ExposureCompensation went from -0.56 to -2.81 in the settings backups.
   - (by design, but it hides in the number) `BrightSceneKneeEV -10` with `BrightSceneCompression 0.22` adds `0.22 x (sceneEV + 10)` EV of exposure to every scene (`histogram.cs.hlsl`, `avgLogLum -= max(avgLogLum - knee, 0) * compression`): **+2.7 EV on the plains, +2.3 EV in the Mare, about +1.3 EV at night, +0.2 EV in Bleak Falls** [computed from the metered values in the memory note]. ExposureCompensation -4.2 / -4.7 mostly cancels that pivot offset.
   - Net true exposure bias today [computed]: plains -4.2 + 2.7 + 0.7 (Local Exposure, if broken) + 0.3 (grading exposure 1.231) = **about -0.5 EV**. Nothing is hiding four stops any more. The -4.2 is fragile, not wrong.
2. **Light types are not scaled uniformly, by design.** With Physical Sky overriding the sun, sun and sky are in "solar illuminance" units (default 10 = full sun, sunlit white about 3.2; saved value is **20**, so sunlit white is about 6.4 x 1.1 x transmittance). Point lights, fires, glow maps and weather ambient stay in vanilla units (white about 1). So daylight is 6-7x (2.7 EV) above a vanilla-unit light. That is the right direction physically and auto exposure absorbs it; it does not flatten daylight. It does shift everything with an absolute threshold (bloom threshold, Light Shafts MaxBrightness, adaptation ranges, fires/torches by day).
3. **Why the image is flat** (ranked, section 2): (a) the display rendering has slope 1.0 and no toe (PsychoV contrast 1.0, highlights 0.88, LUT and Look Grade off): the picture is a linear print of the scene; (b) additive veils set the black floor: **COD Bloom sums 7 un-normalised mips, so BlendFactor 0.05 is really about 0.35 of a wide blur of everything above the threshold**, plus the game's volumetric-lighting haze; (c) sky fill is on the high side and under-occluded (SSGI Thickness 0.02, a fifth of default); (d) Local Exposure, whichever state it is in, is not doing anything useful for a neutral base.
4. **IBL / Skylighting / SSGI are not fighting, but only one of them is in charge.** With SSGI on, `ReplaceAmbient` is forced to 1 (`src/Features/ScreenSpaceGI.cpp:1212`) and the forward ambient is zeroed for deferred geometry (`package/Shaders/Lighting.hlsl:3819-3820`). Outdoor ambient on opaque surfaces is the SSGI cubemap fallback, which reads the IBL and Skylighting *settings* (SkyIBLScale, SkyIBLSaturation, DALCAmount, MinDiffuseVisibility) but not their code path.

## 1. Effective values, feature by feature

Layering [read]: code default, then baseline pack, then user file (`src/BaselineManager.cpp:192-215`). Log of the last run (`Documents\My Games\Skyrim Special Edition\SKSE\BottledShaders.log`, 01:05) shows all 23 baseline files applied except **Skin** (rejected: unrecognised keys). "Eff." = value in effect.

### Post Processing chain (order: Fire, DoF, Vignette, Local Exposure, Auto Exposure, Motion Blur, Glare, Bloom, Lens Flare, Lens, Composite, Color Grading, Look Grade, LUT, Camera, Border; `PostProcessing.h:112-131`)

| Stage / key | Default | Baseline | User | Eff. | What it does | Verdict |
|---|---|---|---|---|---|---|
| HAE ExposureCompensation | 0 | -0.15 | -4.2 | -4.2 EV | gain = 0.18 x 2^comp / adapted luminance (`composite.ps.hlsl`, `PSComposite`) | See headline 1. Fragile |
| HAE BrightSceneKneeEV / Compression | 3 / 0 | - | -10 / 0.22 | -10 / 0.22 | scenes above the knee adapt only 78% | Knee at the slider minimum = constant offset on every scene |
| HAE AdaptationRange (day / interior / night) | [-2,6] / [-1.65,4.5] / same | **[-0.85,-1.31] (inverted)** | [-6,16] / [-10,10] / [-8,10] | user | clamps adapted luminance, EV100 (`HistogramAutoExposure.cpp:79-82`) | Fine. The baseline value is a trap: if the user key is ever dropped, exposure is pinned again |
| HAE AdaptArea | 0.6 | 0.4 | - | 0.4 | central 40% box, 10-90% trimmed log mean | On a landscape the box is half sky: under-exposes ground |
| HAE AdaptSpeed | 1.5 | 0.6 | 1.0 | 1.0 | | Fine |
| Local Exposure enabled / Strength / Exposure | on / 1.0 / 0.7 | on | 0.4 / 0.63 | on, 0.4 | base-layer contrast: shadows x0.8, highlights x0.75 beyond +-1 EV (`composite.ps.hlsl`, `RemapBaseContrast`). `Exposure` is only used when HAE is off | Working: lifts shade up to +0.3 EV, pulls highlights -0.2 EV. Broken: uniform +0.7 EV. Either way it reduces sun:shade or does nothing |
| COD Bloom Threshold | 0 EV100 | 0.82 | 3.14 | 3.14 (1.10 scene units) | luminance threshold before exposure (`CODBloom.cpp:213`) | With the sun at 20 the sky (about 1.5-2.5 units [computed]) and all sunlit ground are above it |
| COD Bloom BlendFactor | **0.01** | 0.15 | 0.05 | 0.05 | scene + bloom x BlendFactor (`Composite.cpp:233`). The upsample chain adds each mip at weight 1 with no normalisation (`CODBloom.cpp:265-287`, `MipBlendFactor` all 1) | **Effective mix about 0.35 on large bright areas; 5x the code default. Prime black-floor suspect** |
| Color Grading tonemapper | GT7 | PsychoV | - | **PsychoV 30** | `ColorGrading.cpp:239-258`, `colorgrading.hlsl:646-667` | See below |
| tonemapParams[0] | [1,1,1,1] | [1,0.8,1,0.92] | [1,0.88,1,1] | exposure 1.0, **highlights 0.88**, shadows 1.0, **contrast 1.0** | contrast = power on the cone response around 0.18 | No toe, slope 1 |
| tonemapParams[1] | [1,1,1,1] | [0.93,1,1,0] | [1,1,1,0] | saturation 1, cone response 1, gamut compression 1, compression 0 = auto | | Fine |
| exposureTemperatureTint | [1,65,0,0] | [1.231,67,0,0] | - | x1.231 (+0.30 EV), 6700 K | `colorgrading.hlsl:828` | A second exposure control; fold into HAE |
| gameTintBlend / gameCinematicBlend | 0 / 0 | 0.2 / - | - | 0.2 / 0 | weather imagespace tint 20%; weather contrast/brightness ignored | NAT's imagespace contrast is not applied (correct for this pipeline) |
| oklchSaturation | 1 | 0.802 | 1 | 1 | | Fine |
| LUT, Look Grade, Vignette | off | on | off | off | | Intended neutral base |
| Camera (grain 0.08, distortion), Border, Glare, Lens | off by default (`PostProcessing.cpp:482`) | - | - | off | | No grain |
| Motion Blur, Fire | off | - | on | on | | not lighting |

PsychoV curve [computed from `psychov_30.hlsl:561-598`, auto compression h = 1.85/log10(1/0.18) = 2.48]: 0.18 maps to 0.18; scene 0.28 maps to 0.28; scene 1.0 maps to 0.77; shadows follow `0.18 x (x/0.18)^1.01`. It is a straight line with a late shoulder. A camera or film rendering has a mid slope of 1.2-1.5 and a toe; the LUT and Look Grade used to supply that and are off.

Output [read]: `package/Shaders/ISHDR.hlsl:154-160` encodes with pure gamma 2.2 and adds +-1/255 dither that is scaled to zero at black. **The output transform and dither do not lift blacks.** Display 0.12 = linear 0.0094.

### Sun, sky, ambient

| Feature / key | Default | Baseline | User | Eff. | What it does | Verdict |
|---|---|---|---|---|---|---|
| Physical Sky sunlightColor | 10 x (1, .97, .95) (`PhysicalSky.h:134`; "10 = full sun, sunlit white about 3.2", `PhysicalSky.h:191`) | - | 20, 19.4, 19 | 20 | sun illuminance before the atmosphere; also drives sky, haze and clouds | 2x the design unit. Ratio sun:sky unchanged. Leave, but know that thresholds are calibrated for 10 |
| trMix / apLumMix / apTrMix | 1 / 1 / 1 | - | - | 1 / 1 / 1 | | Physical |
| cloudShadowRemapRange | [0,1] | - | [0,0.5] | [0,0.5] | `features/Physical Sky/Shaders/PhysicalSky/Common.hlsli:868-880`: cloud transmittance 0.1 becomes 0.2, 0.25 becomes 0.5, 0.5 becomes 0.875 | **Halves the volumetric cloud shadow on surfaces.** See 2.4 |
| cloudLayer.lighting deckLight / deckGroundLight | 0 / 0 (`PhysicalSky/Ndf.h:346,350`) | - | - | off | cloud deck ground light | Off: not a contributor |
| aerosolType / Loading / scatter | Custom / 1 / 39.96 | - | 1 (Continental) / 0.2 / [2.52,3.42,4.58] Mm^-1 | | | Very clean air: aerosol optical depth over 3 km x exaggeration is about 0.03 [computed]. All distance haze is blue Rayleigh |
| Linear Lighting directionalLightMult | 1.0 | 1.10 | - | 1.10 | surfaces only (`package/Shaders/Common/ColorManagement.hlsli:82-85`); sky/haze/clouds do not see it. With Physical Sky the pi factor is dropped (`src/Features/LinearLighting.cpp`, `directionalLightMult = (physicalSkyEnabled ? 1 : pi) x setting`) | **The clean sun:fill lever** |
| Linear Lighting ambientMult | 1.0 | 1.18 | - | 1.18 | multiplies weather DALC only (`ColorManagement.hlsli:92-95`) | Ambient raised more than the sun, but DALC is negligible outdoors (vanilla units x 0.25 against a sun of 20). Matters indoors |
| Linear Lighting pointLightMult | 1.0 | - | - | 1.0 (x pi, cancelled by the 1/pi diffuse) | | Vanilla scale. Not inflated |
| IBL EnableIBL / DALCMode / DALCAmount | 0 / 2 / 1.0 | 1 / 3 / 0.5 | - / 2 / 0.25 | 1 / 2 / 0.25 | ambient = DALC x 0.25 + sky cube SH (`features/IBL/Shaders/IBL/IBL.hlsli`, `GetDiffuseIBL`) | Fine |
| IBL SkyIBLScale / SkyIBLSaturation | 1 / 1 | 1.21 / 0.6 | 1.0 / - | 1.0 / 0.6 | scale and saturation of sky fill; also read by the SSGI fallback (`diffuseGI.cs.hlsl:225-227`) | 1.0 is physical if the cube is right. 0.6 makes shade grey instead of blue |
| IBL SkylightingAffectsEnv | 0 | - | 1 | 1 | sky visibility also dims the DALC share | Good |
| Skylighting MinDiffuseVisibility / MinSpecular / MaxZenith | 0.1 / 0.1 / 90 deg | 0.29 / 0.2 / 70 deg | 0.1 / - / - | 0.1 / 0.2 / 70 deg | floor of sky visibility (`features/Skylighting/Shaders/Skylighting/Skylighting.hlsli:106`) | Already at default. Fully enclosed shade still gets 10% of the sky |
| SSGI Enabled / EnableGI / cubemap fallback | on / on / on | - | - | on, so ReplaceAmbient = 1 | | See headline 4 |
| SSGI AOPower | 1.0 | 2.0 | - | 2.0 | shapes only the fallback occlusion (`diffuseGI.cs.hlsl:442-443`) | Already strengthened |
| SSGI GIStrength | 1.0 | 1.03 | - | 1.03 | bounce source brightness (`diffuseGI.cs.hlsl:370`) | Fine |
| SSGI Thickness | **0.1** | - | 0.02 | 0.02 | occluder thickness as a share of depth (`diffuseGI.cs.hlsl:338`) | **5x thinner than default: occluders leak, more open sectors, more sky fallback under eaves and at contacts** |
| SSGI FallbackSkyBoost | 1.0 | - | 0.0 | 0 | extra sky on up-facing surfaces (`diffuseGI.cs.hlsl:203`) | Correctly removed |
| Sky Sync HorizonFadeElevation / MinShadowElevation | 7 / 7 | 9.3 / - | 1.5 / 3.5 | 1.5 / 3.5 | | Good; irrelevant at noon |
| Sky Sync Full / Crescent / New moon intensity | 1.0 / 0.25 / 0.05 | 0.191 / 0.159 / 0.133 | - | baseline | | Night only; see 5 |

### Shadows

| Feature / key | Default | Eff. | Verdict |
|---|---|---|---|
| Screen Space Shadows Enable / SampleCount / SurfaceThickness / ShadowContrast / FilterShadowMask (`ScreenSpaceShadows.h:29-36`) | 1 / 1 / 0.01 / 1.0 / 0 | 1 / 2 / 0.02 / 1.0 / 1 (baseline) | Fine |
| Terrain Shadows | on | on | Fine |
| Cloud Shadows (vanilla cubemap) Opacity / Scattering (`CloudShadows.h:15-16`) | 0.5 / 0.4 | 0 / 0.4 | Off on purpose. With Opacity 0 the scatter term is also 0 (`package/Shaders/Common/ShadowSampling.hlsli:88`). Leave off |
| LOD Shadows | - | off | Parked by user |
| Light Limit Fix EnableContactShadows / EnableLocalShadows / RealisticFalloff | - | on / **off** / off | Interiors: point lights cast no shadows, so nothing is grounded by lamp light |

### Haze and fog

| Feature / key | Default | Eff. | Verdict |
|---|---|---|---|
| Atmosphere and Fog distanceExaggeration / Haze share / Limit (`ViewAtmosphere.h:46-52`) | 1 / 0.35 / 5.0 | 6 / 0.35 / 5.0 | At 3 km: blue transmittance about 0.59, green 0.80, red 0.89 [computed]. Depth cue is real but all blue. Agrees with your sweep: not the main veil |
| Atmosphere and Fog heightFogSkyLight | 0 | 0 | Height fog lit by the weather fog colour (vanilla units, so dim against a sun of 20) [inferred] |
| Volumetric Lighting ExteriorStrength / SunFocus / ShaftDefinition | 1 / 1 / 0 | 1.4 / 1.0 / 1.0 | With SunFocus 1 the 1.4 only raises the lobe around the sun (`VolumetricLighting.cpp:328-345`) |
| Volumetric Lighting ExteriorDayHaze | 1.0 | 0.3 (user; baseline 0.15) | Scales the weather's whole volumetric intensity (`VolumetricLighting.cpp:348`). The result is **added** to the frame after the froxel medium, with no extinction (`package/Shaders/ISCompositeLensFlareVolumetricLighting.hlsl`, `color += volumetricLightingColor * volumetricLightingPower`). A second haze on top of the froxels; lifts near blacks wherever the view ray crosses lit air. Size depends on NAT's records: not derivable from code |
| Exponential Height Fog enabled / vanillaFogStrength / fogLightingInfluence / sunlightAttenuationAmount | 0 / 1.25 / 0.35 / 1.0 | 1 / 0.1 / 0.7 / 1.0 | Sun is attenuated by fog as well as by the atmosphere (`Lighting.hlsl:3166-3169`, `ExponentialHeightFog.hlsli:305-340`). Double extinction in principle, small at strength 0.1 |
| Light Shafts SunStrength / VeilRemoval / MaxBrightness (`LightShafts.h:38-52`) | 0.1 / 1 / 1.0 | 0.25 / 1 / 1.0 | Contrast-only (no veil). MaxBrightness is in "sun = 10" units, so it is half as high relative to a sun of 20 |
| Ground Fog | - | off | Parked |

### Vegetation and the rest

| Feature / key | Default | Eff. | Verdict |
|---|---|---|---|
| Tree Wind LODTreeBrightness / CrownOcclusion / RoundNormal / WrapFrontLit / Variation (`TreeWind.h:67-77`) | 1.7 / 0.5 / 0.6 / 0.2 / 0.08 | 1.6 / 0.65 / 0.75 / 0.15 / 0.10 | Near defaults |
| Tree Wind NearTreeBrightness (`TreeWind.h:85`: "the full-model textures need no lift") | 1.0 | **1.6** | Near trees are 60% brighter than their textures. Lifts foliage shade with everything else |
| Grass Lighting MidLODBrightness / PBRWrappedLightingAmount | 1.0 / 0.5 | 0.99 / 0.507 | Defaults. Wrapped lighting 0.5 softens grass shading by design |
| Subsurface Scattering, Wetness, Water, Terrain Blending | | defaults + baseline | Not sun:shade levers |
| Skin baseline | | **not applied** (unrecognised keys) | Skin runs at code defaults; unrelated to this audit but the pack file is stale |

## 2. Light path, noon, sunlit vs shaded surface

Units: scene units before exposure. Exposure factor on the plains [computed]: 0.18 x 2^-4.2 / 2^-3.40 = 0.103, x 1.231 = 0.127, x 1.61 if Local Exposure is the uniform gain = 0.205.

**Sunlit opaque surface** (`Lighting.hlsl:3164-3213`):
`sunlightColor 20` x Sky Sync factor (1 at noon) x `directionalLightMult 1.1` x height-fog attenuation (about 1) x atmosphere transmittance x remapped cloud transmittance x cascade / terrain / screen-space shadow, then x albedo x N.L / pi. Sunlit white facing the sun is about 5.6 [computed, transmittance 0.8].

**Shaded opaque surface** (deferred): the forward ambient is discarded (`Lighting.hlsl:3819-3820`). Fill is the SSGI output (`diffuseGI.cs.hlsl`): traced bounce x 1.03, plus for every open sector the fallback = [weather DALC x 1.18 x 0.25 (negligible outdoors)] + [sky reflection cube at mip 3 x saturation 0.6 x `SkyIBLScale 1.0`] x Skylighting visibility (floor 0.1), then x AO^2.0. Then `DeferredCompositeCS.hlsl:199-211` multiplies the direct term by sqrt(multi-bounce AO).

**Then** (order matters): game volumetric lighting is added; Local Exposure x auto exposure gain; **bloom is added after, scaled by auto exposure only**; x 1.231; PsychoV (linear); gamma 2.2.

Why shade sits close to sun:

1. **Display rendering has no contrast** [read/computed]. Slope 1.0, no toe, highlights pulled to 0.88. Measured near range 0.12-0.56 display = 0.0094-0.28 linear = 4.9 stops, printed 1:1. A slope of 1.3 around 0.18 would put the same floor at display 0.08 and the same top at about 0.63.
2. **Additive veils set the floor** [inferred, strong]. The floor is the same in all three depth bands (0.12 / 0.13 / 0.14), which points at a screen-space term, not distance haze. Bloom: effective mix about 0.35 of a wide blur of (luminance - 1.1). With sky at 1.5-2.5 units and clouds/snow at about 3, a frame-average excess of about 0.4 units through the 2-3 widest mips gives 0.005-0.008 display-linear against a measured floor of 0.0094 [computed, rough]. Bloom alone can be half or more of the floor. Game volumetric haze adds on top.
3. **Fill is on the high side** [inferred]. From the reference frames, sky luminance is about 0.3-0.5 of sunlit-white luminance; clear sky is nearer 0.15-0.25, scattered cumulus pushes it up. Sunlit vs shaded thatch in `plains__yaw250__fov25.png` is about 2:1 in linear, which needs fill about equal to direct on that slope: plausible for a grazing sun under a bright partly-cloudy sky, but soft. Thickness 0.02 leaks sky into contact shade. Dark vanilla-era albedos (grass, thatch, wood about 0.1-0.15) keep the sunlit side low while snow and sky stay bright.
4. **Local Exposure** compresses by up to 0.5 EV across sun and shade if working, or is a pure gain if broken.
5. **Cloud shadow remap** halves cloud shadow depth (2.4).

Largest leverage on the **sun:shade ratio**: (1) PsychoV contrast `tonemapParams[0][3]`; (2) Linear Lighting `directionalLightMult` (sun on surfaces only) and IBL `SkyIBLScale` (fill only); (3) Local Exposure on/off; (4) SSGI `Thickness` (and `AOPower`); (5) Physical Sky `cloudShadowRemapRange`.

Largest leverage on the **black level**: (1) COD Bloom `BlendFactor`; (2) Volumetric Lighting `ExteriorDayHaze`; (3) PsychoV contrast (a power below 0.18 is a toe); (4) SSGI `Thickness`; (5) Skylighting `MinDiffuseVisibility` (already at 0.1).

### 2.4 Volumetric cloud shadow strength

The dark drifting patches are Physical Sky's own shadow volume (`Lighting.hlsl:3175-3178`), not the Cloud Shadows feature. With the remap [0, 0.5] a dense cumulus (transmittance 0.1) passes 0.2 of the sun. Horizontal ground under it [computed, fill = 0.36 of sunlit white]: (0.2 x 3.9 + 2.0) / 5.9 = 0.47 of sunlit, about 1.1 stops down. With identity [0, 1] it is 0.40; with [0, 0.75] it is 0.43. Real cumulus shadow is roughly 0.2-0.35. So the cloud shadow is weak, but **the fill term, not the remap, is what limits it**. The remap is worth a third of a stop at most. Do not enable the old Cloud Shadows feature.

## 3. Proposed changes

Where to write: user-layer keys go in `SettingsUser.json`. Keys that exist only in the baseline (Linear Lighting, SSGI AOPower, IBL saturation, Volumetric Lighting strength) are edited in the baseline file or overridden in the user layer. **Caution [from memory note, unverified in code]: a save drops user keys equal to code defaults, and then the baseline value comes back.** Bloom `BlendFactor` 0.01 is the code default while the baseline says 0.15; use 0.012, or fix the baseline file.

### Step 0: one diagnostic shot (settles headline 1)

Same harness shot, Local Exposure `enabled = false`, nothing else changed.
- All three bands drop by the same factor (about x0.62, -0.69 EV) and p1:p99 ratios are unchanged: Local Exposure was a uniform gain: bug confirmed.
- Shadows drop less than highlights or ratios change: it works, and it was compressing.

### (a) Safe corrections toward physical plausibility (one harness run)

| # | Change | Expected effect | Risk | Verify |
|---|---|---|---|---|
| a1 | Post Processing / Local Exposure `enabled`: true -> **false** | Removes the uniform gain (if broken) or the shadow lift / highlight pull (if working). A neutral base should not have it | Image darker by up to 0.7 EV until a2 | Step 0 |
| a2 | HAE `ExposureCompensation` -4.2 -> **-3.5**, `InteriorExposureCompensation` -4.7 -> **-4.1**, `NightExposureCompensation` -4.7 -> **-4.4** (only if step 0 shows the uniform gain; otherwise leave) | Restores today's brightness without Local Exposure | If Local Exposure was working these over-brighten by its amount | Mid plains median back to today's value |
| a3 | COD Bloom `BlendFactor` 0.05 -> **0.012** (exterior value; the interior scene override stays for now) | Removes most of the screen-wide veil | Less glow around sun, snow, fires by day | Near and mid p1 fall (expect 0.12 -> about 0.08-0.10); p99 nearly unchanged |
| a4 | Color Grading `tonemapParams[0][1]` (Highlights) 0.88 -> **1.0** | Sunlit side back to the tonemapper's neutral | Slightly hotter clouds and snow | Near p99 and far p99 rise a little |
| a5 | Screen Space GI `Thickness` 0.02 -> **0.06** | More occlusion under eaves, at wall/ground contacts, under rocks: grounded shadows | Dark halos behind thin foreground objects (characters against walls); stop at 0.04 if seen | Near p1 falls; sunlit p99 unchanged |
| a6 | Volumetric Lighting `ExteriorDayHaze` 0.3 -> **0.15** (the baseline value; it was raised yesterday) | Halves the un-extinguished additive haze; the froxel volume keeps the physically shadowed haze | Thinner god rays / less "air" near the sun | Near and mid p1 fall; far band changes least |

If the run must be smaller: a1 + a3 + a5 are the three that test the main hypotheses.

### (b) Taste: a more striking look

| # | Change | Expected effect | Risk | Verify |
|---|---|---|---|---|
| b1 | Color Grading `tonemapParams[0][3]` (Contrast) 1.0 -> **1.25** (try 1.15 / 1.25 / 1.35) | The rendering slope a camera has. Pivot is 0.18: shade deepens, sunlit brightens, blacks anchor | Crushed interiors and nights if those are keyed low (they are: see 5); scene-layer it for day if needed. Saturation rises with contrast | Near p1 0.12 -> about 0.08; near p99 0.56 -> about 0.62 |
| b2 | Linear Lighting `directionalLightMult` 1.10 -> **1.35** | Sun on surfaces +0.3 EV against sky, clouds and fill. The one control that changes sun:fill without touching the sky | Not physical; snow and bright rock clip sooner; auto exposure will pull the whole frame down a little, which also deepens shade | Sunlit:shaded thatch ratio 2.1 -> about 2.6 |
| b3 | IBL `SkyIBLScale` 1.0 -> **0.8** | Fill -20% on everything | Shade interiors of forests get darker; water and specular sky reflection also drop (`SkySpecularIBLScale` follows it, `src/Features/IBL.cpp`) | Near p1 and shaded faces fall; sunlit faces fall slightly |
| b4 | IBL `SkyIBLSaturation` 0.6 -> **0.85** | Blue open shade against warm sun: colour contrast reads as light contrast | Blue cast on snow shadows may be strong | Shade hue shifts blue, luminance unchanged |
| b5 | Physical Sky `cloudShadowRemapRange` [0, 0.5] -> **[0, 0.75]** | Cloud shadows about a third of a stop deeper | The far-field mean dims clear-ish days slightly (the reason the remap was added) | Cloud-shadowed ground / sunlit ground 0.47 -> about 0.43 |
| b6 | Tree Wind `NearTreeBrightness` 1.6 -> **1.2** | Foliage shade stops glowing | Trees darker against LOD trees (LODTreeBrightness 1.6): may need the pair moved together | Tree-crown p1 |
| b7 | COD Bloom `Threshold` 3.14 -> **4.5** with BlendFactor back up to about 0.03 | Bloom only from sky-bright and specular sources instead of all sunlit ground | Less overall softness | Veil stays low while highlights glow |

Do b1 first; b2 or b3, not both at once.

### (c) Leave alone

- Physical Sky `sunlightColor` 20: ratio-neutral for sun vs sky. Halving it to the design value 10 would be cleaner (thresholds, Light Shafts MaxBrightness, fires by day) but needs every absolute EV setting re-derived. Not now.
- `trMix`, `apLumMix`, `apTrMix` = 1; aerosol Continental 0.2; `distanceExaggeration` 6 (your sweep was right: it is not the veil).
- Skylighting `MinDiffuseVisibility` 0.1, SSGI `FallbackSkyBoost` 0, `AOPower` 2.0, IBL `DALCAmount` 0.25, `SkylightingAffectsEnv` 1: already set toward contrast.
- Cloud Shadows `Opacity` 0, deck ground light 0, LOD Shadows off, Ground Fog off.
- Sky Sync values; Screen Space Shadows; Light Shafts (contrast-only, no veil).
- HAE knee -10 / compression 0.22: keep the behaviour; just know that about 2.7 EV of the "-4.2" is this pivot.
- LUT and Look Grade stay off until the base is settled.
- Weather records (NAT.CS III) and Helios: untouched.

### Code changes (need a DLL rebuild; not part of the harness run)

- **C1. Bind SharedData on the compute stage for Local Exposure** (one call at the top of `LocalExposure::Draw`, as ae00ed0ee did for the histogram; or once in the Post Processing draw loop so DoF, Physical Glare, Lens Flare and `bloom.cs` are covered too). This is the real fix for headline 1. After it, Local Exposure can be re-evaluated on its merits.
- C2. Reject or swap an inverted `AdaptationRange` on load (the baseline's [-0.85, -1.31] pins exposure).
- C3. Normalise the bloom mip sum (divide by the sum of active `MipBlendFactor`), so BlendFactor means what the tooltip says.
- C4. Refresh or delete the stale parts of the baseline pack (`PostProcessing.json`: inverted range, LUT/Look Grade on, bloom 0.15; `Skin.json`: rejected).

### What ExposureCompensation should return to

- With Local Exposure off or fixed, same brightness as today: **day -3.5, interior -4.1, night -4.4** (knee -10 / 0.22 kept).
- Expressed without the knee offset (what the numbers mean): day about **-0.8 EV**, interior about **-1.8 EV**, night about **-3.1 EV** below a standard mid-grey meter, plus +0.3 EV from the grading exposure 1.231. If you ever set `BrightSceneCompression` 0 (full adaptation), those are the compensations to enter.
- Folding the grading exposure into HAE (set `exposureTemperatureTint[0]` to 1.0 and add +0.3 to each compensation) leaves one exposure control.

## 4. What lifts blacks in the Post Processing chain

| Candidate | Lifts blacks? | Evidence |
|---|---|---|
| COD Bloom | **Yes, main suspect** | additive, 7 mips unnormalised, threshold below sky and sunlit ground; added after Local Exposure (`composite.ps.hlsl`, `result = scene x global x local + bloom x global`) |
| Game volumetric lighting haze | **Yes** | additive, no extinction (`ISCompositeLensFlareVolumetricLighting.hlsl`) |
| Local Exposure | Yes if working (shade up to +0.3 EV); uniform gain if broken | `RemapBaseContrast`, ShadowContrast 0.8 |
| Tone curve | No lift, but no toe either | PsychoV shadows are linear |
| Auto exposure floor | No | day range [-6, 16] EV100 is never hit outdoors |
| Dither | No | scaled to zero at black (`ISHDR.hlsl:157-159`) |
| HDR-off output transform | No | pure gamma 2.2 (`ISHDR.hlsl:156`) |
| Film grain | No | Camera stage off by default (`PostProcessing.cpp:482`) |
| Vignette off | Neutral | |
| Color Grading lift / gamma / gain | No | defaults (lift 0) |
| Neural Rendering (final image) | **Not audited.** If the harness shot had it on, repeat one shot with it off | memory note: it once lifted blacks 10x (fixed 11-05) |

**Where to anchor the black point:** first remove the veils (a3, a6), because a subtractive fix on top of an additive veil crushes real shadow detail unevenly. Then use PsychoV Contrast (b1): it is scene-referred, pivots at 0.18 and behaves like a toe. Keep the final display-referred trim for Look Grade (`BlackPoint`, `ShadowsLift`) when it comes back. Do not use Color Grading `lift`: it acts on linear output (`colorgrading.hlsl:75-99`), where -0.003 already removes the whole current floor.

## 5. Interiors and night

**Interiors**
- Exposure [computed]: Bannered Mare (metered +0.6 EV) gets +2.3 EV from the knee, -4.7 compensation, about +0.6 EV from Local Exposure if broken, +0.3 grading: net about -1.5 EV. Low-key but reasonable. After a1 use -4.1.
- Ambient: no sky term indoors; fill = weather/cell DALC x 1.18 x 0.25 through the SSGI fallback, plus traced bounce. Helios window light arrives through the weather copies and is untouched by anything proposed here.
- **Bloom is the interior black lifter:** the Scene Manager interior override is Threshold 1.0 EV100 (0.25 units, about the average interior luminance) and BlendFactor 0.15, which with 7 mips is about a 1:1 add of a wide blur of everything brighter than average. Proposal (taste, it was set deliberately on 11-21): Threshold 1.0 -> **2.5**, BlendFactor 0.15 -> **0.05**. Verify: p1 in a lit tavern falls, flames and windows still glow.
- Grounding: Light Limit Fix `EnableLocalShadows` is false, so lamps and fires cast no shadows; contact shadows only. SSGI Thickness (a5) helps here too. Re-enabling local shadows is a performance decision, not proposed.
- If b1 (contrast) is adopted globally, check one dark interior: at a -1.5 EV key a 1.25 slope takes display 0.10 to about 0.07. Scene-layer the contrast for interiors if that is too much.
- Do not set hour or weather inside interiors when testing (Helios rule).

**Night**
- Exposure [computed, scene EV assumed about -4]: +1.3 knee, -4.7, +0.3 Local Exposure, +0.3 grading: net about -2.8 EV. After a1 use -4.4.
- Moon light: `masserColor` 0.26-0.39 and `secundaColor` 0.11-0.18 are 2.6-3.6x the defaults, then Sky Sync scales by 0.13-0.19 (baseline, defaults 0.05-1.0). Net full-moon light is about half the default, new-moon light about 7x the default [computed]: moon phase barely changes night brightness. That is a look decision; flag only.
- Volumetric Lighting `ExteriorNightHaze` 0.04 and night strength 1.4: haze is already minimal at night. Bloom threshold 3.14 EV is far above night luminance, so bloom adds almost nothing at night: night blacks are set by fill and exposure, not by veils.
- `PurkinjeStrength` 0: no blue shift. Fine for a neutral base.
- The earlier note "nights are quite bright" predates the exposure fixes; re-measure near-camera blacks at night after a1-a3 before changing anything.

## 6. Not verified

- Nothing was run. Every number marked [computed] comes from settings and formulas.
- **Local Exposure reading zero** is inferred from the identical dependency and pipeline position as the fixed histogram bug, and from the settings history. Step 0 settles it. What clears compute slot b5 between frames was not identified.
- Bloom's share of the black floor is an order-of-magnitude estimate; a3 measures it.
- The size of the game volumetric-lighting haze depends on NAT.CS III weather records, which were not read.
- The fill:sun ratio (about 0.36) was estimated from the two reference PNGs by eye; the below-horizon content of the sky reflection cube (ground albedo 0.2 / ocean) and its effect on downward-facing surfaces was not traced.
- Whether a settings save drops keys equal to code defaults (and so re-exposes baseline values) comes from a memory note, not from code read here.
- Neural Rendering, the Fire stage, Subsurface Scattering, Wetness, Water and Terrain Blending were not audited in depth.
- PsychoV "Shadows" parameter semantics (which direction deepens) not read; use Contrast.

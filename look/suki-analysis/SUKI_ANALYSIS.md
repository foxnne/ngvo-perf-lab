# Suki's ENB Preset NLVA ("insane") - how the look is built

Source: `C:\Users\foxnn\dev\suki-enb\ref\nlva\insane\` (Skyrim LE, ENB DX9). Port of the colour chain: `suki_post.py` (same folder as this file).
Helpers: `inidiff.py` (diff a weather ini against the global one), `tables.py` (regenerates the appendix tables).

Conventions: D / N / I = Day / Night / Interior. "Scene value" = the HDR colour Skyrim LE renders. LE lights and blends in
non-linear (display-like) space and ENB never linearises it: every sampler in the post shaders has `SRGBTexture=FALSE` and every pass
`SRGBWRITEENABLE=FALSE`. So **all post steps below operate on gamma-encoded values**, including bloom and the tone curve.
Things I could not read from the files are marked **(not in files)** or **(estimate)**.

---

## 0. Findings that change the picture

1. **The global `enbseries.ini` is not the look.** `[WEATHER] EnableMultipleWeathers=true`; every listed weather has its own 950-key file and
   those differ from the global file in about 720 keys. Example, Day: global DirectLightingIntensity 0.4 / curve 1.0, while 40 of the 50
   weather files use 1.3-1.6 with curve 3.0-3.6. The global file only matters for (a) sections with `IgnoreWeatherSystem=true`
   (LENS, VEGETATION, LIGHTSPRITE, FIRE, DEPTHOFFIELD, SHADOW, REFLECTION, RAIN, SUBSURFACESCATTERING, WATER, CHARACTERGLOW, SKINSPECULAR,
   COMPLEXFIRELIGHTS, COMPLEXPARTICLELIGHTS), (b) non-weather sections (COLORCORRECTION, ADAPTATION, SSAO_SSIL, TIMEOFDAY, NIGHTDAY),
   (c) weathers whose form ID is not in `_weatherlist.ini`.
2. **The palette is only one of four tone-shaping stages**, and the shadow crush and cool shadows do not come from it. On the neutral axis the
   palette is a display-space darkening curve (0.1->0.01, 0.2->0.05, 0.3->0.11, 0.5->0.31, 0.7->0.62, 0.9->0.91) with a slightly *warm* mid
   (R-G about +0.02, B-G about -0.01). Cool shadows come from the lighting (cyan ambient filters, desaturated near-white sun) and are amplified
   by the pre-tonemap saturation power.
3. **There is a pre-bloom "eye adaptation" step that is really a fixed luminance-squared toe**: `color *= compLuma`, which for dark pixels is
   `color * 30 * luma` (exterior). This is the main black-crush.
4. **Bloom is an unthresholded multi-radius blur added at 0.5-0.9x before the tone curve** = a diffusion veil. It is the main reason fog
   weathers read as a bright low-contrast veil and why dark objects against sky/fog are lifted. `BlueShiftAmount` is ignored by this
   `enbbloom.fx` (it never reads `BloomParameters.z/.w`), so the bloom has no blue shift.
5. **The EENE (night eye) block is disabled** (`---- EENE Enable ----=false`), so none of its CC / tint / vignette / sharpening / blur / noise
   runs. The vignette, sharpening, grain, contrast and vibrance that are visible come from `effect.txt` (`[GLOBAL] UseEffect=true`), which
   runs after `enbeffect.fx`.
6. Two brightness multipliers sit after the palette: ENB core `[COLORCORRECTION] Brightness=1.1` (and `GammaCurve=1.1`) and effect.txt
   "Kinematic Filter" brightness 1.1 (ext day) / 1.15 (ext night) / 1.0 (interior). They are what pushes highlights to 0.95-1.0.

---

## 1. `enbeffect.fx` - active chain

Compiled in: `POSTPROCESS 2`; all `EENE_ENABLE_*` defines (but gated off at run time, see above); `APPLYGAMECOLORCORRECTION` is commented
out (vanilla imagespace tint/contrast/fade is not applied; the scene colour goes in raw). `E_CC_PALETTE` is **not** defined in the file:
the ENB core defines it at compile time when `[COLORCORRECTION] UsePaletteTexture=true` (standard ENB LE behaviour, **not in files**), which
activates the in-shader lookup at line 1489. The core does not apply the palette by itself; the lookup position is where the shader puts it:
after the tone curve. `UseProceduralCorrection=true` only defines `E_CC_PROCEDURAL`, for which this shader has no code -> no effect.

Blend of D/N/I values (line 1458-1464): `lerp(Interior, lerp(Night, Day, ENightDayFactor), 1 - EInteriorFactor)`.
The eye-adaptation block blends exterior/interior only.

| # | step (line) | formula | Day | Night | Interior |
|---|---|---|---|---|---|
| 0 | read scene (1348) | `color = tex(_s0)` HDR, gamma space, vanilla imagespace bypassed | | | |
| 1 | prod80 eye adaptation (1424-1436), **pre-bloom** | `EyeAdapt = clamp(luma(adaptTex), min, max)`; `s = luma(color) * middleGray / EyeAdapt`; `comp = s*(1 + s/maxLuma^2)/(1+s)`; `color *= comp` (luma weights 0.2125/0.7154/0.0721) | min 0.05, max 0.1, middleGray 3.0, maxLuma 12 | same as Day | min 0.3, max 0.13 (min > max), middleGray 0.73, maxLuma 5 |
| 2 | kaBloom (1440), `Enable KBLOOM=true`, blend mode 6 | `k = levels(sat(bloomTex), inB 0.33, gamma 0.38, inW 0.48, outB 0.47, outW 0.79)`; `k *= (0.987,1.000,1.013)`; `k *= 2^-0.83`; contrast 1.41 (`k^c/(k^c+(1-k)^c)`); saturation 0.31 (lerp to mean); `k = k^(1/(0.31*cLuma(k)))`; `k *= 2^-1.27`; `color += 1-(1-sat(k))*(1-sat(3k))` | same | same | same |
| 3 | ENB bloom (1447-1449) | `color += bloomTex * EBloomAmount` | 0.5-0.9 per weather (clear 0.5-0.6) | 0.5-0.9 (mostly 0.5-0.6) | 0.5 |
| 4a | adaptation divide (1466-1468) | `color /= clamp(adapt,0,50) * AdaptMax + AdaptMin` (adapt = max channel of adaptTex) | Max 0.1, Min 0.05 | Max 0.02, Min 0.04 | Max 0.06, Min 0.07 |
| 4b | brightness (1470) | `color *= EBrightnessV2; color += 1e-6` | 0.5 | 0.5 | 0.5 |
| 4c | intensity contrast (1472-1474) | `n = normalize(color); len = color/n; len = len^IC` | 0.94 | 0.85 | 0.82 |
| 4d | colour saturation (1475-1476) | `n = n^CS` (per channel, **not renormalised**); `color = len * n` | 1.38 | 1.17 | 1.10 |
| 4e | tone curve (1478-1479) | `color = color*(1 + color/W)/(color + C)` per channel | C 1.4, W 310 | C 1.5, W 160 | C 3.1, W 340 |
| 5 | palette (1489-1498) | `sat(color)`; 16^3 LUT from `enbpalette.bmp` (x = floor(15b)*16 + 15r, y = 15g), bilinear in r,g, lerp over b = trilinear | same | same | same |
| 6 | EENE night eye (1505-1735) | skipped (`EENE_Enable=false`) | | | |
| 7 | output | `alpha = 1`, no gamma, no dither in this shader | | | |

Notes per step:

- **Step 1.** `[ADAPTATION] ForceMinMaxValues=true, AdaptationMin=0.12, AdaptationMax=0.7` keeps the adaptation texture in [0.12, 0.7], so
  the exterior clamp [0.05, 0.1] always returns 0.1 -> `s = 30 * luma` (constant, no real adaptation). Interior: `clamp(x, 0.3, 0.13)`
  compiles to `min(max(x,0.3),0.13) = 0.13` -> `s = 5.6 * luma`. Because the colour is multiplied by the compressed luminance itself,
  dark pixels get `color * s` (quadratic toe) and bright ones `color * ~1.0-1.2`.
  Exterior gain `comp`: scene luma 0.01 -> 0.23, 0.02 -> 0.38, 0.05 -> 0.61, 0.1 -> 0.77, 0.2 -> 0.89, 0.5 -> 1.04, 1.0 -> 1.17.
  Interior gain: 0.05 -> 0.22, 0.1 -> 0.37, 0.2 -> 0.55, 0.5 -> 0.82, 1.0 -> 1.04, 2.0 -> 1.33.
- **Step 2.** "White input" does not clamp, so the term is a soft-thresholded glow: bloomTex 0.33 -> 0, 0.5 -> +0.003, 0.6 -> +0.013,
  0.75 -> +0.043, >=1.0 -> +0.125 (R,G,B = 0.123, 0.126, 0.130, i.e. very slightly cool). Added pre-tonemap, so +0.125 is the same as
  adding 0.125 to the scene value: visible only where the blurred scene is bright (sky, snow, fog).
- **Step 3.** `EBloomAmount` = `[BLOOM] Amount<TOD>` from the active weather file. No per-pixel shaping here.
- **Step 4a.** Day divisor 0.062-0.12 -> with 4b a gain of x8.1 (adapt 0.12) to x4.2 (adapt 0.7): about one stop of auto exposure.
  Night divisor 0.042-0.054 -> gain x11.8-x9.3 (almost fixed). Interior 0.077-0.112 -> x6.5-x4.5.
- **Step 4c/4d.** `len` is the vector length (sqrt(r^2+g^2+b^2)). For grey, `n` = 0.577 per channel, so 4d also scales grey by
  0.577^(CS-1): x0.811 Day, x0.911 Night, x0.947 Interior. On colour it raises the channel ratios to the power CS:
  R/G 1.36 -> 1.53 for skin-like (0.75,0.55,0.45) at CS 1.38.
- **Step 4e.** Reinhard with white point. Day: 0.5 at x = 1.41, 0.8 at 5.2, 0.9 at 9.6, 1.0 at 20.8, and it keeps rising above 1 (the palette step clamps) (per channel, so highlights desaturate
  and hue-shift towards the brightest channel).
- **Step 5.** Neutral axis of the palette (in -> out R,G,B): 0.1 -> .012,.009,.017; 0.2 -> .063,.051,.047; 0.3 -> .125,.111,.103;
  0.4 -> .208,.192,.184; 0.5 -> .331,.309,.296; 0.6 -> .475,.455,.443; 0.7 -> .635,.620,.611; 0.8 -> .792,.776,.788; 0.9 -> .909,.907,.909.
  Primaries: R -> (.949,.067,.051), G -> (.137,.918,.035), B -> (.039,.039,.961). Everything below 0.067 input maps to 0.

After the shader, **(not in files, standard ENB LE order)**: ENB core applies `[COLORCORRECTION] Brightness=1.1`, `GammaCurve=1.1`
(formula inside d3d9.dll; whether GammaCurve 1.1 brightens or darkens mids is not determinable here), then `effect.txt`, then the
`d3d9_smaa.dll` proxy (SMAA ULTRA).

### effect.txt (runs after enbeffect.fx, 8-bit display space) - all techniques enabled in the ini except Border

| pass | what | values (D / N / I) |
|---|---|---|
| 1 Kinematic Filter | `c *= brightness`; clamp; "blackness": `c = lerp(c*-0.45 + noise*0.0075, c, (0.27*2.133*(r+g+b))^0.01)` (mix is 0.93-1.0, i.e. about -5..-10 % only in near-black) | brightness 1.1 ext day, 1.15 ext night, 1.0 interior |
| 2 LumaSharpen | pattern 4, luma high-pass added to all channels | strength 1.6 / 1.4 / 1.4, clamp 0.98 / 0.9 / 0.9 (effectively unclamped), offset bias 1.0 |
| 3 Blurring | horizontal 5-tap box, range 0.32 px | softens the sharpen slightly |
| 4 Sharpening | 8-tap unsharp, by colour, faded on bright blue channel (`b^3`) | range 0.8 px, amount 1.4 / 1.4 / 1.5 |
| 5 Color Shift | R sampled 1.34 px above, B 1.34 px below (vertical chromatic fringe) | range 1.34 |
| 6 Contrast | SweetFX curve on luma: `x=l-0.5; x = x/(1.25|x|+0.375)+0.5; l' = lerp(l, x, amt)`; chroma re-added | 0.25 ext day, 0.1 ext night, 0.55 int day, 0.2 int night |
| 7 Vibrance | `c = lerp(luma, c, 1 + v*(1 + (max-min)))` with v negative -> desaturates, strongest on already saturated colours (factor 0.87 for greys-ish, 0.74 for fully saturated) | -0.13 all (the rain branch only survives for weather index 38 and gives -0.126) |
| 8 AfterFX | vignette to black `amount * sat(|(uv-0.5)*1.5|^2)^1.5`; grain; dither; letterbox | vignette 0.2 / 0.1 / 0.2 (day: -20 % in the corners, about -8 % at the middle of an edge); grain 0.015 / 0.01 / 0.015 (saturation 0.1); letterbox 8.6 % top and bottom |

### Net transfer, enbeffect.fx only (no bloom, adaptation 0.3), from `suki_post.py`

Scene grey value that lands on a given display value (s = LE scene value; L = s^2.2 = linear-light equivalent, **estimate**, assumes the LE
scene value is roughly gamma 2.2 encoded):

| display out | Day s (L) | Night s (L) | Interior s (L) |
|---|---|---|---|
| 0.02 | 0.062 (0.0022) | 0.038 (0.0007) | 0.171 (0.021) |
| 0.05 | 0.090 (0.0050) | 0.055 (0.0017) | 0.248 (0.047) |
| 0.10 | 0.135 (0.012) | 0.084 (0.0043) | 0.373 (0.114) |
| 0.18 | 0.201 (0.029) | 0.128 (0.011) | 0.556 (0.275) |
| 0.30 | 0.297 (0.069) | 0.194 (0.027) | 0.819 (0.64) |
| 0.46 | 0.446 (0.170) | 0.300 (0.071) | 1.216 (1.54) |
| 0.60 | 0.620 (0.350) | 0.426 (0.153) | 1.661 (3.06) |
| 0.80 | 1.099 (1.23) | 0.773 (0.57) | 2.776 (9.4) |
| 0.90 | 1.660 (3.05) | 1.152 (1.36) | 3.892 (19.9) |
| 0.95 | 2.192 (5.6) | 1.478 (2.4) | 4.808 (31.6) |

With core Brightness x1.1 (guess: plain multiply) and the effect.txt colour passes, Day reaches 0.80 at s 0.68, 0.90 at s 0.88, 0.95 at s 1.02
and clips at about s 1.3; Night clips at about s 0.75; Interior reaches 0.95 at s 3.2.

Reading for Day: display mid-grey sits on scene value ~0.45-0.5 (about 1:1 around mid), a hard toe below scene 0.13 (display 0.10) that
reaches black near scene 0.04, a long shoulder. Interior: the same scene value comes out 2-3 stops darker (C = 3.1, 5.6x instead of 30x in
step 1): interiors are dark by tone mapping, and only point lights / fire / window sprites reach the upper half.

Saturation through the chain (Day, HSV saturation in -> out of enbeffect.fx): red (.6,.2,.2) 0.67 -> 0.88; foliage (.30,.42,.18) 0.57 -> 0.84;
skin (.75,.55,.45) 0.40 -> 0.43; sky (.35,.55,.85) 0.59 -> 0.55; cool shadow (.06,.08,.11) 0.45 -> 0.66 at display (.023,.038,.067), i.e. R/B 0.34.

---

## 2. `enbseries.ini` - lighting and atmosphere

### 2a. Not weather dependent (always these values)

| section | values |
|---|---|
| EFFECT | everything on except Prepass and SkinSpecular: Bloom, Lens, Adaptation, DepthOfField, AmbientOcclusion, DetailedShadow, SunRays, SunGlare, SkyLighting, ImageBasedLighting, Reflection, SoftParticles, ParticleLights, SubSurfaceScattering, Water, Underwater, CloudShadows, VolumetricRays, ProceduralSun, Mist, AutomaticAmbientCalculation, RainOcclusion, DistantShadow, ComplexFireLights, ComplexParticleLights; UseOriginalPostProcessing=false, UseOriginalObjectsProcessing=false |
| COLORCORRECTION | UsePaletteTexture=true, Brightness=1.1, GammaCurve=1.1, UseProceduralCorrection=true (no code for it) |
| ADAPTATION | ForceMinMaxValues=true, Sensitivity 0.01, Time 1.1 s, Min 0.12, Max 0.7 |
| TIMEOFDAY | Dawn 2.2 h before Sunrise 8.0, Day 11.5, Sunset 17.65, Dusk 2.0 h after, Night 1.0 |
| NIGHTDAY | DetectorLevelDay 0.9, DetectorLevelNight 0.06, curve 1.0 (drives ENightDayFactor) |
| SSAO_SSIL | AOAmount 2.5 / interior 4.0; AOIntensity 0.67 / interior 0.45 (lower = darker); ILAmount 2.4 / interior 4.3; AOType 2, ILType 1, complex AO + complex IL + ambient IL on; AOMixingType 0 ext / 2 int; SamplingRange 0.18; SizeScale 0.78; FilterType 4; denoiser on |
| SHADOW | UseSoftShadow, blur range 4.0 ext / 1.0 int, SoftShadowBlurRangeMin 0.3, bilateral filter, detailed + distant shadow |
| REFLECTION (SSR) | Amount 2.0 / int 3.6, Power 1.5 / int 1.2, glossiness 0.09-0.23, blur 0.7 |
| SUBSURFACESCATTERING | Radius 6.6, Amount 0.59, Epidermal 2.2, Subdermal 5.2, mixes 0.8 / 0.7; interior: 7.0, 0.65, 2.6, 4.0, 1.0 / 0.9 |
| LENS (ignore weather) | ReflectionIntensity 0.02 (N 0.01), power 4; DirtIntensity 0.07-0.09, DirtPower 3.5 (N 5, I 2) |
| FIRE (ignore weather) | Intensity Sunrise 5, Day 6, Sunset 5, Night 2, Interior 10 / 10; Curve 1.7 / 2.0 / 1.5 / 1.6 / 1.9; AdditiveBlending |
| LIGHTSPRITE (ignore weather) | Intensity 1.1 / 1.0 / 1.1 / 1.3 / 1.0 / 1.0; Curve 3 (Day 4) |
| VEGETATION (ignore weather) | SSS multiplier 0.25 (int 0.3), power 2.0 (Day 1.3, Night 2.2) |
| COMPLEXFIRELIGHTS / COMPLEXPARTICLELIGHTS (ignore weather) | Intensity 0.08 ext, 0.4 int, curve 4 / 3; particle lights 0.2 ext, 0.4 int, curve 4-5 / 3 |
| WATER (ignore weather) | Reflection 0.99, Fresnel x2.61 (0.56-0.63), SunSpecular 4.2, SunScattering 9.5, Caustics 1.87, Muddiness 0.18 |
| PROCEDURALSUN | Size 0.33, EdgeSoftness 0.3 |
| SKY (scalars) | StarsIntensity 1.26, curve 0.73; Aurora 0.5 / 2.1; CloudsEdgeClamp 0.31, CloudsEdgeIntensity 21, CloudsEdgeFadeRange 0.88, CloudsEdgeMoonMultiplier 3.1; SunCorona 4.0 / curve 1 / desat 0.2; DisableWrongSkyMath |
| MIST (scalars) | ColorFromEnvironmentFog 0.25, EnableAnchors |

FIRE and LIGHTSPRITE have `IgnoreWeatherSystem=true` in the global file, so the values in the weather files (FIRE 0.6 day / 2.2 interior)
should be ignored and the global ones above used (ENB semantics, **not verifiable from files**).

### 2b. Weather-driven sections

The global values are in the appendix ("global" table). They are a fallback only. The values that define the look are the per-weather ones;
"typical clear day" below = `!_ClearWeather__tundra.ini`, full tables for six weathers and min / median / max over all 50 files are in
the appendix.

Clear tundra, all six times of day:

| key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| DirectLighting Intensity / Curve / Desaturation | 1.4 / 3.5 / 0.7 | 1.5 / 3.6 / 0.6 | 1.4 / 3.1 / 0.4 | 0.7 / 2.0 / 1.0 | 1.0 / 2.0 / 1.0 | 1.0 / 2.0 / 1.0 |
| DirectLighting ColorFilter @ amount | (.80,.67,.54) @ .58 | (.90,.93,.96) @ .50 | (.92,.70,.46) @ .60 | (.17,.29,.38) @ .66 | (.47,.52,.55) @ .80 | (.28,.33,.35) @ .30 |
| AmbientLighting Intensity / Curve / Desaturation | 1.5 / 2.4 / 0.2 | 1.7 / 2.2 / 0.3 | 1.5 / 2.3 / 0.1 | 0.3 / 2.0 / 0.5 | 3.0 / 1.0 / 0.0 | 0.5 / 2.0 / 1.0 |
| AmbientColorFilter amount | 0.40 | 0.52 | 0.43 | 0.30 | 0.80 | 0.40 |
| Ambient filter Top | (.34,.54,.72) | (.51,.74,.82) | (.43,.65,.75) | (.09,.27,.34) | (.63,.68,.71) | (.38,.51,.56) |
| Ambient filter Middle | (.56,.49,.38) | (.67,.60,.51) | (.61,.51,.41) | (.19,.38,.46) | (.56,.60,.62) | (.32,.51,.62) |
| Ambient filter Bottom | (.08,.29,.39) | (.17,.37,.46) | (.14,.28,.33) | (.13,.31,.39) | (.45,.53,.57) | (.21,.40,.48) |
| Specular Amount / Power / FromLight | 0.6 / 3 / 0.4 | 0.6 / 3 / 0.3 | 0.6 / 3 / 0.4 | 0.6 / 3 / 0.8 | 1 / 0.3 / 0.5 | 1 / 0.3 / 0.5 |
| PointLighting Intensity / Curve / Desaturation | 0.4 / 1.2 / 0.1 | 0.4 / 1.2 / 0.1 | 0.4 / 1.2 / 0.1 | 0.5 / 1.2 / 0.1 | 1.4 / 1.7 / 0.4 | 1.4 / 1.7 / 0.4 |
| Fog ColorMultiplier / Curve | 0.39 / 1.0 | 0.16 / 1.0 | 0.29 / 0.64 | 0.02 / 4.0 | 0.4 / 1.5 | 0.2 / 1.5 |
| Fog ColorFilter @ amount | (.76,.73,.63) @ .2 | (.41,.56,.63) @ .5 | (.26,.33,.39) @ .64 | (.24,.44,.55) @ .1 | white @ .2 | (.64,.64,.64) @ .1 |
| ColorPow | 1.1 | 1.07 | 1.04 | 1.2 | 1.1 | 1.15 |
| Sky GradientIntensity / Desaturation | 1.8 / .56 | 1.7 / .4 | 1.8 / .4 | 1.6 / .5 | 2.2 / .3 | 1.0 / .3 |
| Sky Top / Middle / Horizon intensity | .7 / .9 / .8 | .7 / .9 / .8 | .7 / .9 / .8 | .03 / .14 / .02 | 1.23 / 2 / 1 | 1 / 1 / .7 |
| Sky Top / Middle / Horizon curve | .6 / .7 / .6 | .8 / 1.0 / 1.0 | .8 / .7 / .6 | 0 / 0 / 0 | 1.2 / .71 / 1.43 | 1.5 / 1.0 / 1.0 |
| Sky filters Top; Middle; Horizon | (.26,.56,.76); (.23,.65,.79); (.83,.72,.60) | (.22,.55,.67); (.31,.61,.72); (.37,.57,.67) | (.28,.64,.74); (.33,.73,.70); (.96,.72,.31) | (.02,.22,.29); (.11,.23,.34); (.31,.35,.42) | white | white |
| Sun Intensity / Desaturation / filter | .23 / .5 / (.88,.63,.48) | .27 / .6 / (.89,.92,.93) | .22 / .3 / (.96,.64,.29) | 1 / 1 / (.19,.49,.62) | .2 / .7 | 1 / 0 |
| SunGlow Intensity / Haziness | 5 / .25 | 2 / .12 | 6 / .1 | 10 / 0 | 1 / 0 | 0 / 0 |
| Clouds Intensity / Curve / Desat / Opacity | .6 / 1 / .3 / 1.1 | .8 / 2.8 / 1.0 / 1.2 | .5 / 1 / 0 / 1.5 | .94 / 3 / .9 / 2.0 | 1 / 2 / 0 / 1.5 | .16 / 1 / 0 / 1.72 |
| Clouds filter | (.88,.82,.77) | (.67,.74,.78) | (.89,.85,.80) | (.22,.32,.43) | (.85,.87,.88) | white |
| Bloom Amount (BlueShift: unused) | 0.5 | 0.6 | 0.5 | 0.5 | 0.5 | 0.5 |
| SkyLighting AmbientMinLevel | .66 | .70 | .64 | .40 | .5 | .5 |
| IBL Additive / Multiplicative / Reflective | .24 / .30 / 1.7 | .29 / .37 / 1.3 | .25 / .30 / 1.3 | .10 / .14 / 2.0 | .1 / 0 / 1 | .1 / 0 / 1 |
| AutoAmbient Blend / Top / Bottom / BottomSat | .5 / .5 / .4 / .2 | .5 / .6 / .45 / .4 | .4 / .5 / .5 / .4 | .9 / 1 / .6 / .9 | 1 / 1 / .5 / .1 | 1 / 1 / .5 / .1 |
| SunRaysMultiplier | 0.4 | 0.4 | 0.4 | 2.0 | 0.3 | 0.3 |
| VolumetricRays Intensity / Density / SkyColor | .6 / 4 / .4 | .4 / 3 / 1.0 | .6 / 3 / .3 | .99 / 1.5 / .5 | 4 / 1 / .5 | 4 / 1 / .5 |
| VolumetricFog Intensity / Curve / LightInfl / Opacity | .6 / .7 / .5 / .6 | .8 / 1 / 1.2 / .9 | .55 / 1 / .2 / .8 | .16 / 1 / .83 / .5 | 2 / .7 / 1 / 1 | 1 / 1 / 1 / 1 |
| Mist SkyLight / SunLight / Desat | 2 / .5 / .4 | 2 / 2 / .6 | 1 / 1 / .6 | 1.3 / 0 / .8 | 1 / .1 / 0 | 1 / .1 / 0 |
| Mist ColorFilter | (.54,.72,.85) | (.75,.86,.89) | (.36,.59,.82) | (.08,.28,.36) | white | white |
| Mist VerticalOffset / Density / VerticalFade / BottomTop / ExpFade / DistFade | -12 / 1 / 0 / .3 / 1.2 / 1 | -16 / 1.3 / 3 / .5 / .5 / .6 | -14 / 1.38 / 2 / 1 / .4 / .7 | 10 / 2 / 4 / 1 / 1.85 / 0 | -11 / 1.5 / 2 / 0 / 1 / 0 | same |
| Particle Intensity / LightingInfluence | .48 / .3 | .8 / .8 | .5 / .97 | .2 / .9 | .8 / .5 | .5 / .5 |
| WindowLight Intensity / Curve | .5 / 1 | .5 / 1 | .5 / 1 | 1.13 / 1.3 | 11 / 1.5 | 1 / 1.5 |
| Grass Directional / Ambient multiplier | 2 / 2 | 2 / 2 | 2 / 2 | 1 / 1 | 2 / 3 | 1.4 / 2 |
| ProceduralSun Glow Intensity / Curve | .4 / 6 | .4 / 5 | .4 / 7 | .6 / 3 | 1 / 1 | 1 / 1 |
| CloudShadows Opacity | .6 | 1.0 | .76 | 1.0 | 1 | 1 |

Dawn and Dusk columns exist too (same pattern, darker and more saturated horizon: Dawn horizon filter (.71,.33,0), Dusk (.98,.48,0)).

Meaning of the ENVIRONMENT keys **(ENB documentation / common knowledge, the formulas are inside the DLL)**: Intensity multiplies the
weather's light colour, Curve is a power on it (above 1 darkens and saturates weak colours, so dawn/dusk and shaded colours drop much faster
than the midday sun), Desaturation pulls that colour to grey, ColorFilter tints it by `Amount`; the ambient filter has three colours chosen
by surface normal (up / sideways / down); ColorPow is a power on the diffuse texture colour; SkyLighting AmbientMinLevel is the floor of the
sky-occlusion term (0.7 = at most 30 % darkening); AutoAmbient replaces part of the ambient with a computed top/bottom gradient.

---

## 3. Per-weather files

50 files are referenced by `_weatherlist.ini` (51 slots, `!_Dwarven_Ruins.ini` twice). `_locationweather.ini` maps interior locations to fake
weather IDs so dungeons get their own file (`d4886` -> `!_Dungeons.ini`, `d4866` / `7548f` -> `!_Dwarven_Ruins.ini`, `aee84` ->
`!_Dungeons2.ini`, `75491` -> `!_Dimhollow_Crypt.ini`, `777cf` -> `!_Caves_Other.ini`). The lower-case 2016 files in the same folder
(`clear_tundra.ini`, `cloudy*.ini`, `ClearRE_A.ini`, ...) and `backup310_weatherlist.ini` are not referenced.

Day values, six representative files (full tables for all times in the appendix):

| Day | global | Clear tundra | Clear pine | Overcast | Foggy | RainStorm heavy |
|---|---|---|---|---|---|---|
| Direct Intensity / Curve / Desat | 0.4 / 1.0 / .22 | 1.5 / 3.6 / .60 | 1.5 / 3.2 / .64 | 1.5 / **0.3** / .45 | 1.0 / 1.0 / .60 | 1.5 / 1.8 / .80 |
| Direct filter @ amount | (.83,.89,.90) @ .7 | (.90,.93,.96) @ .5 | (.91,.92,.93) @ .64 | (.69,.76,.80) @ .6 | (.78,.81,.82) @ .5 | (.77,.85,.91) @ .7 |
| Ambient Intensity / Curve / Desat | 0.4 / 1.1 / .3 | 1.7 / 2.2 / .3 | 1.6 / 2.0 / .4 | **0.3** / 1.4 / .1 | 1.4 / 1.3 / .3 | 2.1 / 1.8 / 0 |
| Ambient filter amount; Top; Bottom | .35; (.94,.94,.91); (.20,.40,.46) | .52; (.51,.74,.82); (.17,.37,.46) | .50; (.54,.80,.87); (.22,.36,.43) | .35; (.78,.89,.94); (.31,.51,.58) | .29; (.58,.75,.83); (.34,.53,.60) | .40; (.40,.64,.74); (.21,.41,.49) |
| Ambient filter Middle | (.23,.33,.38) | (.67,.60,.51) | (.70,.63,.55) | (.33,.30,.17) | (.50,.47,.44) | (.61,.51,.41) |
| Specular Amount / Power | 2.2 / .24 | 0.6 / 3 | 1 / 3 | 3 / 22 | 0.7 / 0.5 | 2.7 / 7 |
| Fog Multiplier / Curve; filter @ amount | .6 / 1.4; grey .39 @ .5 | **.16** / 1.0; (.41,.56,.63) @ .5 | .8 / 2.0; (.75,.93,1) @ .64 | .45 / .73; (.48,.59,.62) @ .2 | **.77** / 1.4; (.53,.58,.62) @ .43 | .6 / 1.8; (.75,.80,.82) @ .5 |
| ColorPow | 1.1 | 1.07 | 1.08 | 1.0 | 1.1 | 1.05 |
| Sky GradientIntensity / Desat | 1.33 / 1.0 | 1.7 / .4 | 1.8 / .5 | 2.0 / .7 | 2.0 / .5 | 2.0 / .4 |
| Sky Horizon curve; Top filter | .74; grey | 1.0; (.22,.55,.67) | .5; (.05,.55,.72) | 3.0; (.46,.62,.69) | 2.0; (.68,.85,.99) | .6; (.47,.60,.73) |
| Sun Intensity / Desat; SunGlow | .2 / 1; 3 | .27 / .6; 2 | .24 / .7; 2 | .6 / 1; 10 | .3 / 1; 5 | .7 / 1; 10 |
| Clouds Intensity / Curve / Desat / Opacity | .75 / 2.5 / .6 / 1.06 | .8 / 2.8 / 1 / 1.2 | 1 / 1.2 / 1 / 1.3 | .9 / 5 / .7 / .7 | **1.4** / 2 / .3 / 1.3 | 1.2 / 1.4 / .6 / .9 |
| Bloom Amount | .6 | .6 | .5 | .7 | .5 | .5 |
| SkyLighting AmbientMinLevel | .6 | .7 | .7 | .6 | **.9** | **.9** |
| IBL Additive / Multiplicative / Reflective | .26 / .35 / 2.8 | .29 / .37 / 1.3 | .25 / .40 / 1.3 | .30 / .20 / 1.5 | .15 / .20 / 1.4 | .17 / .20 / 3.0 |
| AutoAmbient Blend / Top / Bottom / BottomSat | .7 / .6 / .5 / .2 | .5 / .6 / .45 / .4 | .5 / .7 / .46 / .3 | .8 / 1 / 1 / 1.4 | 1 / .7 / .9 / 0 | .5 / .6 / .7 / 1 |
| SunRaysMultiplier | .8 | .4 | .5 | 8 | **16** | 1 |
| VolumetricRays Intensity / Density | .5 / 1.9 | .4 / 3 | .5 / 4 | 1 / 1.3 | 1 / 1.3 | 1.2 / 1 |
| VolumetricFog Intensity / Opacity | .7 / 1 | .8 / .9 | .8 / .9 | .4 / 0 | 1.2 / .1 | .76 / .8 |
| Mist Density / VerticalOffset / VerticalFade / DistFade | 1.4 / 10 / 10 / 0 | 1.3 / -16 / 3 / .6 | 1.2 / 90 / 1 / 2 | 1.6 / 10 / .5 / .1 | **4** / -7 / 2 / 3 | 1.2 / 10 / 0 / 1 |
| Mist SkyLight / SunLight / Desat; filter | 3 / .6 / 1; (.80,.91,.93) | 2 / 2 / .6; (.75,.86,.89) | 2 / .1 / .4; (.58,.70,.75) | 2 / .3 / .8; (.71,.81,.85) | .98 / .3 / .8; (.69,.76,.78) | 2 / .6 / .9; (.73,.77,.80) |
| Particle LightingInfluence | .55 | .8 | .9 | .1 | .1 | .4 |

Interiors (InteriorDay / InteriorNight). Dungeons vs the interior columns of an exterior file:

| key | global | Dungeons | Dwarven_Ruins | Caves_Other | Clear tundra |
|---|---|---|---|---|---|
| Direct Intensity / Curve / Desat | 1 / 1 / 0 ; 1 / 2 / 1 | 1 / **3** / 1 ; 1 / 3 / 1 | 1 / 2 / 1 | 1 / 2 / 1 | 1 / 2 / 1 |
| Direct filter @ amount | white @ .7 ; (.20,.35,.42) @ .3 | (.45,.53,.57) @ .7 ; (.28,.33,.35) @ .5 | same @ .6 ; .5 | (.58,.61,.64) @ .8 ; (.29,.31,.34) @ .3 | (.47,.52,.55) @ .8 ; (.28,.33,.35) @ .3 |
| Ambient Intensity / Curve / Desat | 2 / 1 / 0 ; .4 / 2 / 0 | 1.4 / 1 / 0 ; 1 / 2 / 0 | 1 / 2 / 1 ; 1 / 2 / 1 | 2 / 2 / .5 ; 1 / 2.5 / 0 | 3 / 1 / 0 ; .5 / 2 / 1 |
| Ambient filter amount; Top | .73 ; .23; (.59,.70,.74) ; (.17,.33,.38) | .5 ; .5; (.62,.69,.72) ; (.40,.50,.55) | .5 ; .5; (.64,.68,.69) ; (.54,.61,.64) | .8 ; .4; (.67,.70,.71) ; (.43,.49,.51) | .8 ; .4; (.63,.68,.71) ; (.38,.51,.56) |
| PointLighting Intensity / Curve / Desat | 1.4 / 1.7 / .4 | 1.4 / 1.7 / .4 | 1.0 / 2.0 / .4 | 1.4 / 1.8 / .4 | 1.4 / 1.7 / .4 |
| Fog Multiplier / Curve | .4 / 1.5 ; .2 / 1.7 | .4 / 1.5 ; .2 / 1.73 | same | same | .4 / 1.5 ; .2 / 1.5 |
| SkyLighting AmbientMinLevel | .1 | .5 | .5 | .5 | .5 |
| IBL Additive / Multiplicative | .5 / 1 | .1 / 0 | .1 / 0 | .1 / 0 | .1 / 0 |
| VolumetricRays Intensity | 1 | 4 | 4 | 4 | 4 |
| VolumetricFog Intensity | 2 ; 1 | 2 ; 1 | 1 ; 1 | 1 ; 1 | 2 ; 1 |
| WindowLight Intensity / Curve | 3 / 1.4 ; .05 / 2 | 6 / 2 ; 2 / 2 | 8 / 2 ; 1 / 2 | 8 / 2.5 ; 1 / 2.5 | 11 / 1.5 ; 1 / 1.5 |
| Bloom Amount | .5 | .5 | .5 | .5 | .5 |

Pattern across the 50 files (Day min / median / max; Night median):

- **Clear / cloudy family (about 30 files)**: Direct 1.3-1.6, curve 3.0-3.6, desaturation 0.5-0.76; Ambient 1.2-1.7, curve 1.5-2.3;
  ambient filter amount 0.45-0.52 with cyan top (R .5, G .75, B .82) and darker cyan bottom, warm middle on clear, cooler on cloudy;
  fog multiplier 0.16-0.8 (tundra / reach2 / dawnguard 0.16 = almost no distance fog brightness; pine / reach 0.8), curve 1-2.3; sky gradient 1.7-1.9;
  sun disc 0.2-0.3; bloom 0.5-0.6; mist density 1.1-2.0; SkyLighting min 0.7-0.92 (cloudy higher = flatter).
- **Fog family (FoggyWeather, FoggyHeavy, FoggyRiften, FogWeathers)**: Direct 1.0-1.3 with curve 0.9-1.3 (soft), Ambient 1.4-1.6 curve 1.2-2.0,
  ambient filter amount only 0.29, fog multiplier 0.77 curve 1.4, clouds 1.4, sky gradient 1.8-2.0, mist density 3 / 3.4 / 4 / 6, SkyLighting min 0.8-0.9,
  SunRays x16 (FoggyWeather), bloom 0.5-0.6. Night: mist density 5, VolumetricRays 4, sky gradient 0.7.
- **Rain / storm**: Direct 1.3-1.5 curve 1.3-2.0 desaturation 0.6-0.8; Ambient 1.7-2.1 (highest of all) with desaturation 0; SkyLighting min 0.9;
  specular amount 2.7 power 7 (wet look); VolumetricRays 1.2-3; fog multiplier 0.4-0.7 curve 1.8-3.
- **Overcast / Storm_Brewing / HelgenAttack**: inverted balance: Direct 1.5 with curve 0.3 (lifts the dim overcast sun colour), Ambient 0.3;
  bloom 0.7; fog 0.45 curve 0.73; specular 3 / power 22; AutoAmbient 0.8 with BottomSaturation 1.4.
- **Dark stylised (DARKEND, Sovngarde, Blackreach, Apocrypha, SnowDay)**: Direct 0.3-0.5 curve 0.8-0.9 desaturation 1.0, Ambient 0.35-0.63 curve 0.1-2,
  bloom 0.65-0.9, mist density 2-4.
- **Night, all families**: Direct 0.7-0.9 (median 0.8), curve 2-3, desaturation 0.9-1.0, filter deep cyan-blue ((.17,.29,.38) to (.23,.44,.60)) at 0.6-0.7;
  Ambient 0.1-0.5 (median 0.3), curve 2-5; fog multiplier 0.02-0.3 with curve 2-4 (fog goes to black); sky top / horizon 0.03 / 0.02 with curve 0;
  moon 2.4-4; SkyLighting min 0.4; bloom 0.5-0.6; point lights 0.5.
- Constant in every file: PointLighting 0.4 day / 0.5 night / 1.4 interior, curve 1.2 / 1.7; ColorPow 1.0-1.3 (median 1.1 day, 1.2 night);
  bloom never below 0.5.

---

## 4. Other shaders

### enbbloom.fx (CR ENB "Ultimate multiple BloomLayer", Carlos) - `[BLOOM] Quality=0`
- Techniques: `BloomPrePass` (9 taps, radius `BloomDistance=2.8` px, weights `lum^BloomCurve` with `BloomCurve=0.04` = practically a plain average),
  `BloomTexture1` / `BloomTexture2` (same 9-tap kernel, second rotated 30 degrees, radii from the core) run by the core per mip level,
  `BloomPostPass` mixes the levels.
- No threshold, no tint, no contrast, no saturation change; `BloomParameters.z/.w` (blue shift, contrast) are never read.
- Mix (ini): original 0.0, initial blur 0.4, 10 px 0.7, 20 px 0.6, 40 px 0.6, 80 px 0.46, 160 px 0.53, 320 px 0.2; `USE_BLOOM_AVG` divides by the
  sum 3.49. Normalised: 11 % / 20 % / 17 % / 17 % / 13 % / 15 % / 6 %. So 51 % of the bloom energy is at 40 px and wider: a wide, soft veil.
- Lens reflections inside the bloom pass: 4 ghosts with cyan/blue/purple filters, `LenzScalar=8`, driven by `[LENS] ReflectionIntensity`
  0.02 and power 4 -> negligible.
- Signature: neutral-coloured diffusion glow of the whole image (Orton-like), 0.5-0.9x added before tone mapping. kaBloom in `enbeffect.fx`
  adds a second, soft-thresholded, very slightly cool glow only where this blur is above about 0.5.

### enblens.fx (kingeric1992 "Weather FX" on Boris' lens) - `[LENS] IgnoreWeatherSystem=true`
- `Draw` p0: 4 lens ghosts from the bloom texture (`Lens Reflect Intensity 0.06 x ReflectionIntensity 0.02`, size 0.11) + lens dirt from
  `enblensmask.png` (`DirtIntensity 0.07-0.09`, power 3.5); p1: anamorphic flare, two streaks at 86 and 3 degrees, but thresholds 90-100 and
  intensities 0.01-0.02 -> effectively off. `LensPostPass`: 8-tap blur (radius 1), additive.
- Weather passes: rain droplets on the lens (size 0.01-0.02, 2.2 Hz, intensity 1.13 day / 1.0 night, refracting the bloom texture) for the
  weather-list indices 04, 14, 16, 25; frost vignette (feather 0.43, min radius 0.27, intensity 0.32 day / 0.14 night) for indices 06, 12, 13.
- Signature: almost nothing in dry weather (faint dirt on bright light), droplets in rain, frosted corners in snow.

### enbdepthoffield.fx (Marty McFly ADOF 3.0.1 DX9) - `[DEPTHOFFIELD] Quality=1, FadeTime=0.3`
- Techniques: ReadFocus / WriteFocus (autofocus, radius 0.2), CoC, DoF_Main (bokeh gather at 0.9 render scale), Combine, Gauss V + H, ChromaticAberration.
- Values: autofocus on; hyperfocal depth 0.016; near blur curve 3.15, far blur curve 1.42; bokeh max size 7.0; 4 vertices with roundness 1.0
  (= round), quality 5 rings; bokeh intensity 0.87 (highlights pop); aspect ratio 0.92 (slightly anamorphic); Gaussian post-blur 2;
  shape chromatic aberration 0.8, type 1; optical vignette compiled out.
- The ini stores the autofocus centre as `centerX=0.58 / centerY=0.27`, the shader's parameter is a float2 named `...sample center`, so the
  centre is probably the default 0.5, 0.5 (**ambiguous**).
- Signature: shallow, smooth far-field blur behind the focused subject with small round bright bokeh and coloured fringes; this is the soft
  background in the author's character and foliage shots.

### enbsunsprite.fx (kingeric1992 lens flare)
- Technique `Draw`, many additive passes: corona (radius 0.47, intensity 0.4), sun sprite (0.2, scale 0.21), diffraction glare (7 blades, f/17,
  curve 8, intensity 0.02, tint (.92,.77,0)), four ghost groups (tints orange (1,.54,.02) and cyan (.5,1,1), chroma 1.04-1.54), four secondary
  sprites (cyan / blue / white), dirt from the alpha of `enbsunsprite.tga`. Global `Lenz flare intensity 0.23`; statics / dynamics / blinking off.
- Signature: restrained cyan-and-orange photographic flare when the sun is on screen; nothing otherwise.

### Grain
Only from effect.txt: 0.015 day / 0.01 night, saturation 0.1 (near monochrome), plus 8-bit dither. EENE noise is off.

---

## 5. Synthesis - what defines the look, and linear-pipeline equivalents

All "linear" numbers are **estimates** derived from the gamma-space values with scene value s ~ L^(1/2.2).

1. **Tone curve with a hard toe, 1:1 mid, long shoulder (steps 1, 4, 5 + effect.txt).**
   Day targets (linear scene -> display code): 0.002 -> 0.02, 0.005 -> 0.05, 0.012 -> 0.10, 0.03 -> 0.18, 0.07 -> 0.30, 0.17 -> 0.46,
   0.35 -> 0.60, 1.2 -> 0.80, 3.0 -> 0.90, 5.6 -> 0.95 (before the two x1.1 multipliers; with them 0.43 -> 0.80, 0.75 -> 0.90, 1.0 -> 0.95).
   In generic terms: exposure so that linear 0.18 lands at display ~0.47-0.5 (about neutral), contrast about 1.25 in display gamma between
   0.10 and 0.50, toe: black point at linear ~0.0005, everything under linear 0.003 below display 0.03; shoulder starts at display ~0.6,
   white at linear ~1.3 with the multipliers. Night: same shape, +1.3 stop exposure (0.011 -> 0.18), clips at linear ~0.5.
   Interior: -3.2 stops relative to Day (linear 0.27 -> 0.18), plus contrast 0.55 S-curve from effect.txt.
   Auto exposure range is small: about 1 stop Day, 0.3 stop Night, 0.5 stop Interior.
2. **Diffusion bloom.** Threshold 0, radii 10-320 px (half the energy at 40 px and wider), neutral tint, amount 0.5-0.6 clear, 0.7 overcast,
   0.9 in the stylised dark weathers, added before the tone curve in gamma space. Equivalent: mix about 62 % sharp + 38 % wide blur
   (1 : 0.6) and re-expose; in a linear pipeline use a lower amount (**estimate** 0.15-0.25 of scene energy, threshold 0, largest mips weighted up),
   because adding in gamma space lifts darks far more than the same amount in linear. Add a second glow of up to +0.125 (gamma) on areas
   whose blurred value exceeds ~0.5.
3. **Lighting balance: strong, steep, desaturated key; strong but cyan fill.** Clear day: sun multiplier 1.5 with power 3.6 and 60 %
   desaturation, tint (.90,.93,.96) at 50 % -> a near-white, slightly cool sun (no warm sun at midday); ambient multiplier 1.7 with power 2.2,
   30 % desaturation, tinted 52 % towards (.51,.74,.82) on up-facing and (.17,.37,.46) on down-facing surfaces, i.e. ambient R:B about
   0.80-0.82 from the filter alone (mult = lerp(1, filter, amount): top (.75,.86,.91), bottom (.57,.67,.72)), and warm (.67,.60,.51) on
   side-facing surfaces (R:B 1.11). Sun-to-ambient ratio: with a typical sun colour 0.9 and ambient colour 0.4 the powers give
   1.5*0.9^3.6 : 1.7*0.4^2.2 = 1.03 : 0.23, about 4.5 : 1 (**estimate**; the weather colours are in the NLVA plugin, not in these files).
   Sky occlusion floor 0.7, AO amount 2.5 at intensity 0.67.
4. **Saturation as a power on the normalised colour before the tone curve**: 1.38 Day, 1.17 Night, 1.10 Interior. It raises channel ratios
   to that power (a 20 % R/G difference becomes 28 %) and is what turns mildly cyan shadows into the measured R/B 0.72/1.20; weakly coloured
   surfaces barely move (skin 0.40 -> 0.43 HSV), foliage goes 0.57 -> 0.84, bright sky loses a little (0.59 -> 0.55) in the per-channel
   shoulder. Then vibrance -0.13 (x0.87 on low-saturation, x0.74 on fully saturated colours). In a linear pipeline: saturation about
   +35-40 % on low-chroma colours applied before the tone curve, followed by a 13-25 % vibrance-style reduction after it; net effect is
   moderate saturation overall with strongly separated cool shadows.
5. **Palette**: per-channel darkening curve in display space (roughly gamma 1.8-2.0 below 0.5, black at input 0.07, 1:1 again at 0.8-0.9),
   mid-tones nudged warm by about +0.02 R / -0.01 B. On its own it gives warm mids; it has to sit after steps 1-4.
6. **Fog and mist per weather.** Clear tundra: fog brightness multiplier 0.16 (distance stays crisp and dark), mist density 1.3 lit mostly by sky
   (2.0) with a cyan-white filter (.75,.86,.89). Fog weathers: fog multiplier 0.77 (4.8x the tundra value), mist density 4-6, clouds 1.4,
   sky gradient 2.0, sky-occlusion floor 0.9, direct light curve ~1.0, ambient filter amount down to 0.29, sun rays x16; with the bloom veil
   this gives the bright, flat, slightly cool-grey fog look. Night fog goes to black (multiplier 0.02-0.3, curve 2-4).
7. **Night**: moonlight 0.7-0.8, fully desaturated then tinted deep cyan-blue (.17,.29,.38) at 66 %; ambient 0.2-0.3 with power 2-5;
   sky top / horizon 0.03 / 0.02; fog black; high fixed gain (x9-12) on a very dark scene; point lights 0.5, fire sprites x2 (global).
8. **Interiors**: dark tone mapping (item 1), ambient 1.0-3.0 with a mild grey-cyan filter (.62,.69,.72), point lights 1.4 with power 1.7
   and 40 % desaturation, fire sprites x10 curve 1.9 (global), window light 6-11, AO amount 4.0 at intensity 0.45 with mixing type 2,
   volumetric rays 4, bloom 0.5. Warm fire against near-black, slightly cool surroundings.
9. **Finishing**: two-stage sharpening (LumaSharpen 1.6 + unsharp 1.4), 1.34 px vertical red/blue fringe, vignette 0.2 with radius 1.5,
   monochrome grain 0.015, 8.6 % letterbox bars, SMAA, ADOF with round bokeh.

---

## 6. Ambiguous or not determinable from the files

- `E_CC_PALETTE` / `E_CC_PROCEDURAL` are defined by the ENB core, not by the shader; treated as defined because `UsePaletteTexture=true`.
- `[COLORCORRECTION] Brightness=1.1`, `GammaCurve=1.1`: applied inside the DLL; formula and direction of GammaCurve unknown.
  `suki_post.py` offers it only as an option (`core_cc`).
- Adaptation texture: how the core computes it (Sensitivity 0.01) and that `ForceMinMaxValues` clamps it to [0.12, 0.7] is ENB behaviour,
  not visible here. The interior clamp with min 0.3 > max 0.13 was read as 0.13 (HLSL `min(max(x,a),b)`); if a driver evaluated it the
  other way round interiors would be another ~1 stop darker in the toe.
- Exact formulas of all `[ENVIRONMENT]`, `[SKY]`, `[MIST]` keys are in the DLL; the sun / ambient / fog colours they act on come from the
  weather plugin (NLVA). Ratios in section 5 that need those colours are estimates.
- Which weather file's Interior columns apply in an ordinary interior (house, inn) that has no `_locationweather.ini` entry: probably the
  last active exterior weather, otherwise the global file. They differ (for example ambient 3.0 vs 2.0, window light 11 vs 3).
- FIRE / LIGHTSPRITE etc. exist in both the global file (IgnoreWeatherSystem=true) and the weather files with very different values
  (fire 6 vs 0.6 by day, 10 vs 2.2 interior); assumed the global ones win.
- Pipeline position of `enblens.fx` and `enbsunsprite.fx` relative to `enbeffect.fx` is fixed by the core (lens is mixed with bloom before
  tone mapping, sun sprite is drawn late in standard ENB LE); not visible in the files.
- The bloom texture's absolute scale and the per-level radii are produced by the core; `suki_post.py` takes the bloom as an input.
- ADOF autofocus centre key mismatch (section 4).
- Letterbox and vignette could not be confirmed on the author's shots because they are cropped.

---

## Appendix - generated tables (`python -I tables.py all`)

### global

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 0.24 | 0.4 | 0.24 | 1 | 1 | 1 |
| ENVIRONMENT.DirectLightingCurve | 1.3 | 1 | 1 | 2 | 1 | 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0.34 | 0.22 | 0.18 | 0 | 0 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.7 | 0.7 | 0.38 | 0.7 | 0.3 |
| ENVIRONMENT.DirectLightingColorFilter | (0.65,0.77,0.79) | (0.83,0.89,0.90) | (0.68,0.75,0.77) | (0.10,0.25,0.32) | (1.00,1.00,1.00) | (0.20,0.35,0.42) |
| ENVIRONMENT.AmbientLightingIntensity | 0.32 | 0.4 | 0.32 | 0 | 2 | 0.4 |
| ENVIRONMENT.AmbientLightingCurve | 0.5 | 1.1 | 1.35 | 1.3 | 1 | 2 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.26 | 0.3 | 0.24 | 0.7 | 0 | 0 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.3 | 0.35 | 0.3 | 0.12 | 0.73 | 0.23 |
| ENVIRONMENT.AmbientColorFilterTop | (0.59,0.78,0.82) | (0.94,0.94,0.91) | (0.78,0.83,0.83) | (0.11,0.34,0.58) | (0.59,0.70,0.74) | (0.17,0.33,0.38) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.14,0.21,0.25) | (0.23,0.33,0.38) | (0.23,0.40,0.45) | (0.11,0.48,0.78) | (0.44,0.55,0.66) | (0.22,0.41,0.49) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.26,0.44,0.53) | (0.20,0.40,0.46) | (0.41,0.53,0.59) | (0.19,0.36,0.43) | (0.43,0.49,0.51) | (0.15,0.38,0.47) |
| ENVIRONMENT.SpecularAmountMultiplier | 2.06 | 2.2 | 2.1 | 1.26 | 1 | 1 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.17 | 0.24 | 0.3 | 0.16 | 0.5 | 0.5 |
| ENVIRONMENT.SpecularFromLight | 0.1 | 0 | 0.12 | 0.1 | 0.5 | 0.5 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.4 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.25 | 1.25 | 1.25 | 1.2 | 1.7 | 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0 | 0 | 0 | 0 | 0.4 | 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.7 | 0.6 | 0.6 | 0.25 | 0.45 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.5 | 0.6 | 0.5 | 0.34 | 0.4 | 0.2 |
| ENVIRONMENT.FogColorCurve | 1.3 | 1.4 | 1.3 | 1.2 | 1.5 | 1.7 |
| ENVIRONMENT.FogColorFilterAmount | 0.5 | 0.5 | 0.5 | 0.63 | 0.2 | 0.1 |
| ENVIRONMENT.FogColorFilter | (0.59,0.75,0.82) | (0.39,0.39,0.39) | (0.83,0.95,0.98) | (0.24,0.44,0.55) | (1.00,1.00,1.00) | (0.64,0.64,0.64) |
| ENVIRONMENT.ColorPow | 1.05 | 1.1 | 1.05 | 1.1 | 1.1 | 1.15 |
| SKY.GradientIntensity | 1.22 | 1.33 | 1.45 | 3.2 | 2.38 | 0.68 |
| SKY.GradientDesaturation | 0.16 | 1 | 0.16 | 0 | 0.5 | 0 |
| SKY.GradientTopIntensity | 0.7 | 0.8 | 0.6 | 0.04 | 1.23 | 1 |
| SKY.GradientTopCurve | 1.3 | 1.2 | 1.3 | 0 | 1.2 | 1.5 |
| SKY.GradientTopColorFilter | (0.39,0.39,0.39) | (0.55,0.55,0.55) | (0.47,0.47,0.47) | (0.03,0.21,0.36) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 0.5 | 0.7 | 0.45 | 0.07 | 2.05 | 1 |
| SKY.GradientMiddleCurve | 1 | 1.15 | 1.2 | 0 | 0.71 | 1 |
| SKY.GradientMiddleColorFilter | (0.67,0.67,0.67) | (0.56,0.56,0.56) | (0.70,0.70,0.70) | (0.03,0.34,0.48) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 0.75 | 0.8 | 0.75 | 0.14 | 3 | 1 |
| SKY.GradientHorizonCurve | 0.9 | 0.74 | 1.6 | 0 | 1.43 | 1 |
| SKY.GradientHorizonColorFilter | (0.63,0.63,0.63) | (1.00,1.00,1.00) | (0.82,0.82,0.82) | (0.08,0.32,0.44) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.3 | 0.2 | 0.3 | 1 | 1 | 1 |
| SKY.SunDesaturation | 1 | 1 | 1 | 0 | 0.7 | 0 |
| SKY.SunColorFilter | (0.86,0.78,0.39) | (1.00,0.98,0.80) | (0.89,0.71,0.36) | (0.24,0.44,0.55) | (1.00,0.94,0.86) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 4 | 3 | 6 | 2 | 1 | 0 |
| SKY.SunGlowHaziness | 0.1 | 0.1 | 0.1 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 0.52 | 0.75 | 0.58 | 0.4 | 2 | 0.3 |
| SKY.CloudsCurve | 2.8 | 2.5 | 2.23 | 1 | 1 | 1 |
| SKY.CloudsDesaturation | 0.53 | 0.6 | 0.52 | 0.21 | 0 | 0 |
| SKY.CloudsOpacity | 1.14 | 1.06 | 1.13 | 1.21 | 1 | 1 |
| SKY.CloudsColorFilter | (1.00,1.00,1.00) | (1.00,1.00,1.00) | (1.00,1.00,1.00) | (0.35,0.69,0.85) | (0.89,0.94,0.99) | (0.34,0.46,0.53) |
| SKY.MoonIntensity | 0.4 | 0.3 | 0.2 | 4 | 1 | 1 |
| BLOOM.Amount | 0.54 | 0.6 | 0.55 | 0.8 | 0.5 | 0.5 |
| BLOOM.BlueShiftAmount | 1.1 | 1.5 | 1.1 | 0.96 | 1 | 1 |
| SKYLIGHTING.AmbientMinLevel | 0.6 | 0.6 | 0.6 | 0.6 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.23 | 0.26 | 0.23 | 0.4 | 0.5 | 0.5 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.37 | 0.35 | 0.35 | 0.6 | 1 | 1 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 2.7 | 2.8 | 2.7 | 0.9 | 2 | 2 |
| AUTOAMBIENT.BlendingAmount | 0.7 | 0.7 | 0.7 | 0.6 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 0.6 | 0.6 | 0.6 | 0.5 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.6 | 0.5 | 0.6 | 0.5 | 0.5 | 0.2 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 | 0.2 |
| RAYS.SunRaysMultiplier | 0.74 | 0.8 | 0.75 | 2 | 0.3 | 0.3 |
| VOLUMETRICRAYS.Intensity | 0.59 | 0.5 | 0.54 | 1 | 1 | 1 |
| VOLUMETRICRAYS.Density | 2.1 | 1.9 | 2.1 | 1 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.8 | 0.6 | 0.8 | 1 | 1 | 1 |
| VOLUMETRICFOG.Intensity | 0.65 | 0.7 | 0.4 | 0.23 | 2 | 1 |
| VOLUMETRICFOG.Curve | 0.84 | 0.53 | 0.6 | 0.57 | 0.6 | 1 |
| VOLUMETRICFOG.LightingInfluence | 0.7 | 0.9 | 0.5 | 0.9 | 0.4 | 1 |
| VOLUMETRICFOG.Opacity | 1 | 1 | 1 | 0 | 1 | 1 |
| MIST.SkyLightingAmount | 2.9 | 3 | 2.9 | 1.8 | 1 | 1 |
| MIST.SunLightingAmount | 0.7 | 0.6 | 0.7 | 0 | 0.1 | 0.1 |
| MIST.Desaturation | 0.3 | 1 | 1 | 0.8 | 0 | 0 |
| MIST.ColorFilter | (0.77,0.88,0.91) | (0.80,0.91,0.93) | (0.71,0.83,0.94) | (0.13,0.43,0.57) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | 10 | 10 | 10 | -30 | -11 | -11 |
| MIST.Density | 1.4 | 1.4 | 1.4 | 1.8 | 1.5 | 1.5 |
| MIST.VerticalFade | 7 | 10 | 5 | 1.7 | 2 | 2 |
| MIST.BottomTop | 1 | 0.8 | 0.6 | 1 | 0 | 0 |
| MIST.ExponentialFade | 1.1 | 1 | 1.2 | 1.8 | 1 | 1 |
| MIST.DistanceFade | 0.2 | 0 | 0.1 | 0 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 1.7 | 1.5 | 1.7 | 3 | 1 | 1 |
| PROCEDURALSUN.GlowCurve | 0.07 | 0.06 | 0.08 | 1 | 1 | 1 |
| PARTICLE.Intensity | 0.56 | 0.7 | 0.53 | 0.4 | 0.8 | 0.6 |
| PARTICLE.LightingInfluence | 0.36 | 0.55 | 0.1 | 1.4 | 1 | 1 |
| FIRE.Intensity | 5 | 6 | 5 | 2 | 10 | 10 |
| FIRE.Curve | 1.7 | 2 | 1.5 | 1.6 | 1.9 | 1.9 |
| LIGHTSPRITE.Intensity | 1.1 | 1 | 1.1 | 1.3 | 1 | 1 |
| LIGHTSPRITE.Curve | 3 | 4 | 3 | 3 | 3 | 3 |
| WINDOWLIGHT.Intensity | 0.7 | 0.4 | 0.7 | 0.8 | 3 | 0.05 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 1.3 | 1.4 | 2 |
| GRASS.DirectionalMultiplier | 1 | 1 | 1 | 1 | 2 | 1.4 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 1 | 3 | 2 |
| CLOUDSHADOWS.Opacity | 1 | 1 | 1 | 1 | 0.9 | 0.9 |

### ClearTundra

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1.4 | 1.5 | 1.4 | 0.7 | 1 | 1 |
| ENVIRONMENT.DirectLightingCurve | 3.5 | 3.6 | 3.1 | 2 | 2 | 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0.7 | 0.6 | 0.4 | 1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.58 | 0.5 | 0.6 | 0.66 | 0.8 | 0.3 |
| ENVIRONMENT.DirectLightingColorFilter | (0.80,0.67,0.54) | (0.90,0.93,0.96) | (0.92,0.70,0.46) | (0.17,0.29,0.38) | (0.47,0.52,0.55) | (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 1.5 | 1.7 | 1.5 | 0.3 | 3 | 0.5 |
| ENVIRONMENT.AmbientLightingCurve | 2.4 | 2.2 | 2.3 | 2 | 1 | 2 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.2 | 0.3 | 0.1 | 0.5 | 0 | 1 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.4 | 0.52 | 0.43 | 0.3 | 0.8 | 0.4 |
| ENVIRONMENT.AmbientColorFilterTop | (0.34,0.54,0.72) | (0.51,0.74,0.82) | (0.43,0.65,0.75) | (0.09,0.27,0.34) | (0.63,0.68,0.71) | (0.38,0.51,0.56) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.56,0.49,0.38) | (0.67,0.60,0.51) | (0.61,0.51,0.41) | (0.19,0.38,0.46) | (0.56,0.60,0.62) | (0.32,0.51,0.62) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.08,0.29,0.39) | (0.17,0.37,0.46) | (0.14,0.28,0.33) | (0.13,0.31,0.39) | (0.45,0.53,0.57) | (0.21,0.40,0.48) |
| ENVIRONMENT.SpecularAmountMultiplier | 0.6 | 0.6 | 0.6 | 0.6 | 1 | 1 |
| ENVIRONMENT.SpecularPowerMultiplier | 3 | 3 | 3 | 3 | 0.3 | 0.3 |
| ENVIRONMENT.SpecularFromLight | 0.4 | 0.3 | 0.4 | 0.8 | 0.5 | 0.5 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.5 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.7 | 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0.1 | 0.1 | 0.1 | 0.1 | 0.4 | 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.7 | 0.6 | 0.6 | 0.25 | 0.45 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.39 | 0.16 | 0.29 | 0.02 | 0.4 | 0.2 |
| ENVIRONMENT.FogColorCurve | 1 | 1 | 0.64 | 4 | 1.5 | 1.5 |
| ENVIRONMENT.FogColorFilterAmount | 0.2 | 0.5 | 0.64 | 0.1 | 0.2 | 0.1 |
| ENVIRONMENT.FogColorFilter | (0.76,0.73,0.63) | (0.41,0.56,0.63) | (0.26,0.33,0.39) | (0.24,0.44,0.55) | (1.00,1.00,1.00) | (0.64,0.64,0.64) |
| ENVIRONMENT.ColorPow | 1.1 | 1.07 | 1.04 | 1.2 | 1.1 | 1.15 |
| SKY.GradientIntensity | 1.8 | 1.7 | 1.8 | 1.6 | 2.2 | 1 |
| SKY.GradientDesaturation | 0.56 | 0.4 | 0.4 | 0.5 | 0.3 | 0.3 |
| SKY.GradientTopIntensity | 0.7 | 0.7 | 0.7 | 0.03 | 1.23 | 1 |
| SKY.GradientTopCurve | 0.6 | 0.8 | 0.8 | 0 | 1.2 | 1.5 |
| SKY.GradientTopColorFilter | (0.26,0.56,0.76) | (0.22,0.55,0.67) | (0.28,0.64,0.74) | (0.02,0.22,0.29) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 0.9 | 0.9 | 0.9 | 0.14 | 2 | 1 |
| SKY.GradientMiddleCurve | 0.7 | 1 | 0.7 | 0 | 0.71 | 1.01 |
| SKY.GradientMiddleColorFilter | (0.23,0.65,0.79) | (0.31,0.61,0.72) | (0.33,0.73,0.70) | (0.11,0.23,0.34) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 0.8 | 0.8 | 0.8 | 0.02 | 1 | 0.7 |
| SKY.GradientHorizonCurve | 0.6 | 1 | 0.6 | 0 | 1.43 | 1 |
| SKY.GradientHorizonColorFilter | (0.83,0.72,0.60) | (0.37,0.57,0.67) | (0.96,0.72,0.31) | (0.31,0.35,0.42) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.23 | 0.27 | 0.22 | 1 | 0.2 | 1 |
| SKY.SunDesaturation | 0.5 | 0.6 | 0.3 | 1 | 0.7 | 0 |
| SKY.SunColorFilter | (0.88,0.63,0.48) | (0.89,0.92,0.93) | (0.96,0.64,0.29) | (0.19,0.49,0.62) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 5 | 2 | 6 | 10 | 1 | 0 |
| SKY.SunGlowHaziness | 0.25 | 0.12 | 0.1 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 0.6 | 0.8 | 0.5 | 0.94 | 1 | 0.16 |
| SKY.CloudsCurve | 1 | 2.8 | 1 | 3 | 2 | 1 |
| SKY.CloudsDesaturation | 0.3 | 1 | 0 | 0.9 | 0 | 0 |
| SKY.CloudsOpacity | 1.1 | 1.2 | 1.5 | 2 | 1.5 | 1.72 |
| SKY.CloudsColorFilter | (0.88,0.82,0.77) | (0.67,0.74,0.78) | (0.89,0.85,0.80) | (0.22,0.32,0.43) | (0.85,0.87,0.88) | (1.00,1.00,1.00) |
| SKY.MoonIntensity | 0.4 | 0.2 | 0.1 | 2.4 | 1 | 1 |
| BLOOM.Amount | 0.5 | 0.6 | 0.5 | 0.5 | 0.5 | 0.5 |
| BLOOM.BlueShiftAmount | 2 | 3 | 2 | 2 | 1 | 2 |
| SKYLIGHTING.AmbientMinLevel | 0.66 | 0.7 | 0.64 | 0.4 | 0.5 | 0.5 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.24 | 0.29 | 0.25 | 0.1 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.3 | 0.37 | 0.3 | 0.14 | 0 | 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 1.7 | 1.3 | 1.3 | 2 | 1 | 1 |
| AUTOAMBIENT.BlendingAmount | 0.5 | 0.5 | 0.4 | 0.9 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 0.5 | 0.6 | 0.5 | 1 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.4 | 0.45 | 0.5 | 0.6 | 0.5 | 0.5 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.4 | 0.4 | 0.9 | 0.1 | 0.1 |
| RAYS.SunRaysMultiplier | 0.4 | 0.4 | 0.4 | 2 | 0.3 | 0.3 |
| VOLUMETRICRAYS.Intensity | 0.6 | 0.4 | 0.6 | 0.99 | 4 | 4 |
| VOLUMETRICRAYS.Density | 4 | 3 | 3 | 1.5 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.4 | 1 | 0.3 | 0.5 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.6 | 0.8 | 0.55 | 0.16 | 2 | 1 |
| VOLUMETRICFOG.Curve | 0.7 | 1 | 1 | 1 | 0.7 | 1 |
| VOLUMETRICFOG.LightingInfluence | 0.5 | 1.2 | 0.2 | 0.83 | 1 | 1 |
| VOLUMETRICFOG.Opacity | 0.6 | 0.9 | 0.8 | 0.5 | 1 | 1 |
| MIST.SkyLightingAmount | 2 | 2 | 1 | 1.3 | 1 | 1 |
| MIST.SunLightingAmount | 0.5 | 2 | 1 | 0 | 0.1 | 0.1 |
| MIST.Desaturation | 0.4 | 0.6 | 0.6 | 0.8 | 0 | 0 |
| MIST.ColorFilter | (0.54,0.72,0.85) | (0.75,0.86,0.89) | (0.36,0.59,0.82) | (0.08,0.28,0.36) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | -12 | -16 | -14 | 10 | -11 | -11 |
| MIST.Density | 1 | 1.3 | 1.38 | 2 | 1.5 | 1.5 |
| MIST.VerticalFade | 0 | 3 | 2 | 4 | 2 | 2 |
| MIST.BottomTop | 0.3 | 0.5 | 1 | 1 | 0 | 0 |
| MIST.ExponentialFade | 1.2 | 0.5 | 0.4 | 1.85 | 1 | 1 |
| MIST.DistanceFade | 1 | 0.6 | 0.7 | 0 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 0.4 | 0.4 | 0.4 | 0.6 | 1 | 1 |
| PROCEDURALSUN.GlowCurve | 6 | 5 | 7 | 3 | 1 | 1 |
| PARTICLE.Intensity | 0.48 | 0.8 | 0.5 | 0.2 | 0.8 | 0.5 |
| PARTICLE.LightingInfluence | 0.3 | 0.8 | 0.97 | 0.9 | 0.5 | 0.5 |
| FIRE.Intensity | 1 | 0.6 | 1 | 1 | 2.2 | 2.5 |
| FIRE.Curve | 0.5 | 0.5 | 0.5 | 0.7 | 1 | 1 |
| LIGHTSPRITE.Intensity | 0.8 | 0.5 | 0.75 | 1.4 | 2 | 2 |
| LIGHTSPRITE.Curve | 1 | 1 | 1 | 1.31 | 1.9 | 2.4 |
| WINDOWLIGHT.Intensity | 0.5 | 0.5 | 0.5 | 1.13 | 11 | 1 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 1.3 | 1.5 | 1.5 |
| GRASS.DirectionalMultiplier | 2 | 2 | 2 | 1 | 2 | 1.4 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 1 | 3 | 2 |
| CLOUDSHADOWS.Opacity | 0.6 | 1 | 0.76 | 1 | 1 | 1 |

### ClearPine

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1.4 | 1.5 | 1.4 | 0.8 | 1 | 1 |
| ENVIRONMENT.DirectLightingCurve | 3.5 | 3.2 | 3.6 | 2 | 1 | 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0.6 | 0.64 | 0.36 | 1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.64 | 0.6 | 0.6 | 0.8 | 0.3 |
| ENVIRONMENT.DirectLightingColorFilter | (0.85,0.68,0.49) | (0.91,0.92,0.93) | (0.74,0.58,0.41) | (0.22,0.38,0.49) | (0.45,0.53,0.57) | (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 1.4 | 1.6 | 1.4 | 0.3 | 3 | 1 |
| ENVIRONMENT.AmbientLightingCurve | 2.1 | 2 | 2.2 | 3 | 1 | 1.4 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.3 | 0.4 | 0.2 | 0.5 | 0 | 1 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.4 | 0.5 | 0.4 | 0.25 | 0.8 | 0.4 |
| ENVIRONMENT.AmbientColorFilterTop | (0.22,0.64,0.80) | (0.54,0.80,0.87) | (0.09,0.42,0.58) | (0.13,0.29,0.38) | (0.63,0.68,0.71) | (0.38,0.51,0.56) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.61,0.52,0.37) | (0.70,0.63,0.55) | (0.49,0.42,0.31) | (0.25,0.39,0.45) | (0.53,0.61,0.65) | (0.42,0.49,0.53) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.15,0.31,0.38) | (0.22,0.36,0.43) | (0.00,0.32,0.52) | (0.27,0.41,0.51) | (0.45,0.53,0.56) | (0.29,0.37,0.40) |
| ENVIRONMENT.SpecularAmountMultiplier | 1 | 1 | 1 | 1 | 1 | 1 |
| ENVIRONMENT.SpecularPowerMultiplier | 3 | 3 | 3 | 3 | 0.3 | 0.2 |
| ENVIRONMENT.SpecularFromLight | 0.4 | 0.3 | 0.4 | 0.8 | 0.5 | 0.5 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.5 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.7 | 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0.1 | 0.1 | 0.1 | 0.1 | 0.4 | 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.7 | 0.6 | 0.6 | 0.25 | 0.45 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.5 | 0.8 | 0.5 | 0.1 | 0.4 | 0.2 |
| ENVIRONMENT.FogColorCurve | 1.4 | 2 | 1.3 | 4 | 1.5 | 1.73 |
| ENVIRONMENT.FogColorFilterAmount | 0.6 | 0.64 | 0.5 | 0.12 | 0.2 | 0.1 |
| ENVIRONMENT.FogColorFilter | (0.56,0.62,0.74) | (0.75,0.93,1.00) | (0.80,0.71,0.54) | (0.14,0.26,0.36) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| ENVIRONMENT.ColorPow | 1.1 | 1.08 | 1.1 | 1.2 | 1.1 | 1.15 |
| SKY.GradientIntensity | 1.7 | 1.8 | 1.5 | 1.6 | 2 | 0.8 |
| SKY.GradientDesaturation | 0.4 | 0.5 | 0.4 | 0.5 | 0.3 | 0.3 |
| SKY.GradientTopIntensity | 0.8 | 0.8 | 0.8 | 0.01 | 1.23 | 1 |
| SKY.GradientTopCurve | 0.7 | 0.83 | 0.5 | 0 | 1.2 | 1.5 |
| SKY.GradientTopColorFilter | (0.17,0.51,0.68) | (0.05,0.55,0.72) | (0.20,0.55,0.76) | (0.13,0.42,0.54) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 0.8 | 0.9 | 0.8 | 0.06 | 2 | 1 |
| SKY.GradientMiddleCurve | 0.9 | 0.8 | 0.7 | 0 | 0.71 | 1 |
| SKY.GradientMiddleColorFilter | (0.42,0.71,0.82) | (0.41,0.65,0.80) | (0.44,0.73,0.73) | (0.09,0.46,0.59) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 0.8 | 0.8 | 0.9 | 0 | 3 | 1 |
| SKY.GradientHorizonCurve | 0.6 | 0.5 | 0.6 | 0 | 1.43 | 1 |
| SKY.GradientHorizonColorFilter | (0.91,0.81,0.68) | (0.34,0.58,0.69) | (0.86,0.54,0.31) | (0.07,0.27,0.66) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.2 | 0.24 | 0.23 | 2 | 1 | 1 |
| SKY.SunDesaturation | 0.5 | 0.7 | 0.2 | 1 | 0.7 | 0 |
| SKY.SunColorFilter | (0.94,0.69,0.50) | (0.92,0.95,0.97) | (0.88,0.56,0.35) | (0.60,0.62,0.63) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 3 | 2 | 7 | 10 | 1 | 0.2 |
| SKY.SunGlowHaziness | 0.1 | 0.14 | 0.1 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 1 | 1 | 0.7 | 1 | 2 | 0.4 |
| SKY.CloudsCurve | 1 | 1.2 | 1.1 | 3 | 2 | 1 |
| SKY.CloudsDesaturation | 0.8 | 1 | 0.5 | 0.9 | 0 | 0 |
| SKY.CloudsOpacity | 1.1 | 1.3 | 1.2 | 1.3 | 1.25 | 1.72 |
| SKY.CloudsColorFilter | (0.89,0.88,0.83) | (0.75,0.82,0.87) | (0.64,0.67,0.74) | (0.30,0.44,0.57) | (0.85,0.87,0.88) | (1.00,1.00,1.00) |
| SKY.MoonIntensity | 0.4 | 0.3 | 0.24 | 3 | 2.8 | 1 |
| BLOOM.Amount | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| BLOOM.BlueShiftAmount | 2 | 3 | 2 | 2 | 1 | 2 |
| SKYLIGHTING.AmbientMinLevel | 0.6 | 0.7 | 0.65 | 0.4 | 0.5 | 0.5 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.2 | 0.25 | 0.23 | 0.1 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.3 | 0.4 | 0.3 | 0 | 0 | 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 1.3 | 1.3 | 1.3 | 1 | 1 | 1 |
| AUTOAMBIENT.BlendingAmount | 0.5 | 0.5 | 0.5 | 0.6 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 0.7 | 0.7 | 0.6 | 1 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.45 | 0.46 | 0.43 | 0.4 | 0.2 | 0.2 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.3 | 0.2 | 0.9 | 0.1 | 0.1 |
| RAYS.SunRaysMultiplier | 0.4 | 0.5 | 0.4 | 2 | 0.3 | 0.3 |
| VOLUMETRICRAYS.Intensity | 0.7 | 0.5 | 0.8 | 1 | 4 | 4 |
| VOLUMETRICRAYS.Density | 4 | 4 | 3 | 2 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.2 | 0.3 | 0.3 | 1 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.8 | 0.8 | 0.7 | 0.13 | 2.3 | 1 |
| VOLUMETRICFOG.Curve | 0.8 | 0.9 | 1 | 0.8 | 0.7 | 1 |
| VOLUMETRICFOG.LightingInfluence | 0.7 | 1 | 0.5 | 0.3 | 1 | 1 |
| VOLUMETRICFOG.Opacity | 0.69 | 0.9 | 0.7 | 0 | 1 | 1 |
| MIST.SkyLightingAmount | 2.7 | 2 | 1.3 | 2 | 1 | 1 |
| MIST.SunLightingAmount | 0.3 | 0.1 | 0.5 | 0.6 | 0.1 | 0.1 |
| MIST.Desaturation | 0.7 | 0.4 | 0.5 | 0.8 | 0 | 0 |
| MIST.ColorFilter | (0.47,0.59,0.69) | (0.58,0.70,0.75) | (0.46,0.68,0.80) | (0.18,0.37,0.49) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | 50 | 90 | 70 | -20 | -11 | -11 |
| MIST.Density | 1.4 | 1.2 | 1.2 | 1.39 | 1.5 | 1.5 |
| MIST.VerticalFade | 1 | 1 | 0.8 | 0 | 2 | 2 |
| MIST.BottomTop | 1 | 0.2 | 1 | 1 | 0 | 0 |
| MIST.ExponentialFade | 1.2 | 1 | 1 | 1.1 | 1 | 1 |
| MIST.DistanceFade | 2 | 2 | 2 | 0.2 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 0.4 | 0.4 | 0.43 | 3 | 1 | 1 |
| PROCEDURALSUN.GlowCurve | 6 | 7 | 6 | 5 | 1 | 1 |
| PARTICLE.Intensity | 0.6 | 0.9 | 0.6 | 0.18 | 0.8 | 0.5 |
| PARTICLE.LightingInfluence | 1 | 0.9 | 0.9 | 1 | 0.5 | 0.5 |
| FIRE.Intensity | 1 | 0.6 | 1 | 1 | 2.2 | 2.5 |
| FIRE.Curve | 0.5 | 0.5 | 0.5 | 0.7 | 1 | 1 |
| LIGHTSPRITE.Intensity | 0.8 | 0.5 | 0.75 | 1.4 | 2 | 2 |
| LIGHTSPRITE.Curve | 1 | 1 | 1 | 1.31 | 1.9 | 2.4 |
| WINDOWLIGHT.Intensity | 0.5 | 0.5 | 0.5 | 1.13 | 14 | 1 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 1.3 | 2.5 | 2.5 |
| GRASS.DirectionalMultiplier | 2 | 2 | 2 | 1 | 2 | 1.4 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 1 | 3 | 2 |
| CLOUDSHADOWS.Opacity | 0.87 | 1 | 0.7 | 1 | 1 | 1 |

### Overcast

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1.3 | 1.5 | 1.3 | 0.7 | 0.3 | 1 |
| ENVIRONMENT.DirectLightingCurve | 0.9 | 0.3 | 1 | 1.9 | 1 | 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0.65 | 0.45 | 0.5 | 0.1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.6 | 0.7 | 1 | 0.5 | 0.12 |
| ENVIRONMENT.DirectLightingColorFilter | (0.51,0.62,0.67) | (0.69,0.76,0.80) | (0.55,0.65,0.70) | (0.00,0.23,0.39) | (0.45,0.53,0.57) | (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 0.2 | 0.3 | 0.2 | 0.4 | 0.5 | 0.2 |
| ENVIRONMENT.AmbientLightingCurve | 1.4 | 1.4 | 1.4 | 3 | 0.8 | 1.02 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.35 | 0.1 | 0.4 | 0 | 0.5 | 0.5 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.3 | 0.35 | 0.3 | 0.2 | 0.35 | 0.26 |
| ENVIRONMENT.AmbientColorFilterTop | (0.64,0.69,0.75) | (0.78,0.89,0.94) | (0.70,0.78,0.82) | (0.13,0.48,0.66) | (0.44,0.52,0.56) | (0.38,0.51,0.56) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.32,0.32,0.32) | (0.33,0.30,0.17) | (0.24,0.31,0.33) | (0.14,0.27,0.33) | (0.28,0.38,0.42) | (0.19,0.35,0.43) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.19,0.30,0.34) | (0.31,0.51,0.58) | (0.18,0.30,0.35) | (0.09,0.49,0.70) | (0.31,0.41,0.46) | (0.21,0.39,0.48) |
| ENVIRONMENT.SpecularAmountMultiplier | 3 | 3 | 3 | 4 | 2 | 2 |
| ENVIRONMENT.SpecularPowerMultiplier | 22 | 22 | 22 | 22 | 2 | 2 |
| ENVIRONMENT.SpecularFromLight | 0.4 | 0.3 | 0.4 | 0.6 | 0.5 | 0.5 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.5 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 |
| ENVIRONMENT.PointLightingDesaturation | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| ENVIRONMENT.ParticleLightsIntensity | 1 | 1 | 1 | 0.9 | 0.5 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.35 | 0.45 | 0.3 | 0.3 | 0.22 | 0.45 |
| ENVIRONMENT.FogColorCurve | 1 | 0.73 | 1.2 | 0.9 | 1.73 | 1.73 |
| ENVIRONMENT.FogColorFilterAmount | 0.2 | 0.2 | 0.2 | 0 | 0 | 0 |
| ENVIRONMENT.FogColorFilter | (0.42,0.52,0.57) | (0.48,0.59,0.62) | (0.42,0.49,0.53) | (0.16,0.31,0.36) | (1.00,1.00,1.00) | (0.64,0.64,0.64) |
| ENVIRONMENT.ColorPow | 1.05 | 1 | 1.05 | 1.1 | 1.15 | 1.15 |
| SKY.GradientIntensity | 1.72 | 2 | 1.73 | 3 | 1.2 | 1 |
| SKY.GradientDesaturation | 0.4 | 0.7 | 0.3 | 0.33 | 0.73 | 0 |
| SKY.GradientTopIntensity | 1 | 0.75 | 1 | 1 | 1 | 1 |
| SKY.GradientTopCurve | 1.1 | 1.2 | 1.1 | 1.1 | 1 | 1 |
| SKY.GradientTopColorFilter | (0.35,0.57,0.63) | (0.46,0.62,0.69) | (0.29,0.43,0.50) | (0.14,0.27,0.33) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 0.9 | 1 | 0.92 | 0.6 | 1 | 1 |
| SKY.GradientMiddleCurve | 1.3 | 1 | 1.2 | 1.05 | 1 | 1 |
| SKY.GradientMiddleColorFilter | (0.49,0.65,0.70) | (0.72,0.82,0.97) | (0.42,0.61,0.67) | (0.02,0.26,0.34) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 0.6 | 0.7 | 0.6 | 0.8 | 1 | 1 |
| SKY.GradientHorizonCurve | 2 | 3 | 2 | 0.6 | 1 | 1 |
| SKY.GradientHorizonColorFilter | (0.56,0.61,0.62) | (0.67,0.74,0.74) | (0.77,0.74,0.59) | (0.51,0.70,0.79) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.7 | 0.6 | 0.7 | 0.1 | 3 | 1 |
| SKY.SunDesaturation | 1 | 1 | 1 | 1 | 0 | 0 |
| SKY.SunColorFilter | (0.93,0.86,0.71) | (0.79,0.89,0.93) | (0.93,0.82,0.71) | (1.00,1.00,1.00) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 10 | 10 | 10 | 10 | 1 | 1 |
| SKY.SunGlowHaziness | 0 | 0 | 0 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 0.85 | 0.9 | 0.83 | 1.2 | 0.15 | 0.09 |
| SKY.CloudsCurve | 2 | 5 | 2 | 3 | 1 | 1 |
| SKY.CloudsDesaturation | 0.7 | 0.7 | 0.7 | 0.1 | 0 | 0 |
| SKY.CloudsOpacity | 0.7 | 0.7 | 0.7 | 0.9 | 1.13 | 1.07 |
| SKY.CloudsColorFilter | (0.51,0.65,0.70) | (0.74,0.84,0.88) | (0.51,0.62,0.67) | (0.19,0.37,0.43) | (1.00,1.00,1.00) | (0.20,0.38,0.47) |
| SKY.MoonIntensity | 1 | 1 | 1 | 1.6 | 1 | 1.6 |
| BLOOM.Amount | 0.6 | 0.7 | 0.6 | 0.5 | 0.7 | 0.5 |
| BLOOM.BlueShiftAmount | 2 | 3 | 2 | 2 | 1 | 3 |
| SKYLIGHTING.AmbientMinLevel | 0.5 | 0.6 | 0.5 | 0.5 | 0.63 | 0.16 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.24 | 0.3 | 0.22 | 0.28 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.24 | 0.2 | 0.25 | 0.3 | 0 | 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 1.5 | 1.5 | 1.5 | 2 | 0.7 | 0.7 |
| AUTOAMBIENT.BlendingAmount | 0.8 | 0.8 | 0.8 | 0.7 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 1 | 1 | 1 | 1 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 1 | 1 | 1 | 1 | 0.2 | 0.2 |
| AUTOAMBIENT.BottomSaturation | 1.4 | 1.4 | 1.4 | 0.9 | 1 | 1 |
| RAYS.SunRaysMultiplier | 6 | 8 | 6 | 0.4 | 0.1 | 0.1 |
| VOLUMETRICRAYS.Intensity | 1 | 1 | 1 | 1 | 4 | 4 |
| VOLUMETRICRAYS.Density | 1.3 | 1.3 | 1.3 | 1 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.3 | 0.4 | 0.3 | 0.19 | 1 | 1 |
| VOLUMETRICFOG.Curve | 1.4 | 1.9 | 1.4 | 0.9 | 1 | 1 |
| VOLUMETRICFOG.LightingInfluence | 0.84 | 0.18 | 0.8 | 0.9 | 1 | 1 |
| VOLUMETRICFOG.Opacity | 0 | 0 | 0 | 0 | 1 | 1 |
| MIST.SkyLightingAmount | 1.7 | 2 | 2 | 1.4 | 1 | 1 |
| MIST.SunLightingAmount | 0.2 | 0.3 | 0.5 | 0.2 | 0.1 | 0.1 |
| MIST.Desaturation | 0.8 | 0.8 | 0.7 | 0.6 | 0 | 0 |
| MIST.ColorFilter | (0.55,0.65,0.70) | (0.71,0.81,0.85) | (0.84,0.77,0.72) | (0.18,0.28,0.37) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | 10 | 10 | 10 | 30 | -10 | -10 |
| MIST.Density | 2 | 1.6 | 2 | 2.1 | 1 | 1.5 |
| MIST.VerticalFade | 0.4 | 0.5 | 0.4 | 0 | 4 | 4 |
| MIST.BottomTop | 1 | 1 | 1 | 0 | 0 | 0 |
| MIST.ExponentialFade | 1 | 1 | 1 | 0.8 | 1 | 1 |
| MIST.DistanceFade | 0.2 | 0.1 | 1 | 1 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 0.8 | 0.6 | 0.8 | 0.5 | 0.4 | 0.4 |
| PROCEDURALSUN.GlowCurve | 10 | 10 | 10 | 10 | 10 | 10 |
| PARTICLE.Intensity | 0.5 | 0.7 | 0.5 | 0.32 | 0.7 | 0.5 |
| PARTICLE.LightingInfluence | 0.4 | 0.1 | 0.3 | 0.65 | 0.5 | 0.5 |
| FIRE.Intensity | 1 | 0.6 | 1 | 1 | 2.2 | 2.5 |
| FIRE.Curve | 0.5 | 0.5 | 0.5 | 0.7 | 1 | 1 |
| LIGHTSPRITE.Intensity | 0.8 | 0.5 | 0.75 | 0.8 | 2 | 2 |
| LIGHTSPRITE.Curve | 1 | 1 | 1 | 1.31 | 1.9 | 2.4 |
| WINDOWLIGHT.Intensity | 0.1 | 0.1 | 0.1 | 0.1 | 0.7 | 0.2 |
| WINDOWLIGHT.Curve | 2 | 2 | 2 | 2 | 0.75 | 1.88 |
| GRASS.DirectionalMultiplier | 2 | 2 | 2 | 2 | 2 | 1.4 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 2 | 3 | 2 |
| CLOUDSHADOWS.Opacity | 0.8 | 0.8 | 0.8 | 0.5 | 1 | 1 |

### Foggy

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1.1 | 1 | 1.3 | 0.7 | 1 | 1 |
| ENVIRONMENT.DirectLightingCurve | 1.2 | 1 | 1 | 2.3 | 1 | 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0.5 | 0.6 | 0.6 | 1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.5 | 0.6 | 0.6 | 0.8 | 0.3 |
| ENVIRONMENT.DirectLightingColorFilter | (0.97,0.72,0.35) | (0.78,0.81,0.82) | (0.82,0.74,0.63) | (0.23,0.44,0.60) | (0.45,0.53,0.57) | (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 1.2 | 1.4 | 1.1 | 0.2 | 2 | 0.3 |
| ENVIRONMENT.AmbientLightingCurve | 1.3 | 1.3 | 1.6 | 2 | 1 | 1 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.4 | 0.3 | 0.4 | 0.7 | 0 | 1 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.22 | 0.29 | 0.24 | 0.2 | 0.75 | 0.26 |
| ENVIRONMENT.AmbientColorFilterTop | (0.42,0.64,0.76) | (0.58,0.75,0.83) | (0.35,0.68,0.78) | (0.16,0.39,0.47) | (0.58,0.64,0.67) | (0.38,0.51,0.56) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.58,0.56,0.51) | (0.50,0.47,0.44) | (0.58,0.56,0.51) | (0.11,0.34,0.44) | (0.48,0.58,0.62) | (0.32,0.51,0.62) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.23,0.45,0.54) | (0.34,0.53,0.60) | (0.23,0.43,0.49) | (0.14,0.42,0.55) | (0.36,0.51,0.58) | (0.21,0.40,0.48) |
| ENVIRONMENT.SpecularAmountMultiplier | 0.7 | 0.7 | 0.7 | 0.7 | 1 | 1 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.5 | 0.5 | 0.6 | 0.8 | 0.3 | 0.3 |
| ENVIRONMENT.SpecularFromLight | 0.18 | 0.1 | 0.1 | 0.13 | 0.6 | 0.6 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.5 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.7 | 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0.1 | 0.1 | 0.1 | 0.4 | 0.4 | 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.6 | 0.6 | 0.6 | 0.4 | 0.5 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.6 | 0.77 | 0.58 | 0.1 | 0.22 | 0.22 |
| ENVIRONMENT.FogColorCurve | 1.1 | 1.4 | 1 | 2 | 1.73 | 1.73 |
| ENVIRONMENT.FogColorFilterAmount | 0.32 | 0.43 | 0.34 | 0.1 | 0.2 | 0.1 |
| ENVIRONMENT.FogColorFilter | (0.64,0.67,0.69) | (0.53,0.58,0.62) | (0.87,0.78,0.62) | (0.28,0.38,0.46) | (1.00,1.00,1.00) | (0.65,0.65,0.65) |
| ENVIRONMENT.ColorPow | 1.07 | 1.1 | 1.08 | 1.2 | 1.1 | 1.15 |
| SKY.GradientIntensity | 2 | 2 | 1.7 | 0.7 | 3 | 1.003 |
| SKY.GradientDesaturation | 0.4 | 0.5 | 0.4 | 0.4 | 0.73 | 0 |
| SKY.GradientTopIntensity | 0.9 | 1 | 0.8 | 0.03 | 1 | 1 |
| SKY.GradientTopCurve | 1.2 | 1.2 | 1.1 | 0 | 1 | 1 |
| SKY.GradientTopColorFilter | (0.29,0.66,0.85) | (0.68,0.85,0.99) | (0.59,0.78,0.88) | (0.10,0.40,1.00) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 1 | 0.8 | 0.8 | 0.1 | 1 | 1 |
| SKY.GradientMiddleCurve | 1 | 1 | 1.2 | 0 | 1 | 1 |
| SKY.GradientMiddleColorFilter | (0.49,0.76,0.90) | (0.79,0.88,0.93) | (0.59,0.70,0.77) | (0.35,0.60,0.85) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 1 | 0.8 | 0.8 | 0.03 | 1 | 1 |
| SKY.GradientHorizonCurve | 1 | 2 | 1 | 0 | 1 | 1 |
| SKY.GradientHorizonColorFilter | (0.93,0.81,0.58) | (0.79,0.95,1.00) | (0.71,0.88,0.93) | (0.40,0.75,0.93) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.24 | 0.3 | 0.22 | 0.7 | 1 | 1 |
| SKY.SunDesaturation | 0.6 | 1 | 1 | 1 | 0 | 0 |
| SKY.SunColorFilter | (0.91,0.77,0.63) | (0.87,0.91,0.94) | (0.84,0.76,0.67) | (0.06,0.37,0.49) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 6 | 5 | 5 | 1 | 1 | 1 |
| SKY.SunGlowHaziness | 0.2 | 0.3 | 0.2 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 1 | 1.4 | 1 | 0.6 | 2 | 1 |
| SKY.CloudsCurve | 1.1 | 2 | 1.4 | 2 | 1 | 1 |
| SKY.CloudsDesaturation | 0.2 | 0.3 | 0.1 | 0 | 0 | 0 |
| SKY.CloudsOpacity | 1 | 1.3 | 1 | 0.8 | 1 | 1 |
| SKY.CloudsColorFilter | (0.77,0.89,0.96) | (0.71,0.88,0.99) | (0.82,0.90,0.93) | (0.52,0.67,0.77) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.MoonIntensity | 1 | 1 | 1 | 3 | 1 | 1.6 |
| BLOOM.Amount | 0.6 | 0.5 | 0.6 | 0.5 | 0.5 | 0.5 |
| BLOOM.BlueShiftAmount | 2 | 4 | 2 | 2 | 1 | 2 |
| SKYLIGHTING.AmbientMinLevel | 0.72 | 0.9 | 0.78 | 0.5 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.13 | 0.15 | 0.13 | 0.2 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.16 | 0.2 | 0.18 | 0.2 | 0 | 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 1.4 | 1.4 | 1.4 | 2 | 0.2 | 0.2 |
| AUTOAMBIENT.BlendingAmount | 0.8 | 1 | 0.9 | 0.4 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 0.8 | 0.7 | 0.9 | 1 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.7 | 0.9 | 0.9 | 0.7 | 0.2 | 0.2 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0 | 0.2 | 0.9 | 0 | 0 |
| RAYS.SunRaysMultiplier | 13 | 16 | 11 | 0.1 | 0.1 | 0.1 |
| VOLUMETRICRAYS.Intensity | 1 | 1 | 1 | 4 | 4 | 4 |
| VOLUMETRICRAYS.Density | 1 | 1.3 | 1.5 | 1 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.8 | 1.2 | 0.8 | 0.6 | 2 | 1 |
| VOLUMETRICFOG.Curve | 0.7 | 1 | 0.7 | 0.9 | 0.5 | 1 |
| VOLUMETRICFOG.LightingInfluence | 1 | 0.6 | 1 | 1 | 0.4 | 1 |
| VOLUMETRICFOG.Opacity | 0.1 | 0.1 | 0.1 | 0.1 | 1 | 1 |
| MIST.SkyLightingAmount | 0.98 | 0.98 | 1.2 | 2.06 | 1 | 1 |
| MIST.SunLightingAmount | 0.4 | 0.3 | 0.5 | 0.2 | 0.1 | 0.1 |
| MIST.Desaturation | 0.8 | 0.8 | 0.9 | 0.7 | 0 | 0 |
| MIST.ColorFilter | (0.82,0.83,0.85) | (0.69,0.76,0.78) | (0.73,0.75,0.76) | (0.38,0.44,0.47) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | -10 | -7 | -5 | 10 | -10 | -10 |
| MIST.Density | 5.4 | 4 | 5 | 5 | 1.5 | 1.5 |
| MIST.VerticalFade | 3 | 2 | 3 | 2 | 4 | 4 |
| MIST.BottomTop | 0 | 0 | 0 | 0 | 0 | 0 |
| MIST.ExponentialFade | 1.03 | 1.02 | 1.05 | 1.15 | 1 | 1 |
| MIST.DistanceFade | 5 | 3 | 2 | 0 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 1 | 1 | 2 | 0.4 | 0.4 | 0.4 |
| PROCEDURALSUN.GlowCurve | 10 | 10 | 10 | 10 | 10 | 10 |
| PARTICLE.Intensity | 0.5 | 0.8 | 0.5 | 0.18 | 0.8 | 0.5 |
| PARTICLE.LightingInfluence | 0.15 | 0.1 | 0.2 | 0.81 | 0.5 | 0.5 |
| FIRE.Intensity | 1 | 0.6 | 1 | 1 | 2.2 | 2.5 |
| FIRE.Curve | 0.5 | 0.5 | 0.5 | 0.7 | 1 | 1 |
| LIGHTSPRITE.Intensity | 0.8 | 0.5 | 0.75 | 1.4 | 2 | 2 |
| LIGHTSPRITE.Curve | 1 | 1 | 1 | 1.31 | 1.9 | 2.4 |
| WINDOWLIGHT.Intensity | 0.5 | 0.5 | 0.5 | 1.13 | 11 | 1.2 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 1.28 | 2 | 2 |
| GRASS.DirectionalMultiplier | 1.8 | 1.8 | 1.8 | 1 | 2 | 1.4 |
| GRASS.AmbientMultiplier | 1.7 | 1.5 | 1.7 | 1 | 3 | 2 |
| CLOUDSHADOWS.Opacity | 1 | 1 | 1 | 0.8 | 1 | 1 |

### RainStormHeavy

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1.3 | 1.5 | 1.4 | 0.8 | 1 | 1 |
| ENVIRONMENT.DirectLightingCurve | 1.5 | 1.8 | 1.3 | 3 | 1 | 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0.6 | 0.8 | 0.7 | 1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.7 | 0.7 | 0.7 | 0.7 | 0.2 |
| ENVIRONMENT.DirectLightingColorFilter | (0.72,0.62,0.54) | (0.77,0.85,0.91) | (0.93,0.64,0.46) | (0.18,0.34,0.42) | (0.45,0.53,0.57) | (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 2 | 2.1 | 2 | 0.2 | 2.3 | 0.42 |
| ENVIRONMENT.AmbientLightingCurve | 1.8 | 1.8 | 1.8 | 5 | 1 | 1.4 |
| ENVIRONMENT.AmbientLightingDesaturation | 0 | 0 | 0 | 0.4 | 0 | 1 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.32 | 0.4 | 0.35 | 0.26 | 0.69 | 0.3 |
| ENVIRONMENT.AmbientColorFilterTop | (0.25,0.51,0.62) | (0.40,0.64,0.74) | (0.34,0.49,0.55) | (0.14,0.32,0.40) | (0.63,0.68,0.71) | (0.38,0.51,0.56) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.52,0.43,0.34) | (0.61,0.51,0.41) | (0.53,0.43,0.33) | (0.11,0.23,0.28) | (0.48,0.58,0.62) | (0.32,0.51,0.62) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.16,0.33,0.39) | (0.21,0.41,0.49) | (0.20,0.31,0.35) | (0.13,0.28,0.35) | (0.40,0.55,0.62) | (0.21,0.40,0.48) |
| ENVIRONMENT.SpecularAmountMultiplier | 2.5 | 2.7 | 2.5 | 3 | 2.3 | 2.3 |
| ENVIRONMENT.SpecularPowerMultiplier | 7 | 7 | 7 | 7 | 0.4 | 0.4 |
| ENVIRONMENT.SpecularFromLight | 0.3 | 0.4 | 0.4 | 0.6 | 0.6 | 0.5 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.5 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.7 | 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0.1 | 0.1 | 0.1 | 0.1 | 0.4 | 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.6 | 0.6 | 0.6 | 0.7 | 0.5 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.4 | 0.6 | 0.5 | 0.2 | 0.22 | 0.45 |
| ENVIRONMENT.FogColorCurve | 1.5 | 1.8 | 1.9 | 2 | 1.73 | 1.73 |
| ENVIRONMENT.FogColorFilterAmount | 0.2 | 0.5 | 0.3 | 0 | 0 | 0 |
| ENVIRONMENT.FogColorFilter | (0.67,0.71,0.76) | (0.75,0.80,0.82) | (0.64,0.69,0.77) | (0.27,0.36,0.51) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| ENVIRONMENT.ColorPow | 1.08 | 1.05 | 1.08 | 1.2 | 1.1 | 1.15 |
| SKY.GradientIntensity | 2 | 2 | 2 | 0.1 | 3 | 0.7 |
| SKY.GradientDesaturation | 0.5 | 0.4 | 0.6 | 0 | 0 | 0 |
| SKY.GradientTopIntensity | 1 | 1 | 0.7 | 0.2 | 1.23 | 1 |
| SKY.GradientTopCurve | 2 | 2 | 2 | 0 | 1.2 | 1.5 |
| SKY.GradientTopColorFilter | (0.29,0.50,0.63) | (0.47,0.60,0.73) | (0.36,0.49,0.57) | (0.14,0.23,0.26) | (0.80,0.90,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 1.4 | 1.1 | 1.3 | 0.2 | 2.05 | 1 |
| SKY.GradientMiddleCurve | 1 | 0.9 | 1 | 0 | 1 | 1 |
| SKY.GradientMiddleColorFilter | (0.48,0.68,0.76) | (0.31,0.47,0.58) | (0.48,0.68,0.69) | (0.23,0.34,0.40) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 0.8 | 1 | 0.8 | 0.03 | 3 | 1 |
| SKY.GradientHorizonCurve | 1 | 0.6 | 1 | 0 | 1.43 | 1 |
| SKY.GradientHorizonColorFilter | (0.98,0.70,0.36) | (0.72,0.80,0.84) | (0.91,0.58,0.35) | (0.22,0.35,0.41) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.6 | 0.7 | 0.7 | 3 | 1 | 1 |
| SKY.SunDesaturation | 0.9 | 1 | 1 | 1 | 1 | 0 |
| SKY.SunColorFilter | (0.82,0.68,0.59) | (0.89,0.93,0.94) | (0.79,0.65,0.56) | (0.19,0.49,0.62) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 10 | 10 | 10 | 10 | 1 | 0 |
| SKY.SunGlowHaziness | 0.25 | 0.2 | 0.27 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 1 | 1.2 | 1 | 0.9 | 2 | 0.7 |
| SKY.CloudsCurve | 1.3 | 1.4 | 1.3 | 8 | 1.3 | 1 |
| SKY.CloudsDesaturation | 0.3 | 0.6 | 1 | 1 | 0 | 0 |
| SKY.CloudsOpacity | 0.8 | 0.9 | 0.8 | 0.87 | 0.6 | 1 |
| SKY.CloudsColorFilter | (0.69,0.72,0.74) | (0.83,0.88,0.93) | (0.67,0.71,0.78) | (0.21,0.36,0.46) | (0.82,0.90,0.98) | (0.29,0.43,0.50) |
| SKY.MoonIntensity | 0.4 | 0.3 | 0.2 | 3 | 1 | 1 |
| BLOOM.Amount | 0.5 | 0.5 | 0.5 | 0.6 | 0.6 | 0.5 |
| BLOOM.BlueShiftAmount | 0 | 3 | 0 | 2 | 0 | 0 |
| SKYLIGHTING.AmbientMinLevel | 0.82 | 0.9 | 0.84 | 0.4 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.16 | 0.17 | 0.16 | 0 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.2 | 0.2 | 0.2 | 0.2 | 0 | 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 3 | 3 | 3 | 2.7 | 1 | 1 |
| AUTOAMBIENT.BlendingAmount | 0.6 | 0.5 | 0.6 | 0.6 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 0.7 | 0.6 | 0.7 | 1 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.7 | 0.7 | 0.7 | 0.5 | 0.2 | 0.2 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 1 | 0.1 | 0.9 | 0 | 0 |
| RAYS.SunRaysMultiplier | 1 | 1 | 1.4 | 1 | 0.1 | 0.1 |
| VOLUMETRICRAYS.Intensity | 1 | 1.2 | 1 | 4 | 4 | 4 |
| VOLUMETRICRAYS.Density | 2 | 1 | 2 | 1.3 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 1 | 1 | 0.7 | 0.5 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.7 | 0.76 | 0.7 | 0.3 | 2 | 1 |
| VOLUMETRICFOG.Curve | 0.8 | 0.7 | 0.8 | 2 | 1 | 1 |
| VOLUMETRICFOG.LightingInfluence | 0.9 | 0.74 | 0.7 | 1 | 1 | 1 |
| VOLUMETRICFOG.Opacity | 0.72 | 0.8 | 0.8 | 0.4 | 1 | 1 |
| MIST.SkyLightingAmount | 1.9 | 2 | 1.5 | 1.2 | 1 | 1 |
| MIST.SunLightingAmount | 0.5 | 0.6 | 0 | 0 | 0.1 | 0.1 |
| MIST.Desaturation | 0.5 | 0.9 | 0.4 | 0.8 | 0 | 0 |
| MIST.ColorFilter | (0.65,0.72,0.74) | (0.73,0.77,0.80) | (0.57,0.64,0.71) | (0.21,0.40,0.49) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | 10 | 10 | 10 | 12 | -11 | -10 |
| MIST.Density | 1.35 | 1.2 | 1.1 | 1.4 | 1.5 | 1.5 |
| MIST.VerticalFade | 1 | 0 | 0 | 3 | 3 | 3 |
| MIST.BottomTop | 0 | 0 | 0 | 0 | 0 | 0 |
| MIST.ExponentialFade | 1.1 | 1.2 | 1.2 | 1.2 | 1 | 1 |
| MIST.DistanceFade | 5 | 1 | 0.8 | 0 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 0.3 | 0.8 | 0.5 | 3 | 1 | 1 |
| PROCEDURALSUN.GlowCurve | 10 | 10 | 10 | 10 | 1 | 1 |
| PARTICLE.Intensity | 0.8 | 0.9 | 0.8 | 0.1 | 0.8 | 0.5 |
| PARTICLE.LightingInfluence | 0.5 | 0.4 | 0.6 | 0.7 | 0.5 | 0.5 |
| FIRE.Intensity | 1 | 0.6 | 1 | 1 | 2.2 | 2.5 |
| FIRE.Curve | 0.5 | 0.5 | 0.5 | 0.7 | 1 | 1 |
| LIGHTSPRITE.Intensity | 0.8 | 0.5 | 0.75 | 1.4 | 2 | 2 |
| LIGHTSPRITE.Curve | 1 | 1 | 1 | 1.31 | 1.9 | 2.4 |
| WINDOWLIGHT.Intensity | 0.1 | 0.1 | 0.1 | 0.1 | 6 | 1.1 |
| WINDOWLIGHT.Curve | 2 | 2 | 2 | 2 | 0.75 | 1.88 |
| GRASS.DirectionalMultiplier | 2 | 2 | 2 | 1 | 2 | 1.4 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 1 | 3 | 2 |
| CLOUDSHADOWS.Opacity | 0.99 | 1 | 0.99 | 0.2 | 1 | 1 |

### Dungeons

| section.key | Sunrise | Day | Sunset | Night | InteriorDay | InteriorNight |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1.4 | 1.5 | 1.4 | 0.8 | 1 | 1 |
| ENVIRONMENT.DirectLightingCurve | 3.6 | 3.4 | 3.6 | 2 | 3 | 3 |
| ENVIRONMENT.DirectLightingDesaturation | 0.5 | 0.3 | 0.36 | 1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.66 | 0.7 | 0.65 | 0.8 | 0.7 | 0.5 |
| ENVIRONMENT.DirectLightingColorFilter | (0.83,0.75,0.67) | (0.78,0.82,0.87) | (0.69,0.63,0.58) | (0.22,0.38,0.49) | (0.45,0.53,0.57) | (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 1.7 | 1.7 | 1.5 | 0.3 | 1.4 | 1 |
| ENVIRONMENT.AmbientLightingCurve | 2 | 2 | 2 | 2.4 | 1 | 2 |
| ENVIRONMENT.AmbientLightingDesaturation | 0 | 0 | 0 | 0.5 | 0 | 0 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.4 | 0.5 | 0.4 | 0.25 | 0.5 | 0.5 |
| ENVIRONMENT.AmbientColorFilterTop | (0.22,0.64,0.80) | (0.54,0.80,0.87) | (0.09,0.42,0.58) | (0.13,0.29,0.38) | (0.62,0.69,0.72) | (0.40,0.50,0.55) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.61,0.52,0.37) | (0.70,0.63,0.55) | (0.49,0.42,0.31) | (0.28,0.33,0.35) | (0.53,0.62,0.65) | (0.34,0.40,0.44) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.15,0.31,0.38) | (0.22,0.36,0.43) | (0.00,0.32,0.52) | (0.27,0.41,0.51) | (0.49,0.57,0.60) | (0.28,0.33,0.35) |
| ENVIRONMENT.SpecularAmountMultiplier | 1.6 | 1.6 | 1.6 | 1.6 | 1 | 1 |
| ENVIRONMENT.SpecularPowerMultiplier | 10 | 10 | 10 | 8 | 0.4 | 0.4 |
| ENVIRONMENT.SpecularFromLight | 0.5 | 0.6 | 0.5 | 0.8 | 0.6 | 0.6 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.5 | 1.4 | 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.7 | 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0.1 | 0.1 | 0.1 | 0.1 | 0.4 | 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.7 | 0.6 | 0.6 | 0.25 | 0.45 | 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.5 | 0.5 | 0.5 | 0.1 | 0.4 | 0.2 |
| ENVIRONMENT.FogColorCurve | 1.4 | 1.6 | 1.3 | 3.58 | 1.5 | 1.73 |
| ENVIRONMENT.FogColorFilterAmount | 0.6 | 0.6 | 0.5 | 0.12 | 0.2 | 0.1 |
| ENVIRONMENT.FogColorFilter | (0.60,0.63,0.71) | (0.68,0.77,0.82) | (0.75,0.72,0.66) | (0.06,0.34,0.49) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| ENVIRONMENT.ColorPow | 1.05 | 1.1 | 1.1 | 1.2 | 1.1 | 1.15 |
| SKY.GradientIntensity | 1.7 | 1.8 | 1.5 | 1.6 | 3 | 0.8 |
| SKY.GradientDesaturation | 0.4 | 0.3 | 0.4 | 0.5 | 0.3 | 0.3 |
| SKY.GradientTopIntensity | 0.7 | 0.9 | 0.8 | 0.01 | 1.23 | 1 |
| SKY.GradientTopCurve | 0.7 | 1 | 0.5 | 0 | 1.2 | 1.5 |
| SKY.GradientTopColorFilter | (0.17,0.51,0.68) | (0.05,0.57,0.89) | (0.20,0.55,0.76) | (0.13,0.42,0.54) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 0.8 | 1 | 0.8 | 0.1 | 2 | 1 |
| SKY.GradientMiddleCurve | 0.82 | 0.8 | 0.7 | 0 | 0.71 | 1 |
| SKY.GradientMiddleColorFilter | (0.42,0.71,0.82) | (0.38,0.63,0.78) | (0.30,0.60,0.62) | (0.09,0.46,0.59) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 1 | 1.3 | 1 | 0.02 | 3 | 1 |
| SKY.GradientHorizonCurve | 0.6 | 0.5 | 0.7 | 0 | 1.43 | 1 |
| SKY.GradientHorizonColorFilter | (0.91,0.81,0.68) | (0.57,0.65,0.69) | (0.83,0.45,0.19) | (0.07,0.27,0.66) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunIntensity | 0.2 | 0.24 | 0.23 | 2 | 1 | 1 |
| SKY.SunDesaturation | 0.4 | 0.7 | 0.2 | 1 | 0.7 | 0 |
| SKY.SunColorFilter | (1.00,0.80,0.49) | (0.92,0.95,0.97) | (1.00,0.68,0.36) | (0.60,0.62,0.63) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 3 | 2 | 7 | 10 | 1 | 0.2 |
| SKY.SunGlowHaziness | 0.1 | 0.14 | 0.1 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 1 | 1.4 | 1 | 1 | 3 | 0.4 |
| SKY.CloudsCurve | 1.1 | 1.3 | 1.1 | 3 | 1.1 | 1 |
| SKY.CloudsDesaturation | 0.8 | 1 | 0.5 | 0.9 | 0 | 0 |
| SKY.CloudsOpacity | 2 | 2 | 2 | 1.3 | 0.7 | 1.72 |
| SKY.CloudsColorFilter | (0.89,0.88,0.83) | (0.72,0.83,0.90) | (0.64,0.67,0.74) | (0.30,0.44,0.57) | (0.82,0.90,0.98) | (0.59,0.67,0.74) |
| SKY.MoonIntensity | 0.4 | 0.3 | 0.24 | 3 | 2.8 | 1 |
| BLOOM.Amount | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| BLOOM.BlueShiftAmount | 2 | 3 | 2 | 2 | 1 | 2 |
| SKYLIGHTING.AmbientMinLevel | 0.7 | 0.7 | 0.69 | 0.4 | 0.5 | 0.5 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.23 | 0.25 | 0.23 | 0.1 | 0.1 | 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.2 | 0.3 | 0.2 | 0 | 0 | 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 3 | 3 | 3 | 2.7 | 1 | 1 |
| AUTOAMBIENT.BlendingAmount | 0.8 | 0.8 | 0.8 | 0.6 | 1 | 1 |
| AUTOAMBIENT.TopIntensity | 0.6 | 0.6 | 0.6 | 0.5 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.45 | 0.5 | 0.43 | 0.4 | 0.2 | 0.2 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.2 | 0.2 | 0.9 | 0.1 | 0.1 |
| RAYS.SunRaysMultiplier | 0.4 | 0.5 | 0.4 | 2 | 0.3 | 0.3 |
| VOLUMETRICRAYS.Intensity | 0.7 | 0.5 | 0.8 | 1 | 4 | 4 |
| VOLUMETRICRAYS.Density | 3 | 4 | 3 | 2 | 1 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.2 | 0.3 | 0.3 | 1 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.8 | 0.9 | 0.7 | 0.13 | 2 | 1 |
| VOLUMETRICFOG.Curve | 0.8 | 0.8 | 1 | 0.8 | 1 | 1 |
| VOLUMETRICFOG.LightingInfluence | 0.4 | 0.7 | 0.5 | 0.3 | 1 | 1 |
| VOLUMETRICFOG.Opacity | 0.69 | 0.9 | 0.7 | 0 | 1 | 1 |
| MIST.SkyLightingAmount | 1 | 1 | 1.3 | 2 | 1 | 1 |
| MIST.SunLightingAmount | 0.3 | 0.1 | 0.5 | 0.6 | 0.1 | 0.1 |
| MIST.Desaturation | 0.7 | 0.6 | 0.5 | 0.8 | 0 | 0 |
| MIST.ColorFilter | (0.55,0.64,0.71) | (0.68,0.77,0.82) | (0.59,0.68,0.77) | (0.18,0.37,0.49) | (1.00,1.00,1.00) | (1.00,1.00,1.00) |
| MIST.VerticalOffset | 50 | 90 | 70 | -20 | -11 | -11 |
| MIST.Density | 1.4 | 1.4 | 1.2 | 1.39 | 1.5 | 1.5 |
| MIST.VerticalFade | 1 | 1 | 0.8 | 0 | 2 | 2 |
| MIST.BottomTop | 1 | 0.2 | 1 | 1 | 0 | 0 |
| MIST.ExponentialFade | 1.2 | 1 | 1 | 1.1 | 1 | 1 |
| MIST.DistanceFade | 2 | 2 | 2 | 0.2 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 0.4 | 0.4 | 0.43 | 3 | 1 | 1 |
| PROCEDURALSUN.GlowCurve | 6 | 7 | 6 | 5 | 1 | 1 |
| PARTICLE.Intensity | 0.6 | 0.9 | 0.6 | 0.18 | 0.8 | 0.5 |
| PARTICLE.LightingInfluence | 1 | 0.9 | 0.9 | 1 | 0.5 | 0.5 |
| FIRE.Intensity | 1 | 0.6 | 1 | 1 | 2.2 | 2.5 |
| FIRE.Curve | 0.5 | 0.5 | 0.5 | 0.7 | 1 | 1 |
| LIGHTSPRITE.Intensity | 0.8 | 0.5 | 0.75 | 1.4 | 2 | 2 |
| LIGHTSPRITE.Curve | 1 | 1 | 1 | 1.31 | 1.9 | 2.4 |
| WINDOWLIGHT.Intensity | 0.5 | 0.5 | 0.5 | 1.13 | 6 | 2 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 1.3 | 2 | 2 |
| GRASS.DirectionalMultiplier | 1 | 1 | 1 | 1 | 1 | 1 |
| GRASS.AmbientMultiplier | 1 | 1 | 1 | 1 | 1 | 1 |
| CLOUDSHADOWS.Opacity | 1 | 0.9 | 0.7 | 0.3 | 1 | 1 |

### Ranges across the 50 referenced weather files (min / median / max), scalar keys

| section.key | Day | Night | InteriorDay |
|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 0.30 / 1.36 / 1.60 | 0.10 / 0.80 / 1.10 | 0.00 / 1.00 / 2.00 |
| ENVIRONMENT.DirectLightingCurve | 0.30 / 3.00 / 3.60 | 0.90 / 2.00 / 3.00 | 0.55 / 1.00 / 4.00 |
| ENVIRONMENT.DirectLightingDesaturation | 0.20 / 0.60 / 1.00 | 0.00 / 0.90 / 1.00 | 0.00 / 1.00 / 1.00 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.00 / 0.60 / 1.00 | 0.00 / 0.69 / 1.00 | 0.03 / 0.80 / 0.80 |
| ENVIRONMENT.AmbientLightingIntensity | 0.30 / 1.50 / 2.10 | 0.00 / 0.30 / 1.00 | 0.30 / 2.00 / 3.00 |
| ENVIRONMENT.AmbientLightingCurve | 0.10 / 2.00 / 4.00 | 1.00 / 2.00 / 5.00 | 0.60 / 1.00 / 2.00 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.00 / 0.25 / 0.70 | 0.00 / 0.50 / 1.00 | 0.00 / 0.00 / 1.00 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.15 / 0.46 / 0.52 | 0.05 / 0.25 / 0.50 | 0.20 / 0.73 / 0.90 |
| ENVIRONMENT.SpecularAmountMultiplier | 0.60 / 1.00 / 3.50 | 0.60 / 1.00 / 4.00 | 0.60 / 1.00 / 4.00 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.50 / 3.00 / 22.00 | 0.30 / 3.00 / 22.00 | 0.15 / 0.30 / 5.00 |
| ENVIRONMENT.SpecularFromLight | 0.00 / 0.30 / 0.60 | 0.00 / 0.70 / 0.80 | 0.40 / 0.50 / 0.70 |
| ENVIRONMENT.PointLightingIntensity | 0.40 / 0.40 / 0.40 | 0.40 / 0.50 / 0.50 | 0.80 / 1.40 / 1.40 |
| ENVIRONMENT.PointLightingCurve | 1.20 / 1.20 / 1.25 | 1.20 / 1.20 / 1.25 | 1.20 / 1.70 / 2.00 |
| ENVIRONMENT.PointLightingDesaturation | 0.00 / 0.10 / 0.10 | 0.00 / 0.10 / 0.40 | 0.00 / 0.40 / 0.40 |
| ENVIRONMENT.ParticleLightsIntensity | 0.60 / 0.60 / 1.00 | 0.25 / 0.40 / 0.90 | 0.45 / 0.50 / 10.00 |
| ENVIRONMENT.FogColorMultiplier | 0.16 / 0.60 / 1.10 | 0.02 / 0.15 / 1.00 | 0.10 / 0.22 / 1.00 |
| ENVIRONMENT.FogColorCurve | 0.20 / 1.40 / 4.00 | 0.61 / 2.40 / 4.00 | 1.00 / 1.50 / 4.00 |
| ENVIRONMENT.FogColorFilterAmount | 0.00 / 0.43 / 0.70 | 0.00 / 0.10 / 0.70 | 0.00 / 0.20 / 0.40 |
| ENVIRONMENT.ColorPow | 1.00 / 1.10 / 1.30 | 1.01 / 1.20 / 1.20 | 1.10 / 1.10 / 1.15 |
| SKY.GradientIntensity | 1.00 / 1.80 / 10.00 | 0.10 / 1.60 / 10.00 | 0.70 / 2.05 / 10.00 |
| SKY.GradientDesaturation | 0.10 / 0.50 / 0.82 | 0.00 / 0.44 / 1.00 | 0.00 / 0.30 / 1.00 |
| SKY.GradientTopIntensity | 0.40 / 0.75 / 1.20 | 0.00 / 0.03 / 1.00 | 1.00 / 1.23 / 2.00 |
| SKY.GradientTopCurve | 0.00 / 1.04 / 4.00 | 0.00 / 0.00 / 3.00 | 0.50 / 1.00 / 1.20 |
| SKY.GradientMiddleIntensity | 0.60 / 0.80 / 4.00 | 0.05 / 0.14 / 2.00 | 1.00 / 2.00 / 3.00 |
| SKY.GradientMiddleCurve | 0.70 / 1.00 / 2.00 | 0.00 / 0.00 / 1.05 | 0.30 / 0.73 / 1.00 |
| SKY.GradientHorizonIntensity | 0.30 / 0.80 / 4.00 | 0.00 / 0.02 / 1.59 | 1.00 / 1.50 / 3.00 |
| SKY.GradientHorizonCurve | 0.50 / 1.00 / 3.00 | 0.00 / 0.00 / 4.00 | 1.00 / 1.43 / 2.00 |
| SKY.SunIntensity | 0.03 / 0.27 / 1.00 | 0.00 / 1.00 / 3.00 | 0.20 / 1.00 / 3.00 |
| SKY.SunDesaturation | 0.00 / 0.80 / 1.00 | 0.00 / 1.00 / 1.00 | 0.00 / 0.70 / 1.00 |
| SKY.SunGlowIntensity | 0.50 / 3.50 / 10.00 | 1.00 / 10.00 / 10.00 | 0.00 / 1.00 / 10.00 |
| SKY.SunGlowHaziness | 0.00 / 0.14 / 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| SKY.CloudsIntensity | 0.52 / 0.90 / 1.40 | 0.45 / 1.00 / 1.29 | 0.15 / 2.00 / 4.00 |
| SKY.CloudsCurve | 1.00 / 2.00 / 7.00 | 0.80 / 2.35 / 8.00 | 0.20 / 1.00 / 4.00 |
| SKY.CloudsDesaturation | 0.00 / 0.70 / 1.00 | 0.00 / 0.90 / 1.00 | 0.00 / 0.00 / 1.00 |
| SKY.CloudsOpacity | 0.60 / 1.00 / 3.00 | 0.00 / 1.00 / 3.00 | 0.00 / 1.13 / 3.00 |
| SKY.MoonIntensity | 0.20 / 0.30 / 3.00 | 1.00 / 3.00 / 4.00 | 1.00 / 1.00 / 2.80 |
| BLOOM.Amount | 0.50 / 0.54 / 0.90 | 0.50 / 0.50 / 0.90 | 0.50 / 0.50 / 0.80 |
| BLOOM.BlueShiftAmount | 1.00 / 3.00 / 4.00 | 1.00 / 2.00 / 2.00 | 0.00 / 1.00 / 2.00 |
| SKYLIGHTING.AmbientMinLevel | 0.40 / 0.74 / 1.00 | 0.30 / 0.40 / 0.70 | 0.10 / 0.16 / 0.63 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.10 / 0.27 / 0.31 | 0.00 / 0.12 / 0.50 | 0.10 / 0.10 / 0.40 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.10 / 0.24 / 0.40 | 0.00 / 0.20 / 1.00 | 0.00 / 0.00 / 0.60 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 0.60 / 1.30 / 3.00 | 1.00 / 2.00 / 2.70 | 0.20 / 1.00 / 3.00 |
| AUTOAMBIENT.BlendingAmount | 0.50 / 0.53 / 1.00 | 0.20 / 0.75 / 1.00 | 1.00 / 1.00 / 1.00 |
| AUTOAMBIENT.TopIntensity | 0.50 / 0.70 / 1.00 | 0.30 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| AUTOAMBIENT.BottomIntensity | 0.20 / 0.50 / 1.00 | 0.20 / 0.50 / 1.00 | 0.20 / 0.20 / 0.50 |
| AUTOAMBIENT.BottomSaturation | 0.00 / 0.30 / 2.00 | 0.90 / 0.90 / 2.00 | 0.00 / 0.10 / 2.00 |
| RAYS.SunRaysMultiplier | 0.40 / 0.60 / 30.00 | 0.10 / 1.00 / 2.00 | 0.10 / 0.30 / 1.00 |
| VOLUMETRICRAYS.Intensity | 0.30 / 0.60 / 3.00 | 0.00 / 1.00 / 4.00 | 4.00 / 4.00 / 4.00 |
| VOLUMETRICRAYS.Density | 0.50 / 1.50 / 4.00 | 1.00 / 1.50 / 3.00 | 1.00 / 1.00 / 1.00 |
| VOLUMETRICRAYS.SkyColorAmount | 0.00 / 0.50 / 1.00 | 0.50 / 0.50 / 1.00 | 0.50 / 0.50 / 0.50 |
| VOLUMETRICFOG.Intensity | 0.40 / 0.86 / 1.30 | 0.10 / 0.20 / 0.60 | 1.00 / 2.00 / 3.00 |
| VOLUMETRICFOG.Curve | 0.60 / 0.85 / 1.90 | 0.70 / 0.90 / 3.00 | 0.50 / 1.00 / 1.00 |
| VOLUMETRICFOG.LightingInfluence | 0.00 / 0.60 / 2.00 | 0.30 / 0.90 / 1.40 | 0.00 / 1.00 / 1.00 |
| VOLUMETRICFOG.Opacity | 0.00 / 0.80 / 1.00 | 0.00 / 0.10 / 0.90 | 0.00 / 1.00 / 1.00 |
| MIST.SkyLightingAmount | 0.90 / 1.35 / 4.00 | 0.75 / 1.85 / 2.40 | 1.00 / 1.00 / 1.00 |
| MIST.SunLightingAmount | 0.10 / 0.45 / 3.00 | 0.00 / 0.20 / 1.20 | 0.10 / 0.10 / 0.10 |
| MIST.Desaturation | 0.11 / 0.78 / 1.00 | 0.00 / 0.70 / 1.00 | 0.00 / 0.00 / 0.50 |
| MIST.VerticalOffset | -80.00 / -7.00 / 90.00 | -30.00 / 10.00 / 30.00 | -11.00 / -11.00 / -10.00 |
| MIST.Density | 1.00 / 1.60 / 6.00 | 1.10 / 2.00 / 5.00 | 1.00 / 1.50 / 2.00 |
| MIST.VerticalFade | 0.00 / 2.00 / 5.00 | 0.00 / 3.00 / 10.00 | 0.20 / 2.00 / 4.00 |
| MIST.BottomTop | 0.00 / 0.10 / 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 0.00 |
| MIST.ExponentialFade | 0.50 / 1.00 / 2.00 | 0.80 / 1.15 / 3.03 | 0.80 / 1.00 / 1.00 |
| MIST.DistanceFade | 0.00 / 1.00 / 15.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 0.00 |
| PROCEDURALSUN.GlowIntensity | 0.30 / 0.50 / 1.80 | 0.30 / 0.55 / 3.00 | 0.40 / 1.00 / 1.00 |
| PROCEDURALSUN.GlowCurve | 0.10 / 10.00 / 10.00 | 1.00 / 10.00 / 10.00 | 1.00 / 1.50 / 10.00 |
| PARTICLE.Intensity | 0.43 / 0.80 / 1.60 | 0.10 / 0.18 / 0.70 | 0.57 / 0.80 / 1.00 |
| PARTICLE.LightingInfluence | 0.10 / 0.70 / 1.20 | 0.20 / 0.90 / 1.80 | 0.40 / 0.50 / 1.00 |
| FIRE.Intensity | 0.60 / 0.60 / 7.00 | 1.00 / 1.00 / 4.00 | 2.20 / 2.20 / 3.00 |
| FIRE.Curve | 0.50 / 0.50 / 2.00 | 0.70 / 0.70 / 2.00 | 1.00 / 1.00 / 1.90 |
| LIGHTSPRITE.Intensity | 0.50 / 0.50 / 0.60 | 0.80 / 1.40 / 1.40 | 2.00 / 2.00 / 2.00 |
| LIGHTSPRITE.Curve | 1.00 / 1.00 / 1.00 | 1.31 / 1.31 / 1.31 | 1.90 / 1.90 / 1.90 |
| WINDOWLIGHT.Intensity | 0.10 / 0.50 / 0.50 | 0.10 / 1.13 / 1.13 | 0.70 / 10.00 / 16.00 |
| WINDOWLIGHT.Curve | 1.00 / 1.00 / 2.00 | 1.28 / 1.30 / 2.00 | 0.75 / 2.00 / 2.50 |
| GRASS.DirectionalMultiplier | 1.00 / 1.80 / 2.00 | 1.00 / 1.00 / 2.00 | 1.00 / 2.00 / 2.00 |
| GRASS.AmbientMultiplier | 1.00 / 2.00 / 2.50 | 1.00 / 1.00 / 2.00 | 1.00 / 3.00 / 3.00 |
| CLOUDSHADOWS.Opacity | 0.00 / 0.90 / 1.00 | 0.00 / 0.55 / 1.00 | 0.00 / 1.00 / 1.00 |

### Day values of the key mood settings for every referenced weather file


**Day**

| file | DirI | DirCrv | DirDes | AmbI | AmbCrv | AmbDes | AmbFlt | FogMul | FogCrv | ColPow | SkyGrad | Cloud | Sun | Bloom | SkyLMin | VolRay | MistDen | MistSky |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ClearWeather_marsh | 1.3 | 3.2 | 0.5 | 1.6 | 1.9 | 0.5 | 0.45 | 0.35 | 1.6 | 1.1 | 1.6 | 0.7 | 0.25 | 0.5 | 0.65 | 0.5 | 1.2 | 1 |
| ClearWeather_reach | 1.5 | 3.4 | 0.57 | 1.6 | 2 | 0.6 | 0.5 | 0.8 | 2 | 1.07 | 1.7 | 1 | 0.24 | 0.56 | 0.7 | 0.6 | 1.2 | 2 |
| CloudyWeather | 1.3 | 3 | 0.76 | 1.4 | 1.5 | 0.1 | 0.46 | 0.6 | 2.3 | 1.1 | 1.9 | 1.01 | 0.23 | 0.5 | 0.92 | 0.6 | 2 | 1.1 |
| RainyWeather | 1.3 | 1.3 | 0.7 | 1.8 | 2 | 0 | 0.4 | 0.7 | 2.1 | 1.06 | 1.7 | 0.9 | 0.3 | 0.5 | 0.9 | 2 | 1.4 | 1.1 |
| FoggyWeather | 1 | 1 | 0.6 | 1.4 | 1.3 | 0.3 | 0.29 | 0.77 | 1.4 | 1.1 | 2 | 1.4 | 0.3 | 0.5 | 0.9 | 1 | 4 | 0.98 |
| SnowyWeather | 1.3 | 1.4 | 0.9 | 1.5 | 2.3 | 0 | 0.35 | 0.72 | 1 | 1.02 | 1.9 | 1 | 0.32 | 0.5 | 0.8 | 2 | 2.5 | 1.5 |
| FoggyRiften | 1 | 1.3 | 0.6 | 1.6 | 1.3 | 0.3 | 0.29 | 0.77 | 1.4 | 1.1 | 2 | 1.4 | 0.2 | 0.6 | 0.9 | 1 | 3 | 0.9 |
| ClearWeather_snow | 1.5 | 3 | 0.5 | 1.5 | 2 | 0 | 0.4 | 0.58 | 2 | 1.07 | 1.7 | 0.9 | 0.2 | 0.54 | 0.86 | 0.3 | 1.2 | 1 |
| DLC02_Volcanicash | 1.3 | 1 | 0.2 | 1 | 2 | 0.4 | 0.47 | 0.4 | 1 | 1.1 | 1.2 | 0.8 | 1 | 0.6 | 0.7 | 1 | 1.8 | 1 |
| Blackreach | 0.3 | 0.8 | 1 | 0.42 | 1 | 0 | 0.15 | 0.6 | 0.6 | 1.1 | 2 | 0.8 | 0.35 | 0.65 | 0.6 | 1 | 4 | 0.9 |
| DA02 | 1.3 | 3 | 0.76 | 1.3 | 1.4 | 0.7 | 0.46 | 0.6 | 2.3 | 1.1 | 1.9 | 0.95 | 0.23 | 0.5 | 0.92 | 0.6 | 2 | 1.1 |
| SnowStorm | 1.2 | 3 | 0.6 | 1.5 | 1.7 | 0 | 0.4 | 0.7 | 4 | 1.1 | 1.7 | 1.1 | 0.3 | 0.5 | 0.9 | 1.4 | 5 | 1.1 |
| FoggyHeavy | 1 | 1 | 0.6 | 1.5 | 1.2 | 0.3 | 0.29 | 0.77 | 1.4 | 1.1 | 2 | 1.4 | 0.2 | 0.6 | 0.9 | 1 | 6 | 1 |
| RainStorm_heavy | 1.5 | 1.8 | 0.8 | 2.1 | 1.8 | 0 | 0.4 | 0.6 | 1.8 | 1.05 | 2 | 1.2 | 0.7 | 0.5 | 0.9 | 1.2 | 1.2 | 2 |
| DARKEND_RAIN | 0.7 | 1.7 | 0.43 | 0.42 | 1.5 | 0.1 | 0.24 | 0.3 | 0.7 | 1.1 | 1 | 1.2 | 1 | 0.7 | 0.76 | 1 | 3.5 | 2 |
| Rainy_clear | 1.5 | 2 | 0.6 | 1.7 | 2 | 0.5 | 0.38 | 0.4 | 3 | 1.05 | 1.4 | 0.76 | 0.28 | 0.5 | 0.7 | 2 | 1.5 | 1.4 |
| FoggyRain | 0.9 | 1 | 0.2 | 0.4 | 3 | 0.1 | 0.4 | 0.45 | 0.73 | 1.3 | 1.4 | 0.87 | 0.8 | 0.5 | 0.4 | 3 | 1.51 | 2 |
| ClearWeather_coast | 1.4 | 3.3 | 0.62 | 1.5 | 2 | 0.5 | 0.5 | 0.3 | 2 | 1.09 | 1.7 | 0.9 | 0.2 | 0.57 | 0.9 | 0.5 | 1.24 | 2.6 |
| ClearWeather_fallforest | 1.4 | 3.5 | 0.67 | 1.5 | 2 | 0.6 | 0.5 | 0.4 | 1 | 1.05 | 1.8 | 1 | 0.27 | 0.56 | 0.74 | 0.6 | 1.3 | 1.8 |
| ClearWeather__tundra | 1.5 | 3.6 | 0.6 | 1.7 | 2.2 | 0.3 | 0.52 | 0.16 | 1 | 1.07 | 1.7 | 0.8 | 0.27 | 0.6 | 0.7 | 0.4 | 1.3 | 2 |
| ClearWeather__pineforest | 1.5 | 3.2 | 0.64 | 1.6 | 2 | 0.4 | 0.5 | 0.8 | 2 | 1.08 | 1.8 | 1 | 0.24 | 0.5 | 0.7 | 0.5 | 1.2 | 2 |
| DARKEND | 0.5 | 0.9 | 1 | 0.35 | 0.1 | 0 | 0.24 | 0.89 | 0.6 | 1.1 | 1.5 | 1 | 0.03 | 0.9 | 0.6 | 1 | 3.9 | 1.2 |
| Overcast | 1.5 | 0.3 | 0.45 | 0.3 | 1.4 | 0.1 | 0.35 | 0.45 | 0.73 | 1 | 2 | 0.9 | 0.6 | 0.7 | 0.6 | 1 | 1.6 | 2 |
| CloudyWeather_coast | 1.4 | 3 | 0.76 | 1.3 | 2 | 0.6 | 0.46 | 0.7 | 1.6 | 1.1 | 1.9 | 0.96 | 0.23 | 0.5 | 0.92 | 0.6 | 2 | 1.1 |
| Dungeons | 1.5 | 3.4 | 0.3 | 1.7 | 2 | 0 | 0.5 | 0.5 | 1.6 | 1.1 | 1.8 | 1.4 | 0.24 | 0.5 | 0.7 | 0.5 | 1.4 | 1 |
| Summerset_Isle | 0.8 | 1.7 | 0.3 | 0.4 | 0.7 | 0.1 | 0.5 | 0.81 | 1.04 | 1.1 | 1.4 | 0.52 | 0.2 | 0.65 | 0.5 | 0.3 | 1 | 4 |
| Sovngarde | 0.3 | 0.8 | 1 | 0.35 | 0.1 | 0 | 0.24 | 0.6 | 0.6 | 1.1 | 1.4 | 0.8 | 0.2 | 0.7 | 0.6 | 1 | 4 | 2.4 |
| Overcast_dark_norain | 1.3 | 0.9 | 0.3 | 2 | 2 | 0 | 0.35 | 0.65 | 1.1 | 1.05 | 2 | 1.4 | 1 | 0.5 | 0.87 | 1.4 | 2.6 | 2 |
| ClearWeather_volcanictundra | 1.33 | 3.3 | 0.7 | 1.6 | 2.3 | 0.5 | 0.46 | 0.2 | 1.1 | 1.1 | 1.8 | 0.8 | 0.24 | 0.5 | 0.74 | 0.6 | 1.66 | 1.1 |
| Soulcairn | 1.3 | 2 | 0.4 | 1.5 | 2 | 0 | 0.36 | 1 | 2 | 1.1 | 1.6 | 0.9 | 1 | 0.5 | 0.5 | 3 | 5 | 2 |
| CloudyWeather_marsh | 1.4 | 3 | 0.76 | 1.3 | 2.3 | 0.6 | 0.46 | 0.7 | 1.6 | 1.11 | 1.9 | 0.96 | 0.23 | 0.5 | 0.76 | 0.6 | 2 | 1.1 |
| Dwarven_Ruins | 1.5 | 3.2 | 0.57 | 1.6 | 2 | 0.6 | 0.5 | 0.8 | 2 | 1.1 | 1.8 | 1 | 0.24 | 0.56 | 0.75 | 0.5 | 1.2 | 2 |
| ClearCloudy | 1.4 | 3 | 0.67 | 1.2 | 2.2 | 0.6 | 0.5 | 0.4 | 1 | 1.05 | 1.82 | 1 | 0.27 | 0.56 | 0.74 | 0.6 | 1.3 | 1.8 |
| CloudyDefault_Skyrim | 1.4 | 3 | 0.76 | 1.3 | 2 | 0.6 | 0.46 | 0.7 | 1.6 | 1.1 | 1.9 | 0.96 | 0.23 | 0.5 | 0.92 | 0.6 | 2 | 1.1 |
| ClearWeather_Tundra2 | 1.5 | 3.2 | 0.74 | 1.5 | 1.7 | 0.54 | 0.52 | 0.16 | 1 | 1.05 | 1.8 | 0.8 | 0.27 | 0.54 | 0.86 | 0.4 | 1.3 | 1.3 |
| Storm_Brewing | 1.5 | 0.3 | 0.45 | 0.3 | 1.4 | 0.1 | 0.35 | 0.45 | 0.73 | 1 | 2 | 0.9 | 0.6 | 0.7 | 0.6 | 1 | 1.6 | 2 |
| SnowDay | 0.3 | 0.8 | 1 | 0.63 | 2 | 0 | 0.3 | 0.6 | 0.6 | 1.1 | 2.2 | 0.8 | 0.35 | 0.9 | 1 | 1 | 2 | 1.5 |
| DLC02_Ash_Fall | 1.3 | 2 | 0.7 | 1.3 | 2 | 0 | 0.4 | 0.5 | 3 | 1.1 | 2 | 0.8 | 0.6 | 0.6 | 0.68 | 1 | 1.8 | 1.2 |
| MAP | 1 | 1.87 | 1 | 0.5 | 4 | 0.2 | 0.4 | 1.1 | 1 | 1.05 | 10 | 0.8 | 0.2 | 0.5 | 0.5 | 1 | 1.3 | 1.4 |
| FogWeathers | 1.3 | 0.9 | 0.6 | 1.5 | 2 | 0 | 0.29 | 0.77 | 1.4 | 1.1 | 1.8 | 1.4 | 0.2 | 0.6 | 0.8 | 1 | 3.4 | 1 |
| ClearWeather_Reach2 | 1.6 | 3.4 | 0.6 | 1.5 | 1.8 | 0.7 | 0.52 | 0.16 | 1 | 1.07 | 1.7 | 0.9 | 0.3 | 0.54 | 0.7 | 0.4 | 1.1 | 1 |
| Dungeons2 | 1.5 | 3.2 | 0.57 | 1.6 | 2 | 0.6 | 0.5 | 0.8 | 2 | 1.1 | 1.8 | 1 | 0.24 | 0.56 | 0.75 | 0.5 | 1.2 | 2 |
| Dimhollow_Crypt | 1.5 | 3.2 | 0.57 | 1.6 | 2 | 0.6 | 0.5 | 0.8 | 2 | 1.1 | 1.8 | 1 | 0.24 | 0.56 | 0.75 | 0.5 | 1.2 | 2 |
| Caves_Other | 1.5 | 3.2 | 0.57 | 1.6 | 2 | 0.6 | 0.5 | 0.8 | 2 | 1.1 | 1.8 | 1 | 0.24 | 0.56 | 0.75 | 0.5 | 1.2 | 2 |
| DLC02_Apocrypha | 0.3 | 0.8 | 1 | 0.42 | 1 | 0 | 0.15 | 0.6 | 0.6 | 1.1 | 2 | 0.8 | 0.35 | 0.7 | 0.6 | 1 | 4 | 0.9 |
| DLC01_Dawnguard | 1.6 | 3.6 | 0.5 | 1.5 | 2 | 0.2 | 0.52 | 0.16 | 1 | 1.1 | 1.7 | 0.8 | 0.3 | 0.5 | 0.7 | 0.4 | 1.1 | 1 |
| HelganAttack | 1.3 | 1.2 | 1 | 1.3 | 2 | 0 | 0.35 | 0.5 | 1 | 1.1 | 2 | 0.9 | 0.6 | 0.6 | 0.6 | 2 | 1.6 | 2 |
| DLC_DawnguardClear | 1.5 | 3.4 | 0.6 | 1.7 | 2 | 0.5 | 0.52 | 0.5 | 2 | 1.07 | 1.8 | 0.9 | 0.3 | 0.5 | 0.7 | 0.4 | 1 | 1 |
| DLC_DawnguardCloudy | 1.6 | 3.6 | 0.5 | 1.6 | 2 | 0.4 | 0.52 | 0.4 | 1 | 1.1 | 1.8 | 0.8 | 0.3 | 0.5 | 0.7 | 0.4 | 1.3 | 1.3 |
| DLC_DawnguardFalmerVall | 1.5 | 3.4 | 0.5 | 1.4 | 2 | 0.2 | 0.52 | 0.5 | 0.2 | 1.1 | 2 | 0.8 | 0.3 | 0.5 | 0.7 | 0.4 | 3 | 1.6 |

**Night**

| file | DirI | DirCrv | DirDes | AmbI | AmbCrv | AmbDes | AmbFlt | FogMul | FogCrv | ColPow | SkyGrad | Cloud | Sun | Bloom | SkyLMin | VolRay | MistDen | MistSky |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ClearWeather_marsh | 0.7 | 2 | 0.9 | 0.4 | 3 | 0 | 0.22 | 0.16 | 3 | 1.2 | 1.3 | 1 | 0 | 0.5 | 0.4 | 0.5 | 1.6 | 2.4 |
| ClearWeather_reach | 0.8 | 2 | 1 | 0.3 | 2.4 | 0.5 | 0.25 | 0.1 | 3.58 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| CloudyWeather | 0.8 | 2 | 0.8 | 0.3 | 3 | 1 | 0.25 | 0.25 | 2.4 | 1.1 | 2.5 | 1 | 1 | 0.6 | 0.4 | 0.5 | 1.7 | 2 |
| RainyWeather | 0.8 | 3 | 1 | 0.3 | 2 | 0.4 | 0.26 | 0.2 | 2 | 1.1 | 0.1 | 0.9 | 3 | 0.6 | 0.5 | 0 | 1.4 | 2 |
| FoggyWeather | 0.7 | 2.3 | 1 | 0.2 | 2 | 0.7 | 0.2 | 0.1 | 2 | 1.2 | 0.7 | 0.6 | 0.7 | 0.5 | 0.5 | 4 | 5 | 2.06 |
| SnowyWeather | 0.5 | 3 | 1 | 0.6 | 1.5 | 0 | 0.5 | 0.3 | 3 | 1.2 | 1.3 | 1.1 | 0.5 | 0.6 | 0.3 | 4 | 2.1 | 1.6 |
| FoggyRiften | 0.7 | 2 | 1 | 0.3 | 2 | 1 | 0.2 | 0.1 | 2 | 1.2 | 0.7 | 0.6 | 0.7 | 0.6 | 0.5 | 4 | 5 | 2.06 |
| ClearWeather_snow | 0.7 | 3 | 1 | 0.2 | 2 | 0 | 0.32 | 0.11 | 3.64 | 1.2 | 1.8 | 1 | 1 | 0.5 | 0.4 | 0.5 | 2.4 | 1.9 |
| DLC02_Volcanicash | 1 | 2 | 0.4 | 0.1 | 2 | 0.2 | 0.3 | 0.2 | 1 | 1.15 | 0.72 | 0.8 | 0.1 | 0.5 | 0.6 | 1 | 2 | 2 |
| Blackreach | 0.1 | 0.9 | 0.5 | 0.38 | 1 | 0 | 0.12 | 0.3 | 1 | 1.1 | 1 | 0.45 | 0.1 | 0.7 | 0.6 | 4 | 4 | 1 |
| DA02 | 0.8 | 1.9 | 0.8 | 0.5 | 2 | 1 | 0.25 | 0.25 | 2.4 | 1.1 | 2.5 | 1 | 1 | 0.6 | 0.4 | 0.5 | 1.7 | 2 |
| SnowStorm | 0.7 | 2 | 1 | 0.1 | 1 | 0 | 0.24 | 0.14 | 1.38 | 1.01 | 2 | 1 | 0.1 | 0.9 | 0.5 | 4 | 2.6 | 1.5 |
| FoggyHeavy | 0.9 | 2.4 | 0.6 | 0.3 | 2 | 1 | 0.2 | 0.1 | 2 | 1.2 | 0.7 | 0.6 | 0.7 | 0.6 | 0.5 | 4 | 5 | 2.06 |
| RainStorm_heavy | 0.8 | 3 | 1 | 0.2 | 5 | 0.4 | 0.26 | 0.2 | 2 | 1.2 | 0.1 | 0.9 | 3 | 0.6 | 0.4 | 4 | 1.4 | 1.2 |
| DARKEND_RAIN | 1.1 | 1.7 | 0 | 0.14 | 1.4 | 0 | 0.12 | 0.3 | 0.9 | 1.1 | 3 | 1.22 | 0.1 | 0.5 | 0.4 | 1 | 2 | 0.77 |
| Rainy_clear | 0.6 | 3 | 1 | 0.3 | 2.3 | 0.4 | 0.26 | 0.1 | 3 | 1.2 | 1.3 | 0.9 | 2 | 0.5 | 0.4 | 4 | 1.5 | 1 |
| FoggyRain | 0.9 | 2 | 1 | 0.2 | 5 | 1 | 0.2 | 0.3 | 2 | 1.2 | 2 | 1.1 | 0.1 | 0.6 | 0.5 | 2 | 1.1 | 0.75 |
| ClearWeather_coast | 0.8 | 3 | 1 | 0.3 | 4 | 0.8 | 0.24 | 0.2 | 3 | 1.2 | 1.3 | 1 | 1 | 0.5 | 0.5 | 0.5 | 1.7 | 1.6 |
| ClearWeather_fallforest | 0.5 | 1.3 | 1 | 0.11 | 1.9 | 0.3 | 0.27 | 0.1 | 3 | 1.1 | 1.1 | 1 | 0.8 | 0.6 | 0.5 | 0.5 | 1.4 | 2 |
| ClearWeather__tundra | 0.7 | 2 | 1 | 0.3 | 2 | 0.5 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 0.94 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |
| ClearWeather__pineforest | 0.8 | 2 | 1 | 0.3 | 3 | 0.5 | 0.25 | 0.1 | 4 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| DARKEND | 0.7 | 1 | 0.5 | 0.4 | 2 | 1 | 0.15 | 0.2 | 0.61 | 1.1 | 1 | 1 | 0.2 | 0.5 | 0.7 | 4 | 5 | 2.2 |
| Overcast | 0.7 | 1.9 | 0.1 | 0.4 | 3 | 0 | 0.2 | 0.3 | 0.9 | 1.1 | 3 | 1.2 | 0.1 | 0.5 | 0.5 | 1 | 2.1 | 1.4 |
| CloudyWeather_coast | 0.8 | 1.9 | 0.8 | 0.5 | 1.6 | 1 | 0.25 | 0.25 | 2.4 | 1.1 | 2.5 | 1 | 1 | 0.6 | 0.4 | 0.5 | 1.7 | 2 |
| Dungeons | 0.8 | 2 | 1 | 0.3 | 2.4 | 0.5 | 0.25 | 0.1 | 3.58 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| Summerset_Isle | 1 | 3 | 0.7 | 0 | 1.2 | 0.1 | 0.05 | 0.08 | 2 | 1.15 | 3.1 | 1.29 | 1 | 0.7 | 0.4 | 0.5 | 3 | 1.8 |
| Sovngarde | 0.5 | 1 | 0.5 | 0.05 | 2 | 1 | 0.2 | 0.2 | 0.61 | 1.1 | 1 | 0.5 | 0.1 | 0.5 | 0.6 | 4 | 5 | 2 |
| Overcast_dark_norain | 0.7 | 2 | 0.1 | 0.5 | 2 | 0 | 0.2 | 0.3 | 1 | 1.05 | 2 | 1 | 0.1 | 0.5 | 0.6 | 1 | 1.8 | 1.3 |
| ClearWeather_volcanictundra | 0.9 | 2.7 | 1 | 0.2 | 2 | 0.3 | 0.09 | 0.1 | 2 | 1.2 | 1.5 | 1.1 | 1 | 0.6 | 0.5 | 0.5 | 2.8 | 1 |
| Soulcairn | 0.9 | 2 | 0.4 | 1 | 2 | 0 | 0.3 | 0.4 | 4 | 1.2 | 1.4 | 0.7 | 0.1 | 0.6 | 0.4 | 4 | 3 | 1 |
| CloudyWeather_marsh | 0.8 | 1.9 | 0.8 | 0.5 | 1.6 | 1 | 0.25 | 0.25 | 2.4 | 1.1 | 2.5 | 1 | 1 | 0.6 | 0.4 | 0.5 | 1.7 | 2 |
| Dwarven_Ruins | 0.8 | 2 | 1 | 0.3 | 2.4 | 0.5 | 0.25 | 0.1 | 3.58 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| ClearCloudy | 0.5 | 1.3 | 1 | 0.11 | 1.9 | 0.3 | 0.27 | 0.1 | 3 | 1.1 | 1.1 | 1 | 0.8 | 0.6 | 0.5 | 0.5 | 1.4 | 2 |
| CloudyDefault_Skyrim | 0.8 | 1.9 | 0.8 | 0.5 | 1.6 | 1 | 0.25 | 0.25 | 2.4 | 1.1 | 2.5 | 1 | 1 | 0.6 | 0.4 | 0.5 | 1.7 | 2 |
| ClearWeather_Tundra2 | 0.8 | 2 | 0.9 | 0.2 | 2 | 0.6 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 1 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |
| Storm_Brewing | 0.7 | 1.9 | 0.1 | 0.4 | 3 | 0 | 0.2 | 0.3 | 0.9 | 1.1 | 3 | 1.2 | 0.1 | 0.5 | 0.5 | 1 | 2.1 | 1.4 |
| SnowDay | 0.7 | 1.6 | 0.5 | 0.22 | 1.6 | 0 | 0.16 | 0.3 | 0.83 | 1.1 | 0.6 | 1.26 | 1 | 0.7 | 0.6 | 4 | 4 | 1 |
| DLC02_Ash_Fall | 0.8 | 2.7 | 1 | 0.2 | 2.4 | 0.4 | 0.26 | 0.2 | 2 | 1.15 | 0.1 | 0.9 | 2 | 0.7 | 0.6 | 4 | 1.5 | 2 |
| MAP | 0.9 | 1 | 1 | 0.1 | 2 | 1 | 0.25 | 1 | 1 | 1.1 | 10 | 1 | 1 | 0.5 | 0.4 | 0.5 | 1.5 | 1.3 |
| FogWeathers | 0.7 | 2 | 1 | 0.3 | 2 | 0.8 | 0.2 | 0.1 | 2 | 1.2 | 0.7 | 0.6 | 0.7 | 0.6 | 0.5 | 4 | 5 | 2.06 |
| ClearWeather_Reach2 | 0.8 | 2 | 0.9 | 0.2 | 2 | 0.6 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 1 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |
| Dungeons2 | 0.8 | 2 | 1 | 0.3 | 2.4 | 0.5 | 0.25 | 0.1 | 3.58 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| Dimhollow_Crypt | 0.8 | 2 | 1 | 0.3 | 2.4 | 0.5 | 0.25 | 0.1 | 3.58 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| Caves_Other | 0.8 | 2 | 1 | 0.3 | 2 | 0.5 | 0.25 | 0.1 | 3.58 | 1.2 | 1.6 | 1 | 2 | 0.5 | 0.4 | 1 | 1.39 | 2 |
| DLC02_Apocrypha | 0.1 | 0.9 | 0.5 | 0.38 | 1 | 0 | 0.12 | 0.3 | 1 | 1.1 | 1 | 0.45 | 0.1 | 0.5 | 0.6 | 4 | 4 | 1 |
| DLC01_Dawnguard | 0.8 | 2 | 0.9 | 0.2 | 2 | 0.6 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 1 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |
| HelganAttack | 0.7 | 1.9 | 0.1 | 0.3 | 2 | 0 | 0.2 | 0.3 | 0.9 | 1.1 | 3 | 1.2 | 0.1 | 0.5 | 0.4 | 1 | 2.1 | 1.4 |
| DLC_DawnguardClear | 0.8 | 2 | 0.9 | 0.2 | 2 | 0.6 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 1 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |
| DLC_DawnguardCloudy | 0.8 | 2 | 0.9 | 0.2 | 2 | 0.6 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 1 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |
| DLC_DawnguardFalmerVall | 0.8 | 2 | 0.9 | 0.2 | 2 | 0.6 | 0.3 | 0.02 | 4 | 1.2 | 1.6 | 1 | 1 | 0.5 | 0.4 | 0.99 | 2 | 1.3 |

### Representative weathers side by side: Day

| section.key | global | ClearTundra | ClearPine | Overcast | Foggy | RainStormHeavy |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 0.4 | 1.5 | 1.5 | 1.5 | 1 | 1.5 |
| ENVIRONMENT.DirectLightingCurve | 1 | 3.6 | 3.2 | 0.3 | 1 | 1.8 |
| ENVIRONMENT.DirectLightingDesaturation | 0.22 | 0.6 | 0.64 | 0.45 | 0.6 | 0.8 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.5 | 0.64 | 0.6 | 0.5 | 0.7 |
| ENVIRONMENT.DirectLightingColorFilter | (0.83,0.89,0.90) | (0.90,0.93,0.96) | (0.91,0.92,0.93) | (0.69,0.76,0.80) | (0.78,0.81,0.82) | (0.77,0.85,0.91) |
| ENVIRONMENT.AmbientLightingIntensity | 0.4 | 1.7 | 1.6 | 0.3 | 1.4 | 2.1 |
| ENVIRONMENT.AmbientLightingCurve | 1.1 | 2.2 | 2 | 1.4 | 1.3 | 1.8 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.3 | 0.3 | 0.4 | 0.1 | 0.3 | 0 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.35 | 0.52 | 0.5 | 0.35 | 0.29 | 0.4 |
| ENVIRONMENT.AmbientColorFilterTop | (0.94,0.94,0.91) | (0.51,0.74,0.82) | (0.54,0.80,0.87) | (0.78,0.89,0.94) | (0.58,0.75,0.83) | (0.40,0.64,0.74) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.23,0.33,0.38) | (0.67,0.60,0.51) | (0.70,0.63,0.55) | (0.33,0.30,0.17) | (0.50,0.47,0.44) | (0.61,0.51,0.41) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.20,0.40,0.46) | (0.17,0.37,0.46) | (0.22,0.36,0.43) | (0.31,0.51,0.58) | (0.34,0.53,0.60) | (0.21,0.41,0.49) |
| ENVIRONMENT.SpecularAmountMultiplier | 2.2 | 0.6 | 1 | 3 | 0.7 | 2.7 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.24 | 3 | 3 | 22 | 0.5 | 7 |
| ENVIRONMENT.SpecularFromLight | 0 | 0.3 | 0.3 | 0.3 | 0.1 | 0.4 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 |
| ENVIRONMENT.PointLightingCurve | 1.25 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 |
| ENVIRONMENT.PointLightingDesaturation | 0 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| ENVIRONMENT.ParticleLightsIntensity | 0.6 | 0.6 | 0.6 | 1 | 0.6 | 0.6 |
| ENVIRONMENT.FogColorMultiplier | 0.6 | 0.16 | 0.8 | 0.45 | 0.77 | 0.6 |
| ENVIRONMENT.FogColorCurve | 1.4 | 1 | 2 | 0.73 | 1.4 | 1.8 |
| ENVIRONMENT.FogColorFilterAmount | 0.5 | 0.5 | 0.64 | 0.2 | 0.43 | 0.5 |
| ENVIRONMENT.FogColorFilter | (0.39,0.39,0.39) | (0.41,0.56,0.63) | (0.75,0.93,1.00) | (0.48,0.59,0.62) | (0.53,0.58,0.62) | (0.75,0.80,0.82) |
| ENVIRONMENT.ColorPow | 1.1 | 1.07 | 1.08 | 1 | 1.1 | 1.05 |
| SKY.GradientIntensity | 1.33 | 1.7 | 1.8 | 2 | 2 | 2 |
| SKY.GradientDesaturation | 1 | 0.4 | 0.5 | 0.7 | 0.5 | 0.4 |
| SKY.GradientTopIntensity | 0.8 | 0.7 | 0.8 | 0.75 | 1 | 1 |
| SKY.GradientTopCurve | 1.2 | 0.8 | 0.83 | 1.2 | 1.2 | 2 |
| SKY.GradientTopColorFilter | (0.55,0.55,0.55) | (0.22,0.55,0.67) | (0.05,0.55,0.72) | (0.46,0.62,0.69) | (0.68,0.85,0.99) | (0.47,0.60,0.73) |
| SKY.GradientMiddleIntensity | 0.7 | 0.9 | 0.9 | 1 | 0.8 | 1.1 |
| SKY.GradientMiddleCurve | 1.15 | 1 | 0.8 | 1 | 1 | 0.9 |
| SKY.GradientMiddleColorFilter | (0.56,0.56,0.56) | (0.31,0.61,0.72) | (0.41,0.65,0.80) | (0.72,0.82,0.97) | (0.79,0.88,0.93) | (0.31,0.47,0.58) |
| SKY.GradientHorizonIntensity | 0.8 | 0.8 | 0.8 | 0.7 | 0.8 | 1 |
| SKY.GradientHorizonCurve | 0.74 | 1 | 0.5 | 3 | 2 | 0.6 |
| SKY.GradientHorizonColorFilter | (1.00,1.00,1.00) | (0.37,0.57,0.67) | (0.34,0.58,0.69) | (0.67,0.74,0.74) | (0.79,0.95,1.00) | (0.72,0.80,0.84) |
| SKY.SunIntensity | 0.2 | 0.27 | 0.24 | 0.6 | 0.3 | 0.7 |
| SKY.SunDesaturation | 1 | 0.6 | 0.7 | 1 | 1 | 1 |
| SKY.SunColorFilter | (1.00,0.98,0.80) | (0.89,0.92,0.93) | (0.92,0.95,0.97) | (0.79,0.89,0.93) | (0.87,0.91,0.94) | (0.89,0.93,0.94) |
| SKY.SunGlowIntensity | 3 | 2 | 2 | 10 | 5 | 10 |
| SKY.SunGlowHaziness | 0.1 | 0.12 | 0.14 | 0 | 0.3 | 0.2 |
| SKY.CloudsIntensity | 0.75 | 0.8 | 1 | 0.9 | 1.4 | 1.2 |
| SKY.CloudsCurve | 2.5 | 2.8 | 1.2 | 5 | 2 | 1.4 |
| SKY.CloudsDesaturation | 0.6 | 1 | 1 | 0.7 | 0.3 | 0.6 |
| SKY.CloudsOpacity | 1.06 | 1.2 | 1.3 | 0.7 | 1.3 | 0.9 |
| SKY.CloudsColorFilter | (1.00,1.00,1.00) | (0.67,0.74,0.78) | (0.75,0.82,0.87) | (0.74,0.84,0.88) | (0.71,0.88,0.99) | (0.83,0.88,0.93) |
| SKY.MoonIntensity | 0.3 | 0.2 | 0.3 | 1 | 1 | 0.3 |
| BLOOM.Amount | 0.6 | 0.6 | 0.5 | 0.7 | 0.5 | 0.5 |
| BLOOM.BlueShiftAmount | 1.5 | 3 | 3 | 3 | 4 | 3 |
| SKYLIGHTING.AmbientMinLevel | 0.6 | 0.7 | 0.7 | 0.6 | 0.9 | 0.9 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.26 | 0.29 | 0.25 | 0.3 | 0.15 | 0.17 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.35 | 0.37 | 0.4 | 0.2 | 0.2 | 0.2 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 2.8 | 1.3 | 1.3 | 1.5 | 1.4 | 3 |
| AUTOAMBIENT.BlendingAmount | 0.7 | 0.5 | 0.5 | 0.8 | 1 | 0.5 |
| AUTOAMBIENT.TopIntensity | 0.6 | 0.6 | 0.7 | 1 | 0.7 | 0.6 |
| AUTOAMBIENT.BottomIntensity | 0.5 | 0.45 | 0.46 | 1 | 0.9 | 0.7 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.4 | 0.3 | 1.4 | 0 | 1 |
| RAYS.SunRaysMultiplier | 0.8 | 0.4 | 0.5 | 8 | 16 | 1 |
| VOLUMETRICRAYS.Intensity | 0.5 | 0.4 | 0.5 | 1 | 1 | 1.2 |
| VOLUMETRICRAYS.Density | 1.9 | 3 | 4 | 1.3 | 1.3 | 1 |
| VOLUMETRICRAYS.SkyColorAmount | 0.6 | 1 | 0.3 | 0.5 | 0.5 | 1 |
| VOLUMETRICFOG.Intensity | 0.7 | 0.8 | 0.8 | 0.4 | 1.2 | 0.76 |
| VOLUMETRICFOG.Curve | 0.53 | 1 | 0.9 | 1.9 | 1 | 0.7 |
| VOLUMETRICFOG.LightingInfluence | 0.9 | 1.2 | 1 | 0.18 | 0.6 | 0.74 |
| VOLUMETRICFOG.Opacity | 1 | 0.9 | 0.9 | 0 | 0.1 | 0.8 |
| MIST.SkyLightingAmount | 3 | 2 | 2 | 2 | 0.98 | 2 |
| MIST.SunLightingAmount | 0.6 | 2 | 0.1 | 0.3 | 0.3 | 0.6 |
| MIST.Desaturation | 1 | 0.6 | 0.4 | 0.8 | 0.8 | 0.9 |
| MIST.ColorFilter | (0.80,0.91,0.93) | (0.75,0.86,0.89) | (0.58,0.70,0.75) | (0.71,0.81,0.85) | (0.69,0.76,0.78) | (0.73,0.77,0.80) |
| MIST.VerticalOffset | 10 | -16 | 90 | 10 | -7 | 10 |
| MIST.Density | 1.4 | 1.3 | 1.2 | 1.6 | 4 | 1.2 |
| MIST.VerticalFade | 10 | 3 | 1 | 0.5 | 2 | 0 |
| MIST.BottomTop | 0.8 | 0.5 | 0.2 | 1 | 0 | 0 |
| MIST.ExponentialFade | 1 | 0.5 | 1 | 1 | 1.02 | 1.2 |
| MIST.DistanceFade | 0 | 0.6 | 2 | 0.1 | 3 | 1 |
| PROCEDURALSUN.GlowIntensity | 1.5 | 0.4 | 0.4 | 0.6 | 1 | 0.8 |
| PROCEDURALSUN.GlowCurve | 0.06 | 5 | 7 | 10 | 10 | 10 |
| PARTICLE.Intensity | 0.7 | 0.8 | 0.9 | 0.7 | 0.8 | 0.9 |
| PARTICLE.LightingInfluence | 0.55 | 0.8 | 0.9 | 0.1 | 0.1 | 0.4 |
| FIRE.Intensity | 6 | 0.6 | 0.6 | 0.6 | 0.6 | 0.6 |
| FIRE.Curve | 2 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| LIGHTSPRITE.Intensity | 1 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| LIGHTSPRITE.Curve | 4 | 1 | 1 | 1 | 1 | 1 |
| WINDOWLIGHT.Intensity | 0.4 | 0.5 | 0.5 | 0.1 | 0.5 | 0.1 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 2 | 1 | 2 |
| GRASS.DirectionalMultiplier | 1 | 2 | 2 | 2 | 1.8 | 2 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 2 | 1.5 | 2 |
| CLOUDSHADOWS.Opacity | 1 | 1 | 1 | 0.8 | 1 | 1 |

### Representative weathers side by side: Night

| section.key | global | ClearTundra | ClearPine | Overcast | Foggy | RainStormHeavy |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1 | 0.7 | 0.8 | 0.7 | 0.7 | 0.8 |
| ENVIRONMENT.DirectLightingCurve | 2 | 2 | 2 | 1.9 | 2.3 | 3 |
| ENVIRONMENT.DirectLightingDesaturation | 0 | 1 | 1 | 0.1 | 1 | 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.38 | 0.66 | 0.6 | 1 | 0.6 | 0.7 |
| ENVIRONMENT.DirectLightingColorFilter | (0.10,0.25,0.32) | (0.17,0.29,0.38) | (0.22,0.38,0.49) | (0.00,0.23,0.39) | (0.23,0.44,0.60) | (0.18,0.34,0.42) |
| ENVIRONMENT.AmbientLightingIntensity | 0 | 0.3 | 0.3 | 0.4 | 0.2 | 0.2 |
| ENVIRONMENT.AmbientLightingCurve | 1.3 | 2 | 3 | 3 | 2 | 5 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.7 | 0.5 | 0.5 | 0 | 0.7 | 0.4 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.12 | 0.3 | 0.25 | 0.2 | 0.2 | 0.26 |
| ENVIRONMENT.AmbientColorFilterTop | (0.11,0.34,0.58) | (0.09,0.27,0.34) | (0.13,0.29,0.38) | (0.13,0.48,0.66) | (0.16,0.39,0.47) | (0.14,0.32,0.40) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.11,0.48,0.78) | (0.19,0.38,0.46) | (0.25,0.39,0.45) | (0.14,0.27,0.33) | (0.11,0.34,0.44) | (0.11,0.23,0.28) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.19,0.36,0.43) | (0.13,0.31,0.39) | (0.27,0.41,0.51) | (0.09,0.49,0.70) | (0.14,0.42,0.55) | (0.13,0.28,0.35) |
| ENVIRONMENT.SpecularAmountMultiplier | 1.26 | 0.6 | 1 | 4 | 0.7 | 3 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.16 | 3 | 3 | 22 | 0.8 | 7 |
| ENVIRONMENT.SpecularFromLight | 0.1 | 0.8 | 0.8 | 0.6 | 0.13 | 0.6 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| ENVIRONMENT.PointLightingCurve | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 |
| ENVIRONMENT.PointLightingDesaturation | 0 | 0.1 | 0.1 | 0.1 | 0.4 | 0.1 |
| ENVIRONMENT.ParticleLightsIntensity | 0.25 | 0.25 | 0.25 | 0.9 | 0.4 | 0.7 |
| ENVIRONMENT.FogColorMultiplier | 0.34 | 0.02 | 0.1 | 0.3 | 0.1 | 0.2 |
| ENVIRONMENT.FogColorCurve | 1.2 | 4 | 4 | 0.9 | 2 | 2 |
| ENVIRONMENT.FogColorFilterAmount | 0.63 | 0.1 | 0.12 | 0 | 0.1 | 0 |
| ENVIRONMENT.FogColorFilter | (0.24,0.44,0.55) | (0.24,0.44,0.55) | (0.14,0.26,0.36) | (0.16,0.31,0.36) | (0.28,0.38,0.46) | (0.27,0.36,0.51) |
| ENVIRONMENT.ColorPow | 1.1 | 1.2 | 1.2 | 1.1 | 1.2 | 1.2 |
| SKY.GradientIntensity | 3.2 | 1.6 | 1.6 | 3 | 0.7 | 0.1 |
| SKY.GradientDesaturation | 0 | 0.5 | 0.5 | 0.33 | 0.4 | 0 |
| SKY.GradientTopIntensity | 0.04 | 0.03 | 0.01 | 1 | 0.03 | 0.2 |
| SKY.GradientTopCurve | 0 | 0 | 0 | 1.1 | 0 | 0 |
| SKY.GradientTopColorFilter | (0.03,0.21,0.36) | (0.02,0.22,0.29) | (0.13,0.42,0.54) | (0.14,0.27,0.33) | (0.10,0.40,1.00) | (0.14,0.23,0.26) |
| SKY.GradientMiddleIntensity | 0.07 | 0.14 | 0.06 | 0.6 | 0.1 | 0.2 |
| SKY.GradientMiddleCurve | 0 | 0 | 0 | 1.05 | 0 | 0 |
| SKY.GradientMiddleColorFilter | (0.03,0.34,0.48) | (0.11,0.23,0.34) | (0.09,0.46,0.59) | (0.02,0.26,0.34) | (0.35,0.60,0.85) | (0.23,0.34,0.40) |
| SKY.GradientHorizonIntensity | 0.14 | 0.02 | 0 | 0.8 | 0.03 | 0.03 |
| SKY.GradientHorizonCurve | 0 | 0 | 0 | 0.6 | 0 | 0 |
| SKY.GradientHorizonColorFilter | (0.08,0.32,0.44) | (0.31,0.35,0.42) | (0.07,0.27,0.66) | (0.51,0.70,0.79) | (0.40,0.75,0.93) | (0.22,0.35,0.41) |
| SKY.SunIntensity | 1 | 1 | 2 | 0.1 | 0.7 | 3 |
| SKY.SunDesaturation | 0 | 1 | 1 | 1 | 1 | 1 |
| SKY.SunColorFilter | (0.24,0.44,0.55) | (0.19,0.49,0.62) | (0.60,0.62,0.63) | (1.00,1.00,1.00) | (0.06,0.37,0.49) | (0.19,0.49,0.62) |
| SKY.SunGlowIntensity | 2 | 10 | 10 | 10 | 1 | 10 |
| SKY.SunGlowHaziness | 0 | 0 | 0 | 0 | 0 | 0 |
| SKY.CloudsIntensity | 0.4 | 0.94 | 1 | 1.2 | 0.6 | 0.9 |
| SKY.CloudsCurve | 1 | 3 | 3 | 3 | 2 | 8 |
| SKY.CloudsDesaturation | 0.21 | 0.9 | 0.9 | 0.1 | 0 | 1 |
| SKY.CloudsOpacity | 1.21 | 2 | 1.3 | 0.9 | 0.8 | 0.87 |
| SKY.CloudsColorFilter | (0.35,0.69,0.85) | (0.22,0.32,0.43) | (0.30,0.44,0.57) | (0.19,0.37,0.43) | (0.52,0.67,0.77) | (0.21,0.36,0.46) |
| SKY.MoonIntensity | 4 | 2.4 | 3 | 1.6 | 3 | 3 |
| BLOOM.Amount | 0.8 | 0.5 | 0.5 | 0.5 | 0.5 | 0.6 |
| BLOOM.BlueShiftAmount | 0.96 | 2 | 2 | 2 | 2 | 2 |
| SKYLIGHTING.AmbientMinLevel | 0.6 | 0.4 | 0.4 | 0.5 | 0.5 | 0.4 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.4 | 0.1 | 0.1 | 0.28 | 0.2 | 0 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.6 | 0.14 | 0 | 0.3 | 0.2 | 0.2 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 0.9 | 2 | 1 | 2 | 2 | 2.7 |
| AUTOAMBIENT.BlendingAmount | 0.6 | 0.9 | 0.6 | 0.7 | 0.4 | 0.6 |
| AUTOAMBIENT.TopIntensity | 0.5 | 1 | 1 | 1 | 1 | 1 |
| AUTOAMBIENT.BottomIntensity | 0.5 | 0.6 | 0.4 | 1 | 0.7 | 0.5 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.9 | 0.9 | 0.9 | 0.9 | 0.9 |
| RAYS.SunRaysMultiplier | 2 | 2 | 2 | 0.4 | 0.1 | 1 |
| VOLUMETRICRAYS.Intensity | 1 | 0.99 | 1 | 1 | 4 | 4 |
| VOLUMETRICRAYS.Density | 1 | 1.5 | 2 | 1 | 1 | 1.3 |
| VOLUMETRICRAYS.SkyColorAmount | 1 | 0.5 | 1 | 0.5 | 0.5 | 0.5 |
| VOLUMETRICFOG.Intensity | 0.23 | 0.16 | 0.13 | 0.19 | 0.6 | 0.3 |
| VOLUMETRICFOG.Curve | 0.57 | 1 | 0.8 | 0.9 | 0.9 | 2 |
| VOLUMETRICFOG.LightingInfluence | 0.9 | 0.83 | 0.3 | 0.9 | 1 | 1 |
| VOLUMETRICFOG.Opacity | 0 | 0.5 | 0 | 0 | 0.1 | 0.4 |
| MIST.SkyLightingAmount | 1.8 | 1.3 | 2 | 1.4 | 2.06 | 1.2 |
| MIST.SunLightingAmount | 0 | 0 | 0.6 | 0.2 | 0.2 | 0 |
| MIST.Desaturation | 0.8 | 0.8 | 0.8 | 0.6 | 0.7 | 0.8 |
| MIST.ColorFilter | (0.13,0.43,0.57) | (0.08,0.28,0.36) | (0.18,0.37,0.49) | (0.18,0.28,0.37) | (0.38,0.44,0.47) | (0.21,0.40,0.49) |
| MIST.VerticalOffset | -30 | 10 | -20 | 30 | 10 | 12 |
| MIST.Density | 1.8 | 2 | 1.39 | 2.1 | 5 | 1.4 |
| MIST.VerticalFade | 1.7 | 4 | 0 | 0 | 2 | 3 |
| MIST.BottomTop | 1 | 1 | 1 | 0 | 0 | 0 |
| MIST.ExponentialFade | 1.8 | 1.85 | 1.1 | 0.8 | 1.15 | 1.2 |
| MIST.DistanceFade | 0 | 0 | 0.2 | 1 | 0 | 0 |
| PROCEDURALSUN.GlowIntensity | 3 | 0.6 | 3 | 0.5 | 0.4 | 3 |
| PROCEDURALSUN.GlowCurve | 1 | 3 | 5 | 10 | 10 | 10 |
| PARTICLE.Intensity | 0.4 | 0.2 | 0.18 | 0.32 | 0.18 | 0.1 |
| PARTICLE.LightingInfluence | 1.4 | 0.9 | 1 | 0.65 | 0.81 | 0.7 |
| FIRE.Intensity | 2 | 1 | 1 | 1 | 1 | 1 |
| FIRE.Curve | 1.6 | 0.7 | 0.7 | 0.7 | 0.7 | 0.7 |
| LIGHTSPRITE.Intensity | 1.3 | 1.4 | 1.4 | 0.8 | 1.4 | 1.4 |
| LIGHTSPRITE.Curve | 3 | 1.31 | 1.31 | 1.31 | 1.31 | 1.31 |
| WINDOWLIGHT.Intensity | 0.8 | 1.13 | 1.13 | 0.1 | 1.13 | 0.1 |
| WINDOWLIGHT.Curve | 1.3 | 1.3 | 1.3 | 2 | 1.28 | 2 |
| GRASS.DirectionalMultiplier | 1 | 1 | 1 | 2 | 1 | 1 |
| GRASS.AmbientMultiplier | 1 | 1 | 1 | 2 | 1 | 1 |
| CLOUDSHADOWS.Opacity | 1 | 1 | 1 | 0.5 | 0.8 | 0.2 |

### Representative weathers side by side: Sunset

| section.key | global | ClearTundra | ClearPine | Overcast | Foggy | RainStormHeavy |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 0.24 | 1.4 | 1.4 | 1.3 | 1.3 | 1.4 |
| ENVIRONMENT.DirectLightingCurve | 1 | 3.1 | 3.6 | 1 | 1 | 1.3 |
| ENVIRONMENT.DirectLightingDesaturation | 0.18 | 0.4 | 0.36 | 0.5 | 0.6 | 0.7 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 | 0.6 | 0.6 | 0.7 | 0.6 | 0.7 |
| ENVIRONMENT.DirectLightingColorFilter | (0.68,0.75,0.77) | (0.92,0.70,0.46) | (0.74,0.58,0.41) | (0.55,0.65,0.70) | (0.82,0.74,0.63) | (0.93,0.64,0.46) |
| ENVIRONMENT.AmbientLightingIntensity | 0.32 | 1.5 | 1.4 | 0.2 | 1.1 | 2 |
| ENVIRONMENT.AmbientLightingCurve | 1.35 | 2.3 | 2.2 | 1.4 | 1.6 | 1.8 |
| ENVIRONMENT.AmbientLightingDesaturation | 0.24 | 0.1 | 0.2 | 0.4 | 0.4 | 0 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.3 | 0.43 | 0.4 | 0.3 | 0.24 | 0.35 |
| ENVIRONMENT.AmbientColorFilterTop | (0.78,0.83,0.83) | (0.43,0.65,0.75) | (0.09,0.42,0.58) | (0.70,0.78,0.82) | (0.35,0.68,0.78) | (0.34,0.49,0.55) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.23,0.40,0.45) | (0.61,0.51,0.41) | (0.49,0.42,0.31) | (0.24,0.31,0.33) | (0.58,0.56,0.51) | (0.53,0.43,0.33) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.41,0.53,0.59) | (0.14,0.28,0.33) | (0.00,0.32,0.52) | (0.18,0.30,0.35) | (0.23,0.43,0.49) | (0.20,0.31,0.35) |
| ENVIRONMENT.SpecularAmountMultiplier | 2.1 | 0.6 | 1 | 3 | 0.7 | 2.5 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.3 | 3 | 3 | 22 | 0.6 | 7 |
| ENVIRONMENT.SpecularFromLight | 0.12 | 0.4 | 0.4 | 0.4 | 0.1 | 0.4 |
| ENVIRONMENT.PointLightingIntensity | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 |
| ENVIRONMENT.PointLightingCurve | 1.25 | 1.2 | 1.2 | 1.2 | 1.2 | 1.2 |
| ENVIRONMENT.PointLightingDesaturation | 0 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| ENVIRONMENT.ParticleLightsIntensity | 0.6 | 0.6 | 0.6 | 1 | 0.6 | 0.6 |
| ENVIRONMENT.FogColorMultiplier | 0.5 | 0.29 | 0.5 | 0.3 | 0.58 | 0.5 |
| ENVIRONMENT.FogColorCurve | 1.3 | 0.64 | 1.3 | 1.2 | 1 | 1.9 |
| ENVIRONMENT.FogColorFilterAmount | 0.5 | 0.64 | 0.5 | 0.2 | 0.34 | 0.3 |
| ENVIRONMENT.FogColorFilter | (0.83,0.95,0.98) | (0.26,0.33,0.39) | (0.80,0.71,0.54) | (0.42,0.49,0.53) | (0.87,0.78,0.62) | (0.64,0.69,0.77) |
| ENVIRONMENT.ColorPow | 1.05 | 1.04 | 1.1 | 1.05 | 1.08 | 1.08 |
| SKY.GradientIntensity | 1.45 | 1.8 | 1.5 | 1.73 | 1.7 | 2 |
| SKY.GradientDesaturation | 0.16 | 0.4 | 0.4 | 0.3 | 0.4 | 0.6 |
| SKY.GradientTopIntensity | 0.6 | 0.7 | 0.8 | 1 | 0.8 | 0.7 |
| SKY.GradientTopCurve | 1.3 | 0.8 | 0.5 | 1.1 | 1.1 | 2 |
| SKY.GradientTopColorFilter | (0.47,0.47,0.47) | (0.28,0.64,0.74) | (0.20,0.55,0.76) | (0.29,0.43,0.50) | (0.59,0.78,0.88) | (0.36,0.49,0.57) |
| SKY.GradientMiddleIntensity | 0.45 | 0.9 | 0.8 | 0.92 | 0.8 | 1.3 |
| SKY.GradientMiddleCurve | 1.2 | 0.7 | 0.7 | 1.2 | 1.2 | 1 |
| SKY.GradientMiddleColorFilter | (0.70,0.70,0.70) | (0.33,0.73,0.70) | (0.44,0.73,0.73) | (0.42,0.61,0.67) | (0.59,0.70,0.77) | (0.48,0.68,0.69) |
| SKY.GradientHorizonIntensity | 0.75 | 0.8 | 0.9 | 0.6 | 0.8 | 0.8 |
| SKY.GradientHorizonCurve | 1.6 | 0.6 | 0.6 | 2 | 1 | 1 |
| SKY.GradientHorizonColorFilter | (0.82,0.82,0.82) | (0.96,0.72,0.31) | (0.86,0.54,0.31) | (0.77,0.74,0.59) | (0.71,0.88,0.93) | (0.91,0.58,0.35) |
| SKY.SunIntensity | 0.3 | 0.22 | 0.23 | 0.7 | 0.22 | 0.7 |
| SKY.SunDesaturation | 1 | 0.3 | 0.2 | 1 | 1 | 1 |
| SKY.SunColorFilter | (0.89,0.71,0.36) | (0.96,0.64,0.29) | (0.88,0.56,0.35) | (0.93,0.82,0.71) | (0.84,0.76,0.67) | (0.79,0.65,0.56) |
| SKY.SunGlowIntensity | 6 | 6 | 7 | 10 | 5 | 10 |
| SKY.SunGlowHaziness | 0.1 | 0.1 | 0.1 | 0 | 0.2 | 0.27 |
| SKY.CloudsIntensity | 0.58 | 0.5 | 0.7 | 0.83 | 1 | 1 |
| SKY.CloudsCurve | 2.23 | 1 | 1.1 | 2 | 1.4 | 1.3 |
| SKY.CloudsDesaturation | 0.52 | 0 | 0.5 | 0.7 | 0.1 | 1 |
| SKY.CloudsOpacity | 1.13 | 1.5 | 1.2 | 0.7 | 1 | 0.8 |
| SKY.CloudsColorFilter | (1.00,1.00,1.00) | (0.89,0.85,0.80) | (0.64,0.67,0.74) | (0.51,0.62,0.67) | (0.82,0.90,0.93) | (0.67,0.71,0.78) |
| SKY.MoonIntensity | 0.2 | 0.1 | 0.24 | 1 | 1 | 0.2 |
| BLOOM.Amount | 0.55 | 0.5 | 0.5 | 0.6 | 0.6 | 0.5 |
| BLOOM.BlueShiftAmount | 1.1 | 2 | 2 | 2 | 2 | 0 |
| SKYLIGHTING.AmbientMinLevel | 0.6 | 0.64 | 0.65 | 0.5 | 0.78 | 0.84 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.23 | 0.25 | 0.23 | 0.22 | 0.13 | 0.16 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 0.35 | 0.3 | 0.3 | 0.25 | 0.18 | 0.2 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 2.7 | 1.3 | 1.3 | 1.5 | 1.4 | 3 |
| AUTOAMBIENT.BlendingAmount | 0.7 | 0.4 | 0.5 | 0.8 | 0.9 | 0.6 |
| AUTOAMBIENT.TopIntensity | 0.6 | 0.5 | 0.6 | 1 | 0.9 | 0.7 |
| AUTOAMBIENT.BottomIntensity | 0.6 | 0.5 | 0.43 | 1 | 0.9 | 0.7 |
| AUTOAMBIENT.BottomSaturation | 0.2 | 0.4 | 0.2 | 1.4 | 0.2 | 0.1 |
| RAYS.SunRaysMultiplier | 0.75 | 0.4 | 0.4 | 6 | 11 | 1.4 |
| VOLUMETRICRAYS.Intensity | 0.54 | 0.6 | 0.8 | 1 | 1 | 1 |
| VOLUMETRICRAYS.Density | 2.1 | 3 | 3 | 1.3 | 1.5 | 2 |
| VOLUMETRICRAYS.SkyColorAmount | 0.8 | 0.3 | 0.3 | 0.5 | 0.5 | 0.7 |
| VOLUMETRICFOG.Intensity | 0.4 | 0.55 | 0.7 | 0.3 | 0.8 | 0.7 |
| VOLUMETRICFOG.Curve | 0.6 | 1 | 1 | 1.4 | 0.7 | 0.8 |
| VOLUMETRICFOG.LightingInfluence | 0.5 | 0.2 | 0.5 | 0.8 | 1 | 0.7 |
| VOLUMETRICFOG.Opacity | 1 | 0.8 | 0.7 | 0 | 0.1 | 0.8 |
| MIST.SkyLightingAmount | 2.9 | 1 | 1.3 | 2 | 1.2 | 1.5 |
| MIST.SunLightingAmount | 0.7 | 1 | 0.5 | 0.5 | 0.5 | 0 |
| MIST.Desaturation | 1 | 0.6 | 0.5 | 0.7 | 0.9 | 0.4 |
| MIST.ColorFilter | (0.71,0.83,0.94) | (0.36,0.59,0.82) | (0.46,0.68,0.80) | (0.84,0.77,0.72) | (0.73,0.75,0.76) | (0.57,0.64,0.71) |
| MIST.VerticalOffset | 10 | -14 | 70 | 10 | -5 | 10 |
| MIST.Density | 1.4 | 1.38 | 1.2 | 2 | 5 | 1.1 |
| MIST.VerticalFade | 5 | 2 | 0.8 | 0.4 | 3 | 0 |
| MIST.BottomTop | 0.6 | 1 | 1 | 1 | 0 | 0 |
| MIST.ExponentialFade | 1.2 | 0.4 | 1 | 1 | 1.05 | 1.2 |
| MIST.DistanceFade | 0.1 | 0.7 | 2 | 1 | 2 | 0.8 |
| PROCEDURALSUN.GlowIntensity | 1.7 | 0.4 | 0.43 | 0.8 | 2 | 0.5 |
| PROCEDURALSUN.GlowCurve | 0.08 | 7 | 6 | 10 | 10 | 10 |
| PARTICLE.Intensity | 0.53 | 0.5 | 0.6 | 0.5 | 0.5 | 0.8 |
| PARTICLE.LightingInfluence | 0.1 | 0.97 | 0.9 | 0.3 | 0.2 | 0.6 |
| FIRE.Intensity | 5 | 1 | 1 | 1 | 1 | 1 |
| FIRE.Curve | 1.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| LIGHTSPRITE.Intensity | 1.1 | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |
| LIGHTSPRITE.Curve | 3 | 1 | 1 | 1 | 1 | 1 |
| WINDOWLIGHT.Intensity | 0.7 | 0.5 | 0.5 | 0.1 | 0.5 | 0.1 |
| WINDOWLIGHT.Curve | 1 | 1 | 1 | 2 | 1 | 2 |
| GRASS.DirectionalMultiplier | 1 | 2 | 2 | 2 | 1.8 | 2 |
| GRASS.AmbientMultiplier | 2 | 2 | 2 | 2 | 1.7 | 2 |
| CLOUDSHADOWS.Opacity | 1 | 0.76 | 0.7 | 0.8 | 1 | 0.99 |

### Interiors: global vs Dungeons vs Dwarven_Ruins vs Caves_Other vs ClearTundra (InteriorDay / InteriorNight)

| section.key | global | Dungeons | Dungeons2 | Dwarven_Ruins | Caves_Other | ClearTundra |
|---|---|---|---|---|---|---|
| ENVIRONMENT.DirectLightingIntensity | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| ENVIRONMENT.DirectLightingCurve | 1 / 2 | 3 / 3 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 |
| ENVIRONMENT.DirectLightingDesaturation | 0 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| ENVIRONMENT.DirectLightingColorFilterAmount | 0.7 / 0.3 | 0.7 / 0.5 | 0.8 / 0.5 | 0.6 / 0.5 | 0.8 / 0.3 | 0.8 / 0.3 |
| ENVIRONMENT.DirectLightingColorFilter | (1.00,1.00,1.00) / (0.20,0.35,0.42) | (0.45,0.53,0.57) / (0.28,0.33,0.35) | (0.45,0.53,0.57) / (0.28,0.33,0.35) | (0.45,0.53,0.57) / (0.28,0.33,0.35) | (0.58,0.61,0.64) / (0.29,0.31,0.34) | (0.47,0.52,0.55) / (0.28,0.33,0.35) |
| ENVIRONMENT.AmbientLightingIntensity | 2 / 0.4 | 1.4 / 1 | 1.4 / 0.5 | 1 / 1 | 2 / 1 | 3 / 0.5 |
| ENVIRONMENT.AmbientLightingCurve | 1 / 2 | 1 / 2 | 1 / 2 | 2 / 2 | 2 / 2.5 | 1 / 2 |
| ENVIRONMENT.AmbientLightingDesaturation | 0 / 0 | 0 / 0 | 0 / 0 | 1 / 1 | 0.5 / 0 | 0 / 1 |
| ENVIRONMENT.AmbientColorFilterAmount | 0.73 / 0.23 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.8 / 0.4 | 0.8 / 0.4 |
| ENVIRONMENT.AmbientColorFilterTop | (0.59,0.70,0.74) / (0.17,0.33,0.38) | (0.62,0.69,0.72) / (0.40,0.50,0.55) | (0.64,0.68,0.69) / (0.54,0.61,0.64) | (0.64,0.68,0.69) / (0.54,0.61,0.64) | (0.67,0.70,0.71) / (0.43,0.49,0.51) | (0.63,0.68,0.71) / (0.38,0.51,0.56) |
| ENVIRONMENT.AmbientColorFilterMiddle | (0.44,0.55,0.66) / (0.22,0.41,0.49) | (0.53,0.62,0.65) / (0.34,0.40,0.44) | (0.54,0.61,0.64) / (0.45,0.53,0.57) | (0.54,0.61,0.64) / (0.45,0.53,0.57) | (0.66,0.67,0.68) / (0.43,0.48,0.51) | (0.56,0.60,0.62) / (0.32,0.51,0.62) |
| ENVIRONMENT.AmbientColorFilterBottom | (0.43,0.49,0.51) / (0.15,0.38,0.47) | (0.49,0.57,0.60) / (0.28,0.33,0.35) | (0.49,0.57,0.60) / (0.38,0.45,0.48) | (0.49,0.57,0.60) / (0.38,0.45,0.48) | (0.49,0.53,0.56) / (0.32,0.36,0.37) | (0.45,0.53,0.57) / (0.21,0.40,0.48) |
| ENVIRONMENT.SpecularAmountMultiplier | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| ENVIRONMENT.SpecularPowerMultiplier | 0.5 / 0.5 | 0.4 / 0.4 | 0.4 / 0.4 | 2 / 2 | 0.5 / 0.5 | 0.3 / 0.3 |
| ENVIRONMENT.SpecularFromLight | 0.5 / 0.5 | 0.6 / 0.6 | 0.6 / 0.6 | 0.7 / 0.7 | 0.5 / 0.5 | 0.5 / 0.5 |
| ENVIRONMENT.PointLightingIntensity | 1.4 / 1.4 | 1.4 / 1.4 | 1.4 / 1.4 | 1 / 1 | 1.4 / 1.4 | 1.4 / 1.4 |
| ENVIRONMENT.PointLightingCurve | 1.7 / 1.7 | 1.7 / 1.7 | 1.7 / 1.7 | 2 / 2 | 1.8 / 1.8 | 1.7 / 1.7 |
| ENVIRONMENT.PointLightingDesaturation | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 | 0.4 / 0.4 |
| ENVIRONMENT.ParticleLightsIntensity | 0.45 / 0.5 | 0.45 / 0.5 | 0.45 / 0.5 | 0.45 / 0.5 | 0.45 / 0.5 | 0.45 / 0.5 |
| ENVIRONMENT.FogColorMultiplier | 0.4 / 0.2 | 0.4 / 0.2 | 0.4 / 0.2 | 0.4 / 0.2 | 0.4 / 0.2 | 0.4 / 0.2 |
| ENVIRONMENT.FogColorCurve | 1.5 / 1.7 | 1.5 / 1.73 | 1.5 / 1.73 | 1.5 / 1.73 | 1.5 / 1.73 | 1.5 / 1.5 |
| ENVIRONMENT.FogColorFilterAmount | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 | 0.2 / 0.1 |
| ENVIRONMENT.FogColorFilter | (1.00,1.00,1.00) / (0.64,0.64,0.64) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (0.64,0.64,0.64) |
| ENVIRONMENT.ColorPow | 1.1 / 1.15 | 1.1 / 1.15 | 1.1 / 1.15 | 1.1 / 1.15 | 1.1 / 1.15 | 1.1 / 1.15 |
| SKY.GradientIntensity | 2.38 / 0.68 | 3 / 0.8 | 5 / 0.8 | 3 / 0.8 | 10 / 0.8 | 2.2 / 1 |
| SKY.GradientDesaturation | 0.5 / 0 | 0.3 / 0.3 | 0 / 0.3 | 0.3 / 0.3 | 0.8 / 0.3 | 0.3 / 0.3 |
| SKY.GradientTopIntensity | 1.23 / 1 | 1.23 / 1 | 1.23 / 1 | 1.23 / 1 | 1.23 / 1 | 1.23 / 1 |
| SKY.GradientTopCurve | 1.2 / 1.5 | 1.2 / 1.5 | 1.2 / 1.5 | 1.2 / 1.5 | 1.2 / 1.5 | 1.2 / 1.5 |
| SKY.GradientTopColorFilter | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) |
| SKY.GradientMiddleIntensity | 2.05 / 1 | 2 / 1 | 2 / 1 | 2 / 1 | 2 / 1 | 2 / 1 |
| SKY.GradientMiddleCurve | 0.71 / 1 | 0.71 / 1 | 0.71 / 1 | 0.71 / 1 | 0.71 / 1 | 0.71 / 1.01 |
| SKY.GradientMiddleColorFilter | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) |
| SKY.GradientHorizonIntensity | 3 / 1 | 3 / 1 | 3 / 1 | 3 / 1 | 3 / 1 | 1 / 0.7 |
| SKY.GradientHorizonCurve | 1.43 / 1 | 1.43 / 1 | 1.43 / 1 | 1.43 / 1 | 1.43 / 1 | 1.43 / 1 |
| SKY.GradientHorizonColorFilter | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) |
| SKY.SunIntensity | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 0.2 / 1 |
| SKY.SunDesaturation | 0.7 / 0 | 0.7 / 0 | 0.7 / 0 | 0.7 / 0 | 0.7 / 0 | 0.7 / 0 |
| SKY.SunColorFilter | (1.00,0.94,0.86) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) |
| SKY.SunGlowIntensity | 1 / 0 | 1 / 0.2 | 1 / 0.2 | 1 / 0.2 | 1 / 0.2 | 1 / 0 |
| SKY.SunGlowHaziness | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| SKY.CloudsIntensity | 2 / 0.3 | 3 / 0.4 | 4 / 0.4 | 2 / 0.4 | 2 / 0.4 | 1 / 0.16 |
| SKY.CloudsCurve | 1 / 1 | 1.1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 2 / 1 |
| SKY.CloudsDesaturation | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| SKY.CloudsOpacity | 1 / 1 | 0.7 / 1.72 | 0.8 / 1 | 1.25 / 1.72 | 0 / 0 | 1.5 / 1.72 |
| SKY.CloudsColorFilter | (0.89,0.94,0.99) / (0.34,0.46,0.53) | (0.82,0.90,0.98) / (0.59,0.67,0.74) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (0.85,0.87,0.88) / (1.00,1.00,1.00) |
| SKY.MoonIntensity | 1 / 1 | 2.8 / 1 | 2.8 / 1 | 2.8 / 1 | 2.8 / 1 | 1 / 1 |
| BLOOM.Amount | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 |
| BLOOM.BlueShiftAmount | 1 / 1 | 1 / 2 | 1 / 2 | 1 / 2 | 1 / 2 | 1 / 2 |
| SKYLIGHTING.AmbientMinLevel | 0.1 / 0.1 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 |
| IMAGEBASEDLIGHTING.AdditiveAmount | 0.5 / 0.5 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| IMAGEBASEDLIGHTING.MultiplicativeAmount | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| IMAGEBASEDLIGHTING.ReflectiveAmount | 2 / 2 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| AUTOAMBIENT.BlendingAmount | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| AUTOAMBIENT.TopIntensity | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| AUTOAMBIENT.BottomIntensity | 0.5 / 0.2 | 0.2 / 0.2 | 0.2 / 0.2 | 0.2 / 0.2 | 0.2 / 0.2 | 0.5 / 0.5 |
| AUTOAMBIENT.BottomSaturation | 0.2 / 0.2 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| RAYS.SunRaysMultiplier | 0.3 / 0.3 | 0.3 / 0.3 | 0.3 / 0.3 | 0.3 / 0.3 | 0.3 / 0.3 | 0.3 / 0.3 |
| VOLUMETRICRAYS.Intensity | 1 / 1 | 4 / 4 | 4 / 4 | 4 / 4 | 4 / 4 | 4 / 4 |
| VOLUMETRICRAYS.Density | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| VOLUMETRICRAYS.SkyColorAmount | 1 / 1 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 |
| VOLUMETRICFOG.Intensity | 2 / 1 | 2 / 1 | 2 / 1 | 1 / 1 | 1 / 1 | 2 / 1 |
| VOLUMETRICFOG.Curve | 0.6 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 0.7 / 1 |
| VOLUMETRICFOG.LightingInfluence | 0.4 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| VOLUMETRICFOG.Opacity | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| MIST.SkyLightingAmount | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| MIST.SunLightingAmount | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 | 0.1 / 0.1 |
| MIST.Desaturation | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| MIST.ColorFilter | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) | (1.00,1.00,1.00) / (1.00,1.00,1.00) |
| MIST.VerticalOffset | -11 / -11 | -11 / -11 | -11 / -11 | -11 / -11 | -11 / -11 | -11 / -11 |
| MIST.Density | 1.5 / 1.5 | 1.5 / 1.5 | 1.5 / 1.5 | 1.5 / 1.5 | 1.5 / 1.5 | 1.5 / 1.5 |
| MIST.VerticalFade | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 |
| MIST.BottomTop | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| MIST.ExponentialFade | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| MIST.DistanceFade | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| PROCEDURALSUN.GlowIntensity | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| PROCEDURALSUN.GlowCurve | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| PARTICLE.Intensity | 0.8 / 0.6 | 0.8 / 0.5 | 0.8 / 0.5 | 0.7 / 0.5 | 0.7 / 0.5 | 0.8 / 0.5 |
| PARTICLE.LightingInfluence | 1 / 1 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 | 0.5 / 0.5 |
| FIRE.Intensity | 10 / 10 | 2.2 / 2.5 | 2.2 / 2.5 | 2.2 / 2.5 | 2.2 / 2.5 | 2.2 / 2.5 |
| FIRE.Curve | 1.9 / 1.9 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |
| LIGHTSPRITE.Intensity | 1 / 1 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2 / 2 |
| LIGHTSPRITE.Curve | 3 / 3 | 1.9 / 2.4 | 1.9 / 2.4 | 1.9 / 2.4 | 1.9 / 2.4 | 1.9 / 2.4 |
| WINDOWLIGHT.Intensity | 3 / 0.05 | 6 / 2 | 8 / 1 | 8 / 1 | 8 / 1 | 11 / 1 |
| WINDOWLIGHT.Curve | 1.4 / 2 | 2 / 2 | 2 / 2 | 2 / 2 | 2.5 / 2.5 | 1.5 / 1.5 |
| GRASS.DirectionalMultiplier | 2 / 1.4 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 2 / 1.4 |
| GRASS.AmbientMultiplier | 3 / 2 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 3 / 2 |
| CLOUDSHADOWS.Opacity | 0.9 / 0.9 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 | 1 / 1 |

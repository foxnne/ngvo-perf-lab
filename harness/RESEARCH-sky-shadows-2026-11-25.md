# Sky-lit sun shadows: why shade is pale and grey, and the A/B switch (2026-11-25)

Branch `fix/sky-lit-shadows` in worktree `C:\Users\foxnn\dev\cs-wt-skyshadow` (off `foxnne/merge-rc2-1123`),
commit `166d5a0d3`. I have not built it. The two SSGI shaders pass a standalone fxc syntax check (cs_5_0, with and without SH).

## 1. What lights a pixel in sun shadow outdoors (the live path)

Live state: SSGI on with GI, `UseDynamicCubemapsAsFallback` on, Dynamic Cubemaps loaded, so
`ssgiSettings.ReplaceAmbient = 1`. (The exception is Effects 11 owning IBL. Then ReplaceAmbient is 0 and the
fallback path below applies.)

| # | Term | Where | Colour handling | Sky occlusion |
|---|------|-------|-----------------|---------------|
| 1 | Vanilla DALC / IBL ambient in Lighting.hlsl | `Lighting.hlsl` ~3794-3898 | Computed, then **set to 0** when ReplaceAmbient (except reflections/char light) | n/a |
| 2 | Cloud scatter + cloud-deck ground light | `Lighting.hlsl` 3901-3902 | Sun colour; deck light only under low cloud shadow | none (clear day ~0) |
| 3 | **SSGI traced bounce** (`totalRadiance`) | `diffuseGI.cs.hlsl` CalculateGI | Radiance of on-screen hit surfaces x `GIStrength` (1.03). Warm when the hits are sunlit ground or bodies | Own horizon bits |
| 4a | **SSGI fallback, sky term** | `SampleDiffuseFallbackCubemap` | `kREFLECTIONS` cubemap (Physical Sky draws sky and clouds into it) at mip 3, the actual sky colour per ray, then `Saturation(SkyIBLSaturation)` and `x SkyIBLScale` | x Skylighting diffuse visibility (floor `MinDiffuseVisibility` 0.10 live) x open bits x `normHitDist^AOPower` (AOPower 2) |
| 4b | **SSGI fallback, env/DALC term** (DALCMode 2/3) | same | `lum(env)/lum(env avg) x Color::Ambient(DALC) x DALCAmount` (0.25 clear). The weather's ambient colour, x `ambientMult`. **Dropped beyond `ReflectionFallbackDistance` (1024 u, ~15 m)** by ApplyIBLReflectionFallback | x Skylighting (SkylightingAffectsEnv=1) |
| 5 | Composite: `ILSaturation` | `composite.cs.hlsl` | Applied to **3 + 4a + 4b together**. E11 overlay uses `E11ILSaturation` 0.8 | x contact AO `lerp(1, nh^AOPower, 0.85)` |
| 6 | Deferred composite AO | `DeferredCompositeCS.hlsl` | `x sqrt(MultiBounceAO(albedo, ssgiAo))` on direct + IL | |
| 7 | Aerial perspective / VL / height fog | DeferredComposite, VL | Additive in-scatter, the same on lit and shaded pixels | |

With ReplaceAmbient off (the E11-owned IBL case), the deferred composite rebuilds the ambient as
`GetDiffuseIBLOccluded`: `DALC x DALCAmount` plus the low-order SH of the sky cubemap x `SkyIBLSaturation` x the
Skylighting visibility. The same greying applies there, and it is not changed by this branch.

## 2. Why shadowed snow isn't blue (and why shade is pale)

1. **`SkyIBLSaturation` = 0.6** in the foxnne-look baseline and on all 264 weather entries of
   foxnne-nat3-clouds-pass5. The only exceptions are SnowClear and SnowClear_Alt, which have 1.3. That takes 40% of the
   sky's chroma out before anything else.
2. **IL Saturation is applied to the whole fill, sky included** (`composite.cs.hlsl`). Its tooltip says it "keeps the
   sky's cool fill", but it greys that fill too. With E11 active the value is 0.8.
3. **The DALC term is added on every ray** as well as the sky. DALC is the weather's stand-in for the same sky, so the sky
   is counted twice and the double is grey or warm. This also explains the `ambientMult` sweep: it only scales DALC, and
   DALC is gone past about 15 m because of the reflection fallback distance. So it is a small share of the fill.
4. **Traced bounce from sunlit warm or white ground.** On flat open ground the horizon tracer sees little geometry. On
   snow slopes and next to bodies or walls it returns neutral, very bright radiance, and the sky's blue is lost in it.
5. **The display pipeline.** The tonemap, the LUT/Look Grade and any white balance compress stops and chroma. The 1.3-stop
   (42%) reading should be redone on linear HDR: the pre-tonemap capture or the RenderDoc main RT.

Note: the sky fill also gets AO three times: `nh^AOPower` in diffuseGI, the contact IL occlusion in the composite, and
`sqrt(MultiBounceAO)` in the deferred composite. That is harmless on open ground (nh ~ 1), but it darkens crevices and
contact zones.

## 3. Changes (all in Screen Space GI, Light Settings)

| Setting (json key) | Default | What it does |
|---|---|---|
| `PhysicalSkyFill` | false | The A/B switch. It needs Physical Sky enabled and an exterior. When off, everything is exactly as before |
| `SkyFillScale` "Open Sky Fill Scale" | 1.0 | Sky term brightness, `lerp(SkyIBLScale, SkyFillScale, skyOpen)`. `skyOpen` is the Skylighting visibility rescaled above its floor. **Canopy keeps the old scale**, so forest shade holds |
| `SkyFillSaturation` | 1.0 | Replaces SkyIBLSaturation for the sky term (1 = the sky's own blue) |
| `SkyFillEnvWeight` "Ambient On Open Sky" | 0.25 | DALC weight on skyward rays (`saturate(dir.z*4)`) under open sky. Horizon and down rays, and occluded sky, keep all of it |
| (`ILSaturation`) | - | With the switch on it is applied in diffuseGI to the **traced bounce only**. It is linear, so it is the same before or after the denoiser, and the sky fill keeps its colour |
| `BounceSkyLimit` "Bounce Limit" | 0 (off) | Only with the switch on, outdoors, with Physical Sky. Strength fades continuously with the open share of the hemisphere and the sky openness. Caps the traced bounce luminance at `k x mean ambient of the open bits x hit measure x GIStrength`. It scales the bounce, so hue is kept. Useful range is 2-6: real sunlit-wall bounce can exceed the sky it hides |

Ways to reach the target ratio (2-2.5 stops = 18-25% on open ground at clear noon) while forest shade holds:
lower `SkyFillScale` (under the canopy the old scale is still used), set `SkyFillEnvWeight` toward 0, and use
`BounceSkyLimit` 3-4 for the player's own shadow. `GIStrength` (traced) and `DiffuseCubemapMult` (all fallback,
forest included) remain the global knobs.

Starting A/B values: `PhysicalSkyFill true, SkyFillSaturation 1.0, SkyFillEnvWeight 0.0, SkyFillScale 1.0,
BounceSkyLimit 4`. If the open-road ratio is still above about 30%, step `SkyFillScale` 0.8, then 0.65, then 0.5.

## 4. Test plan (linear HDR captures where possible; switch each setting on and off at the same frame)

1. **Open road ratio**: `stables_road_eye` (Whiterun Stables), clear weather, 13:00, the player standing so that her shadow
   falls on the road. Measure the mean luminance in the shadow vs the adjacent sunlit road. Baseline first (switch off;
   the earlier reading was 42% at 16:00), then the A/B values, then the `SkyFillScale` steps. Target 18-25%. Also log the
   shadow chroma (b/(r+g+b)): it should rise with the switch on.
2. **Snowfield hue**: the High Hrothgar approach or the Pale at noon, clear (SnowClear, which has DALCAmount 0 and
   SkyIBLSat 1.3 in the pack). Sample shadowed snow: the hue should move to blue (B > R by a clear margin) with the
   switch on. Then `BounceSkyLimit` 0 vs 4 on a slope next to sunlit snow.
3. **Forest hold**: `riverwood_floor` from views.json. The shaded-floor mean luminance must stay within about 10% of the
   baseline (expected, since a canopy keeps SkyIBLScale and DALC). If it drops, raise `SkyFillEnvWeight` or check `skyOpen` there.
4. Regression checks: the Ilinalta clear benchmark (protect-clear-day-look), one overcast weather (the switch only removes
   DALC on open sky, so watch for overcast shade getting too dark) and one interior (it must be identical).

## 5. Review fixes (Codex, 2026-11-25, commit after 166d5a0d3)

- With the switch off, the code path is the legacy one (the new work sits behind uniform branches); the composite is unchanged.
- Everything new is blended in by sky openness (Skylighting visibility above its floor): openness 0 is exactly legacy. That covers the sky scale and saturation, the DALC weight, and IL Saturation on the fallback (now applied in diffuseGI as `lerp(ILSaturation, 1, openness)`; traced bounce gets the full IL Saturation as before). Without SKYLIGHTING compiled in, and on the non-IBL fallback, openness is 0, i.e. legacy.
- The Bounce Limit is gated by the switch, outdoors and Physical Sky. Its strength is `saturate(4 x open share) x openness`, so there is no hard threshold. The slider is greyed out with the switch off.
- The openness and weight accumulation only runs with the switch on.

## 6. Second review round

- `fillBlendTotal` is now divided by SSGI_ROTATION_COUNT like the other totals. ROTATION_COUNT is 1 today, so this was latent.
- The composite's IL Saturation pass and clamp are back, unchanged, for every pixel. With the switch on, diffuseGI only pre-scales the open-sky fallback's chroma by `lerp(IL, 1, fillShare) / IL`. That keeps luminance, is limited so no channel goes below zero, and is skipped at IL ~0 or 1, so the composite pass lands the fallback at `lerp(IL, 1, fillShare)`. fillShare 0 is the untouched legacy signal. Traced bounce gets the legacy IL Saturation.
- Layout check: C++ `ScreenSpaceGI::SharedData` is 48 B (static_assert) with the same field order as HLSL `SSGISettings` (12 x 4 B, no 16 B straddle). It sits in the same FeatureData slot on both sides (between ProceduralNightSky and SSR).
- No compile-time define for the off case: toggling the switch would then recompile the shaders mid-A/B. The runtime branches are uniform.

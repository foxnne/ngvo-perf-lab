# Dusk brightness jump at 19:1 (Riften Stables, SunnyPF): 2026-11-25

Branch `fix/dusk-handover` in worktree `C:\Users\foxnn\dev\cs-wt-dusk` (from `foxnne/merge-rc2-1123`), commit `07b3c9196`. I worked from the code only. Nothing was built or run.

## Timing (worked out from the plugins and the code)

- Climate: `SkyrimClimate` (00000812), unchanged in NAT-ENB.esp. Sunrise 5:30-10:00, sunset 16:00-20:30.
- Alternate sun path (Southern, 55 deg peak): the sun reaches the horizon at **18.50**. The directional light starts to dim at +0.5 deg (**18.46**). The handover at -1 deg (`sunBelowHorizon`) is at **18.59**. The sun reaches -5.7 deg at 19.0 and -6.8 deg at 19.1.
- The twilight cap (`GetTwilightCap`) is 0 at 18.59 and reaches 1 at 18.59 + 0.7 = **19.29**.

## Root cause (SkySync.cpp, before the fix)

- `UpdateMoonlightFade` (lines 536-541) set the target to 1 whenever `sunBelowHorizon`. Its only limit was the twilight cap, which is counted on the clock from the sun's handover (lines 551-556). Neither looked at whether a moon was actually giving light.
- At 18.59 no moon was lit: it was below the effective horizon or its alpha was 0. `ShadowFader` therefore fell back to `Zenith`, and the direct light went to 0. This is correct.
- When a moon became the caster at about 19.0-19.1, the fade was already 0.6-0.73 through. The swap from the zenith to the moon (lines 946, 953, 997) ramps `intensityFactor` and `casterFade` over `ShadowTransitionDuration`, which is 301 *game seconds* (0.08 h). In a 0.1 h step (and DevBench `hour` also snaps the fader, line 965) or at TimeScale 5000 (about 0.06 s), this happens at once. So about 70% of the moonlight appeared in one step, and it was full by 19.3. This matches 59 -> 95 -> 105-111 and the EV rise.
- `ApplyMoonlightColors` (lines 285-290) also switched the sunlight colour to night at once. That was hidden while the light was 0 at the handover, but it was a step.

## Other terms checked (by code and data, not measured)

- **DALC/ambient:** vanilla time blend from sunset to night over 16:00-20:30. NAT-CS SunnyPF night ambient (27,32,37) and night DALC are below the sunset values, so this term is continuous and falls.
- **Scene Manager:** the pack has SunnyPF period files only for cloud coverage, and they are the same for Sunset, Dusk and Night. No period overrides apply to clear weather.
- **Physical Sky sky LUT / IBL:** the moon terms are `masserColor x phase x transmittance` and depend on the moon's direction only, not on its alpha. They are continuous, but they do add sky light as a moon rises.

## Fix

- `UpdateMoonlightFade` now runs after `ShadowFader::Update`. It ramps only while Masser or Secunda is the target, by game hours / `HorizonFadeHours` (frame advance = max(dt x timescale, hour delta), so it holds at any TimeScale). It is still capped by the twilight cap.
- On the first frame a moon is the caster, the ramp starts at 0 and none of that update's elapsed time is added. This also applies to a scrub or time jump longer than `HorizonFadeHours`. Only a game load or a new worldspace sets the fade at once.
- Any light still showing when a moon takes over (for example a moon picked again partway through a zenith fade-out) is kept in a separate `moonlightOut` level. That level fades out over `HorizonFadeHours`, and the light used is the larger of it and the new ramp. The new ramp always starts at 0.
- Where a weather hides the moons, the cut-off for moonlight is now scaled by the night weight (`1 - w`), in both Sky Sync and Effects11, so it is no longer an on/off switch during the blend. (Codex review, follow-up commit.)
- Second review: any change of caster to a moon now restarts the fade from zero, including a direct Masser to Secunda swap; the old moon's light is kept and faded out. The light kept from before the swap is capped by the twilight cap, and the sun's light is never kept at all, so daylight cannot leak into the moonlight. The hidden-moon scale is now smooth in the glare brightness: it fades over glare 0 to 4/255 and over the night weight, so it no longer switches in one update.
- The night sunlight colour now blends in by the twilight cap (`lightNightWeight` 0-1). Effects11 `BlendGradedWeathers` and VL `GetWeatherSunlight` blend the same way.
- `ShadowDirectionHoldAngle` is still 0.

## Caveat: the moonlight level is a setting

The plateau after 19.2 (103-110) is above the 59 at 19.0, so full moonlight on its own is brighter than late dusk. The fix turns the pop into a 0.7 h ramp, but brightness can still rise from about 59 to about 105 between 19.05 and 19.75. Under Physical Sky `overrideDirLight`, the Sky Sync New/Crescent/Full moon intensities are **not** used for the direct light (`ApplyLightColor` uses PS `masserColor x photometric phase x alpha`). The live `masserColor` (0.35, 0.40, 0.52) is 3.5-5x the PS default and about 7% of `sunlightColor` 6. Lowering `masserColor` and `secundaColor` (try 0.05-0.1) is the lever for "far dimmer".

## What to measure

- Repeat the 0.1 h step test from 17:00 to 21:00 (SunnyPF, frozen, 3000 up). Log brightness and EV, plus the Sky Sync debug values Dim, Caster fade, Transition intensity factor and caster.
- Expected: Dim is about 0 at 18.6-19.0. When the caster becomes a moon, Dim rises by at most 0.14 per step (0.1/0.7) and is full about 0.7 h later. There should be no step between 19.0 and 19.1.
- If brightness still rises after 19.1, it is moonlight level, not a pop: lower `masserColor` and re-run.
- Flight check: during a time-lapse arc there should be no single bright frame at dusk.

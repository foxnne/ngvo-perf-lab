# Findings log

## 2026-11-17 baseline-A (config fe68e81446), 2 clean reps
| scenario | render fps | frames >100 ms / 100 s | stall ms | worst frame | peak VRAM |
|---|---|---|---|---|---|
| plains (static) | 30.9 | 0 | 0 | 94 ms | 9.4 GB |
| sprint (Onward) | 28.4 | 10, 17 | 2811, 3781 | 739 ms | 12.5 GB |
| flight | 32.6 | 8, 5 | 1214, 2935 | 897 ms | 12.2 GB |
Noise: fps within ~3; stall counts vary a lot (need >=3 reps). Flight distance differed between reps (CapsLock toggle), fixed.

## 2026-11-17 Tracy capture tracy-A (PR-Tracy build), plains: 32.2 ms/frame
GPU zones (ms per frame, inclusive): Neural Rendering 9.5 (NREvaluate 9.1), Deferred 2.25, Upscaling (DLSS) 2.1,
SSGI 1.1, Prepass 0.9, Terrain Blending 0.8, SSR 0.7, Screen Space Shadows 0.35, NR composite 0.2.
Instrumented GPU zones sum to roughly 17 ms; about 15 ms of GPU time per frame is NOT in any zone
(scene geometry / g-buffer, shadow maps, grass, sky, water, frame generation).
CPU zones: all CS zones together are only ~4.3 ms/frame on plains (6.3 on sprint): Terrain Depth 1.3,
State::Draw 0.8 (6,137 draws per frame), NREvaluate 0.7. Main thread shows ~29 ms CPU per frame, so most of it is
outside CS zones (engine draw submission, other plugins, or spinning inside the FSR frame generation present path;
an earlier stack sample put ~39% of main-thread samples under amd_fidelityfx_framegeneration_dx12.dll).
GPU was at 96-98% in these scenes: the static scene is GPU-bound.
Sprint: TreeWind::BuildBendWeights still costs 1.5 ms/frame on average with single builds up to 15 ms,
State::Draw max 46.8 ms, NREvaluate CPU max 23 ms, HiZ prepass max 12.8 ms.

## Implication for the 50 fps target (20 ms)
Neural Rendering alone is ~9.5 ms of GPU per frame, so everything else must fit in ~10.5 ms (now ~22 ms).
Levers to test: NR skip-frame reuse (tuning `skipFrameReuse` / `skipFrameGapMode`), frame generation cost,
the uninstrumented 15 ms (add GPU zones around the main scene, shadows, grass), SSGI/SSR/terrain blending.

## 2026-11-17 suite B (config 55c7cef3e2: compendium merge + Tree Wind fix, old Upscaling-hosted NR)
| scenario | reps | render fps (range) | frames >100 ms | stall ms | worst | main CPU ms | peak VRAM |
|---|---|---|---|---|---|---|---|
| plains | 3 | 31.8 (31.6-32.0) | 1/0/0 | 56 | 169 | 28.5 | 9.7 GB |
| sprint (Onward) | 3 | 28.9 (26.9-31.1) | 13/12/10 | 3238 | 1493 | 30.8 | 12.6 GB |
| flight | 3 | 30.5 (30.4-30.7) | 5/5/5 | 794 | 258 | 29.8 | 11.9 GB |
| forest | 1 | 27.7 | 1 | 174 | 174 | 32.9 | 9.2 GB |
| city (Whiterun) | 1 | 29.8 | 0 | 0 | 62 | 23.4 | 10.5 GB |
| interior (Bannered Mare) | 1 | 37.3 | 0 | 0 | 57 | 24.2 | 11.3 GB |
| plains, frame generation OFF | 1 | 39.4 | 0 | 0 | 48 | 21.2 | 8.8 GB |
Frame generation off: +7.6 real fps on plains (31.4 -> 25.4 ms per frame), main-thread CPU 28.5 -> 21.2 ms, VRAM -0.9 GB.
The fg-off sprint run died with a bridge timeout and the game stopped responding (not investigated).
Suite cut short after fg-off to switch NR to Bottled PR #6 (branch foxnne/nr-pr6, builds clean, deployed as config c70ddbd3ef).
Installed afterwards: Hitch Hunter And Fixes 1.2.0 (Hitch Report on), Chicken Soup 1.0.3, Crash Fix Compendium 1.6.0, SkyrimNet 1.2.0,
OStimNet 2.7.1, OStim Navigator 2.4.0, NarrativeEngine 0.10.0, BodyLanguage 2.2.2, Phantasm 1.2.0 (old folders disabled, kept).

## Camera flash (2026-11-17)
User-confirmed gone after SmoothCam was disabled in favour of Cinemacam. OmniSight was switched off at the same time; untested whether it can go back on without the flash.

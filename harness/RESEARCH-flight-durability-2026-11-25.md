# Flight durability: the time-lapse crash, visual-only time-lapse, soak plan (2026-11-25)

Goal: the Sky Above cross-map flight must survive unlimited use. This was done offline (code, logs and harness data only; the game was not run).

Code (both on their own branches in worktrees; not merged or deployed):
- Sky Above: `C:\Users\foxnn\dev\sky-above-wt-durable`, branch `flight/durability`, commit `411a8ee`.
- CS fork: `C:\Users\foxnn\dev\cs-wt-visualclock`, branch `flight/visual-clock` (from `c1b155bce`), commit `02fb689bf`. Not built.
- Harness: `travel_ft.py` now also logs Sky Above's time-lapse and census lines for each trip (uncommitted).

## 1. Verdict

**The theory holds, with one caveat.** The crash and the extra memory both come from game time the live world goes through during the flight. The data cannot tell apart the two ways that time could cause it:

- **(a) Simulating the hours in real time.** At 5000x the world simulates the time-lapse at full fidelity, with physics and 3D running.
- **(b) The game hours themselves.** Respawns, spawned encounters and corpses pile up whichever way the hours pass.

The new design removes (a) completely. It keeps (b) at the same level as vanilla fast travel and waiting, which also advance the clock by hours per trip. Soak run B below tells the two apart.

Evidence:

| | TimeScale 5000 (smooth arc) | TimeScale 20 | Plain teleports |
|---|---|---|---|
| Flights or jumps | 14, then a crash (another run: 21, then a crash) | 24, no crash | 24, no crash |
| Game time per flight | 13–18 h (about 224 h by flight 14) | about 0.1 h | 0 |
| Private memory, start → end | 30.5 → 45.9 GiB | 30.4 → 43.4 GiB (levels off) | 41.7 → 42.0 GiB (flat) |

Private memory at the same step of the same route (`arcs_smooth.json` against `arcs_ts20.json`, in GiB; the routes are identical):

| Step | 5000x | 20x | Difference |
|---|---|---|---|
| r1 Riften | 33.5 | 33.3 | +0.2 |
| r1 Dawnstar (6) | 40.3 | 39.0 | +1.3 |
| r2 Dawnstar (12) | 44.2 | 41.2 | +2.9 |
| r3 Solitude (14, crash) | 45.9 | 40.1 | **+5.8** |

- Most of the growth from about 31 to 44 GiB is cache warm-up. It happens at 20x too, and it levels off.
- The time-lapse adds about 0.4 GiB per flight on top, and the amount speeds up in the third round.
- That extra memory is never returned. That is what "objects kept in the world" looks like, not a cache.

### The crash, in both logs (`crash-2026-11-25-02-19-28.log`, `crash-2026-11-25-02-36-43.log`)

The two stacks are the same. Names come from `re-refs/AddressLibraryDatabase/skyrimae.rename`:

```
Main::Update 36564 -> Main 36581 -> TES 13288 (grid update)
 -> GridCellArray/GridArray shift 15954/15941/15939/15955 -> TESObjectCELL 19130 (attach)
 -> 41292 -> 41468 -> Character 37501 -> Actor 37624 (vfunc 244, 3D/physics set-up) -> 39897 -> 32952
 -> BShkbAnimationGraph 63622 -> hkaRagdollInstance 64158 -> hkpWorld 61307 -> hkp3AxisSweep 64677+0x2DE
    mov dword ptr [rax], 0 with rax = 0
```

Objects on the stack in both crashes:

- `MovementAgentPathFollowerVirtual`: the soldier was moving along a path *virtually*, as low-process actors do.
- A runtime-created (FF) "Imperial Soldier" and a FF "Stormcloak Soldier".
- The HDT-SMP world.
- The Solitude cells.

The FF numbers are high: 0xD829, about 55,000, and 0xA3E3, about 42,000 forms created in a 13-minute session.

`SkyrimDelirium` wrote ragdoll rig files at both crash times for groups of consecutive FF actors: FF00A303–A30D at 02:19 and FF006E32–E38 at 02:36. A spawned group of soldiers got ragdolls during the arrival. Delirium takes over Skyrim's ragdolls ("take over Skyrim's ragdolls true"), so it is a co-factor I can't rule out. It is not on the crashing stack, though.

What this means: an actor that walked into the loaded area *virtually* is given its 3D and ragdoll as the destination grid attaches. Adding that ragdoll to the Havok broadphase fails with a null pointer.

- I could not disassemble 64677: the exe on disk is SteamStub-encrypted, and the live reader needs the game running.
- A write through a fresh null pointer in the broadphase fits a broadphase array that could not grow. A NaN/garbage AABB from a huge virtual step is also possible.
- Either way, there are more and more actors and bodies in physics, and they arrive faster.

This happened before spread attach existed (the first crash was 02:19; spread attach came in the afternoon), so spread attach is not the cause.

## 2. What a high TimeScale makes the engine do per real second

At 5000x, one real second is 1.39 game hours. The ramp ends by 85% of the flight. The camera-only flight keeps the player **parked at the start for the first half and at the destination for the second**, so two full loaded grids live through the hours. Everything below scales with game time:

| System | Effect at 5000x (250 times vanilla 20x) |
|---|---|
| AI schedules (packages by hour) | Every actor in the loaded and buffered cells changes package every few real seconds: sleep, eat, work, travel. Each change means equipping, furniture, pathing and food items. |
| Low-process actors on travel and patrol packages | `MovementAgentPathFollowerVirtual` moves them along their path by game time, so 250 times faster. Patrols such as civil-war soldiers around Solitude keep streaming into the loaded area and get 3D and ragdolls during the grid update (the crash stack). |
| Story manager and spawned encounters | Runtime-created actors (FF IDs) appear on game-time schedules and are only cleaned up when the cell resets. Corpses and dropped items stay. |
| Papyrus `RegisterForUpdateGameTime` / `RegisterForSingleUpdateGameTime` | A script on a 1-hour interval fires 1.4 times per real second instead of once a minute. Stacks pile up during the move hitch. |
| Weather | Region weather changes every few game hours, so several weather changes per flight: textures, precipitation, sounds. |
| Respawn timers | Cells reset after `iHoursToRespawnCell` (vanilla 240 h). After 10–20 flights every cell revisited at Solitude is past its reset time: actors re-created, more ragdolls on attach. This applies to (b). |
| Calendar | Engine Fixes' calendar-skipping fix (on the stack) keeps the date right. Not a crash source. |

Not affected by TimeScale: Havok stepping, combat, animation and magic durations, which all use real time.

## 3. How vanilla advances time in one step

| Path | Address Library (AE / SE) | What it does |
|---|---|---|
| `PlayerCharacter::StartWaiting(int hours)` | 40415 / 39344 | Arms a wait: `INFO_RUNTIME_DATA::sleepSeconds = hours*3600`, `hoursToSleep`. |
| `Actor::StartSleeping(int hours)` | 40414 / 39343 | Same for sleep. |
| `Actor::AdvanceSleepWaitTick()` | 40485 / 39410 | The tick `SleepWaitMenu`'s Update calls each frame. It takes `iSecondsToSleepPerUpdate` off `sleepSeconds`, advances the calendar and the AI schedules, and finishes the wait at 0. CommonLibSSE-NG documents looping it directly, without the menu. |
| `Actor::CanSleepWait(bed)` | 40443 / 39371 | Vanilla's "can you wait here" checks (combat, enemies near), with the HUD message. |
| `SleepWaitMenu` | vtable 215936 / 269872; subs 52486/52487 | The menu that drives the ticks. It pauses the game, so the world does not simulate visibly while waiting. |
| Vanilla fast travel | `papyrus::Game::FastTravel` 55457; GMST `fFastTravelSpeedMult` 375544 | Advances the clock by distance / speed during the load screen. The exact routine is not identified, because the encrypted exe can't be read offline. |
| `Calendar::Update(seconds)` | hooked by Engine Fixes `CalendarSkipping` | Adds `seconds*TimeScale` to `GameHour`, rolls the day, month and year, and keeps `GameDaysPassed` in step. Engine Fixes makes a multi-day step in one update correct. |

**Safe from SKSE at landing?**

- **Clock step: yes.** This means writing `GameHour` and `GameDaysPassed` on the main thread, which is what the `set gamehour` console command and Papyrus `GameHour.Mod/SetValue` do. Players and mods do this all the time.
  - Each step stops just before 24:00, so the engine's own `Calendar::Update` crosses midnight with its normal increment. The hour global never leaves 0–24.
  - The world then takes the skipped hours the summarised way. AI evaluates the current package (unloaded and low-process actors jump to where their schedule puts them), each due `OnUpdateGameTime` fires **once** instead of hundreds of times, and respawn and decay timers are evaluated on the next cell load.
- **Vanilla wait ticks: probably, but unverified.** The functions are real and documented in CommonLib. What happens when the wait ends without the menu (events, fades, player state) can't be checked offline. It is shipped as experimental (`iTimeCatchUp=1`) and falls back to clock steps if a tick doesn't advance.

## 4. What was built

### CS fork: `Utils/VisualClock.{h,cpp}` plus small edits (commits `02fb689bf`, then review fixes `bd9ba120d` and `b5efd3893`)

New exports, found with `GetProcAddress` the same way as `BottledShaders_GetCloudDeck`:

```cpp
extern "C" bool BottledShaders_SetVisualClock(double a_daysPassed, float a_rate); // false = refused, nothing activated
extern "C" void BottledShaders_ClearVisualClock();
extern "C" bool BottledShaders_VisualClockSupported();  // Sky::Update hook installed and Sky Sync enabled
```

- **No calendar writes, and no lasting change to engine fields** (review round 2). `GameHour` and `GameDaysPassed` are never touched. `Sky::currentGameHour` holds the visual hour only for the duration of the engine's `Sky::UpdateColors` call: CS's detour (AE 26233) saves the value, sets the visual hour, and restores it on return, all on the main thread. This makes the time-of-day colours follow the visual hour. Our own readers use `VisualClock::SkyHour(sky)` instead of the field:
  - Sky Sync's sun and shadow direction, plus its alternate sun path (writes the sun node and `gSunPosition`);
  - exposure;
  - Effects11;
  - the night sky.
  Weather timing, moon phases and all engine code stay on the real clock.
- **One coherent snapshot.** Set and Clear publish target, rate, stamp and sequence under a mutex. The main thread takes one `Frame` at the start of `Sky::Update`, and every consumer reads that single copy through `VisualClock::Current()`, which makes no game reads. Consumers use its values only while it is active; otherwise their original code runs unchanged.
- **Gated.** Set returns false and activates nothing unless `Supported()` is true: both hooks installed, the calendar usable and Sky Sync enabled. The last two are snapshotted per frame on the main thread.
- **Leaving.** The log line `[Visual Clock] ended (<cleared|lapsed|unsupported|caught up>): sky X h -> game Y h, jump Z h` records the reason and the actual jump from the last hour shown to the game's hour. A time-jump transition is requested only if that jump is more than half a game minute. After a normal landing, the "caught up" exit has a jump of about 0.
- **Unverified offline:** that the engine's colour interpolation reads `Sky::currentGameHour` and not the calendar. If the colours stay on the real hour in game while the sun moves, the colours need their own override.
- **Not covered:** the vanilla moon positions don't follow the visual clock. They are minor during a daytime flight.
- `VolumetricClouds::UpdateCloudWind` touches lines next to the main checkout's uncommitted 1/30 s hitch-cap change. If git doesn't resolve it on its own, keep both changes.

### Sky Above: `src/TimeLapse.{h,cpp}` plus hooks in `Plugin.cpp` (commit `411a8ee`)

New ini keys under `[Flight]` (also added to the ini in the repo):

```
bVisualTimeLapse=1        ; 0 = old behaviour (world runs at fTimescale)
iTimeCatchUp=0            ; 0 = clock step, 1 = vanilla wait ticks (experimental)
fTimeCatchUpStepHours=6   ; largest step per frame
```

- **Take-off (`ApplyFlightTimescale`):** `TimeLapse::Begin()` is called and the game's TimeScale is **left alone**.
- **Each flying frame:** `TimeLapse::Advance(FlightTimescaleAt(x), delta)` runs the same ramp as before, starting at 0, reaching `fTimescale` by 20% of the flight and back to normal by 85%. It moves only the visual clock, by `(rate - TimeScale) * min(delta, 0.05)`, so a hitch frame no longer jumps the sun. The visual clock is published to CS every frame.
- **Landing (and EndFlight: abort, rescue, death):** `TimeLapse::Land()` fixes the target time, and `TimeLapse::Tick()` steps the real clock up to it over the next frames: about 3–4 frames for a 15 h flight, plus one per midnight crossed. CS stops overriding the sky by itself once the real clock arrives, so the picture does not change at the step.
- **Game load or new game:** `TimeLapse::Cancel()`.
- **Cloud fade colour (`FadeBrightness`):** uses the hour the sky shows.
- **Menu:** a checkbox under the timescale slider, plus a warning when CS has no visual clock.
- **Fallback:** if CS doesn't export the visual clock, the flight still runs at normal time and the clock still steps at the landing. That keeps it durable, but no time-lapse shows, and a warning is logged.
- **Census:** one log line per landing and one after the catch-up: `Census (landed): day … hour … TimeScale … | actors high/midHigh/midLow/low (runtime-created N, dead N)`. `travel_ft.py` stores these per trip as `census_landed` and `census_clock_caught_up`, along with the last `Time-lapse:` lines.

**Build check:** the coordinator's build script needs a configured build folder, and running the configure step was blocked. Instead, `TimeLapse.cpp`, `Plugin.cpp`, `Camera.cpp` and `main.cpp` were compiled in the scratchpad with the project's flags and linked against the main checkout's `CommonLibSSE.lib`. That gave 0 errors and a DLL with the SKSE exports. The DLL is a check only, not for deployment: `…\scratchpad\sa_build\SeamlessFastTravel.dll`. The real build is the coordinator's `build-msvc.ps1` after the merge.

## 5. Other things we keep per flight (task 4)

| Item | Finding |
|---|---|
| Preload (`Preloader::held`, `bPreloadDestination`) | Up to about 2,000 `NiPointer<NiNode>` are held until the trip ends, then released 8 per frame (`PreloadRelease`). `g_flight = {}` at the next trip releases the rest. Bounded, no leak. This is a temporary peak of the destination models (355 on the test route). |
| Cell read-ahead (`CellReadAhead`, TESWorldSpace 20460) | Creates the destination's 25 CELL forms only (no references or actors), the same ones the engine creates at the move anyway. Exterior CELL forms stay in the worldspace map in vanilla as well. Bounded by the worldspace. `g_todo` is cleared at the end of each flight. |
| Spread attach (`SpreadAttach::g_queue`) | Grid coordinates only. Cleared at Arm, flushed at EndFlight and landing, disarmed after 3 s without a grid attach. The terrain job guard flag is reset on every path. No leak. |
| Cloud-fade image space instances | Stopped and their keys restored in `CloudFadeStop` on every end path, including game load. The carriage cover is stopped too. No leak. |
| Weather override | Released at the landing, EndFlight and game load. |
| Camera (`Cam::Release`) | Called at EndFlight and game load. The camera code keeps no per-flight allocations. |
| Preload manifests | One small text file per destination cell, overwritten each time. |

**Untested:** all three long runs (`arcs_4200`, `arcs_smooth`, `arcs_ts20`) were recorded **before** spread attach, cell read-ahead and the terrain-clearance arc existed. Those features have never been through 20+ flights, which is why the soak plan runs them as currently deployed.

## 6. Soak test plan (`harness/travel_ft.py`)

Prerequisites:

- The coordinator merges and builds `flight/visual-clock` (CS) and `flight/durability` (Sky Above) and deploys both.
- The ini keeps `fTimescale=5000` and `bScriptedFastTravel=1`, and adds the three keys above.
- Start each run from a fresh game start and the same save. Note the private memory at the start.
- The standard route is 6 destinations per round, including Solitude Sawmill, where both crashes happened.

| Run | Settings | Command | Pass if |
|---|---|---|---|
| **B: main test** | `bVisualTimeLapse=1 iTimeCatchUp=0` | `python travel_ft.py vis_step --rounds 7` (42 flights, twice the worst crash point) | No crash. Private memory levels off at or below about 45 GiB as the 20x run did (44 GiB). `census_landed.dyn` and `.dead` do not climb steadily from round to round. Each log shows `Time-lapse: clock caught up (done) in N frames`, with N at most about 8. |
| Look check during B | same | watch flights 1–3 live | The sun and sky visibly move through the hours as before. No sky jump at the touchdown step. The cloud-fade colour matches the time shown at the apex. |
| **C: vanilla wait path** | `iTimeCatchUp=1` | `python travel_ft.py vis_wait --rounds 4` | No crash. The log shows `vanilla wait for N h armed` and the caught-up line. No stuck "waiting" state: controls and the menu work after the landing. Only take this mode if it beats B, for example with fewer FF actors around in the census. |
| **D: only if B crashes** | `bVisualTimeLapse=1` | compare at which **game-hour** total B crashed (from `census_landed.day`) against A's about 224 h | A crash at a similar game-hour total, not flight count, means cause (b): respawns and spawns. Next, test `iHoursToRespawnCell` (Skyrim.ini, Engine Fixes) or a Sky Above cap on hours per trip. |
| A: baseline (already done twice) | `bVisualTimeLapse=0` | – | Crashed at 14 and 21. Only repeat it if B's result is unclear. |

Read the results with:

```
python -c "import json;[print(r['step'],r['privateMB'],r.get('census_landed')) for r in json.load(open('results/travel_ft/vis_step.json'))]"
```

Also keep an eye on:

- `SeamlessFastTravel.log`: `Time-lapse:`, `Census`, and `Spread attach: all grid cells attached …`.
- New `SkyrimDelirium_ragdoll_FF*.json` files, as a proxy for spawned groups ragdolling on arrival.
- The private memory after a 60 s stand at the end.

## 7. Risks and open points

- **During the flight the real clock is behind what the sky shows.** Anything that reads the calendar mid-flight, such as Papyrus or AI, sees the real time, which is the intended design. After the review fix (`bd9ba120d`) nothing writes the calendar outside Sky Above's landing step.
- **The field override is limited to the `Sky::UpdateColors` call.** An engine read of `Sky::currentGameHour` on another thread during exactly that call would see the visual hour. None is known.
- **No visual time-lapse without SkySync's hook.** If SkySync's hook is not installed (EVLaS conflict), the time-lapse doesn't show, and Sky Above logs it.
- **The exact 64677 failure is not proven.** It needs a live disassembly or a crash dump with Havok symbols.
- **Delirium as a co-factor.** If B still crashes in the same place, rerun with Delirium's ragdoll takeover off to separate it out.

## 8. Review round 3 (2026-11-25 evening): current commits

- **CS:** `flight/visual-clock` was merged into `foxnne/merge-rc2-1123` as `9713cf906`. The new branch `flight/visual-clock-2` (`d660cd515`) versions the exports:
  - `BottledShaders_VisualClockVersion()` returns 2.
  - `BottledShaders_SetVisualClock2` returns bool.
  - The unversioned `SetVisualClock` is dropped, because an early build returned void from it and its result could not be trusted.
- **Sky Above:** `flight/durability` `2f51fea`.
  - **No 5000x fallback.** The world-wide `fTimescale` runs only with `bVisualTimeLapse=0`. If the visual clock cannot start (no calendar), the flight has no time-lapse and the log says so.
  - **Versioned CS link.** Sky Above publishes only with version 2 or later and the full export set.
  - **Clock step.** At most 6 h per frame. A step that crosses midnight rolls the date over itself (day, month and year globals, `rawDaysPassed`, `midnightsPassed`). The catch-up never gives up: it warns with the hours still owed, and only reports "caught up" when nothing is owed.
  - **Vanilla wait mode removed.** `iTimeCatchUp=1` now logs a warning and uses the clock step, so soak run C is dropped.
  - **Census.** Once per landing, as an SKSE task.

These supersede the `iTimeCatchUp=1` and "experimental wait" parts of sections 3, 4 and 6.

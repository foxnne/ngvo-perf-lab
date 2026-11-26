# Seamless arrival weather for Sky Above flights (2026-11-25)

Branch `flight/arrival-weather` in worktree `C:\Users\foxnn\dev\sky-above-wt-weather` (Sky Above fork).
New module `Source/src/ArrivalWeather.{h,cpp}`, hooks in `Plugin.cpp`, ini key `bArrivalWeather` (default 1).
Not built or deployed here; `cl /Zs` with the main build's flags passes for `ArrivalWeather.cpp` and `Plugin.cpp`.
No Community Shaders changes.

Legend: **[V]** verified in the 1.6.1170 `.text` dump (`scratchpad/text_1170.bin`, `relib.py`, the same
setup as `RE-grid-attach-2026-11-25.md`). **[I]** inferred. Constants in `.rdata`/`.data` are not in the
dump, so their values are inferred from how the code uses them.

## 1. What happened on Riverwood -> Riften

The flight showed about 10 h on the sky through the CS visual clock, and the real clock stayed at TimeScale 20.
At the landing `TimeLapse` stepped the real clock 9.95 h in 2 frames. The weather clock was not touched, so
`Sky::UpdateWeather` saw about 10 h of "elapsed weather time". That is past the climate's change interval, so the
engine rolled a new region weather (RiftenOvercastFog) and started a transition on the ground. The log of that
flight has no weather lines at all, because `bClearWeather=0` and the region change at the move kept the old
weather (see the region-change rule below).

## 2. The engine's weather logic (Sky::UpdateWeather, AE 26231, RVA 0x40B490) [V]

Fields (CommonLib `RE::Sky`):

- `currentGameHour` +0x1B0
- `lastWeatherUpdate` +0x1B4. This is the weather clock: the game hour at which the current weather started.
- `currentWeatherPct` +0x1B8
- `currentClimate` +0x40, `currentWeather` +0x48, `lastWeather` +0x50, `defaultWeather` +0x58,
  `overrideWeather` +0x60, `region` +0x68
- `flags` +0x1DC. Bit 3 means accelerate. Bit 4 is fast travel: transitions are instant while it is set.
  Bit 21 releases the override.
- `lastMoonPhaseUpdate` +0x1D8 holds the accelerate start blend (CS knows this too).

Definitions:

- **elapsed** `e = currentGameHour + (lastWeatherUpdate > currentGameHour ? 24 : 0) - lastWeatherUpdate`.
  It wraps only once, so a skip of about 24 h looks like about 0 h to the engine.
- **change interval** `T = 1 + 22 * (255 - climate.TNAM.volatility) / 255` game hours. Volatility is byte
  `TESClimate+0x7C`; the constants 1.0 and 1/255 are [I]. T ranges from 1 h (volatility 255) to 23 h (volatility 0).

Per frame, while there is a climate:

1. **Override.** If `overrideWeather` is set and `e > T`, the override expires: flag 0x200000 is set and the
   override is cleared. Otherwise the override weather is the target. `ForceWeather` and the CS lock refresh
   `lastWeatherUpdate` to keep an override alive.
2. **Region weather.** The region comes from `PlayerRegionState+0x48` (singleton `0x20FBA80`, written by
   `PlayerRegionState::Handle` 41264 from the cell's region list, 18999). It is used when there is no override.
   - **Region changed** (or the override was just released):
     - `sky->region = new`
     - `pick = new->SelectWeather()`
     - If `pick == current`, the weather is kept.
     - Otherwise, if the current weather is not in the new region's list (16450), the weather switches to `pick`.
     - Otherwise it switches with probability `e / T` (an RNG compare), and keeps the current weather otherwise.
     - This is the "X -> Y after the move" swap seen in earlier flights.
   - **Same region:** if `e > T`, the target is `region->SelectWeather()`. Otherwise nothing changes.
   - **No region:** the region-less path uses `defaultWeather`. A roll uses the climate's `WLST` list with the
     same weighted pick (20433).
3. **Starting a transition** (0x40B826). This happens only if no transition is running (`lastWeather == null`)
   or the fast-travel flag is set, and the target differs from the current weather:
   - `lastWeather = current` (or null for an instant switch: fast-travel flag or interior mode)
   - `currentWeather = target`
   - `lastWeatherUpdate = currentGameHour` (unless a global flag at `[0x317ABA8]+0x340` bit 1 is set; meaning
     unknown [I])
   - flags: set bit 0, clear bit 22
   - weather-change listeners are called (`[0x20F6320]+0xD00` list)

   **A running transition blocks every new change.**
4. **Blend.** It is rebuilt from the clock every frame:
   `pct = e / (fWeatherTransMin + transDelta/255 * (fWeatherTransMax - fWeatherTransMin))`.
   `transDelta` is the new weather's DATA byte at `TESWeather+0x667`. The GMSTs are three consecutive `Setting`s
   at .data 0x1FFB320/38/50 (Max, Min, Accel) [I from layout; CS uses the same names]. With accelerate set, it
   becomes `pct = (pct - snap) * (accel + 1) + snap`. If `pct > 1`, then `lastWeather = null` and `pct = 1`.

`TESRegion::SelectWeather` (AE 16449; CommonLib `TESRegion::SelectWeather`, `RELOCATION_ID(16203, 16449)`) [V]:
it takes the region's weather data (type 3) and runs `20433`, a plain weighted roll. The weight of each entry is
its `chance`, or `(int)global->value` when a chance global is set. It uses the engine RNG (`GetRandomNumber`,
68276). **There is no time-of-day, season or classification filter in vanilla.** It has no side effects except
advancing the RNG. `TESRegion::SetCurrentWeather` (16448) only records a weather on the region (save-load path).

`Sky::SetWeather` (26241) [V]:

- With override: it sets `overrideWeather`.
- **Without override:** it sets `defaultWeather` and nulls both `PlayerRegionState.region` and `sky->region`.
  Region weathers then stop until the player crosses a region border, and later rolls come from the climate list.
- With accelerate: it sets bit 3 and snapshots the blend.

This is also why our old `RestoreWeather` (`SetWeather(prev, false, false)` after `bClearWeather`) turns
region weather off until the next border. That is a pre-existing bug, not touched here.

## 3. Design (as implemented)

States: `Waiting` -> `Pending` -> `Blending` or `Steady` -> `Holding` -> `Off`. All of it runs on the main thread,
from the `PlayerCharacter::Update` hook.

1. **Arm at take-off.** The flight is skipped and the reason logged if any of these is true:
   - `bArrivalWeather=0`
   - our own `bClearWeather` override is on
   - `sky->overrideWeather` is set (a quest or script `ForceActive`/`SetActive` override)
   - the sky is in interior mode, or there is no climate

   When armed, the old move-blend (`UpdateWeatherBlend`, `moveWeather`/`weatherWatch`) is off for the flight.
2. **Forecast at the move.** After the apex move (or half way on a flight without a move), it waits until the
   engine has set the arrival's weather region (`sky->region` changed or is one of the arrival cell's regions),
   for at most 1.0 s. If the region does not arrive, it uses the arrival cell's weather region with the highest
   priority. It then builds a `Request`:
   - region, climate, current weather (already after the engine's own region-change decision)
   - hours to the landing: the visual hours still owed, plus the rest of this flight's time-lapse (the
     `FlightTimescaleAt` curve integrated over the remaining share), plus the real-time remainder
   - the engine's elapsed at the landing, and `T`

   **EngineForecast** follows the engine's rule. If the elapsed time at the landing is at most `T`, it keeps the
   current weather. Otherwise it calls `region->SelectWeather()`, the engine's own routine, or rolls the climate
   list when there is no region. A `ForecastProvider` (`SetProvider`) can supply the weather first; this is the
   hook for `dev/weather-sim`. If it returns nullopt, the engine roll is used.
3. **Blend.** The engine starts the transition itself. One `Sky::Update` runs with `overrideWeather = forecast`
   (`lastWeatherUpdate` is set to now first, so the override cannot expire), and the engine's full weather-change
   path runs. Next frame the override is removed directly; we do not call `ReleaseWeatherOverride`, which would
   make the engine re-roll.
   - If the engine's own region change at the move had already started a transition: when it heads to the
     forecast, it is adopted at its current blend. Otherwise it is stopped at the weather the sky mostly shows;
     that happens under the cloud fade, a few frames after the move.
   - Progress: `t = smoothstep(max(time share, time-lapse-hours share))` from the start point. It is written as
     `lastWeatherUpdate = hour - t * transitionHours`, so the engine's own `pct` equals `t`. `lastWeather` and
     `pct` are written too.
   - The time-lapse ends at 85 % of the flight, so the blend completes there and the transition is closed
     (`lastWeather = null`). The rest of the descent is `Steady`.
   - A running transition blocks every engine roll. In `Steady` the weather clock is held at "now".
   - If the weather region changes again before the landing, the forecast is redone (at most 3 times).
   - The forecast is dropped (no lock, the game's weather from then on) if:
     - an override appears (quest or script)
     - the region weather is cleared (a script's non-override `SetActive`)
     - the weather changes some other way
4. **Lock at landing.** At touchdown (`Touchdown()`, before the catch-up steps) the forecast is the current weather
   at 100 % (`lastWeather = null`, `pct = 1`, accelerate off). Each frame after `TimeLapse::Tick` steps the clock,
   `lastWeatherUpdate` is set to the game hour. Raw `GameHour` is used, which is correct across the 24-30 midnight
   wait because the elapsed formula wraps the same way. The skipped hours therefore never count as weather time.
   Three frames after the catch-up ends, the lock is logged and the feature lets go. The weather clock restarts at
   the arrival hour, so the next natural change can come after `T` hours, as in the game.
5. **Edge cases.**
   - **Interiors:** not flown (CanFly), and the forecast drops if the arrival cell or sky mode is interior.
   - **No regions:** the climate roll is used, or the current weather is kept.
   - **Solstheim:** nothing special. Its region weathers work the same way; the scripted ash storms are overrides,
     so the feature is skipped.
   - **Aborted flights and rescues:** `EndFlight` before touchdown drops the forecast with no lock. A running
     transition then simply continues at the engine's speed.
   - **Very short trips** (no move): the forecast is made at half way and revised if the region changes.
   - **Landing before any forecast:** the visible weather is kept and locked; there is no snap.
   - **Game load:** cancelled; nothing is written to the save's sky.

## 4. ini

```
[Flight]
bArrivalWeather=1   ; also in the MCM-style page: "Arrival weather: forecast at the top, blend to it, keep it after landing"
```

The shipped `SKSE/Plugins/SeamlessFastTravel.ini` still has `bClearWeather=1` as the default, and with that on the
feature is skipped. The NGVO ini has `bClearWeather=0`, so it is active there.

## 5. Log lines (SeamlessFastTravel.log)

Lines to expect, with placeholders in braces:

- `Arrival weather: on (...)`, at settings load
- `Weather forecast: armed (weather {W} for {e} h, region {R}, climate {C} changes weather after {T} h)`, at take-off
- `Weather forecast: skipped ...`, which names the reason (override / bClearWeather / no climate)
- `Weather forecast ({x} s after the move): {F} [{kind}] for the landing at {hour} h ({h} h from now); {why} (by engine roll|<provider>); region {R} [{list with chances}]; climate {C} changes weather after {T} h; game weather now {W}`
- `Weather: stopping the game's transition ...` / `the game's own transition ... is the forecast`
- `Weather: transition {A} -> {F} started; blending ... ({d} h engine transition: fWeatherTransMin .., fWeatherTransMax .., transDelta ..)`
  (or `... is already the weather; holding it to the landing`)
- `Weather blend check: the sky's blend after its update {p}, ours {t}`, once at t >= 0.5. This shows whether the
  engine follows our clock; CS easing can make the two differ.
- `Weather: blend to {F} complete at {n}% of the flight`
- `Weather: touchdown on {F} at 100%; holding the weather clock through the time-lapse catch-up`
- `Weather: arrival locked: {F} at 100% at game hour {h} (region {R}); ... next change possible after {T} h (game hour {x})`
- `Weather check 30 s after the lock: {W} (forecast {F}) -> MATCH|MISMATCH`, which is the test's verdict line
- `Weather: arrival forecast dropped ({why}); the game's weather takes over`
- `Weather forecast ... revised: the weather region is now {R}`

## 6. Test plan

Use the user test character (see the memory note), Riverwood -> Riften Stables at 09:00, with `bClearWeather=0`,
several flights.

1. Per flight, check in the log:
   - `armed`
   - one `Weather forecast (... after the move)` line, with region = the Rift region and a weather list
   - `transition ... started` or `already the weather`
   - `blend complete` before touchdown
   - `touchdown on F`
   - `arrival locked: F`
   - **`Weather check 30 s after the lock: F (forecast F) -> MATCH`**. This is the pass criterion: the weather
     30 s after landing equals the forecast logged at the move.
2. Visual check:
   - no weather switch after touchdown
   - the cloud and light change happens in the air during the second half
   - no snap at the move beyond the cloud fade
3. Expect **both outcomes across runs.** Riverwood 09:00 plus about 10 h is well past T for most climates, so
   "rolled" is common. Riften overcast or fog should appear in some runs and clear in others, in proportion to
   the region's chances listed in the forecast line.
4. **Override test:** `fw <weather>` in the console (an override) before the flight. Expect
   `Weather forecast: skipped, a weather override is active`, and the override stays after landing.
5. **Abort test:** abort mid-flight from the menu. Expect `arrival forecast dropped (flight ended before the
   touchdown: ...; no lock)`.
6. **Short trip** (Whiterun -> Whiterun Stables, no move): expect `half way, no move on this flight`, then the
   lock and MATCH.
7. **Regression:** with `bArrivalWeather=0` the old move blend lines (`after the move (game blend ..)`) come back.
8. **Engine check:** the `blend check` line should show the sky's blend close to ours. If it sits near 0 or 1
   while ours is 0.5, the GMST transition length is wrong. The transition line names the GMST values, and
   `(GMST missing: default)` would point at it.

## 7. Future hook

`ArrivalWeather::ForecastProvider` (`Name()`, `Predict(const Request&) -> optional<Forecast>`) with `SetProvider`.
The request carries the worldspace, arrival cell and position, region, climate, current weather, landing
`GameDaysPassed` and hour, hours to the landing, the elapsed time at the landing and the change interval.
The weather sim can return any weather, and the blend and lock work the same. A nullopt return falls back to
the engine roll.

## 8. Open points

- [I] constants 1.0 and 1/255 in `T`, and the GMST identity of the transition length. Both are checked in game
  by the `blend check` and `GMST` log text.
- The global flag `[0x317ABA8]+0x340` bit 1 (it keeps the current weather and freezes `lastWeatherUpdate`) is not
  identified.
- The one-frame override briefly makes `Weather.GetCurrentWeather`-style script queries and CS's weather-lock UI
  see an override for one frame.

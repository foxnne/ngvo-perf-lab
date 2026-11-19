# NGVO perf lab protocol

Goal: 50 real fps (20 ms render frames) at 3440x1440 with DLSS Quality (0.67x), frame generation to ~100 presented fps,
no frame over 50 ms while sprinting, VRAM peak under ~13.5 GB of 16 GB so cell loads have headroom.

## Rules
- One driver: only one process drives the game at a time. Parallel agents may read logs, write code and research.
- Never benchmark while a build or other heavy job is running.
- One variable per run. Stamp every result with `state.py manifest` (bench.py does this).
- Fresh launch per repetition; first-visit effects exist (Faster Objects bakes a cell on its first visit, shader and
  texture caches warm up), so compare like with like and keep a warm-up pass out of the numbers.
- `stacksamp.ps1` suspends the game's main thread per sample. Never run it unattended or from a call that can be
  interrupted; prefer the Tracy build (`build/PR-Tracy`, capture with `ext/tracy/tracy-capture.exe`).
- MO2 rewrites the profile on launch: edit modlist/plugins/ini only with MO2 and the game closed.
- The DynDOLOD MCM settings loader re-applies LOD distances on load; change them in
  `mods/DynDOLOD - Settings Loader/MCM/Config/DynDOLOD/settings.ini`, not in skyrimprefs.ini.

## Driving the game
- Bridge: `http://127.0.0.1:8920/api/tool/<name>` (`harness/cs.py`). Keys go through the bridge (keyboard only).
- Launch: `ModOrganizer.exe moshortcut://NGVO`, wait for Main Menu, `game loadLast`, answer the SkyrimNet prompt with
  Delete History (right, enter).
- Ground movement: Onward. Stand on a road, tap C (auto-move), CapsLock toggles run, hold Shift to sprint.
- Flight: `tcl`, hold W; tgm on.

## Scenarios (bench.py)
plains (static, Whiterun exterior), sprint (Onward along the Whiterun road south), flight (no-clip line west-southwest),
forest, city, interior. Default tier: plains,sprint,flight.

## Tools
- CS frame recorder: render frames. PresentMon: presented frames incl. generated ones (needs the account in the
  local group "Performance Log Users" or an elevated shell).
- VramTracker: create `VramTrack.on` in the CS plugin folder; writes VramTrack.jsonl (per module|category + call sites).
- Tracy: deploy `build/PR-Tracy/Release/CommunityShaders.dll`, run bench with `--tracy`.
- `addrlib.py`: SkyrimSE RVA -> Address Library id. `llvm-symbolizer --obj=<dll> --relative-address --no-inlines`.

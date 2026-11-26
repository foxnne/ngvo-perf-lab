# RE: distant LOD during the fast-travel flight (Skyrim SE 1.6.1170)

Date: 2026-11-25. Offline only (no game launched). Source: in-memory `.text` dump
(`scratchpad/text_1170.bin`, see RE-grid-attach-2026-11-25.md for the method and the hook caveat),
Address Library `versionlib-1-6-1170-0.bin`, CommonLibSSE-NG headers (BGSTerrainManager/Node/Block/
Chunk, TESWaterSystem, PlayerCamera, TES, TESWorldSpace). Disassembly scripts: `scratchpad/lod/`.
Legend: **[V]** verified in the bytes, **[I]** inferred, **[?]** still open.

Code: Sky Above worktree `C:\Users\foxnn\dev\sky-above-wt-lod`, branch `flight/camera-lod`,
commits `a23d07e` (first version) and the review-fix commit after it. **Not built here** (the coordinator builds it in main after the merge).

---

## 0. Short answer

* **The LOD already follows the camera.** Every land, water, object and tree LOD decision is the
  **2D (x, y) distance from a view position** to a quadtree node, and both callers pass the camera:
  the per-frame job 39102 passes `PlayerCamera 50785` (camera node world position, or the cached
  `PlayerCamera::pos`), and the grid update 13288+0xC0F passes the scene camera's world translate. [V]
  That is why writing `PlayerCamera::pos` changed nothing: it was already the camera.
* **Water LOD is not a separate system.** The distant water is part of each terrain LOD block
  (`BGSTerrainBlock::water`, BTR water shapes). It is added to TESWaterSystem when a terrain chunk is
  attached (`BGSTerrainChunk::Attach` 31737 -> `TESWaterSystem::AddLODWater` 32209) and removed on
  detach (31739 -> 32210). So it rides on the same quadtree as the land. [V]
* **What follows the player** (not the camera):
  1. the **active grid** (`uGridsToLoad` around `TES::currentGridX/Y`): nodes overlapping it get
     `kInActiveGrid` and are always split down; LOD is hidden for loaded cells; [V]
  2. the **large-reference grid** (`uLargeRefLODGridSize`, 9 here) -> `kInLargeRefGrid`: object LOD
     always split, large refs shown as full models; [V]
  3. **per-cell LOD visibility culling** (31865): a bitset stored with the *player's* cell
     (`cell->exterior+0x10`, tested by 31973 with the node number) hides nodes the player's spot
     cannot see. Land checks the 3x3 cells around the player; **water checks the player's cell only**.
     It is skipped while `CameraAboveMaxHeight` (402260) is set. [V]
* **Altitude does not matter** to the level choice (z is ignored): a camera 10k up gets the same
  LOD4 under it as a camera on the ground. [V]
* **Refresh rate**: the job's partial update (type 0) refreshes **one top-level node per call**
  (`updateNodes[nextUpdateNode]`, round-robin). How many top-level nodes Tamriel has is not known
  offline [?] (the new log prints it).

So the mid-flight "broken land / missing sea rectangle" is not a wrong centre. The candidates, best
first: (a) culling by the parked player's cell (only possible if `CameraAboveMaxHeight` stays 0, i.e.
the camera is in the free-camera state or over the player's cell below its max height); (b) the
round-robin refresh plus async block loading lagging a fast camera (parent block gone before the
children are loaded: holes, and the water goes with its block); (c) the job guard window during
spread attach (short); (d) VRAM pressure (93% of budget seen earlier) slowing block loads.
The switches below separate these, and the log tells which one it is.

---

## 1. How Skyrim chooses LOD

### 1.1 Callers of `BGSTerrainManager::Update(mgr, const NiPoint3* viewPos, const int* type)` — 31802, RVA 0x50E430

| Caller | View position | type | Notes |
|---|---|---|---|
| Job_Partial_Terrain_Manager_Update **39102** (BSJobs thread) | `PlayerCamera 50785(cam, &out)` | 0 (partial) | mgr = `TESWorldSpace 20469(player->GetWorldSpace())` [V] |
| TES::UpdateGrid **13288+0xC0F** (main thread, on a grid shift) | `[[gWorldRootNode 403513]+0x128]+0xA0` = SceneGraph camera world translate [I: SceneGraph+0x128 = camera] | 2 (full objects pass) | skipped while a save loads; the call before it at +0xBF8 (get manager) is **hooked by another plugin** in this dump [V] |

`PlayerCamera 50785` [V]: under the camera lock, if `isProcessed` (+0x163) is set it returns the cached
`pos` (+0x144). Otherwise it returns `cameraRoot->world.translate`, except in first person with the
player as target, where it uses the player's 3D, or position plus eye height. Then it caches the result.
`20469` returns `worldSpace->terrainManager` (+0x90), following `parentWorld` when the world uses the
parent's LOD. [V]

### 1.2 Inside Update [V]
* Every call copies the INI values into globals (31859): `fBlockLevel0Distance²` -> 0x315B8D0,
  `fBlockLevel1Distance²` -> 8D4, `fBlockMaximumDistance²` -> 8D8, `fTreeLoadDistance²` -> 8DC,
  `fSplitDistanceMult` -> 8E0, two level thresholds (8E4 terrain, 8E8 objects), `uGridsToLoad` -> 8EC,
  `uLargeRefLODGridSize` -> 8F0. (The console handler 22838 writes the first three settings; this is how
  they were identified.)
* **CameraAboveMaxHeight (0x315B6A1)** is set to 0 on every call. It is then set to 1 when the game is
  not in an interior, the camera is not in the free-camera state (`cameraStates[3]`), and the player has
  a parent cell, *and* either `TESObjectCELL 19037(playerCell, viewPos)` fails (the camera is outside the
  player's cell) or the camera is higher than that cell's max-height grid plus a constant (379919).
* The rest runs under `CameraTerrainLock` (402330): type 2 does `31835(root, viewPos, playerCell, 0x22)`
  and then `TES 13414`. Type 0 updates one node from `updateNodes` with `31828 -> 31835(node, viewPos,
  playerCell, 7 | 0x20 if kInLargeRefGrid)`, then the immediate-update list, then `31915` (finish block
  loads and attach them).

### 1.3 Per node, 31835 [V]
1. It sets `kInActiveGrid` (bit 14) or `kInLargeRefGrid` (bit 15) when the node overlaps the TES grid of
   size `uGridsToLoad` or `uLargeRefLODGridSize` (player-centred).
2. It calls the visibility culling `31865(node, playerCell, 0)` for land and `31865(node, playerCell, 1)`
   for water. Each returns true (visible) when: the switch **379910** is 0, CameraAboveMaxHeight is 1,
   or a Solitude special case applies (nodes 0x62D, 0x62E and 0x632 while the player's cell has x < -8
   and y > 22). Otherwise the result is the bit in the cell's visibility bitset: the 3x3 cells around
   the player for land, the player's cell for water.
3. Then it runs the layers: terrain 31836 (bit 0), objects 31837 (bits 1 and 5), trees 31838 (bit 2),
   and recurses into the 4 children.

### 1.4 Split / load rules (distance = 2D distance from viewPos to the node's square, 31871) [V]
| Layer | Rule | With this list's SkyrimPrefs (`fSplitDistanceMult=1`, L0 100000, L1 180500, Max 327680, Tree 233155) |
|---|---|---|
| Terrain + water LOD (31836) | always split when `kInActiveGrid`; else split when dist < `fSplitDistanceMult x 0.707 x L x 4096` | LOD8 -> LOD4 inside 23.2k, LOD16 -> 8 inside 46.3k, LOD32 -> 16 inside 92.7k |
| Objects (31837) | unload beyond `fBlockMaximumDistance`; always split when `kInLargeRefGrid`; level 8 splits at `L0² x NAMA`, level 16 at `L1² x NAMA`, level 32 always | LOD4 objects inside 100k x sqrt(NAMA), LOD8 inside 180.5k |
| Trees (31838) | `fTreeLoadDistance` | 233k |

Block loads are queued with `31914` on the loader at 402263 and finished in `31915`, asynchronously.

### 1.5 This list's terrain LOD textures (foxnne - xLODGen Terrain 2026-11-21)
| Level | Tile size | Units per texel |
|---|---|---|
| 4 | 512 | **32** |
| 8 | 512 | 64 |
| 16 | 512 | **128** |
| 32 | 2048 | 64 |

LOD4 at 32 units per texel is what the user saw as "blurry flat snowfields". LOD16, which covers 46k to
93k from the camera, is the blurriest level of all.

---

## 2. Code changes (branch `flight/camera-lod`)

`Source/src/Plugin.cpp`, new `namespace FlightLOD` (after `SpreadAttach`), plus documentation in
`SKSE/Plugins/SeamlessFastTravel.ini`. 1.6.1170.0 only. Byte check: 31865+0x1C must be
`cmp byte [rip->379910],0`. If a check fails,
the feature turns off and the log says why.

| Switch (`[Flight]`) | Default | What it does |
|---|---|---|
| `bFlightLODNoCulling` | 0 | At take-off it saves the culling switch (379910), sets it to 0 and restores it in `EndFlight` (every exit path). Side effect: LOD hidden behind mountains is drawn (a little more GPU). It writes data only and installs no hook. |
| ~~`iFlightLODPumpCalls`~~ | removed | Review round 2 (coordinator decision): extra LOD updates are dropped from this branch. Running them on the main thread could race with the job. A job-thread wrapper clashed with flight/apex-stall, which is rewriting the same stub with an in-job handshake. The stub is back to main's direct `skip / jmp 31802`. If the round-robin turns out to be the bottleneck, revisit after that merge. |
| `bFlightLODLog` | 1 | Once a second while flying, main-thread state only: eye position (camera root), camera state index (3 = free), distance to the player, TES grid, interior, whether the culling override is on, and whether the terrain job is skipped for spread attach. It reads no manager fields and not `PlayerCamera::pos`, which 50785 also caches from the job thread. |
| `fShortHopLODHeight` | 0 | Carried trips only (not parked): runs `TerrainArc` again with this value as the clearance above the treetops (ramped in over the first and last quarter of the trip, at least 6144) and raises the arc if needed, capped at 100k. With bSmoothArc it lengthens the flight by the same sqrt factor as the other raises. |

Review fixes (Codex, 2026-11-25 21:14 and 21:26):
* Everything checks the exact runtime `1.6.1170.0` before any ID is resolved: the log, the culling
  switch, and `fShortHopLODHeight` (via `FlightLOD::ExactRuntime`).
* Bools read through `ReadBool`, so NaN and inf count as off. Floats are checked for finite values and
  clamped.
* The culling byte is written only on the main thread: at take-off, and at the end of the flight or a
  game load during one. The saved value is restored exactly. Both writes go through
  `FlightLOD::BeforeCullWrite()`, a marked **TODO hook** where the apex-stall branch's "terrain job idle"
  handshake will be called at merge time.
* The short-trip log reports the clearance actually reached (`MinClearance`: same sampling, after the
  cap), marks `(capped)`, and tells apart "too short" (no point far enough from both ends), "no terrain
  samples under the middle of the path" and a missing height grid for the worldspace.

`TerrainArc` gained optional `a_clearance` / `a_ramp` parameters (the defaults behave as before).

Not done, and why:
* **Moving the active or large-ref grid to the camera.** That would mean faking `TES::currentGridX/Y`.
  31835/31841 read it on the job thread, but the cell attach code reads it too: unsafe.
* **Changing `uLargeRefLODGridSize` at run time.** 31859 re-reads it every update, so it would take
  effect, but the large refs already attached stay. You would get object LOD and full models on top of
  each other.

---

## 3. Short hops: numbers (task 3)

Today: trips under 40k use arc = clamp(0.25 x d, 7000, 50000), plus `fCamHeight` 1500. That puts the
camera 8.5k–11.5k above the mean of the two ends, matching the 7–11k the user saw. The carried player
keeps the 5x5 grid under the camera. Full-detail land ends 6144 to 10240 units out horizontally (the grid
re-centres 4096 from the centre cell's middle). Past that, LOD4 terrain sits under the **9x9 large-ref
mountains** (full models out to about 14.3–18.4k): that is the "LOD land through mountain meshes".

The camera has to be far enough away that a LOD4 texel (32 units) stays small on screen. At 3840 px
across an 85° horizontal FOV, one pixel is 3.86e-4 rad.

| Target | Slant distance D | Camera height above the grid edge: H = sqrt(D² - 6144²) |
|---|---|---|
| today, 10k up | 11.7k | 32 units ≈ 7 px per texel (blurry, as seen) |
| 3 px per texel (acceptable) | 27.6k | **≈ 27k** |
| 2 px per texel (good) | 41.4k | **≈ 41k** |
| 1 px per texel (sharp) | 82.9k | ≈ 83k (not practical) |

At 2560 px wide, divide these by 1.5 (about 18k and 27k).

Cost: for a 30k hop at `fShortHopLODHeight=27000`, the arc is about the same as the trip length. With
bSmoothArc that makes the path (and the flight) about 2x longer, and the climb is steep.

**Cheaper alternatives (no code):**
1. Regenerate xLODGen terrain LOD4 at **1024** (16 units per texel). Then 2 px per texel is reached at
   20.7k, about H 20k. At **2048** (8 units per texel) it is reached at 10.4k, so the current arcs are fine.
   LOD16 should go to 1024–2048 as well. Costs: disk (1536 LOD4 tiles x 4 at 1024 ≈ 4x today) and a
   little VRAM (about 16 LOD4 tiles near the camera).
2. A modest `fShortHopLODHeight` of 15–20k together with option 1 at 1024.

The intersection smears come from the large-ref ring. Height only shrinks them on screen; only better LOD
(or DynDOLOD terrain underside / seasonal LOD fixes) removes them.

---

## 4. What to test (user, in game)

1. **Baseline log:** build the branch and fly the Solitude trip that broke, with everything at defaults
   (only the log on). In `SeamlessFastTravel.log`, read the `Flight LOD:` lines:
   * `camera state 3` mid-flight means culling is active (CameraAboveMaxHeight is never set in the free
     camera state). Test step 2 either way.
2. `bFlightLODNoCulling=1`, same trip. If the sea rectangle and the broken land are gone, the cause was
   culling by the player's cell.
3. If culling off does not fix it, the cause is most likely refresh or load lag. The extra-updates switch
   was removed from this branch; revisit after the apex-stall merge.
4. Short hop under 40k (for example Riverwood to Whiterun, west side): `fShortHopLODHeight=20000`, then
   `27000`. Compare the snowfields and the mountain smears, and how the flight feels.
5. Regression: the hero tree and the spread-attach landing, interiors, and the world map opened mid-flight (it writes 379910 as well).

## 5. Risks

* **bFlightLODNoCulling** writes an engine byte that the terrain job reads in 31865. A byte write is
  atomic on x86, and the job reads it once per node. Until the apex-stall handshake is wired into
  `BeforeCullWrite`, one job pass may see a mix of old and new values (some nodes culled, some not, for
  one frame).
* **bFlightLODNoCulling:** a game load during a flight restores the switch (`kPreLoadGame`). After a
  crash nothing persists, because the switch is process memory. Opening the world map mid-flight writes
  1 (53147); the end of the flight then restores the value saved at take-off.
* All IDs and offsets are for 1.6.1170 and checked against the dump. A plugin hooking 31865 turns the feature off (byte
  check).
* Open [?]: the top-node count (no longer logged; needs a job-side read after the apex merge); whether the flight camera is ever in the free state; the exact
  value of the max-height margin (379919).

## 6. Build status

Not built in this session. The coordinator builds after merging to main. The worktree holds a
`--shared` CommonLibSSE-NG clone at 6ef06fb (gitignored, about 360 MB): delete it after the merge.
This code has never been compiled, so expect small compile fixes.

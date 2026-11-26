# The stall at the top of the arc: what is in the move frame, and what now spreads it

Date: 2026-11-25 (evening). Offline work only: dumps, code and reverse engineering; nothing was run in the game.
Companions: `RE-grid-attach-2026-11-25.md` (grid attach call graph, ids), `RESEARCH-flight-streaming-2026-11-25.md`.

Branches:
- **Sky Above:** `flight/apex-stall`, worktree `C:\Users\foxnn\dev\sky-above-wt-apex`, commit `8dfebf4`. **Not built:** the worktree
  has no configured build tree, and the one-time configure was refused by the permission check. It was syntax-checked with
  `cl /Zs` against the main build's exact flags (it passes, and an injected error is caught).
- **Community Shaders:** `foxnne/merge-rc2-1123`, two HitchSampler commits, `f06075838` and `227510ce6`. Not built.

Legend: **[V]** verified in the dump's bytes or in the samples. **[I]** inferred.

---

## 0. Short answer

Since the cell read-ahead and the spread attach, a move frame of about 300 ms is roughly:

- **~50%: the start area going away**, all of it at once in `GridArray::Shift → DetachAll`:
  - 3D teardown;
  - Havok removal;
  - Community Shaders' grass removal;
  - exterior-buffer evictions.
- **~27%: a main-thread spin on an IO task.**
- **The rest:** the centre cell's attach, the Havok world shift, the render, and the 38 ms the sampler does not see.

The destination side is already small. Most of what is left is the **start** side, and that can move into the climb. This
branch does exactly that (`bEarlyDetach`, **experimental and off by default since the Codex review, §4.5**): one start
cell per frame between 15% and 42% of the flight, using the grid's own detach, keeping the 3x3 around the player. It also loads the destination's centre cell on the engine's own background loader (`iQueueDestinationCells`), and it
attaches the destination centre-out under a time budget (`iAttachSlotsPerFrame` / `fAttachBudgetMs`).

**Expected move frame:** roughly 300 → 120–170 ms on the first try. This is an estimate; the next test settles it. What remains
then:
- the IO-task spin, whose caller the deeper sampler will now name;
- the world shift;
- the render.

---

## 1. Data used, and its limits

- **Dumps:** 302 files in `SKSE/HitchSamples`. The move frames were picked out by their signature: an IO-task wait
  (`75633/75695/75676`), plus Havok remove/shift, plus 3D release (tool: `harness/apex_buckets.py`).
  - **Frames since the read-ahead (12:28 onwards):** six frames of 301–342 ms, at 12:28:40, 15:57:31 (the terrain-job crash
    frame), 16:07:09, 18:38:11, 19:28:01 and 20:58:11.
  - **Frames from before it:** two, of 457 and 529 ms (12:00 and 12:02).
  - Today's typical 220–286 ms move frames are **not** in the dumps: the threshold was 300 ms. So the analysed frames are the
    worse half of the distribution, but they have the same shape.
- **Sampling coverage:** samples start 38 ms into the frame and come every ~1.6 ms (`Sleep(1)`).
- **Stack depth:** exe chains are a stack scan, kept to 6 return addresses. That is too shallow to reach the caller of a wait
  (`13288`/`13430` show in only ~5% of samples). Buckets are therefore by **leaf subsystem**, not by caller. Fixed for the next
  test (§5).
- **Community Shaders names:** CS offsets resolve only for the 20:58 dump, which matches the deployed 19:58 PR-Tracy PDB. In
  older dumps the "CS (old build)" bucket is, by the same signature, almost all `GrassBucketStore`.
- **Sky Above log:** it is rewritten at every start. The move-timing lines of the afternoon tests are gone, so dumps cannot be
  matched to flights by time. The dump file names now carry the time (§5).

---

## 2. Breakdown of the move frame

The move frame is the frame of the `SetPosition` at u = 0.5. The grid update in `Main::sub 36581 → 13288` runs later in the
same frame.

Values are ms of the frame, from samples × (frame − 38 ms) / samples.

| bucket (what the main thread is in) | 20:58 | 19:28 | 18:38 | 16:07 | 15:57 | 12:28 | **typical** |
|---|---|---|---|---|---|---|---|
| IO-task wait: steal-or-spin (`75706 → 75633 → vfunc+0x20 → 75695 → 75696 → 75676`) | 80 | 78 | 77 | 78 | 98 | 73 | **~80** |
| 3D teardown (`NiNode::DetachChildAt 70294 → BSFixedString/BSStringPool::Release → BSMultiStreamInstanceTriShape 76328 → EngineFixes free`) | 65 | 43 | 54 | 39 | 55 | 41 | **~50** |
| Havok (`13288+0x837 → 77909 → 77910/77911 → 61307 → hkp3AxisSweep`; `SetCenter 15941 → 19196 → 78632 → 77837 → 61409 → hkp3AxisSweep`; `77918` add) | 46 | 61 | 20 | 60 | 30 | 59 | **~45** |
| Community Shaders `GrassBucketStore` (`QueueEvent`/`RemoveEngineGroup` from the grass-shape destructor; `EndFrame → DrainPending → ApplyRemoval/ApplyCapture`) | 25 (+~10 other CS) | 48 | 39 | 44 | 42 | 56 | **~40** |
| render (`BSBatchRenderer` 1076xx on the main thread) | 27 | 33 | 25 | 10 | 35 | 33 | **~27** |
| engine grass (`GrassManager 15375`) | 2 | 8 | 7 | 12 | 0 | 8 | ~6 |
| CELL record reads (`20460 → 20456 → TESFile`) | 2 | 0 | 2 | 3 | 0 | 2 | **~2: the read-ahead works** |
| not sampled (first 38 ms) + other | ~50 | ~50 | ~70 | ~55 | ~70 | ~55 | |

The two frames from before the read-ahead (12:00, 12:02; 457 and 529 ms) had:
- **CELL records:** 112–141 ms;
- **Actor::Predestroy:** 36 ms (`40288 → 37175 → 37176 → 41336/41331`).

The read-ahead removed the first. Predestroy has not shown since, but one sample is little evidence.

### What each bucket is

- **IO-task wait, ~27% [V for the mechanism].**
  - **What runs:** `IOManager::Func17` (75706) loops. Each pass calls `BSTaskManager::Func17` (75633). That function tries to
    take a queued task out of the IO queue to run it inline (vfunc +0x20: a lock-free split-ordered hash, 75695 → 75696 →
    75676, with an `mfence` per node).
  - **Why it spins:** while a worker is running that task, the take fails. The main thread then bumps a counter
    (`[0x3275DF8]`) and walks the queue again. So it waits for a specific background task, and every pass costs a full walk
    of the queue.
  - **Who waits:** cut off by the 6-deep chain. In one 12:02 sample the chain is
    `20460+0xA1 → 75712 IOManager::sub → 75643 → 19084`: the main thread reaching into the loader for a cell.
  - **Suspects [I]:**
    - the exterior-buffer evictions of the big detach (`13434 → 13721`), which unload cells whose references still have tasks
      in flight;
    - the centre cell's references waiting on their queued 3D.

  The first suspect moves into the climb with the early detach; the second becomes cheaper with the cell queue.
- **3D teardown [V]:** the start grid's scene graph freed in the move frame. That includes the grass shapes:
  `BSMultiStreamInstanceTriShape`'s destructor, which Community Shaders hooks (`QueueEvent` sits under it).
- **Havok [V]:**
  - the **remove batch** of the 25 start cells (13288+0x837 → 77909);
  - the **world-origin shift** of the broadphase at `SetCenter` (it walks every body still in the world);
  - the **add flush** of the centre cell.
- **Community Shaders `GrassBucketStore` [V, 20:58 only]:**
  - removal events queued per grass group as the engine destroys grass;
  - then `DrainPending` applies all of them at `EndFrame` in that same frame.

  This is ours (CS fork). A per-frame cap in `DrainPending` would spread it (§6). The early detach already spreads its cause.
- **Render:** the normal draw on the main thread plus first draws. It is not streaming as such.

### The frames after the move (current session, 20:58)

- **The 50–60 ms frames:** present pacing. Community Shaders' `DX12SwapChain::Present → HDRDisplay` waits in `D3D12Core` and
  FSR frame generation. Not streaming.
- **One 245 ms frame, 1 s after the move:** Neural Rendering's `D3D12Interop::BeginD3D12` waiting on the GPU, under
  `NeuralRendering::Evaluate`. Same finding as at midday: VRAM pressure. Not CPU work.
- **The 50–120 ms frames of the "Move timing" line:** most likely the spread attach (3 slots per frame). Below 300 ms, so not
  dumped. The new budget makes them one slot per frame unless a slot is cheap.

---

## 3. The plan

| # | step | moves out of the move frame | status |
|---|---|---|---|
| 1 | **Early detach:** the start grid a slice per frame during the climb | 3D teardown, Havok removal, CS grass removal, buffer evictions, maybe the IO spin: **~120–150 ms** | built (`bEarlyDetach`) |
| 2 | **Destination centre cell on the background loader** (door-preload path) | reference creation for the centre cell, part of its Havok/3D, maybe the IO spin | built (`iQueueDestinationCells=1`) |
| 3 | **Attach budget, centre-out** | the 50–120 ms frames after the move | built (`iAttachSlotsPerFrame`, `fAttachBudgetMs`) |
| 4 | Terrain LOD keeps following the camera during the climb (the job is held off only during our slices) | — (keeps the other agent's camera-centred LOD working) | built (handshake in the job guard) |
| 5 | Name the IO-spin owner with deep chains | — | built (CS sampler, 24-deep exe chains) |
| 6 | CS `GrassBucketStore::DrainPending` cap per frame | the residual CS grass cost, if any | proposed (CS fork) |
| 7 | Second pass of 13430 (activation) spread over frames | only if the log's "final pass" turns out large | proposed |
| 8 | Neural Rendering paused/lowered for the second after the move | the 245 ms GPU-side frame | proposed (CS export, like `BottledShaders_GetCloudDeck`) |

### Why not move the player to a holding position

Any move of the parked player is another big move, with the same detach, and right next to the start. The engine's own
per-cell detach (`GridCellArray::Detach`, the call `GridArray::Shift` makes for every slot) does the same work in pieces, and
the player can stay in their cell. That cell is the only one kept attached.

---

## 4. What was implemented (Sky Above, `flight/apex-stall`)

### 4.1 Early detach (`SpreadAttach::Early`)

- **At take-off of a parked apex flight (not carriages), after self-checks:**
  - the player's cell is the grid centre (`TES::currentGridX/Y`);
  - every slot holds the cell `(currentGridX − half + x, currentGridY − half + y)`;
  - the grid's vtable slot 5 is the game's `GridCellArray::Detach` (15955), and its prologue bytes match.

  It then lists the attached slots outside `iEarlyDetachKeepRadius`: outer ring first, and within a ring the cells **behind**
  the flight first, so the camera, which looks ahead, sees the cells it flies over switch to LOD last.
- **Every frame while the flight time is between `fEarlyDetachStart` (0.15) and `fEarlyDetachEnd` (0.42):** detach
  `iEarlyDetachPerFrame` (1) slots, wrapped as follows:
  - the engine's own Havok remove batch, `77908` … `77909(world, 0)`, which flushes once per slice. Bytes are checked; the
    world comes from the pointer-to-pointer global, as in the fix for the 08:31 crash;
  - the terrain-job handshake (§4.4).

  A slot is skipped if it no longer holds the planned attached cell. Everything stops if the grid moved.
- **At the move:** the grid shift's `DetachAll` finds only the centre cell (and any slots not reached). Empty slots are skipped
  (null check in 15955).
- **Flight ends before the move** (rescue, death, menu, new trip): if the player is still within a cell of the start and the
  grid has not moved, the detached slots go into the spread-attach queue. `EndFlight`'s `Flush` then attaches them (and runs
  13430's second pass).
- **Game load:** dropped (`kPreLoadGame`). This also fixes an existing gap: a load in the middle of the drain used to leave the
  spread-attach queue armed, with slots from the old grid.
- **Why it should be safe:**
  - The engine never re-fills an empty slot without a grid shift: the attach loop is only in the shift path of 13288 [V].
  - Everything found that walks the grid null-checks its slots [V]:
    - engine: 13414, 13440, 13319;
    - CS: LODShadows, UnifiedWater;
    - Sky Above's own grid readers.
  - "Only the player's cell attached" is exactly the state the spread attach already leaves after every move. It is only
    longer here.
  - The exterior detach does **not** clear the Havok step flag `+0xC5F9`; only interior cells do (19130+0x189 tests
    `cell+0x40` bit 0, the interior flag, before the write at +0x19D) [V].

### 4.2 Destination cell queue (`DestCellQueue`)

- **What it calls:** `TES::QueueCellLoad` (13378 → `CellLoaderQueue` 18540), the engine's **door preload** path. Bytes are
  checked.
- **When:** one cell at a time, the next only when `Pending (18548) == 0`. It starts after the early detach is done (or at 5% of
  the flight if the detach is off), so the buffer churn of the detach comes first.
- **Which cells:** cells already loading, loaded or attached (`cellState` ≥ 3, the 13308 test) are skipped.
- **At the move:** it logs what it reached, including the arrival cell's state (6 = loaded).
- **Size:** `iQueueDestinationCells=9` is the 3x3. The old 25-at-take-off queue (`bPreloadDestinationCells`, froze once) is
  untouched and stays off.

### 4.3 Spread attach

- The queue is sorted **centre-out**.
- Each frame attaches one slot, then more while the frame's attach time is below `fAttachBudgetMs` (8), up to
  `iAttachSlotsPerFrame` (3). It used to be a fixed 3.
- Every frame's slots go in one add batch.
- New log line: `Spread attach: all grid cells attached X ms after the move, over N frames; worst frame, worst slot, final pass`.
  The final pass is 13430's activation pass, which decides step 7.
- `Install` now also checks the bytes of 77905/77906/77908/77909. If they are wrong, the spread attach is not installed.

### 4.4 Terrain job guard, extended

- **Before:** a byte flag skipped the job's call to `BGSTerrainManager::Update` (39102+0x5D → 31802) for the whole drain after
  the move.
- **Now (after the Codex review, §4.5):** one hold flag and an in-job counter.
  - The job counts itself in (`lock inc`) before it reads the hold flag, and out after 31802 returns.
  - The main thread sets a hold bit, then waits for the count to reach 0 before **any** grid change of ours. If the wait gives up
    after 20 ms, the change is deferred to the next frame, never forced.
  - So the job is held off **only while one of our slices changes the grid**, and terrain LOD keeps following the camera in
    between. That matters for the camera-centred LOD work.
- **Why calling through 31802 is safe:** the stub now calls 31802 through its own aligned frame. 31802 takes three register
  arguments and no stack arguments: it is called with rcx/rdx/r8 from both sites, and its prologue reads only its home space
  [V].
- **Size:** the stub is ~75 bytes in the shared 256-byte trampoline (it was ~40).

### 4.5 Changes after the Codex review (`results/codex_reviews/sky-above-fast-travel_flight-apex-stall_20261125-2126.md`)

1. **Terrain-job handshake, done properly.**
   - **The stub** (one clearly marked block, `// ---- apex-stall stub`): counts in, reads one hold byte, calls 31802 or leaves,
     then counts out.
   - **The main thread:** `HoldTerrainJob(bit)` sets a bit and waits for the count to reach 0. There are two bits: drain and
     slice.
   - **Every grid change waits first:**
     - **the apex move:** `ReadyForMove()` before `SetPosition`. If a job is still inside after 20 ms, the move waits a frame,
       and the log says how many;
     - **each spread-attach frame** and **each early-detach slice;**
     - **the re-attach after an abort:** it goes through `Drain`.
   - On timeout the change is deferred, never forced. `Flush` no longer bypasses anything: what it can't do now, `Drain` does
     in the next frames.
2. **Grid identity on every deferred slot.** Each queued attach and planned detach carries worldspace, grid origin and a
   generation.
   - **The generation:** `ObserveGrid` (every player update, and inside each use) bumps it on any change of worldspace, origin,
     or interior/exterior.
   - **On a mismatch:** a slot of another grid is dropped with a log line, the deferred second pass is dropped, and the early
     detach stops (or does not re-attach).
3. **Early detach:** off by default (`bEarlyDetach=0`, experimental), and it never detaches inside the 3x3 around the parked
   player (`iEarlyDetachKeepRadius` is now 1..2).
4. **Centre cell:** requested at take-off, even with the loader busy (one cell, as a door does). Further cells (3x3) follow only
   when the loader is idle, and no longer wait for the detach list. `AtMove` logs the cached arrival cell's state (no 20460
   lookup in the move frame).
5. **Budget:**
   - the frame's time counts from before the terrain-job wait;
   - another slot only while under budget (the first always);
   - the second pass (13430) goes to the next frame if the slots used the budget up. It is dropped if the grid changed
     meanwhile.

   The Havok add batch is still closed in the frame it was opened: an add batch left open across frames would keep bodies out
   of the world, so that is not deferrable.

### 4.5b Round 2 of the review (`..._20261125-2135.md`)

1. **Interception limited to one loop.**
   - **Opening:** `Arm` (at the move) opens a capture, and only the next 13430 attach loop is taken.
   - **Closing:** after all n×n slots, on a slot seen twice (a new loop), or at the next player update. The loop runs
     synchronously inside 13288 on the main thread, so it is over by then.
   - **Other calls:** a later native grid update and our own second pass go straight through.
   - **Draining:** tracked separately (`g_arm`).
2. **Centre cell:** the request is sent in the take-off update itself (`Start` then `Tick`).
3. **Flush:**
   - **Landing:** nothing forced; the drain goes on at its per-frame budget, and the log says how many slots were left.
   - **Abort or rescue:** the rest at once, unbudgeted, with a log line `abort flush of N slots took X ms`. Still behind the
     terrain-job wait.
   - **Measured but not budgeted:** the first slot of each frame and the Havok add-batch close. Both are reported in the "all
     grid cells attached" line.
4. **Community Shaders readers of cells and land: investigation (code read, CS fork `foxnne/merge-rc2-1123`).**

| feature | what it reads | thread | kept across frames? |
|---|---|---|---|
| **LODShadows** `CollectScene/CollectTerrain` | `tes->gridCells` slots, `cell->cellLand->loadedData->mesh` | main thread (render setup), under the engine's terrain spin lock | `NiPointer<BSGeometry>` (owning); slots and land are re-read on each collection. A detached land's mesh stays alive until the next collection drops it, so a stale shadow caster for up to one collection, not a dangling pointer. |
| **UnifiedWater** `BGSTerrainNode_UpdateWaterMeshSubVisibility` | `gridCells->GetCell`, `cellState` | inside `BGSTerrainManager::Update` (31802): **the terrain job (39102)**, or the main thread at 13288+0xC0F | no. The job path is exactly what our hold covers (the job is out of 31802 before any grid change). |
| **UnifiedWater** `BGSTerrainBlock_Attach/Detach` | terrain LOD blocks (not cells) | inside the terrain manager, as above | own caches of LOD water shapes |
| **LandscapeSeams** `TESObjectLAND_SetupMaterial` + `IsBlended/Bind/Sweep` | `land->loadedData` (quads, mesh) | the hook runs **inside the land attach** (main thread, i.e. inside our attach slot); `Bind`/`IsBlended` at draw (main thread) | `BSGeometry*` keys plus geometry it holds a reference to. `Sweep` frees them when it is the last owner, so no dangling pointer after a detach. |
| **TerrainHelper** `TESObjectLAND_SetupMaterial` | `land->loadedData` texture sets | inside the land attach (main thread) | texture-set handles only |
| **GrassOptimizations** (`GrassBucketStore`, `GrassMeshLibrary`, `GrassBucketBuffers`) | grass shapes' instance data, copied on the main thread at capture | 3 own worker threads | **own copies** (`sourceData`) and shape records whose lifetime is tracked (`registered`/`current` atomics); no cell or land pointers |
| GroundFog, SnowDeformation, FootstepParticles, SnowCover | `GetParentCell()` / `ForEachReferenceInRange` | main thread | no |

**Conclusion [I, from code reading]:** no CS feature reads cells or land on another thread while we change the grid. The
renderer's scene work (`BSBatchRenderer`) runs on the main thread, as the samples show; the CS "render thread" is the
DX12/Neural Rendering present thread, which does not touch cells. The cross-frame holders own references rather than raw cell
or land pointers. The one off-thread reader is UnifiedWater inside 31802, and the terrain-job hold covers it.

**So a render fence does not look necessary** for the spread attach or the early detach. Still unaudited:
- engine-side job threads other than 39102 that read the grid (none found in the dump scan, but not proven);
- other plugins (DynDOLOD DLL, NGIO, SPS).

That is the remaining reason `bEarlyDetach` stays off by default until a test.

### 4.6 INI switches (`[Flight]` in `SeamlessFastTravel.ini`)

| key | default | meaning | A/B to "as before" |
|---|---|---|---|
| `bEarlyDetach` | **0** | EXPERIMENTAL: start grid detached in slices during the climb | 0 |
| `iEarlyDetachKeepRadius` | **1** | rings kept around the parked player's cell (1 = 3x3, the minimum; 2 = nothing detached) | — |
| `iEarlyDetachPerFrame` | 1 | slots detached per frame | — |
| `fEarlyDetachStart` / `fEarlyDetachEnd` | 0.15 / 0.42 | window as a share of flight time (move at ~0.5) | — |
| `iQueueDestinationCells` | 1 | destination cells loaded on the engine's loader, one at a time (0 off, 1 centre, 9 = 3x3) | 0 |
| `iAttachSlotsPerFrame` | 3 | spread attach: at most this many slots per frame | 3 |
| `fAttachBudgetMs` | 8 | spread attach: another slot only while under this many ms | 100 (≈ the old fixed 3) |

Unchanged: `bSpreadAttach`, `bReadAheadCells`, `bPreloadDestinationCells` (stays 0), `bPreloadDestination`.

The startup log line `Apex streaming: ...` echoes all of these.

---

## 5. Community Shaders sampler changes (`foxnne/merge-rc2-1123`, not built)

- **`f06075838`:** `kDumpMs` 300 → **120**. Dump names now carry the local time, e.g. `frame55260_317ms_205811.523.txt`, so a
  dump can be matched to the Sky Above log line.
- **`227510ce6`:** each sample keeps **24 exe return addresses** (was 6) from **32 KB** of stack (was 6 KB). That is deep enough
  to reach `Main::Update` from a Havok or IO wait and finally name the IO-spin owner.
  - The log line still groups by the innermost 6.
  - Cost: a 32 KB memcpy per sample while the thread is suspended, a few microseconds.

---

## 6. What to measure in game

**Same route both ways, three flights each** (e.g. Whiterun Stables ↔ Windhelm Stables; parked camera-only flights, so
distance > `fJumpDistance`).

| run | ini |
|---|---|
| A (today) | `bEarlyDetach=0`, `iQueueDestinationCells=0`, `fAttachBudgetMs=100` |
| B | defaults: A + `iQueueDestinationCells=1`, `fAttachBudgetMs=8` |
| C | B + `bEarlyDetach=1` (experimental) |

**`SeamlessFastTravel.log`, per flight:**
- `Early detach: 24 start cells to detach ...`, then `Early detach: N/24 start cells detached before the move (X ms over K
  frames, worst Y ms)`. **Expect** N = 24, a worst slice of ≤ 10–15 ms, and frames in the climb no worse than 1–2 ms more on
  average.
- `Destination cell (x, y) queued ...`, then `Destination cell queue: ... arrival cell state S`. **Good:** S = 6 at the move.
- `Move timing [...]: move frame X ms; next N frames ...`. **The number:** today 220–300. **Target:** under 150 with B, lower
  with C.
- `Spread attach: all grid cells attached ... worst frame, worst slot, final pass`. Worst frame should be around one slot. The
  final pass decides step 7.

**Dumps:** `SKSE/HitchSamples/*_HHMMSS.mmm.txt`.
- `python harness/apex_buckets.py --since HHMM`: the same buckets as §2.
- `python harness/hitch_report.py --dump`: the deep chains. Look for the caller above `75706` (the IO spin) and above `77918`.

**By eye, during the climb (live view):**
- holes or popping where the start area switches to LOD behind the camera;
- terrain LOD following the camera (it should, between slices);
- the start area's NPCs.

**Safety:**
- One flight aborted mid-climb (die, or let a rescue trigger), and one save loaded mid-climb. The log should show
  `Early detach: attaching N start cells back` (abort), and a clean load.
- Any crash in `hkp3AxisSweep`, `39102`/`31802`/`13414`, or `TESObjectCELL 19130`.

---

## 7. Risks

- **Not built and not run.** Only syntax-checked. The Xbyak stub, the vtable call and the handshake are new code paths. Watch
  the first flight's log for `Terrain job guard installed (... with the grid-change handshake)` and
  `Spread attach hook installed ...; early detach available`.
- **Long holes in the start grid** (seconds instead of ~8 frames), with the world simulated at `fTimescale` 5000:
  - NPCs walking out of the detached cells are unloaded, which is normal at the grid edge;
  - followers standing in a neighbouring cell are unloaded until the arrival;
  - scripts with OnCellDetach fire during the climb instead of at the move.

  The 3x3 around the player now always stays attached (9 cells left for the move frame, 16 detached in the climb).
- **Visual:** object and tree LOD for the detached start cells relies on the engine and DynDOLOD DLL re-enabling LOD at cell
  detach. If they only do it on a grid shift, holes appear behind the camera during the climb. Order and window are tunable,
  or the feature can be switched off.
- **Exterior buffer:** 24 detached cells go into a 36-cell buffer and evict the oldest. That is the same eviction the move frame
  does today, only spread out. A loaded destination centre cell survives only if fewer than ~36 cells are pushed after it,
  The queue now starts at take-off (§4.5), so with the early detach on, 16 cells are pushed after it. If the arrival cell state is not 6 at the move, the cell was evicted or
  not finished.
- **Background cell load:** the 25-cell queue froze the game once (ActorValueGenerator.dll threads, buffer overflow). One cell
  at a time on the door-preload path is what the engine does constantly near doors, but it is new for this modlist at this
  moment. Switch: `iQueueDestinationCells=0`.
- **Handshake timeout:** if a terrain job holds 31802 for more than 20 ms, the slice is skipped that frame. It is never forced
  during the climb. Nothing proceeds without it any more (§4.5).
- **Abort re-attach:** `Flush` attaches all detached cells in one frame (or the next ones, if a terrain job is inside), so an abort costs a frame like today's move. That is
  acceptable for an abort path.
- **Early detach and render-side readers (Codex):** the handshake covers the BSJobs reader only. A reader on another thread
  (Community Shaders render passes) that holds a cell or land pointer across a detach was not audited. That is why it is off by
  default.
- **Trampoline:** ~120 of 256 bytes used by this plugin. Other agents adding hooks to the same trampoline should check.

---

## 8. Ideas not done here

- **CS `GrassBucketStore::DrainPending` with a per-frame cap.** For example, apply at most N removals per `EndFrame` and keep
  the rest queued. The removal holds the group's lifetime, so stale grass would only draw a few more frames under a camera in
  the sky. Worth it only if §2's CS bucket survives the early detach.
- **Two-phase attach** (land first, references later; `RESEARCH-flight-streaming` §4-E). Only if a single slot is still
  > 50 ms.
- **Neural Rendering eased off for the first second after the move.** The 245 ms frame is NR waiting on the GPU, not streaming.
- **Disk hygiene:** the worktree `C:\Users\foxnn\dev\sky-above-wt-apex` has no build folder. Remove it with
  `git worktree remove` after the merge.

---

## 9. Regression 2026-11-25 22:10: the move that never arrived (fix `cf505e6`, branch `fix/apex-move-regression`)

**What happened:** Riften → Solitude Sawmill logged the move, but the grid stayed at (42, −23) and the player stayed at Riften
with 0/25 destination cells. The landing then settled onto the camera mod's live pose at Riften.

**Cause [V, from the dump]:**
- `Main::sub 36581` looks up the cell at the player's position (13717) and **skips `TES::UpdateGrid` (13288) while that cell's
  state is 4 (being loaded) or 7 (attached)**: `36581+0x146 cmp cl,4 / je`, `+0x14F cmp cl,7 / je`.
- `iQueueDestinationCells=1` had put the arrival cell on the background loader, and both flights logged "arrival cell state 4"
  at the move.
  - In flight 1 the load finished 0.28 s after the move, which matches "arrival cell attached 0.28 s after the move", and the
    grid followed.
  - In flight 2 it never left state 4, so no grid update ever ran.

**Fix:**
- `iQueueDestinationCells` now defaults to 0. The deployed ini has no such line, so the default applies.
- If it is turned on, the apex move waits for a queued arrival cell to leave state 4, at most 2 s.
- **Landing check:** at the start of the way down and at touchdown, a player more than two cells from the destination is
  rescued. The rescue is a teleport to the destination marker, after which the camera is handed back. It logs
  `Landing aborted ...: the player is N units from the destination`.

**Open question:** why the background load stayed in state 4, and whether the engine's own door preloads can ever leave the
arrival cell in that state. If they can, the landing check is the safety net.

---

## 10. Descent and landing hitches, 2026-11-25 22:37 (branch `flight/descent-hitches`)

Flight Riverwood → Riften: move frame 237 ms, all 25 cells attached 0.55 s after the move. Four dumps were taken during the
way down: 228, 141, 137 and 273 ms, at 22:37:19–23.

### What the frames are

All of them are GPU or driver waits. None is game logic.

| dump | samples | where the main thread waits |
|---|---|---|
| `frame13505_273ms` | 141/143 | `ntdll` kernel wait ← `NeuralRenderingNGX::D3D12Interop::BeginD3D12` ← `NeuralRendering::Evaluate` ← game render 105676/105674 ← `Main::Draw+0xA59` (end of the frame). Neural Rendering's D3D12 interop waiting on a GPU fence. Same signature as the 616 ms frame at 22:47:49 (VRAM 14.0/16.3 GB) and the 245 ms one at 20:58. |
| `frame13421_228ms` | 98/114 | kernel wait inside game 77263+0x68, the engine's draw wrapper (`[0x32887B0]` is the D3D11 device context; vtable +0x60 is `DrawIndexed`), under `BSBatchRenderer` / `BSShaderAccumulator`. A D3D11 call blocking in the driver while drawing. |
| `frame13487_137ms` | 38/61 | the same, at 77263+0xC7 |
| `frame13428_141ms` | 23 + 13 + 7 of 63 | `DX12SwapChain::Present` waits (pacing and frame generation), Neural Rendering's `BeginD3D12`, and draw-call waits |

### The generator chain was a misreading

The chain `55511 → 32354 → 32703 → 32770 (BGSGamebryoSequenceGeneratorHolderSingleton) → 32704 → 32788` is the **CS DLL column
of the dump read as SkyrimSE.exe offsets.** The hex values `52B956, 540B97, 544ABC, 54102D, 545F65, A10D06` resolve, against
the CS PDB of the 22:33 build, to `NeuralRendering::Evaluate → State::Evaluate → State::Run → EvaluateModel →
D3D12Interop::BeginD3D12`, and above them `Profiler::EndPass`.

- In a dump line, column 2 is CS offsets (name them with `cs_symbols.py`) and column 3 is exe RVAs.
- No sequence generator, KF file or controller is involved. Preloading them would not help, so it was not built.

### What follows [I]

- **GPU-bound frames.** In the descent the camera comes down into fully loaded cells, and:
  - Neural Rendering must finish GPU work before its interop can start;
  - D3D11 draws stall in the driver, which is typical when the driver waits on a full command queue or pages resources in at
    first use with VRAM near budget (14.0/16.3 GB).
- **Out of reach for CPU-side preloading.** The model preload already creates the meshes and textures; GPU residency and the
  frame-time cost are not something it can buy ahead.

### Levers (not implemented here)

| lever | where | notes |
|---|---|---|
| ease Neural Rendering off during the way down (skip or alternate frames, or lower its scale for ~3 s) | CS, via an export like `BottledShaders_GetCloudDeck` | the biggest single wait |
| lower VRAM pressure | — | it was 14.0/16.3 GB |
| check Hitch Hunter `RenderGate` and the dynamic geometry buffer size | Hitch Hunter | it can show buffer waits at landing |
| pre-draw the destination's new resources once while still high, hidden | — | hard; residency is per use |

### Built: `bLogDescentTiming` (default 1)

One line per flight: `Descent timing: N frames over X s, average A ms, worst W ms; frames over 100 ms: HH:MM:SS.mmm +s
way down|landing ms, ...`. The wall-clock times match the dump file names. Commit on `flight/descent-hitches`; not built.

# RE: exterior grid attach after a big player move — Skyrim SE 1.6.1170

Date: 2026-11-25. Read-only research on the in-memory `.text` dump
(`scratchpad/text_1170.bin`, RVA = file offset + 0x1000), Address Library
`versionlib-1-6-1170-0.bin`, community names from `skyrimae.rename`, CommonLibSSE-NG
headers for struct layouts. Disassembly via capstone; helper scripts live in the session
scratchpad (`relib.py`, `hooks.py`, `dis/*.txt`).

Legend: **[V]** = verified in the bytes of this dump. **[I]** = inferred from code structure /
CommonLib / community names. **[P]** = public knowledge, source named.

Important caveat about the dump: it was taken from the live, modded process. It contains the
SKSE plugins' hooks (calls/jumps into trampolines below the image base, and a 14-byte
`jmp [rip]` on `Main::Update`). Every proposed hook site below was checked to be unpatched in
this dump, but bytes at *hooked* sites (listed in §5) are not the vanilla bytes and must not be
used as "original opcodes". A plugin should always verify the bytes it quotes before patching.

---

## 0. One-paragraph answer

The whole 5x5 attach after a big move happens inside **one call of `TES::sub` AE id 13288
(RVA 0x19B0B0)** — call it `TES::UpdateGrid(pos, flag)` — which `Main::sub` 36581 calls every
frame with the player position. For a shift of more than one cell it (a) lets
`GridArray::Shift` (15942) fall into `DetachAll()` (whole grid), (b) calls `TES::sub` 13362
which **synchronously creates/loads all 25 CELL records from the ESM/ESP files** on the main
thread (`TESWorldSpace::sub` 20460 → 20456 → `TESFile` reads — the BSFile frames in the sampler),
and (c) calls `TES::sub` 13430, which loops over all 25 grid slots calling the per-cell attach
**`TES::sub` 13427 (RVA 0x1A5790)** inside a Havok "add batch" (`bhkWorld::sub` 77905 … 77906).
Closing the batch (77906 → 77918 → `ahkpWorld::sub` 61315) is the "physics wait" in the sampler:
it is the deferred insertion of every new collision object into the Havok world, not the
per-frame step. For normal walking the same functions run, but only one 5-cell strip is
detached/attached, and that strip's CELL records were already pre-loaded in the background by
the engine's **CellLoaderTask queue** (singleton `0x30FDB38`, enqueue `18541`) when the player
entered the neighbouring cell. The per-frame Havok step is `bhkWorld` vtable slot 50
(`bhkWorld::Func50` 77851, RVA 0xE85310), run on a job thread by `UpdateExteriorWorldJob`
(18870); the engine's own on/off switch is the byte `bhkWorld+0xC5F9` (what `tcl` toggles and
what `TES::SetCurrentCell` clears during a cell transition), but cell attach (`TESObjectCELL::sub`
18976) re-derives it from the global `0x20F6A44`, so the robust way to skip the step is a
vtable/call hook. Best lever for a seamless flight: **pre-queue the 25 destination cells into
the CellLoaderTask queue during the flight** (exactly what the engine does for doors and for the
next strip), wait until the pending count (`18548`) is 0, then move the player; the main-thread
work left is attach + Havok batch, which can additionally be spread over frames by hooking the
`call 13430` at 13288+0x9C5.

---

## 1. Goal 1 — the grid attach path

### 1.1 Call graph (AE ids, RVAs 1.6.1170) [V]

```
Main::Update            36564  0x645EA0  (+0x2A7 call 36581; +0x825 direct call 13288 when !paused && !Main::freezeTime)
 └ Main::sub            36581  0x6474C0  "update player cell": pos = player pos, cell = TESDataHandler::sub 13717(pos)
    └ +0x201  call 13288 (TES::UpdateGrid)(gTES, &pos, r8b=1)   unless Actor::IsOnFlyingMount
       ├ +0x463/+0x4C3/+0x4F7  18541  CellLoaderQueue::QueueCell(mgr, ws, x, y, 0)   <- next-strip pre-load (walking)
       ├ +0x6F1  13440  TES::sub  (land shader flag loop over grid, uGrids==5 only)
       ├ +0x6FD  18545, +0x709 18543, +0x719 18544  (CellLoaderQueue bookkeeping, IOManager::sub 75638/75639)
       ├ +0x7E2  77906 bhkWorld::sub  / +0x7F3 77909 / +0x802 77908 bhkWorldM::sub      (batch bracketing, see §2)
       ├ +0x813  call [gridCells->vtbl+0x18]  = GridCellArray::SetCenter (15954)
       │          └ GridArray::SetCenter 15941 → Shift (15942): |d|>=uGrids → DetachAll (15939), else strip Detach/MoveItem/ClearItem
       │             └ GridCellArray::Detach 15955 → TESObjectCELL::sub 19130 (detach cell, dl=1) ; then 19196 → bhkWorld origin 78632
       ├ +0x9A9  call 13362  TES::sub   ONLY if |dx|>1 || |dy|>1 : create/load every CELL record of the new grid  (sync, disk)
       ├ +0x9BD  call 77905  bhkWorld add-batch begin
       ├ +0x9C5  call 13430  TES::sub   = attach loop (see 1.4)
       ├ +0x9F5  call 77906  bhkWorld add-batch end  → 77918 flush (ahkpWorld::sub 61315 batch add)  <- sampler "physics wait"
       ├ +0xA1D..+0xBB0  grass loops (gGrassManager 0x20F8988; remove 15375 / add via NGIO-hooked call) — NOT cell loading
       └ +0xC0F  call 31802 BGSTerrainManager::Update
```

Other callers of 13288 [V]: `TES::SetCurrentCell` 13316 tail-jumps to it at +0x44 when the
target cell is the current one; 13317+0x3BA; 35652+0x2AF; 36582+0x2C (`36582` = "update grid
then SetJobTaskEvent(1)").

### 1.2 `TES::UpdateGrid` — id 13288, RVA 0x19B0B0 [V]

Signature (inferred from usage): `bool TES::UpdateGrid(TES* this, const NiPoint3* pos, bool r8b)`.
`r8b` is saved at entry (`44 88 44 24 18`) and read back as `[rsp+0xb0]`; callers pass 1.
TES offsets used match CommonLib AE: gridCells +0x78, objRoot +0x80, currentGridX/Y +0xB0/+0xB4,
currentQueuedX/Y +0xB8/+0xBC, interiorCell +0xC0, interiorBuffer +0xC8, exteriorBuffer +0xD0,
worldSpace +0x148. `[this+0x140]/[0x144]` are written with "distance to shift threshold" floats.

Key excerpts:

```
0019B1C6  movss xmm0,[rdi]          ; pos.x  -> r15d = floor(x)        (y -> r13d)
0019B217  mov eax,r15d ; shl ecx,0xc ; sub eax,ecx ; sub eax,0x800      ; x - (gridX*4096 + 2048)
0019B20F  movss xmm6,[0x17A8104]    ; cell size (4096.0, inferred)  [uGrids==3 variant at +0x18A]
0019B267  subss xmm1,xmm0           ; dist = 4096 - |offset|
0019B272  movss [rbx+0x140],xmm1    ; store distX / distY
0019B299  comiss xmm1,xmm2 ; jbe 0x19b60b     ; distX<=0 or distY<=0 -> shift path (+0x55B)
0019B2AF  test sil,sil ; jne 0x19b60b          ; sil = [gBGSSaveLoadManager+0x340] bit1 (loading-game) -> shift path
```
→ The grid re-centres only when the player is ≥4096 units from the centre of the current
centre cell (i.e. halfway into the neighbouring cell) **[I: assumes 0x17A8104 == 4096.0f, which
is the same constant used as `(gridX+0.5)*C` for world positions at +0x66C..+0x684]**.

Inside-grid path (+0x208, normal walking): when the player has crossed into an adjacent cell
(`currentQueued` ≠ player cell) it queues the strip *beyond* the grid edge:

```
0019B4C3  sub r12w,r14w             ; dx = newX - queuedX  (±1)
0019B4D8  imul edx,ecx ; add r14w,dx ; (half+1)*dx  -> column just outside the grid
0019B4F0  mov rdx,[rbx+0x148]       ; worldspace
0019B507  mov rcx,[0x30FDB38]       ; CellLoaderQueue singleton
0019B50E  mov byte [rsp+0x20],0
0019B513  call 0x29c530             ; 18541 QueueCell(mgr, ws, x, y, false)   (loop over the strip)
...
0019B5BB  mov [rbx+0xb8],r15d ; mov [rbx+0xbc],r13d   ; currentQueuedX/Y = new
```

Shift path (+0x5A1 …): updates currentGridX/Y, the world-origin globals (0x2033108..0x2033118),
then:

```
0019B82F  mov eax,r14d ; cdq ; xor/sub -> |dx| ; cmp r14d,1 ; jg -> sil=1      ; sil = "big move" = |dx|>1 || |dy|>1
0019B855  (same for dy)
0019B883  test sil,sil ; jne 0x19b88d          ; big move -> 77906(world,0); 77909(g,0)
0019B888  test bpl,bpl ; jne 0x19b8af          ; (r8b arg) -> skip them
0019B8B2  call 77908   bhkWorldM::sub          ; remove-batch begin (counter +0xC5DC)
0019B8B7  mov rcx,[rbx+0x78] ; mov r8d,r13d ; mov edx,edi ; mov rax,[rcx]
0019B8C3  call [rax+0x18]                      ; gridCells->SetCenter(newX,newY)
0019B8E2  call 77909                           ; remove-batch end (edx = big ? 0 : arg)
0019B8E7..0019BC0E  loop over grid slots: GetCell(x,y) null? -> look up ws cell map (hash 68220) / exteriorBuffer -> flag [rsp+0xb8]
0019BA2A  call 15335 ([0x20F69F8])             ; lock master-file loads
0019BA42  cmp r14d,1 ; jg -> / dy -> 
0019BA59  call 0x1a1010  ; 13362  TES::sub     ; BIG MOVE ONLY: create/load every CELL record of the new grid
0019BA6D  call 0xe88620  ; 77905  add-batch begin
0019BA75  call 0x1a5df0  ; 13430  attach loop
0019BAA5  call 0xe88630  ; 77906  add-batch end (edx = big ? 0 : arg)  -> flush -> 77918
```

### 1.3 `GridArray::Shift` — id 15942, RVA 0x221450 [V]

```
00221450  push rbx ; push r14 ; push r15 ; sub rsp,0x30
0022145A  add [rcx+8],edx ; add [rcx+0xc],r8d        ; centre += (dx,dy)
00221474  cmp eax,ecx                                ; |dx| vs length (uGridsToLoad)
00221476  jae 0x22166f                               ; -> DetachAll
00221486  jae 0x22166f                               ; |dy| >= length -> DetachAll
...   per-column/row: vtbl+0x28 Detach(x,y) on the leaving edge, +0x38 MoveItem, +0x30 ClearItem   (repeated |dx| times)
0022166F  mov rax,[rbx] ; mov rcx,rbx ; ... ; jmp [rax+8]     ; GridArray::DetachAll (15939): Detach every slot
```

`GridCellArray::Detach` (15955, 0x221A40): `cell = cells[x*len+y]; if (cell) { TESObjectCELL::sub
19130(cell, 1); ClearItem(x,y); }` — 19130 is the cell detach (it clears `bhkWorld+0xC5F9` at
+0x19D when the cell owns the Havok world, see §2). Detached exterior cells are not freed: they
go to the exterior buffer (13434) and are unloaded later by `TESDataHandler::sub` 13721 when the
buffer (`uExterior Cell Buffer`, global 0x1FD4768) overflows [V for 13434/13436, I for the setting name].

### 1.4 The attach loop — `TES::sub` 13430, RVA 0x1A5DF0 [V]

```
001A5E99  call 77905               ; bhkWorld add-batch begin (nested; counter +0xC5D8)
001A5EE0..001A5F91   for gy in 0..uGrids: for gx in 0..uGrids:
001A5EF5    call 0x1a5790  ; 13427 TES::AttachCellAtSlot(this, gx(edx), gy(r8d), cellX(r9d), cellY([rsp+0x20]))
001A5F13    call 13718     ; TESDataHandler::GetCell(x,y,ws,create=0) -> if in interior/exterior buffer -> 13434 (remove from buffer)
001A5FE7  call 77906               ; add-batch end
001A600F  call 35567(0)            ; (only when not loading a save)
001A6023  call 77905               ; second batch
001A602F  call 41313([0x20F69B0])
001A6060..001A6102   second loop over grid: cell=13718(...); if cell->cellState(+0x44)==6 { 19063(cell,!flag); 13434; 18978 -> NiAVObject::UpdateObjectUpwards }
001A611D  call 77906               ; batch end
001A613A  TESWorldSpace::sub 20518 (if ws flag 0x40) ; 18234(ws+0x250,0)
```

Callers of 13430 [V]: 13288+0x9C5 and 13428 (+0x1D1, +0x245; 13428 is the "first grid load"
helper called from 13288's init path and from 13287).

Per-cell attach `TES::sub` 13427, RVA 0x1A5790 [V] — args `(TES*, int gridX, int gridY, int cellX, int cellY)`:

```
001A57D3  call 0x306a50  ; TESWorldSpace::sub 20460 (ws, cellX, cellY)  -> cell from map; LOADS THE CELL RECORD FROM FILE if absent (20460+0x10F -> 20456 -> TESFile::Seek/ReadData ...)
001A57DE  jne 0x1a5846   ; found
001A57FA  call 13718 (TESDataHandler::GetCell(x,y,ws,create=1)) ; 20532 (add to ws map) ; 19115(cell,1) ; GetLocation/BGSLocation ; 18224(ws+0x250,cell)
001A5850  call 15950 GridCellArray::sub  ; slot already holds an attached cell (state 7)?  -> 13434 and return
001A58A2  snprintf(name, 0x104, fmt, x, y)   ; "Wilderness" style name
001A58B4  call 15949 GridCellArray::sub  ; cells[gx*len+gy] = cell
001A58CA  call 15962 GridCellArray::sub  ; -> TESObjectCELL::sub 18976(cell, objRoot)   <- the actual cell attach (3D/Havok/refs)
001A58E4  TESObjectLAND::sub 18747(land,1) ; 18767 (water height) ; 19001 ; flags ; 32030([0x20F8970],cell,0) ; 18733(land, [this+0x12c], 0)
```

`TESObjectCELL::sub` 18976 (0x2B7280) is the cell attach proper: it fetches/creates the cell's
Havok world (`ExtraDataList::GetHavokWorld` or the global bhkWorld), sets
`bhkWorld+0xC5F9 = (byte[0x20F6A44]==0)` at +0xCE, then 18223/20513/ShadowSceneNode/NavMesh and
walks the references (vtbl calls) [V for the calls, I for "attach"].

### 1.5 Normal one-cell crossing vs big move [V unless noted]

| step | walking (|dx|==1) | big move (|dx|>=uGrids) |
|---|---|---|
| pre-load | when the player enters the neighbouring cell, 13288 inside-grid path queues the next strip (5 cells) into the CellLoaderTask queue (18541); shift only happens ~half a cell later [I on threshold] | nothing is pre-queued; the move lands directly in the shift path |
| Shift | detaches 1 strip (5 cells → exterior buffer) | `DetachAll`: 25 cells detached (→ buffer, overflow → unload via 13721) |
| 13362 | skipped (`|dx|<=1`) | runs: 25× `TESWorldSpace::sub 20460` → file read of every CELL record not in memory (main thread) |
| 13430/13427 | 5 slots attach; cells found in map/buffer, no disk | 25 slots attach; each 20460 may read from disk again; 25× 18976 (refs, Havok shapes, land) |
| Havok | 5 cells' collision added in one batch flush (77906→77918) | 25 cells' collision added in one flush (the sampled 35% wait) |
| bhkWorld bracketing | `77906(w,0); 77909(g,0)` skipped when `r8b` set | always `77906(w,0); 77909(g,0)` before SetCenter, and `77909(g,0)`/`77906(w,0)` after |

So the engine has no per-frame limiter: even walking attaches a strip within one frame; it is
cheap only because the strip was pre-loaded.

### 1.6 Hook sites for limiting cells per frame

All bytes below are **[V]** in the dump and unpatched (hook scan §5 found nothing at these RVAs).

| site | RVA | id+off | bytes (5/6/prologue) | what it is |
|---|---|---|---|---|
| A | 0x19BA75 | 13288+0x9C5 | `e8 76 a3 00 00` | `call 13430` (attach loop) — **primary hook (write_call5)** |
| B | 0x19BA59 | 13288+0x9A9 | `e8 b2 55 00 00` | `call 13362` (big-move sync CELL creation) |
| C | 0x1A5EF5 | 13430+0x105 | `e8 96 f8 ff ff` | `call 13427` per-slot attach inside 13430 |
| D | 0x1A5DF0 | 13430+0 | `40 53 55 56 57 41 54 41 55 41 56 41 57 48 83 ec 58` | 13430 entry (write_branch alternative) |
| E | 0x1A5790 | 13427+0 | `48 8b c4 48 89 58 20 55 41 56 41 57 48 81 ec 50 01 00 00` | 13427 entry |
| F | 0x1A1010 | 13362+0 | `40 55 56 57 41 54 41 55 48 83 ec 30` | 13362 entry |
| G | 0x221450 | 15942+0 | `40 53 41 56 41 57 48 83 ec 30` | GridArray::Shift entry |
| H | 0x2219C0 | 15954+0 | `48 89 5c 24 08 48 89 74 24 10 57 48 83 ec 20` | GridCellArray::SetCenter (vtable slot 3; VTABLE_GridCellArray AE id 188592) |
| I | 0x19B8C3 | 13288+0x813 | `ff 50 18` | virtual SetCenter call (3 bytes, not directly hookable; use H) |
| J | 0x6476C1 | 36581+0x201 | `e8 ea 39 b5 ff` | per-frame `call 13288` from Main::sub |
| K | 0x6466C5 | 36564+0x825 | `e8 e6 49 b5 ff` | `call 13288` in Main::Update |
| L | 0x6477AC | 36582+0x2C | `e8 ff 38 b5 ff` | `call 13288` in 36582 |

Proposed design ("attach K slots per frame after a flight arrival"):

1. `write_call5` at **A**. The detour `MyAttachGridCells(TES* tes)`: if the plugin is not in
   "arrival" mode → call original 13430. Otherwise reproduce 13430's first half for a budget of
   K slots per frame: `77905(world)`; for the next K slots in centre-out order (centre cell
   first — the player stands in it and `Main::sub` 36581 → 19411 moves the player into that cell
   every frame) call `13427(tes, gx, gy, gridX - half + gx, gridY - half + gy)`; `77906(world, 0)`.
   Remember the remaining slots. Return.
2. On the following frames (e.g. a `write_call5` at **J** detour that first calls 13288 and then
   continues the queue, or any per-frame hook the plugin already has), attach the next K slots
   inside their own 77905/77906 pair. When the queue is empty run 13430's second half once
   (the 19063/13434/18978+UpdateObjectUpwards loop, then 20518/18234) — simplest is to call the
   original 13430 once at the end: its first loop finds every slot filled (15950 → state 7) and
   skips to the second loop.
3. Also hook **B** to skip 13362 in arrival mode if the destination records were pre-queued
   (§3), or leave it (it only loads records that are not already in memory).

Things that tolerate `null` grid slots while the queue drains [V by reading the code]:
`TES::GetCellByCoords` 13319 (falls back to `TESDataHandler::GetCell`), 13440 (null check),
13288's slot loop (looks the cell up in the worldspace map), `GridCellArray::Detach`
(null check), 13430's second loop (looks cells up via 13718). Things that do **not** (risks):
anything that reads `TES::gridCells->cells[]` directly expecting attached cells (LOD/terrain
manager 31802 is called at the end of 13288 with the worldspace — unknown whether it iterates
the grid; `TESObjectCELL::sub` 19063 "activate" is only applied in 13430's second loop; NPC AI
"ProcessLists" use the player's parent cell which exists once the centre slot is attached).
Water/land seams between attached and not-yet-attached cells are visible from the ground but
the camera is in the sky during arrival. Save-game/`PositionPlayer` events during the drain
must flush the queue first. Confidence that this is mechanically possible: **medium**;
confidence that it is safe without testing: **low** — it must be tried with the queue drained
within a few frames and `freezeTime`/menu handling.

Cheaper variant: hook **C** instead and make the detour skip (record) slots beyond the budget;
then run the recorded `13427` calls on later frames. Same semantics, no need to re-implement the
loop.

---

## 2. Goal 2 — the Havok step and how to skip it

### 2.1 Where the step runs [V]

The per-frame step is **`bhkWorld` vtable slot 50 (offset 0x190) = `bhkWorld::Func50`, id 77851,
RVA 0xE85310**, signature `void (bhkWorld*, bool)`. It is invoked from the job function
**`UpdateExteriorWorldJob` id 18870 (RVA 0x2B1D30)**:

```
002B1D34  mov rax,[0x20F8928] ; mov rcx,[rax]      ; current bhkWorld (global id 400440)
002B1D46  xor edx,edx
002B1D48  ff 90 90 01 00 00   call [rax+0x190]      ; bhkWorld::StepWorld(false)
002B1D4E  call 69518 ; ... ; lea ecx,[rax+0xd] ; jmp 69514 SetJobTaskEvent(13)
```

`Job_Ragdoll_post_physics` (39068) waits on event 13 (`WaitForJobTask(0, 0xd)`), so the step
runs on a job-list thread, started by `Main::Update`'s `SetJobTaskEvent(1..4)` calls at
36564+0x82A..+0x859 — which sit **immediately after the `call 13288` at +0x825** [V]. The job
table itself is in `.data` (not dumped), so "event 1 == UpdateExteriorWorldJob" is **[I]**.

Inside 77851: flushes pending adds if `[world+0xC5EC]>0` (77917/77920/77919), then
`cmp byte [r14+0xC5F9], 0 ; je exit` and `movss xmm0,[0x202C688] ; comiss ; jbe exit` (dt<=0 →
no step), substep count from `[0x20294F8]`/`[0x202C6C0]` with a floor of 4 (`mov ecx,4 ; cmovl`)
written to `hkpWorld+0x3D4/+0x3E0`, then `ahkpWorld::sub` 61434/61420/61414/61413/61415/61421…
(the multithreaded step) under the world read lock. `77850` (0xE85250, no direct caller found —
likely reached through a hooked call, see §5) writes the dt globals 0x202C688/0x202C68C/0x202C690.

**The sampled "physics wait" is not this step.** `bhkWorld::sub` 77918 (0xE89370) is reached
only from 77906 (+0x36) and 77839/77840/77841/77907 [V]. 77906 is the "add-batch end":

```
00E88636  mov eax,[rcx+0xc5d8] ; ... sub eax,1 ; mov [rcx+0xc5d8],eax ; jne ret     ; nested counter
00E88657  call 77917 / 00E8865E call 77916                                           ; (dl selects)
00E88666  call 77918   ; flush: for i in 0..[+0xC510]: entries [+0xC500] -> ahkpWorld::sub 61315 (batch add), 77799, vfunc+0x130, hkReferencedObject::removeReference (57011)
00E8866E  call 77919 ; jmp 77920
```

13288 and 13430 bracket the attach with 77905/77906 (counter `bhkWorld+0xC5D8`), so all the
new cells' collision objects are inserted when the outer 77906 at 13288+0x9F5 brings the
counter to 0. The `BSTaskManager::Func17` (75633) wait seen in the sampler is only called from
`IOManager::Func17` (75706, a "spin until task state == 6" loop) [V]; which object in the flush
reaches it was not resolved (the sampler's intermediate frames `36581 → 13641 → 77918` are not
a real call chain: 13641 is the worldspace cell-map hash lookup used by 13718, so those frames
are stack-walk noise). Main::Update also wraps `IOManager::sub` 75705 (finish queued IO tasks →
attaches loaded 3D) in a 77905/77908 … 77906/77909 batch at 36564+0x5AC..+0x5E9 [V].

### 2.2 Existing enable/disable flag [V]

`bhkWorld+0xC5F9` (CommonLib calls it `toggleCollision`) gates the whole step. Writers found by
byte scan:

| writer | id+off | RVA | value |
|---|---|---|---|
| `TES::SetCurrentCell` (cell transition start) | 13316+0x22 | 0x19D4B1 | 0 (`41 c6 81 f9 c5 00 00 00`) |
| `TES::sub` 13317 (transition finish) | 13317+0x31 | 0x19DCC0 | 1 (`41 c6 80 f9 c5 00 00 01`) |
| 13375 (= `papyrus::Debug::ToggleCollisions` body, tcl) | +0x42 | 0x1A1EC2 | `!byte[0x20F6A44]` (also toggles 0x20F6A44, writes 0x202CB30) |
| 13376 `(bool)` setter | +0x35 | 0x1A1F15 | `!dl` (writes 0x202CB30 too) |
| `TESObjectCELL::sub` 18976 (cell attach) | +0xCE | 0x2B734E | `byte[0x20F6A44]==0` — **re-derives on every attach** |
| `TESObjectCELL::sub` 19130 (detach) | +0x19D | 0x2C177D | 0 |
| 19195 +0x326, 19197 +0x2C | | | al / 0 |
| reader: `bhkWorld::Func50` | 77851+0xBA | 0xE853CA | `cmp byte [rsi+0xc5f9], ch ; je exit` |

Also relevant: `Main::freezeTime` is `Main+0x16` (`[r12+0x16]` in Main::Update; CommonLib
RUNTIME_DATA at 0x10) and `gIsInMenuMode` byte `0x318714B` (set from `UI+0x160 numPausesGame`);
both skip the `call 13288` at 36564+0x825 but **do not** skip `SetJobTaskEvent(1..4)` — the step
job is still signalled; it is the dt (0x202C688 <= 0) that makes the step a no-op while paused [I].

### 2.3 Hook options

| option | site | bytes | notes |
|---|---|---|---|
| vtable swap | `VTABLE_bhkWorld` (AE id 238918) slot 50 (0x190) | n/a | cleanest; detour: `if (skip) return; orig(world, b);` |
| write_call6 | 18870+0x18, RVA 0x2B1D48 | `ff 90 90 01 00 00` | 6-byte indirect call, replace with `call [rip+x]`/write_call6 to a detour taking `(bhkWorld*, bool)`; only this job calls slot 50 in the frame path (other `[+0x190]` callers: 77851 itself for sub-worlds) |
| engine flag | set `byte[0x20F6A44] = 1` (tcl state) and `bhkWorld+0xC5F9 = 0` | | survives cell attach (18976 re-reads 0x20F6A44) but equals `tcl`: player/NPC collision stops being simulated; restore both afterwards; 13375 also writes 0x202CB30 — set it the same way to stay consistent |
| direct byte | `bhkWorld+0xC5F9 = 0` only | | **not reliable**: 18976 rewrites it during the attach you are trying to protect |

Risks: skipping the step is what `tcl`, cell transitions and a paused game already do, so the
hkpWorld itself is fine with it for seconds. Side effects: ragdolls/havok-driven refs freeze,
`Job_Ragdoll_post_physics` still runs (it only waits on the event), character controllers are
not integrated (fine while the player is parked). Expected benefit for the measured stall:
**low** — the step runs on a job thread; the main-thread cost is the batch flush and the
synchronous loads. It may reduce world-lock contention (`77918` and the step both take
`bhkWorld+0xC598`/`+0xC5A0` locks) and GPU/CPU background load during the arrival frame, so it is
worth an A/B, but it is not the fix. Confidence on the mechanism: **high**; on the benefit: **low**.

---

## 3. Goal 3 — loading the destination over several frames

### 3.1 The engine's background cell loader (CellLoaderTask) [V]

Singleton pointer `0x30FDB38` (AE id 400899); the queue is served by `CellLoaderTask::sub`
18529/18530/18531/18557 (community names) through `IOManager` (`75638/75639`). API found:

| id | RVA | signature (inferred from call sites) | used by |
|---|---|---|---|
| 18541 | 0x29C530 | `void QueueCellByCoords(mgr, TESWorldSpace* ws, int16 x, int16 y, bool flag)` — if the cell exists and is loaded → `TES` buffer checks (13433/13437 → 13434 add to exterior buffer), else append `(x<<16|y)` under `BSReadWriteLock` | 13288 next-strip pre-load |
| 18540 | 0x29C330 | `void QueueCell(mgr, TESObjectCELL* cell, bool)` — allocates a task (18554) and submits via `IOManager` vfunc +0x88 | 13378 |
| 13378 | 0x1A1FD0 | `void TES::QueueCellLoad(TES*, TESObjectCELL*)` → `18540(mgr, cell, true)` | 40845 (door preload), 19074, 19187 |
| 18547 | 0x29CE00 | `void Remove(mgr, uint32 key)` (lock, 18561) | CellLoaderTask, 40845 |
| 18548 | 0x29CE70 | `int Pending(mgr) = [mgr+0x14] - [mgr+0x18]` | 13288+0x56B (defers the shift while busy) |
| 18542 | 0x29C7A0 | `void CancelAll(mgr)` | `TES::CancelMasterFileLoads` 13333 (= 18542 + lock 15335 on 0x20F69F8), `TES::ProcessEvent(PositionPlayerEvent)` 13419 (event type 0 → cancel; type 3 → unlock) |
| 18543/18544/18545 | 0x29C7B0/0x29C990/0x29CB80 | queue bookkeeping around a shift (lock, IOManager::sub 75638/75639, 18562) | 13288+0x6FD.. |

`PlayerCharacter`-side 40845 (0x752500, called from 40447+0x1097) is the engine's **door
destination preload**: for each nearby door it takes `TESObjectREFR::GetTeleportData` → target
cell, and if `TES::sub 13308(cell,0)` (cell state 3..7 = loading/loaded/attached) is false →
`13378` queue load; when its list is full → `18547` + `TES::sub 13370` (→ 13721 unload).
`CellLoaderTask::sub` 18529 ends with `TESObjectCELL::sub 18979` + `13434` (put the loaded cell
into the exterior buffer) [V].

**Use for Sky Above:** at flight start (destination known), for the 25 cells of the destination
grid call `18541(*(void**)(base+0x30FDB38), ws, x, y, false)` (or `13378(gTES, cell)` for cells
already in memory), prioritising the centre. Poll `18548(mgr) == 0` (and optionally
`13308(gTES, cell, 0)` per cell) before moving the player; cap the wait. After the move,
`13427`'s `20460` lookups hit the worldspace map (no `TESFile` reads), `13362` finds every cell
present, and the exterior-buffer path makes `13427` cheap apart from `18976`. This is exactly the
engine's own pre-load path, so it is the lowest-risk lever. Risks: exterior buffer capacity
(`uExterior Cell Buffer`, global 0x1FD4768 — if < 25 the oldest pre-loaded cells get unloaded by
13434 → 13721 before you arrive; check the INI), and `TES::ProcessEvent(PositionPlayerEvent)`
type 0 cancels the queue — if the mod fires PositionPlayer events, do so before queuing.
Confidence: **medium-high** that it removes the disk/CELL-record part of the stall; the Havok
batch and `18976` (3D attach, model loads via IOManager are already async) remain.

### 3.2 Exterior cell buffer [V]

`TES::exteriorBuffer` (+0xD0, size `[0x1FD4768]`) and `interiorBuffer` (+0xC8, size
`uInteriorCellBuffer` 0x1FD4750, id 358814). `13434(TES*, cell)` pushes a detached/loaded cell
into the buffer (rotating; full → oldest unloaded with `TESDataHandler::sub` 13721); `13436(TES*,
bool)` purges the interior buffer; `13310` moves a cell to a slot. `TES::PurgeBufferedCells` is
13299 (CommonLib). The buffer is why walking back and forth is cheap; a big move evicts it.

### 3.3 Other multi-frame knobs

* `13362` (B above) is the only place that *forces* synchronous creation of all records; with
  the pre-queue it becomes a no-op lookup loop.
* `IOManager::sub` 75705 in Main::Update (+0x5C3) finishes queued IO (models) each frame — the
  3D of attached refs already streams in over frames; nothing to do there.
* `TES::SetCurrentCell` (13316) is the loading-screen path (PlayerCharacter::sub 40744 →
  13316/13317; 36549/36641/36642): it disables physics (`+0xC5F9=0`), unloads via 13721, uses
  `IOManager::sub 75708` to flush, and 13317 re-enables. Not useful for seamless travel but shows
  the engine's own "big move" recipe: cancel loads (13333), move, attach, resume (13334).

---

## 4. Address table (RVA, 1.6.1170, all [V] via Address Library unless marked)

| thing | id | RVA | note |
|---|---|---|---|
| `TES::UpdateGrid` | 13288 | 0x19B0B0 | 0xE76 bytes |
| `TES::SetCurrentCell` | 13316 | 0x19D490 | CommonLib name |
| `TES::sub` finish transition | 13317 | 0x19DC90 | sets +0xC5F9=1 |
| `TES::GetCellByCoords(x,y)` | 13319 | 0x19E5F0 | |
| `TES::sub` ensure grid cells exist | 13362 | 0x1A1010 | big move only |
| `TES::sub` attach loop | 13430 | 0x1A5DF0 | |
| `TES::sub` attach one slot | 13427 | 0x1A5790 | |
| buffer helper | 13434 | 0x1A61D0 | |
| `TES::QueueCellLoad` | 13378 | 0x1A1FD0 | |
| `TES::IsCellLoaded(cell,strict)` | 13308 | 0x19CDF0 | states 3..7 |
| tcl toggle / set | 13375 / 13376 | 0x1A1E80 / 0x1A1EE0 | |
| `TES::CancelMasterFileLoads` / Resume | 13333 / 13334 | 0x19F260 / 0x19F290 | CommonLib names |
| `TESDataHandler::GetCell(x,y,ws,create)` | 13718 | 0x1B5F30 | uses 13641 hash lookup, 13710 create |
| `TESDataHandler::sub` unload cell | 13721 | 0x1B66D0 | |
| `TESWorldSpace::sub` GetCell (loads from file) | 20460 | 0x306A50 | → 20456 (0x3064C0) TESFile reads |
| `GridArray::DetachAll/KillAll/SetCenter/Shift` | 15939/15940/15941/15942 | 0x221380/0x2213F0/0x221400/0x221450 | |
| `GridCellArray::SetCenter/Detach/ClearItem/MoveItem` | 15954/15955/15956/15957 | 0x2219C0/0x221A40/0x221AB0/0x221AF0 | |
| `GridCellArray::GetCell` / set slot / slot attached? / attach 3D | 15946/15949/15950/15962 | 0x221830/0x2218A0/0x2218E0/0x221E20 | |
| `TESObjectCELL::sub` attach / detach | 18976 / 19130 | 0x2B7280 / 0x2C15E0 | |
| CellLoaderQueue fns | 18540/18541/18542/18547/18548 | 0x29C330/0x29C530/0x29C7A0/0x29CE00/0x29CE70 | |
| `bhkWorld` add-batch begin/end | 77905 / 77906 | 0xE88620 / 0xE88630 | counter +0xC5D8 |
| `bhkWorldM` remove-batch begin/end | 77908 / 77909 | 0xE886F0 / 0xE88700 | counter +0xC5DC |
| `bhkWorld` flush pending adds | 77918 | 0xE89370 | → `ahkpWorld::sub` 61315 (0xB39470) |
| `bhkWorld::Func50` = per-frame step | 77851 | 0xE85310 | vtable slot 50, `VTABLE_bhkWorld` id 238918 |
| dt setter | 77850 | 0xE85250 | writes 0x202C688/68C/690 |
| `UpdateExteriorWorldJob` | 18870 | 0x2B1D30 | |
| `Main::Update` / `Main::sub` / 36582 | 36564 / 36581 / 36582 | 0x645EA0 / 0x6474C0 / 0x647780 | |
| `BGSTerrainManager::Update` | 31802 | 0x50E430 | |
| globals: gTES | 403450 | 0x31872C8 | |
| gMain | 403449 | 0x31872C0 | freezeTime at +0x16 |
| gPlayerCharacter | 403521 | 0x31874F8 | |
| gTESDataHandler | 400269 | 0x20F6320 | |
| current bhkWorld* | 400440 | 0x20F8928 | |
| gGrassManager | 400452 | 0x20F8988 | |
| CellLoaderQueue* | 400899 | 0x30FDB38 | |
| IOManager* | 411121 | 0x3275DF0 | |
| UI (MenuManager) | 400327 | 0x20F6A00 | numPausesGame +0x160 |
| gIsInMenuMode byte | 403437 | 0x318714B | |
| uGridsToLoad | 359676 | 0x1FD6EB0 | |
| uExterior Cell Buffer [I] / uInteriorCellBuffer | 358817 / 358814 | 0x1FD4768 / 0x1FD4750 | |
| tcl state byte | 400334 | 0x20F6A44 | |
| master-file-load lock | 400326 | 0x20F69F8 | 15335 lock / 15336 unlock |
| save/load manager (flags +0x340, bit1 = loading) [I] | 403330 | 0x317ABA8 | |
| physics dt / dt raw / max step | 389089/389090/389091 | 0x202C688/0x202C68C/0x202C690 | |
| grid world-origin floats | 390976.. | 0x2033108..0x2033118 | |

---

## 5. Hooks already present in this dump (conflict check) [V]

Scan: all `E8/E9` rel32 and `FF 25/FF 15` whose target leaves the image. Confirmed real hook
sites in the functions of interest (trampoline targets ≈ image_base − 0x7E8xxxxx and
image_base − 0x1xxxx):

* `TES::UpdateGrid` 13288: **+0xA1D** (`jmp [rip]`, 6 bytes, replaced `mov edi,[uGridsToLoad]`-sized instruction), **+0xB29** (call), **+0xBF8** (call) — these are the grass loops (gGrassManager) and match NGIO-NG's grass-radius hooks; `NGIO-NG.dll` is in the modlist. Not in the way of sites A–L.
* `GrassManager` 15373 (+0x597), 15374 (+0xD4, +0x25C), 15383 (+0x7E); `TES::sub` 13335 and 13336 whole-function jumps; 76329.
* `Main::Update` 36564: entry (14-byte `jmp [rip+0]` → 0x7FFBF6804D30, a DLL, not SKSE trampoline), +0x9A (call, rcx = dword `[0x317ABF0]`, save-system related — original callee unknown), +0x26B, +0xC2B; `Main::sub` 36555 +0x5D5; 36566 +0x3A; 36544 +0x1AE.
* `TESObjectREFR::InitHavok` +0x9, `Load3D` +0x965, `InitItemImpl` +0x801, 19535 +0x348, 47338 (+0x47/+0x56); `TESWorldSpace::sub` 20541 +0xF7; `TESObjectCELL::GetLocation` +0x114; `QueuedTree::sub` 13023 (+0x165, +0x25C); `NavMeshInfoMap::InitItemImpl`; `Sky::sub` 26218 +0x1A0; `ShadowSceneNode::sub` 106342 +0x16; `MissileProjectile::UpdateImpl`; 18218/18223/19413/15330 (-7E850000 group); 41296 (+0x3AB/+0x424); 105674 (three sites); 82323; 80924; 77856 +0x61.
* Plugins in the list that plausibly own these: NGIO-NG, SSEDisplayTweaks, EngineFixes, DynDOLOD.DLL, SkyrimLODFixes, FasterCellLookup, HitchHunter, PriorityMod, Precision, CommunityShaders, TheosRenderPipeline, large_sector_fix, skyrim-freeze-fix, SeamlessFastTravel, devbench (own). Attribution per site is **not** verified.

None of the proposed sites A–L, 18870+0x18, 77851, 13316+0x22, 13317+0x31, 13375/13376,
18541/18548/13378 are patched in this dump.

---

## 6. Not found / open

* The vanilla bytes at hooked sites (13288+0xA1D/+0xB29/+0xBF8, Main::Update entry/+0x9A/…) —
  the on-disk exe is SteamStub-encrypted and no clean dump was available.
* Which object inside the 77918 flush reaches `IOManager::Func17 → BSTaskManager::Func17`
  (the sampled wait). 61315 (`ahkpWorld::sub`, batch add) uses `hkLifoAllocator`/`hkpPhantom`
  calls and does not obviously wait; the wait may be in a destructor reached via
  `hkReferencedObject::removeReference` (57011). Needs a sampler with correct frame pointers.
* The exact meaning of `18541`'s last `bool`, and whether the CellLoaderTask also pre-loads
  reference models (it ends in 18979 + buffer insert; 18979 not analysed).
* `TES+0x140/+0x144` naming: CommonLib calls 0x134/0x138 `gridBufferDistanceX/Y` for SE; in this
  build they hold "distance to shift threshold" computed per call (my reading).
* The job table (which event index starts `UpdateExteriorWorldJob`) lives in `.data`.

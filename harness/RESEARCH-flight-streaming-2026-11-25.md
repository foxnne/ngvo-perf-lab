# Research: streaming for a seamless flight — what others did, what the engine offers, what we could build

Date: 2026-11-25. Read-only web + local research. Companion to `RE-grid-attach-2026-11-25.md`
(our own reverse engineering of the 5x5 grid attach on 1.6.1170); this file does not repeat it.

Access notes: Nexus pages return 403 to the fetcher, so mod descriptions were read through the
Nexus API (`api.nexusmods.com/v1/games/.../mods/<id>.json`) with the user's key (nothing was
downloaded). Nexus **forum** threads, the UESP CK wiki, the Fallout CK wiki and Reddit were not
reachable, so anything from those is from search snippets only and is marked **[snippet]**. Mod
descriptions are the authors' own claims, marked **[author]**; I could read source only where a
GitHub README was reachable, marked **[source]**. Nothing here was tested in the game.

Legend: **[V]** verified in a primary source I could read · **[author]** mod author's claim ·
**[snippet]** search-result excerpt only · **[hearsay]** forum users · **[I]** my inference.

---

## 0. Short answer

1. **Nobody in the Skyrim scene has solved exterior streaming for a fast-moving viewpoint.** Every
   flying/dragon/travel mod I found either (a) stays inside the loaded grid, (b) slows down, or
   (c) accepts the hitches. The brand-new hawk VR mod ("Hawk Vision VR", Nexus 196970, released
   2026-11-24) does exactly (a): the body stays, the hawk is leashed to ~2 cells so **the grid never
   shifts**. There is no public "async cell loading" / "smooth cell transition" SKSE plugin; the
   one historical attempt (Altimor's multithreaded cell loading, 2013) was never released and the
   companion plugin was dropped for memory corruption.
2. **The engine has no exposed knob for what we want.** The only async piece is the
   `CellLoaderTask` queue we already use; `bUseBackgroundFileLoader` is unused; Fallout 4 has
   `PreloadTargetArea`/`PreloadExteriorCell` Papyrus natives, Skyrim does not. The likely
   per-frame IO budget knobs are `iPostProcessMilliseconds` (5) and
   `iPostProcessMillisecondsLoadingQueuedPriority` (20) **[I]**.
3. **The most useful things on the shelf are measurement and precedent**, not solutions:
   *Hitch Hunter and Fixes* (installed) attributes hitches to named textures/meshes and already
   spreads NPC appearance rebuilds one-per-frame — the exact pattern we are applying to cell
   attach. *Faster Cell Lookup* (installed) speeds the CELL-record file lookup that our
   `13362`/`20460` path hits. *skyrim-freeze-fix* and *Baked Goods* document two cell-loading
   races we must not widen.
4. Ranked ideas are in §4. Top three: finish the budgeted attach (per-slot Havok batches,
   centre-out) and **measure with Hitch Hunter's report**; **"strip-walk" the player to the
   destination along the engine's own 1-cell pre-queue/shift path instead of one 5-cell jump**
   (an A/B worth one evening); **warm GPU resources for the landing view** (textures, skinned
   actors) during the flight, since attach-spreading does nothing for first-draw hitches.

---

## 1. Survey: flying, free-camera and travel mods

| Mod | Game | How it moves | What it does about streaming | Source quality |
|---|---|---|---|---|
| **Hawk Vision VR** (Asterrath, Nexus SE/VR 196970, 2026-11-24) | VR 1.4.15 only | SKSE-VR plugin; flight runs on HIGGS's per-frame hook; "your body stays standing where you cast"; vanilla hawk mesh fitted round the HMD; dive stages 25/45/70°, "safety bumper" steers off obstacles | **Leash**: "By default you can fly about 117 metres (two cells) from your body … past the limit the hawk tires and slows … a quarter further and it returns you home." Optional no-limit. Outdoors only, load doors unusable. Tells PLANCK to ignore the invisible flying player. No LOD/cell handling described. | [author] https://www.nexusmods.com/skyrimspecialedition/mods/196970 |
| Dragonborn Can Surely Fly VR (alpha, r/skyrimvr Feb 2024) | VR | unknown | unknown — could not open the thread (rtrace mirror 502, reddit blocked); not found on Nexus | [snippet] https://reddit.rtrace.io/r/skyrimvr/comments/1aj2mx6/ |
| **Paraphernalia – VR Dragon Riding** (gavwhittaker/staalo18, 106120, 2023) | VR | Papyrus; summon, mount, pick a map marker, dragon flies there and circles | "reduce the dragon's speed and flying height to give the game more time to update the landscape and to reduce LOD switching"; "a lot of LODs, textures and meshes to swap in and out during flight"; recommends VRAMr; "don't ride/wait/ride … let the game engine catch up"; free-roam flight abandoned in VR: "could not achieve consistent functionality, performance or game stability … it's the game engine!" | [author] https://www.nexusmods.com/skyrimspecialedition/mods/106120 |
| **Intuitive Dragon Ride Control** (staalo18, SE 64679 / LE 111136) | SE/LE | Papyrus, camera-based dragon control; **"After you selected a fast travel target on the map, your dragon will fly with you to this target in real time (no load screen)"** | Nothing about cell loading in the description (posts unreadable). The same author's VR port admits speed/height were cut for streaming. | [author] https://www.nexusmods.com/skyrimspecialedition/mods/64679 |
| Real-Time Dragon Fast Travel (Keldis, SE port 4275) | SE | Bend Will dragon flies to the chosen marker in real time | No streaming notes; walled cities unreachable because dragons can't enter those worldspaces; "keep the ESP near the end" | [author]/[snippet] https://www.nexusmods.com/skyrimspecialedition/mods/4275 |
| Command Dragon – Ultimate Dragon Riding (LE 31697, 2013) | LE | Papyrus; "Real-time fast travel as a bonus feature" | None documented | [author] https://www.nexusmods.com/skyrim/mods/31697 |
| (ESL) Fully Flying Dragons SE (gg77, 3191) | SE | J3X "Flyable Dragons" scripts | **"The speed is at the maximum of the possibilities on 'my' computer … or when I change of cell … CTD"** — speed is capped by cell loading | [author] https://www.nexusmods.com/skyrimspecialedition/mods/3191 |
| Dragon Aspect Flight SKSE (nwn9, 183254, 2026) / Flying Vampire Lords SKSE (LvxMagick) | SE | CommonLib plugin; player flies with collision ("invisible platform" artefact); OAR/BDI animations | None. README talks only about velocity-smoothing state and a jthread. | [author][source] https://www.nexusmods.com/skyrimspecialedition/mods/183254 , https://github.com/nwn900/DragonAspectFlight |
| Real Flying (with Gliding and Collisions) (Anton, LE 64769, 2015) | LE | SKSE plugin + FNIS; engine collision while flying | None | [author] https://www.nexusmods.com/skyrim/mods/64769 |
| Flying Mod Beta (porroone) / Overhaul / Rework; Animated Wings Ultimate; Bird Races of Skyrim (Bad Dog, 42300) | LE/SE | Papyrus + animation; "no collisions while flying and you really zoom along" | None; Bad Dog recommends DynDOLOD because "up in the air, your eyes are on the horizon". Porroone's own page could not be opened. | [author] https://www.nexusmods.com/skyrimspecialedition/mods/42300 |
| SkyTrek SE – Skyrim on Autopilot (25308) | SE | Papyrus autopilot on foot/horse/dragon | None | [author] https://www.nexusmods.com/skyrimspecialedition/mods/25308 |
| Touring Carriages / Scenic Carriages (real-time carriage rides) | LE/SE | Papyrus-driven cart along roads | Pages not fetched. Forum reports of stutter "EXACTLY at cell border lines" and carts stuck at a "bad cell". | [hearsay] https://forums.nexusmods.com/topic/924235-only-terrain-and-sky-loading-sceniccarriages |
| **Clean Loading Transitions** (ahzaab, 190193, Aug–Nov 2026) | SE/AE | SKSE: hides LoadingMenu/FaderMenu/MistMenu, keeps the last rendered frame, fades to the new cell; progress bar | Not streaming, but a data point: **"If a cell is already in memory … an almost immediate transition … without seeing any black screen"**; "Some pop-in may be visible while fading into the next cell". Conflict list = its hook points: LoadingMenu, FaderMenu, MistMenu, loading image-space modifiers, DirectX Present, world/Scaleform render functions. GPL source "Skyrim Load Progress on GitHub" (repo not found by search/gh). | [author] https://www.nexusmods.com/skyrimspecialedition/mods/190193 |
| po3 Photo Mode / `tfc` photo tools | SE | free camera | Nothing special: sheson: "If you use tfc to fly close, then LOD does not get replaced by the full model" — loading is player-centred, the camera sees LOD. Matches our design (camera-only flight over LOD). | [snippet] STEP forum via search |
| Horse speed mods | — | — | Only hearsay: "when moving at a fast rate … the game fails to load the grass or many other objects fast enough"; micro-stutter "as soon as they mount up and run". No mod addresses it. | [hearsay] |

**What this means for us.** Our architecture (park the player, fly only the camera, move the
player once) is already the strongest pattern in the field; Hawk Vision VR arrived at the same
split independently and simply refuses to leave the grid. Nobody has a per-frame limiter; the
pragmatic answers were "slow down", "fly lower to reduce LOD switching", "VRAM headroom".

### LOD tools (DynDOLOD, NGIO, large references) — relevant facts [V from dyndolod.info]

* DynDOLOD "How LOD works": the active grid is player-centred; when a cell attaches "the game first
  loads the ground and lowers the terrain LOD meshes by a fixed amount under the ground", disables
  water LOD, then loads trees and disables tree LOD, then full objects and disables object LOD;
  "the full models and their object LOD are both rendered for a brief time". Render range ≈100
  cells. https://dyndolod.info/How-LOD-Works
* Dynamic LOD (NearGrid/FarGrid) enables/disables neverfade refs "based on the distance to the
  player" — the camera is not mentioned, so during our camera-only flight dynamic LOD will not
  react to the camera (fine: it sits in the sky). https://dyndolod.info/Help/Dynamic-LOD
* **DynDOLOD DLL NG fixes "object LOD not unloading after fast travel" and "tree LOD missing after
  fast travel"** — i.e. the engine's own big-move path has LOD bookkeeping bugs that the DLL
  papers over. Our move is a fast travel without the menu: after landing, check that object/tree
  LOD in the destination grid actually unloaded (the DLL may key off events we don't raise).
  https://dyndolod.info/Help/DynDOLOD-DLL
* Large reference system (SE only): full models of RNAM-listed STAT/MSTT refs are loaded out to
  `uLargeRefLODGridSize` (odd, launcher offers 5/7/9/11; 5 = off). The engine therefore already
  has a path that loads full models **outside** the active grid — and it is "limited and buggy"
  (z-fighting when object LOD isn't disabled, overwrites by non-ESM plugins). Its existence is
  the precedent for "warm the landing area's models before the grid arrives".
  https://dyndolod.info/Help/Large-References
* Grass: NGIO-NG / Grass Cache Helper NG make the game load `.cgid` per cell instead of generating
  grass at attach; the NGIO hooks we saw inside `TES::UpdateGrid` (13288+0xA1D/+0xB29/+0xBF8) are
  these. Grass cost at attach is therefore file IO, not generation. Nothing documented about
  async loading of the cache. https://github.com/DwemerEngineer/No-Grass-In-Objects-NG ,
  https://www.nexusmods.com/skyrimspecialedition/mods/101095

---

## 2. Engine knowledge: what is documented

### 2.1 INI settings (STEP wiki, defaults for Skyrim; SE identical unless noted) [V]

| setting | default | documented meaning | relevance |
|---|---|---|---|
| `uGridsToLoad` | 5 | odd, ≥5 recommended; STEP: leave default; DynDOLOD made raising it pointless | our 25-cell attach |
| `uExterior Cell Buffer` | 36 | "at least (uGridsToLoad+1)²"; negative = CTD | **must be ≥25 + headroom for our pre-queued cells**; if the user's INI is lower than 36 the pre-load evicts itself (RE §3.1) |
| `uInterior Cell Buffer` | 3 | | — |
| `iPreloadSizeLimit` | 26214400 (25 MB) | no description on STEP; community formulas conflict (UESP snippet says "400 MB" for a Fallout title) — treat as unknown | may cap how much the background loader holds **[I]** |
| `bPreemptivelyUnloadCells` | 0 | no description; STEP forum tweak thread exists | an engine "unload early" switch worth a look in the dump |
| `bBackgroundCellLoads` | 1 | STEP: just "default is 1"; a STEP thread says setting it 0 hides crashes from a problem cell | probably gates the CellLoaderTask queue **[I]**; must stay 1 |
| `bUseBackgroundFileLoader`, `bUseMultiThreadedTrees`, `bLoadBackgroundFaceGen` | 0/1/0 | "believed to be unused by the game" | ignore |
| `bLoadHelmetsInBackground`, `bUseMultiThreadedFaceGen` | 1 | | — |
| `bSelectivePurgeUnusedOnFastTravel` | 0 | undocumented | fast-travel purge switch; the name suggests the engine purges *everything* on fast travel by default — relevant to why a big move thrashes the buffer **[I]** |
| **`iPostProcessMilliseconds`** | 5 | undocumented | **likely the per-frame budget of `IOManager::sub 75705` ("finish queued IO → attach loaded 3D") in Main::Update [I]**; raising it during arrival would drain the model queue faster at the cost of frame time; lowering it during the camera flight smooths frames |
| **`iPostProcessMillisecondsLoadingQueuedPriority`** | 20 | undocumented | same budget while a loading screen is up **[I]** |
| `bPreloadLinkedInteriors` | — | **not found anywhere** (STEP General/BackgroundLoad pages, search) — may not exist in Skyrim | — |
| `uLargeRefLODGridSize` | 11 (Prefs) | see §1 | — |

Sources: https://stepmodifications.org/wiki/Guide:Skyrim_INI/General ,
https://stepmodifications.org/wiki/Guide:Skyrim_INI/BackgroundLoad ,
https://stepmodifications.org/forum/topic/2520-bpreemptivelyunloadcells1-tweak

### 2.2 Prior art on the engine's cell loading

* **Stable uGridsToLoad (Altimor, LE 41592, 2013) [author]**: let uGrids be changed at runtime
  ("setini uGridsToLoad:General 7 … open & close the map screen to force the game to load the new
  cells") and load saves across uGrids changes. Forum relays **[hearsay]**: he found "bad code in
  cells when loaded that cause … stack overflows", that infinite loading screens "are caused by two
  threads waiting on each other", and he "was working on multithreaded cell loading" — never
  released; STEP dropped the plugin "due to concerns regarding a potential memory corruption
  issue" (a Steam post describes "an infinite loop in its cell loading code"). Lesson: the grid
  code tolerates runtime re-sizing (idea §4-I), and multithreading the attach itself has defeated
  at least one competent attempt. https://www.nexusmods.com/skyrim/mods/41592 ,
  https://stepmodifications.org/forum/topic/2864-stable-ugridstoload-by-altimor/
* **Skyrim Cell load Freeze fix NG (wyongcan, 160704, installed) [author]**: "two threads acquire
  locks in opposite order and hang … Based on the call stack … related to Cell loading … more
  likely with many mods". Fix = reorder one lock acquisition. Source:
  https://github.com/GarrixWong/skyrim-freeze-fix . Relevance: any plugin that calls
  `13427`/`18976` from the main thread while CellLoaderTask threads are busy touches the same
  locks; keep the pre-queue drained (`18548 == 0`) before we start spreading the attach.
* **Baked Goods (ItzIvy, 197744, installed) [author]**: `bQueued3DCellFix` — "fixes a crash when an
  actor's 3D finishes loading while it is changing cells". Spreading the attach widens exactly
  that window (actors whose cell is attached on frame N while their queued 3D lands on frame
  N+k); keep this fix on and watch its log.
* **Faster Cell Lookup (Asciim0v, 178777, installed) [author]**: regenerates missing OFST
  (cell offset) tables for ESPs/edited ESMs so "the game uses this to quickly find which files
  belong to which coordinates in a cell". This is the `TESWorldSpace::sub 20460 → 20456 → TESFile`
  cost in our `13362` path; it is already as cheap as it gets without pre-queuing.
* **Hitch Hunter and Fixes (Zzyxzz, 194231, installed) [author + local INI]**: the closest thing
  to a "streaming smoother" that exists:
  - `RenderGate`: "While the world is being drawn, loading threads wait briefly before creating
    new textures and buffers" (max 8 ms/frame) — directly targets our first-draw hitches.
  - `SpreadNPCRebuilds`: "only one is rebuilt per frame and the others follow in the next frames"
    — the engine does several 30–60 ms facegen rebuilds in one frame otherwise; same pattern as
    our budgeted attach, so there is precedent that the engine survives it.
  - `IdleGeometrySubmit` (loading screens only): "hands finished geometry to the GPU in idle
    moments instead of in one large burst".
  - `TESFilePrewarm` (off by default; needs MaxStdio): the first cell loads otherwise build the
    plugin file cache — part of any *first* big move in a session.
  - **Hitch Report** (currently `Enable=1`, threshold 50 ms): names "which textures and meshes
    took how long to load", NPC rebuilds, GPU/VRAM limits per spike. **Use it to attribute our
    arrival frame and the post-landing hitches before building anything.**
* **SSE Engine Fixes** (TOML read from GitHub) [V]: nothing touches cell attach. Relevant bits:
  `bFormCaching`, `bTreeLodReferenceCaching` ("speeds up a tree LOD function that slows as plugins
  increase"), `bMaxStdIO`, memory-manager overrides incl. Havok's, `bCellInit` (a form→pointer
  conversion crash), `bSavedHavokDataLoadInit`.
  https://raw.githubusercontent.com/aers/EngineFixesSkyrim64/master/Skyrim/Data/SKSE/Plugins/EngineFixes.toml
* **Disabled Reference Integrity Fix** [snippet]: micro-stutter from refs/navmesh below the
  worldspace floor, "intercepts references before their meshes and textures load" on cell load —
  evidence that per-reference hooks at attach time are viable and already shipped.
* **Skyrim Priority** (installed): just `SetPriorityClass(HIGH)`. Not relevant.

### 2.3 Fallout 4 / Starfield equivalents

* Fallout 4 Papyrus has **`ObjectReference.PreloadTargetArea()`** ("preloads the target area for
  the calling reference", intended for doors; "will fail for other refs and if called to preload
  an exterior while the player is in an exterior"; verify with console `MGO Cell`) and
  **`PreloadExteriorCell`** ("Do not use … may break questing, items, and other things in the area
  that rely on loading notifications to know when the player is 'nearby'"). **[snippet]** from
  https://falloutck.uesp.net/wiki/PreloadTargetArea_-_ObjectReference and
  https://falloutck.uesp.net/wiki/PreloadExteriorCell_-_ObjectReference . Skyrim has neither
  (our Plugin.cpp comment already notes this); the engine-side equivalent is the door preload
  `40845 → 13378 → CellLoaderTask` we found. The FO4 warning is a real caveat for *our*
  pre-queue too: pre-loaded cells go through `CellLoaderTask::sub 18529 → 18979 → buffer`, which
  may fire load-time logic early — nothing observed yet, but worth a Papyrus-log glance.
* Vertibird flights in FO4 are scripted real-time flights with the same engine; no documentation
  of special streaming was found (forum claim "no way to script a vertibird to fly" is wrong and
  irrelevant).
* FO4 *High FPS Physics Fix* / *Load Accelerator* / *Long Loading Times Fix* speed up **loading
  screens** by uncapping the frame rate and removing sleeps/waits in the loader ("speeding up
  slow locations in the game code that were slowing down other loading threads", "almost no
  effect on HDD"). Transferable idea: the loader threads have artificial waits; Hitch Hunter's
  `DynamicGeometryWaitYield`/`RenderGate` are the Skyrim analogues. **[snippet]**
* Starfield: a Nexus article notes "Starfield's active uGrid cells move with the player" — same
  model, nothing more found. **[snippet]**

### 2.4 Havok batch insertion

Havok SDK docs were not reachable (deepwiki mirror 429). From memory of the 2010 SDK, flagged
**[unverified recollection]**: `hkpWorld::addEntityBatch` exists precisely because single
`addEntity` calls each re-insert into the 3-axis sweep-and-prune broadphase (sorted endpoint
arrays, O(n) shifts per insert), while the batch path sorts once; fixed (`MOTION_FIXED`) bodies
still pay the broadphase insert but no island/solver setup; `hkpEntityActivation::DO_NOT_ACTIVATE`
avoids waking islands. Our RE shows the game already brackets the attach in one batch
(77905/77906 → 61315). Implication: splitting into per-cell batches costs several broadphase
sorts instead of one — modest, since each sort is over the existing world — but there is no
documented "cheaper insert"; the only real lever is **inserting fewer bodies per frame or later**
(§4-D). No SKSE plugin was found that touches `bhkWorld` insertion.

### 2.5 Existing "async cell loading" plugins — none

Searches for async/smooth/preload cell plugins (Nexus, GitHub, STEP) returned only: Clean Loading
Transitions (visual), Hitch Hunter (loader-thread gating, NPC spreading), Faster Cell Lookup
(record lookup), skyrim-freeze-fix (deadlock), Grass Cache Helper (grass IO), the 2013 Altimor
attempt. A general-purpose budgeted-attach loader would be new.

---

## 3. First-draw hitches — what is known

* Hitch Hunter's author (measured, **[author]**): loader threads creating D3D11 textures/buffers
  mid-frame stall the driver ("hold the graphics driver in the middle of a frame"); NPC
  appearance rebuilds are 30–60 ms each and the engine does all of them in one frame; dynamic
  geometry buffers (4 MB vanilla) fill and force waits; the sun-glare occlusion query forces a
  driver flush every frame. All of these have fixes in the installed build.
* Forum symptom reports **[hearsay]**: "stuttering when moving the camera to look around, but only
  the first time, after that no more" — first use of textures; VRAM rising at the same moment.
* No Skyrim plugin pre-warms textures or shader permutations for a future view. Community
  Shaders compiles its permutations ahead of time (we know this from our own CS work), so the
  remaining first-draw cost is **texture residency/upload, skin-partition/facegen builds for
  actors, and BSDynamicTriShape/particle buffer growth** — all measurable per spike with the
  Hitch Report.

---

## 4. Ideas, ranked (benefit × confidence ÷ risk)

Hook ids are AE 1.6.1170 (see RE §4). "Budget" = main-thread ms per frame.

### A. Finish the budgeted attach, then **measure before adding anything** — benefit high, risk low
What: the hook at `13430+0x105` (RE site C) already records slots; make the per-frame drain
centre-out with its own `77905/77906` pair per slot (so each frame pays one cell's broadphase
insert, not all 24), keep `13362` (B) skipped/no-op via the pre-queue, and run `13430` once at the
end for the activation pass. Then enable Hitch Hunter's report (`HitchThresholdMs=20` for this)
around 10 flights and read which frames remain and what they contain (textures/meshes by name,
NPC rebuilds, GPU). Everything below should be chosen from that report, not guessed.
Risks: the Baked Goods `bQueued3DCellFix` window; `PositionPlayer` events during the drain
(flush first); save during drain (block). Confidence this halves the stall: medium-high — the
RE says the 13362 file reads are already gone with the pre-queue, and 25 → 1 cell/frame bounds
the attach frame by the biggest single cell (cities will still be 100+ ms).

### B. **"Strip-walk" teleport: move the player along the engine's own 1-cell path** — benefit potentially high, risk medium, cheap to A/B
What: instead of one ≥5-cell jump, during the last part of the flight move the parked player
one cell at a time toward the destination along a straight line, two sub-steps per cell:
(1) set the position just across the next cell border → `TES::UpdateGrid` inside-grid path
queues the strip beyond the grid (`18541`) and does **not** shift; wait until `18548 == 0`;
(2) set the position to that cell's centre → shift path with `|dx|==1`: 5-cell detach, `13362`
skipped, 5-cell attach of **already-loaded** cells, one small Havok batch. Repeat. A 40-cell trip
is 80 sub-steps; at 4/s it fits a 20 s flight; the camera is above clouds the whole time.
Why it might win: it uses the exact code path the engine tunes for walking (no synchronous CELL
creation, buffer in play, strip-sized Havok batches) with zero hooks.
Costs/risks: total IO is higher (every intermediate strip is loaded and dropped — `uExterior Cell
Buffer` churn); the *actual* player passes through cells: triggers, encounter zones, dragon
attacks, NPC detection, OnCellAttach scripts along the route (mitigate: SetGhost + invisible +
`tcl`-equivalent via `0x20F6A44` + stop AI; still fires Papyrus `OnCellAttach`/`OnLoad` on refs);
water/landing-height issues when the parked player is placed over cliffs/water (place at a high
Z with no collision and no gravity); grass IO per strip. Confidence it beats A: low-medium —
unknown whether 5-cell strips of pre-loaded cells attach in <16 ms in this modlist (our walking
hitches say "small but not zero"). Worth one evening as an A/B because it needs no new hooks.

### C. **Warm the landing view on the GPU during the flight** — benefit medium-high for the post-landing hitches, risk low
What: the model preloader already demands the destination's models; extend it to
(1) textures: for each preloaded `BSGeometry` force its `BSShaderMaterial` texture set to load
(the engine loads textures lazily on first `BSLightingShaderProperty` setup) — simplest is to
attach the preloaded model briefly under a hidden node (`kHidden`/zero scale) inside the current
grid so the renderer's `BSShaderAccumulator` touches it once, or to call the texture-set
`SetTexture`/load path directly; (2) actors: during the flight call `Load3D`/facegen build for
NPCs in the destination's manifest (Hitch Hunter shows these are the 30–60 ms items) — the
engine already allows actors' 3D outside the grid (dead bodies, dragons);
(3) keep Hitch Hunter `RenderGate=1` and raise `DynamicGeometryBufferMB` if the report shows
buffer waits at landing. Confidence: medium that textures/actors are the residual; the report
settles it.

### D. **Deferred collision for far cells (lazy Havok)** — benefit medium, risk medium-high
What: during arrival, hook `TESObjectREFR::InitHavok` (already hooked by another plugin at +0x9
— check who; probably Precision or CS) or `bhkWorld` add in `18976`'s reference walk to skip
collision for refs farther than R from the landing point, record them, and insert on later
frames (or when the player/camera approaches). Land/water collision stays. The engine's own
`tcl` path proves the world survives missing collision for a while, and refs in the outer ring are
by definition far from the parked player.
Risks: NPCs in the outer ring fall through nothing (they stand on land collision — fine) but
collide with nothing (buildings) → path through walls briefly; physics-driven refs (hanging
objects, traps) misbehave; Precision/other hooks on the same sites. Only worth it if the report
shows the Havok flush (`77906 → 77918 → 61315`) still dominates after A.

### E. **Two-phase attach: land/water first, references later** — benefit medium, risk high
What: inside the per-slot hook, call `13427` for the slot but intercept `18976`'s reference walk
(the vtable calls) so only `TESObjectLAND` (18747/18767) and water are set up on the arrival
frame, and references are attached by budget afterwards. Gives a correct ground under the camera
immediately; references stream in over ~0.5 s while the camera is still descending.
Risks: `18976` is one function with locking and cell state (`+0x44`) transitions; splitting it
needs a re-implementation of its loop, and the second `13430` pass (`19063` activate) assumes
refs are present. Only after A/B/C and only if the single-cell attach frame is still >50 ms.

### F. **Tune the IO budget around the move** — benefit low-medium, risk very low
What: `setini iPostProcessMilliseconds` (or write the global it maps to) to ~1–2 during the camera
flight (smoother frames while the pre-queue streams models) and to ~20 for the first second after
the move (drain the queued 3D quickly while the camera is still high), then restore. First confirm
in the dump that `75705` reads this setting **[I]**.

### G. **Time the unavoidable stall where it hurts least** — benefit low (perceptual), risk nil
What: whatever frame does the attach, make the camera nearly static and looking at sky/sun/cloud
for that frame window, disable frame generation around it (FG amplifies a long frame into a visible
repeat), and optionally hold the previous frame (Clean Loading Transitions shows the renderer
tolerates "render last frame while loading"). Already partly how the arc is designed; keep it.

### H. **Hide the stall behind a fade** (fallback only) — benefit high, cost: not seamless
What: the engine's own big-move recipe (`13316/13317`: cancel loads, disable physics, unload,
attach, resume) behind a 0.3 s fade at the top of the arc. Mention only as the floor to beat.

### I. **Shrink the grid for the move** (`uGridsToLoad` 5 → 3 → 5) — benefit medium, risk high
What: Altimor showed uGrids can change at runtime if the grid array is rebuilt (he forced it with
a map open/close). Attach 9 cells at the move, then grow back to 5 (a 16-cell ring attach a second
later, itself spreadable). The `GridCellArray` is allocated with `length` at init
(`15941/15954`); re-sizing means re-creating it (what 13428 "first grid load" does) — invasive,
and DynDOLOD/NGIO/Grass Cache Helper read `uGridsToLoad` for their own radii. Not recommended
while A–E are untried; recorded because it is the only historical precedent for runtime grid
changes.

### J. **General-purpose streaming loader (releasable)** — what it would be
A small CommonLib plugin exposing: `Prefetch(ws, cx, cy, radius)` (→ `18541`/`13378`, with
`18548` polling and `uExterior Cell Buffer` check/warn), `WarmModels(manifest)` (today's
preloader + C), `BeginBudgetedShift(targetPos, msPerFrame, order=centre-out)` (hooks C + per-slot
Havok batches + end-pass `13430`), `OnStreamingIdle` callback for the caller (Sky Above, carriage
mods, dragon mods, photo tools), and a `Settle()` that flushes the queue before saves/menus/
`PositionPlayer`. Hooks needed: `13430+0x105` (C), optionally `13288+0x9A9` (B) and a per-frame
tick (we have `PlayerCharacter::Update`). Conflict surface: NGIO (grass loops in 13288 — not on
our sites), Precision/CS (`InitHavok`), Baked Goods (queued 3D), freeze-fix (lock order). Guard
every hook with byte checks as Hitch Hunter and our plugin already do. Risk profile is the same
as A; the extra work is the API and the save/menu edge cases. Expected demand: the dragon/VR
riding authors above explicitly cut speed because of this, so there is an audience.

---

## 5. Open items / not found

* Hawk Vision VR's Reddit release post (r/skyrimvr "three_new_magic_mod_releases") and the Nexus
  posts tab could not be read; whether the author hit grid-shift problems before adding the leash
  is unknown.
* "Dragonborn Can Surely Fly VR" (Feb 2024 alpha): thread unreadable; no Nexus page found.
* Porroone's Flying Mod Beta page (LE) and Touring/Scenic Carriages pages: not read (403).
* `bPreloadLinkedInteriors`: no documentation anywhere; may not be a Skyrim setting at all.
* Havok batch-add cost: SDK docs unreachable; §2.4 is recollection.
* Clean Loading Transitions source repo: linked from the mod page but not found by search/`gh`.
* Whether `iPostProcessMilliseconds` is the `75705` budget: needs a glance at the dump.

## 6. Source list

Mods (Nexus, read via API unless noted): Hawk Vision VR 196970 · Clean Loading Transitions 190193 ·
Dragon Aspect Flight SKSE 183254 (+ https://github.com/nwn900/DragonAspectFlight) · Real-Time
Dragon Fast Travel 4275 · Paraphernalia VR Dragon Riding 106120 · Intuitive Dragon Ride Control
64679 / LE 111136 · Command Dragon LE 31697 · Fully Flying Dragons SE 3191 · Bird Races SE 42300 ·
SkyTrek SE 25308 · Real Flying LE 64769 · Stable uGridsToLoad LE 41592 · Hitch Hunter and Fixes
194231 · Faster Cell Lookup 178777 · Skyrim Cell load Freeze fix NG 160704
(https://github.com/GarrixWong/skyrim-freeze-fix) · Baked Goods 197744 · Grass Cache Helper NG
101095 · DynDOLOD DLL NG 97720 · Skyrim Priority 50129 · Horizon Fix 184607 (not relevant, read
by accident).
Docs: https://dyndolod.info/How-LOD-Works · https://dyndolod.info/Help/Dynamic-LOD ·
https://dyndolod.info/Help/DynDOLOD-DLL · https://dyndolod.info/Help/Large-References ·
https://stepmodifications.org/wiki/Guide:Skyrim_INI/General ·
https://stepmodifications.org/wiki/Guide:Skyrim_INI/BackgroundLoad ·
https://raw.githubusercontent.com/aers/EngineFixesSkyrim64/master/Skyrim/Data/SKSE/Plugins/EngineFixes.toml ·
https://github.com/DwemerEngineer/No-Grass-In-Objects-NG ·
https://stepmodifications.org/forum/topic/2864-stable-ugridstoload-by-altimor/
Snippets only: https://falloutck.uesp.net/wiki/PreloadTargetArea_-_ObjectReference ·
https://falloutck.uesp.net/wiki/PreloadExteriorCell_-_ObjectReference · https://ck.uesp.net/wiki/UGridsToLoad ·
https://forums.nexusmods.com/topic/13000854-psa-ugridstoload-limits ·
https://forums.nexusmods.com/topic/5068975-ugridstoload-talk-and-testing ·
https://reddit.rtrace.io/r/skyrimvr/comments/1aj2mx6/ · STEP forum DynDOLOD threads (sheson on tfc/LOD).
Local: `C:\Modlists\NGVO 8.0 Beta\mods\Hitch Hunter And Fixes\SKSE\Plugins\HitchHunter.ini`,
`...\Faster Cell Lookup\SKSE\Plugins\FasterCellLookup.ini`, `...\Baked Goods - Skyrim Engine Fixes\SKSE\Plugins\BakedGoods.ini`,
`C:\Users\foxnn\dev\sky-above-fast-travel\Source\src\Plugin.cpp` (current preloader / spread-attach hook).

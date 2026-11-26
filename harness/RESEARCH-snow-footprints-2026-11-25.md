# Snow deformation without a trench, and footprints that match the ground (2026-11-25)

Nothing is deployed or installed, and the live modlist is untouched. You run the tests.

| Piece | Where | State |
|---|---|---|
| Deformation code | CS fork worktree `C:\Users\foxnn\dev\cs-wt-snowdeform`, branch `feat/snow-deform-v2` (from `foxnne/merge-rc2-1123`), commits `8387805aa` + `9a156d989` (Codex review fixes) | Builds clean with PR-Tracy. Not pushed. Untested in game. |
| Footprint mod (staged) | `C:\Users\foxnn\dev\ngvo-perf-lab\staged\foxnne - Footprints Match Ground\` | Generated. Not installed. |
| Generator | `C:\Users\foxnn\dev\ngvo-perf-lab\harness\footprints_match_ground.py` | Rerunnable. It refuses to write into `mods\`. |
| Previews | `...\staged\foxnne - Footprints Match Ground\_preview\` (`beast_prints_on_landscape.png`, `report.txt`) | |

No downloads are needed. Everything is built from mods that are already installed.

---

## 1. Deformation without a trench

### What made the trench (confirmed in `SnowDeformation.cpp`)

1. **Full blanket carve on every press stamp.** `StampMotion.w` was the global blanket height for every stamp, and the shader carved `min(height, raise)`. So every planted foot cut straight down to the ground.
2. **Wade stamps.** `makeWade` ran on every collision capsule below the blanket top (calves, thighs and so on), widened ×1.6 and carved `raise - clearance`.
3. **The root "trail" stamp.** It was as wide as the widest shape, up to 48 units, carved the full blanket and was swept along the actor's motion every frame.
4. **Smeared prints.** A press stamp swept across the whole per-frame contact motion (up to 96 units), so a foot that landed while still moving cut a slot.

### What the branch changes (`src/Features/SnowDeformation.{h,cpp}`, `SnowDeformationUpdateCS.hlsl`, `en.json`)

- **Per-stamp carve.** `StampMotion.w` is now the fraction of the local blanket that a stamp carves, and the shader multiplies it by the blanket raise at that texel.
  - Planted feet carve `Foot Sink` (0.75), scaled by weight and impact.
  - Leg wades carve 0.7 and the trail carves 0.55, so foot holes stay deeper than the furrow between them.
  - Trench mode sends 1.0, which is exactly the old `min(height, raise)`.
- **Furrow gate (trail and wade only in deep snow).** Leg wades and the root trail are only emitted when the local blanket depth under the actor is at least `Furrow Depth` × the actor's height (default 0.3, about knee deep).
  - The local depth comes from the probes that already exist: each actor's highest blanket raise under its prints, read back 3 frames later.
  - Release has 15 % hysteresis. An unknown depth counts as shallow.
  - With your 30-unit blanket, a person (about 128 units tall, threshold 38) leaves separate prints. A dog, fox or child ploughs a furrow.
- **Per-foot, contact-only prints.** A shape stamps only while its bottom is within 2 units of the land, as before. In Footprints mode:
  - a planted foot's sweep is capped at 35 % of its length, so prints stay print-shaped;
  - ghost races (`ActorTypeGhost`) leave no prints.
- **Depth from weight and speed.**
  - Weight factor = scale × (0.9 + 0.2 × NPC weight / 100) × (1 + equipped weight / 150), clamped to 0.6–1.8.
  - Impact factor = 1 + 0.5 × clamp(downward speed on the landing frame / 300 u/s).
  - Both scale the print depth and the carve fraction, so running and heavy armour press deeper and sneaking presses shallower.
- **`DeformableSnowAt(pos)` and decal suppression.**
  - Deformable snow means: the vanilla snow material, or Snow Cover snow ≥ 0.5 (the same estimate the stamps use), and not a Firm Road.
  - A footprint decal is any decal whose texture set's diffuse path contains `footprint` or `footstep`, which covers all `NMN_Footprints\...`.
  - When such a decal lands on deformable snow, it is culled and its lifetime is cut to 0.05 s, so it expires.
  - Both kinds of decal are covered: geometry decals in the existing `RegisterDecal`, and simple decals through a new `BSTempEffectSimpleDecal::Initialize` vfunc hook (0x25).
  - Footprint decals are no longer added to the displaced-decal list, so prints are never drawn inside a dent.
  - Decals stay on bare ground, on roads and on snow too thin to deform.
- **Debug.** The Debug section shows:
  - press / wade / trail stamp counts and the number of actors furrowing;
  - footprint decals hidden / seen.


### Review fixes (`9a156d989`)

- **Prints only on contact.** A pressed shape prints when it lands, and again only after moving 0.6 × its radius (at least 3 units) while planted. Held contacts send probe-only stamps, so sinking and the local snow depth keep their measurements.
- **Decal hooks only classify and queue.** On the main thread, the Main::Update gather culls a queued footprint decal on deformable snow. It retires the decal only when a deformation print lands within 24 units within 30 frames; otherwise it un-culls it.
- **Thread check.** The first 4 hook calls log their thread id against the main thread. Debug shows hidden / restored / seen, plus a count of hook calls made off the main thread.
- **Landscape only.** Simple decals must lie within 16 units of the land height to be hidden. Snow Cover is read at the point, not as the area upper bound.
- **Tighter furrow gate.** Furrows release at 0.95 × the threshold, and a missing depth measurement is dropped after 0.25 s.

### Settings (Snow Deformation → Tracks)

| Setting | JSON key | Default | Use |
|---|---|---|---|
| Track Style | `TrackStyle` | 1 = Footprints | 0 = Trench (legacy). **This is the A/B switch.** |
| Furrow Depth | `FurrowDepth` | 0.3 × height | 1.0 means never furrow. Lower values make legs plough sooner. |
| Foot Sink | `PressCarve` | 0.75 | 1.0 pushes the foot through to the ground. Lower leaves packed snow at the bottom of the print. |
| Depth From Weight And Impact | `WeightDepth` | on | |
| Hide Footprint Decals On Snow | `SuppressFootprintDecals` | on | A/B for double prints. |

**Requirement:** the local depth needs probes. If both `SinkActors` and `SnowHeightVariable` are off, there are no probes, so there are never furrows (prints only). Both are on by default.

### Not done

- Plan step 5 (blood pools that fill the deformed snow) and step 6 (mover slowdown) are not done. They are separate jobs.

---

## 2. Footprints that match the ground

### Findings

- **How Dynamic Footprints (DF) places a print.**
  1. DF sinks `BSAnimationGraphEvent` (`FootLeft`/`FootRight`) for each actor.
  2. It picks a ground profile (`[Profile …]`). Rules are checked by LTEX, TXST, TXST path, mesh, MATO and weather, and the first profile that matches wins.
  3. It maps `[Race EDID=…]` to a `Set`, then `[Set <Set>:<FootprintSet>]` to one of 13 grounds (Ash, Dirt, Dirt01, DirtPath, FDG, FFD, FMDS, RD, RMud, Sand, Snow, VTD1, VTD2).
  4. It picks a footwear tier key: `Default`, `Barefoot…`, `Light…`, `Heavy…`, `HighHeels…`, and walk/run/sneak.
  5. The key gives an **IPDS** EDID. The IPDS points to an IPCT, the IPCT to a TXST, and the decal is played as an impact on an XMarker.
  6. Ini fragments come from `NMN_DynamicFootprints\<folder>\Profiles.ini` and `Patches\*\Humanoids.ini`.
- **Why the prints look wrong on our landscapes.**
  - The TXST diffuse paints a fixed colour (brown dirt, grey snow, and so on) with near-opaque alpha over 26–46 % of the texture, including a scattered "soil" halo. It is a brown sticker on any texture.
  - Our landscape is PBR. The winners are TomatoRim PBR Landscapes 2K for dirt01, snow01/02, rivermud, coastbeach and fallforestdirt; `foxnne - 2K Downscale` for dirt02, pineforest01 and frozenmarshdirtslopes01; and `foxnne - Dusty Roads` for dirtpath01. No fixed colour can match all of them.
  - **The normal maps use the wrong convention.** I integrated the maps into height fields and checked which channel convention makes them a consistent surface. TomatoRim and Bethesda-style maps only work in the game's convention (green = −dH/drow). Every DF print normal map I checked only works in the OpenGL convention, so in game the lighting does not form a clean dent.
  - The Sabrecat and Troll maps (the ones the Beast Race Expansion uses for Khajiit and Argonians) also encode a **mound**, probably because the image was rotated 180° without fixing the normals.
- **Which way is feasible with our decal path.**
  - Our decal hook only adds hull and domain shaders, so decals follow the displaced surface. The pixel stage is the engine Lighting shader with the decal's own texture set.
  - That decal draw has no access to the landscape's 6 layers or their blend weights, so "sample the underlying terrain" would need a new Lighting permutation and per-draw identification of footprint decals.
  - **The practical route gives the same result with data only.** The decal's diffuse becomes black RGB with alpha equal to the pressed area. With the decal's normal alpha blend (DODT flags 0x0B), the result is ground × (1 − alpha): the same material, just compressed and darker, on any landscape texture, plus the print's normal map.
  - A shader permutation would only add a roughness tweak on top. I do not recommend it for now.

### What was generated (staged mod `foxnne - Footprints Match Ground`)

1. **Darken-only diffuse for every DF and Beast Race Expansion print.** These use the same file names as Tomato's, so it is a drop-in override with no plugin changes.
   - The pressed area comes from each print's own normal map, integrated into a height field, so tread, toes and rims stay where the artist put them.
   - Darkening at the bottom of a print, by ground: mud 0.50, forest floor 0.40, dirt/roads 0.34, ash 0.30, sand 0.20, snow 0.14 (snow decals only remain where the snow is too thin to deform). Rims get 30 % of that.
2. **Normal maps rewritten in the game convention as dents** (same file names). `_preview\report.txt` lists every map that was converted, with the per-map red/green flips.

   Result: 402 diffuse files and 62 normal maps (271 MB staged). 82 TXSTs in the two plugins point to diffuse files that neither mod ships (for example `NMN_Bear_FMDS_*` and `NMN_Deer_Dirt01_*`). They are listed in `report.txt`, and those prints are already invisible today.
3. **Procedural digitigrade beast prints** (512², BC7 with mips) in `textures\NMN_Footprints\foxnne\`:
   - **Khajiit:** cat paw. A trapezoid plantar pad with a three-lobed rear edge, four oval toe pads with the medial-middle toe leading, no heel and no claws (claws retract). Decal size 14 units.
   - **Serval:** the same cat paw, 18 % narrower and 12 % longer. Decal size 13 units.
   - **Argonian:** three splayed forward toes with knuckle beads and claw tips that dig in, a short medial rear toe with a claw, a metatarsal pad, a little webbing at the toe roots, and no heel. Decal size 19 units.
   - Each has a left and right normal map and 13 per-ground darken diffuses. Left and right are mirrored, and toes point down the texture like the DF sets.
4. **`foxnne - Beast Footprints.esp`** (ESL; masters Skyrim.esm, Dragonborn.esm, Dynamic Footprints - Beast Race Expansion.esp).
   - It overrides the 46 `Beast_Khajiit_*` and `Beast_Argonian_*` texture sets: new diffuse and normal paths, and new decal sizes.
   - It adds 26 `Beast_Serval_*` chains (TXST → IPCT → IPDS), cloned from the Khajiit ones.
5. **`SKSE\Plugins\NMN_DynamicFootprints\Patches\Beast_ServalKhajiit\Humanoids.ini`.** This is the Beast Race Expansion Serval fragment pointed at `Beast_Serval_*`. It must win over the Expansion's copy.

**What we change in race and foot selection:** nothing in the DLL. Khajiit and Serval already use beast sets for all footwear. Argonians use `Beast_Argonian` only when barefoot, and human prints in boots, which is right for vanilla boots. Left and right come from DF's FootLeft and FootRight events.

### Still needs art or a decision

- The procedural paws are a solid first pass, but an artist sculpt (or a photo-sourced paw) would beat them close up. Judge them in game first.
- I did not author any new snow-specific decals. The deformation owns snow now.
- Human prints keep Tomato's shapes; only their colour and normals changed.
- Optional: a slightly lower roughness inside mud prints (wet), which needs the Lighting-permutation route.

---

## Install (when you choose to; MO2 closed)

1. Copy the staged folder into `mods\`.
2. Enable it **below** (winning over) `Dynamic Footprints Skse - Tomato's` and `Dynamic Footprints Beast Race Expansion 2.0`.
3. Enable `foxnne - Beast Footprints.esp` after `Dynamic Footprints - Beast Race Expansion.esp`.
4. Deploy the CS build from the branch yourself.

To back out, disable the mod and the plugin, and set Track Style to Trench.

---

## Test plan

**Setup:** CS from `feat/snow-deform-v2`, Snow Deformation open in the CS menu with Debug expanded, and your BlanketHeight of 30.

1. **Deep snow, walking and running (Footprints vs Trench).**
   - With Track Style set to Footprints, walk 20 m in open snow, then run back beside the first track, then sneak.
   - Expect separate left and right prints with rims, and no continuous trench. Running prints should be deeper and slightly longer, sneaking prints shallower.
   - Debug should show press stamps > 0, wade and trail = 0, and actors furrowing = 0.
   - Switch to Trench and repeat: the old trench should come back. That is the A/B.
   - Lower Furrow Depth to 0.15: a furrow should appear between the prints, with the foot holes still deeper inside it.
2. **Gradual fill.** Stand and watch a fresh track for 2–4 minutes (Lifetime 240 s).
   - Walls should slump and the prints should fill evenly, faster in snowfall, without leaving the bare ground or packed tint from the old trench edges.
3. **Double prints.** On vanilla-snow ground and on Snow Cover snow over dirt:
   - no flat DF decal should appear inside or beside the dents;
   - Debug "hidden / restored / seen" should rise together, with restored low. Check the CommunityShaders log for "Footprint ... decal initialised on thread X (main thread Y)"; if X != Y the deferral is doing its job.
   - Then walk onto a Northern Roads road with snow (Firm Roads): decal prints should appear again, and hidden should stop rising.
   - **If seen stays 0 while DF prints are visible, the prints use another decal path.** Tell me and I will hook it.
4. **Dirt roads.** With the staged mod installed, walk on a dirt road (DirtPath, `foxnne - Dusty Roads`), on TomatoRim dirt01, on river mud and on a beach.
   - Prints should read as darker, pressed ground of the same texture, with no brown stickers and no grey halo.
   - They should look like dents, not mounds, with the sun low.
   - If every print looks raised, the normal convention is backwards for decals. That is one line in the generator; tell me.
5. **Khajiit (and a Serval).** Load or spawn a Khajiit and walk on dirt and on thin snow:
   - you should see cat paws (four toes, a lobed pad, no heel) in boots and barefoot;
   - in deep snow, foot-sized dents and no trench.
   - A Serval should show the narrower paw.
   - If a Khajiit still shows human or Sabrecat prints, Tomato's `[Race EDID= KhajiitRace…] Set = Khajiit` is winning over the Expansion patch.
6. **Argonian.** Barefoot on mud and dirt you should see three clawed toes and a small rear toe. In boots you should see human boot prints, which is intended.
7. **Small and heavy actors.** Check that a dog or wolf ploughs a short furrow in a 30-unit blanket. Check that a giant or mammoth leaves deeper prints than you, not trenches.
8. **Performance.** Compare the `SnowDeformation::Update` pass time in Trench and Footprints. Footprints should be equal or lower, because there are fewer and smaller stamps.

## Risks and unknowns

- **Decal type.** DF prints are impact decals. If they are neither geometry decals nor simple decals, the hidden/seen counter will stay 0.
- **Culling and lifetime.** Cutting `lifetime` to 0.05 s after `Initialize` is assumed to expire the decal on the next update. Culling alone already hides it.
- **Foot collision shapes.** Prints rely on the biped foot collision shapes touching the ground. If an actor's skeleton has none, that actor leaves no prints in Footprints mode where it used to wade. Watch the press counter.
- **DF ini load order.** The Serval ini override depends on MO2 priority. Its race-to-set precedence against Tomato's base ini is untested.

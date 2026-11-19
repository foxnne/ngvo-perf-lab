# Height map with mountain/rock objects - working notes (2026-11-18)

## Loader facts re-read from the fork (src\Features\TerrainShadows.cpp, ShadowUpdate.cs.hlsl, TerrainShadows.hlsli)
- Name fields: world.Terrain.HeightMap.minX.minY.maxX.maxY.zMin.zMax ; zRange = zMin*8 .. zMax*8 game units.
- Texel -> height: lerp(-262136, +262136, texel) (fixed, independent of the name). 16-bit: raw = h/8 + 32767.
- zRange only normalises the R16G16_UNORM shadow-height texture: norm = (h - zMin*8)/(zMax*8 - zMin*8), UNORM clamps.
  => if real heights exceed zMax*8 they are CLAMPED (peaks cast shorter shadows and anything above zMax*8 is never shadowed).
  => the file name MUST carry the new max; a larger range only coarsens shadow-height quantisation (range/65535, ~1.2 units for 80k range).
- LightDeltaZ is derived from zRange too, so everything stays consistent when the name changes.
- Receiver test: pixel shadowed if worldPos.z < shadowHeight(bilinear) - 256 bias (soft band from penumbra heights).
  Consequence: a height map HIGHER than the visible surface anywhere (overhang, or bilinear interpolation across a cliff edge)
  darkens that surface even when it faces the sun. So the object layer must be conservative (see erosion rule below).
- Two files for one worldspace: last enumerated wins -> the new file has a different name (new zMax), so the old
  16-bit mod must be DISABLED when testing, not just out-prioritised.

## Plan
- Placed references (STAT etc.) with model path filter, full meshes, rasterised top-down at texel centres; max with LAND grid.

## Survey (obj_survey*.py; refs.pkl via floating-mesh/scan.py: 918 plugins, 331,410 Tamriel REFRs, last override wins)
- Enabled refs by model folder: landscape\mountains 7,817 (19 models, scale up to 5.5), landscape\rocks 37,521 (rockcliff01-08 ~5,000,
  the rest boulders/piles), wetrocks 3,612, dirtcliffs 1,410, ice 3,683 (glacier*/iceberg* ~520 large), tundra 713, volcanic 309,
  landscape\unique: markarthcliff01-04, hhmountainridge01, solituderockarch01-04. No mod-added mountain folders in Tamriel refs
  (mods replace the vanilla paths). full table: survey_land.txt
- BTO route rejected: DynDOLOD merges shapes per atlas/texture so rock vs tree vs building cannot be separated per shape, the LOD
  is simplified, stale (2026-11-08) and LOD4 only holds what has LOD. Placed refs + full meshes give class control and exact geometry.

## Rotation convention (check_rotation.py, check_rotation.log) - IMPORTANT
- 400 tilted (|rx|,|ry| > 0.08..0.2 rad) ground-hugging refs (rock piles, tundra land pieces, dirt islands, volcanic plateaus):
  spread of (object top - landscape) inside the footprint: world = Rx*Ry*Rz*v (Z applied FIRST, all clockwise-positive): median 37.7 / p90 77;
  floating-mesh nif.py ref_matrix (Rz*Ry*Rx): 92.8 / 268 (no better than ignoring tilt, 87 / 224); counter-clockwise variants 104-152.
  Ry*Rx*Rz is indistinguishable (38.1) - only "Z first" is decided by the data; Rx*Ry*Rz used (the usual documented convention).
- So floating-mesh/nif.py ref_matrix is wrong for tilted refs (fine for Z-only rotation). Not modified there; build script has its own.
- Triangle winding: cross(b-a, c-a).z > 0 = up-facing (mountain meshes: 96-100% of projected area up-facing; open-bottomed shells).

## Build script: build_heightmap_objects.py (~35 s, 24 workers, numpy only)
- Classes (model path regex): mountains (landscape\mountains\*, landscape\unique\markarthcliff*, hhmountainridge), cliffs (rockcliff*,
  rockcaveentrance*, rockanimalden*, dlc01 cave entrance), dirtcliffs, ice (glacier*, iceberg*), landforms (rocktundraland*, volcanicplateau*),
  rocks (rockl/m/s/pile incl. wet). 'arches' (solituderockarch*) exists but is OFF by default.
- Skips: deleted / initially disabled refs, refs whose enable parent (XESP, incl. opposite flag) is initially disabled, objects whose
  scaled horizontal extent < --min-footprint (512).
- Meshes: winning loose file (most from "Enhanced Rocks and Mountains - Addon", glaciers "Gleaming Glaciers"), else BSA. Hidden shapes skipped.
- Per object and texel: vertical crossings at the texel centre -> solid intervals [bottom, top] from triangle facing (open bottom = solid to
  the ground). An interval raises the surface only if bottom <= surface below + --gap (256); iterated so stacked objects support each other.
- Filter (default erode r=1): final = max(land, min3x3(max(land, objects))). Rationale: the receiver test uses BILINEAR shadow heights; with a
  3x3 min every interpolated height is <= the true top surface, so sun-facing cliff faces are not darkened by their own texel, and anything
  narrower than 3 texels (spikes, spires, thin walls) disappears. Costs one texel (128 u) of horizontal extent around each object.

## RESULT (supersedes the "erode default" line above: default filter is now OPEN r=1)
- Output: mod-objects\textures\terrain\HeightMaps\Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds (3808x3008 L16, 22,909,056 bytes,
  same header/layout as the 16-bit land map). zMax did NOT change with the default filter (Throat summit object tip, raw 39527, is narrower
  than 3 texels and is filtered; land max 39392 stays the maximum) -> SAME file name as the landscape-only map: pure file-conflict replacement.
  The unfiltered variant does exceed it (name ...-4629.4941.dds): then the old map must be disabled, two names = last enumerated wins.
- 26,084 refs used: mountains 7,820, rocks 10,339 (25,647 smaller than 512 skipped), cliffs 5,121, dirtcliffs 1,410, ice 746, landforms 648.
  144 skipped as disabled. 8.47 M object-texel intervals, 60,125 rejected as unsupported (air gap > 256 below).
- Final vs landscape: 27.4% of texels raised (20.1% by >128, 11.2% by >512, 1.9% by >2000, 765 texels by >8000), mean +663, median +368,
  p99 +3840, max +10080 at (230528,-74240) (eastern border mountains). Never lowered. Single-texel spikes (> all 8 neighbours + 256): 1 (land has 8).
- Why open and not erode: validate_filter_choice.py (truth = objects re-rasterised at 32 units, map shadow sampled bilinearly with the 256 bias).
  False darkening of truly lit samples is ~0 for every variant (no filter 0.02-0.04%, open <=0.01%, erode 0.00%): the 256 bias already covers
  the bilinear cliff-edge problem I feared. Recall of true shadow, west sun, Ilinalta crop:
     el 12: land 37% | no filter 69% | open 63% | erode1 57% | erode2 47%
     el 15: land 16% | no filter 51% | open 41% | erode1 33%
     el 20: land 11% | no filter 43% | open 34% | erode1 25%
  The remaining misses are mostly the shader's 256 self-shadow bias + 128-unit resolution (not fixable in the map).
- 128-grid simulation (validate_objects.py, validation\validation.txt), receiver = visible top-down surface, Ilinalta crop:
     el 8: shadowed 74.7% -> 85.2% (ideal 86.9%), recall 86% -> 98%; rock-object texels shadowed 57% -> 71% (ideal 75%)
     el 12: 19.4% -> 32.5% (ideal 35.8%), recall 54% -> 91% ; el 15: 5.6% -> 13.9% (ideal 17.0%), recall 33% -> 82%
     whole map el 8: object texels shadowed 56.7% -> 67.4% (ideal 69.3%).
- Placement sanity: per class the median object straddles the land (median top-land within +-30 units for mountains/rocks/cliffs/dirtcliffs,
  p5 below ground, max above). "Floating" objects (p5 > +256): mountains 0.3%, rocks 1.8%, cliffs 0.6%, ice 24% (icebergs over the sea floor: fine).
- Variants (own folders so they never collide): variants\nofilter, variants\erode1, variants\mountains-cliffs-ice-only.
- Intermediates (regenerable, ~200 MB): refs.pkl, meshidx.pkl, meshcache.pkl, objects_layers.npz, objects_intervals.npz, objects_sel.pkl.

## Known weaknesses
- Height field only: the area under any accepted overhang (< 256 air gap) or beside a near-vertical face is treated as solid/ shadowed.
- Open-bottomed shells are assumed solid to the ground (correct for mountains; a shell edge poking over a drop becomes a wall).
- Enable state = plugin data only (initially disabled + enable parent); quest-toggled rocks, Base Object Swapper swaps and runtime moves unknown.
- Only refs in Tamriel itself; child worldspaces that use Tamriel land (city worldspaces) contribute nothing.
- Solitude arch excluded (class 'arches'): its span would be solid if included; without it the arch casts no terrain shadow.
- Trees, buildings, walls, bridges, glacier-free ice floes, small rocks (< 512) not included.
- Receiver side unchanged: shader bias 256 still leaves shallow lee faces lit; LOD/landscape seen far away now sits BELOW the map where rocks
  cover it, which is the intent, but terrain LOD poking out near rock edges can get darker than before.

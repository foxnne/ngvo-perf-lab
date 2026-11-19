# Scene content audit: what makes the Whiterun exterior heavy

Instance `C:\Modlists\NGVO 8.0 Beta`, profile `foxnne-nsfw`, 2,003 enabled mods, 856 active plugins.
Read-only, 2026-11-17, done while a benchmark was running (header/table reads only, no archive bulk extraction).

Method notes
- Grass cache: `.cgid` files are uncompressed; each instance is a 30-byte record after a mesh-path header.
  Instances = bytes between mesh names / 30 (approximate, sub-block headers ignored). Script: `cgid_sample.py`, `cgid_tris.py`.
- NIF triangle/vertex/shape counts read from BSTriShape / NiTriShapeData block headers. Script: `nif_tris.py`.
- Reference census: GRUP-header walk of the Tamriel worldspace of all 856 active plugins (177 touch Tamriel),
  counting NEW placed references per plugin by base record type in cells x -2..12, y -9..4. Script: `refscan.py` -> `refscan.json`.
- Model weights: base record -> winning MODL (load order) -> first enabled mod with that loose mesh (modlist priority),
  else 4 BSAs (NotWL, Lux Via, Lux Resources, JK's) read in memory. Script: `basescan.py`, `baseagg.py` -> `baseagg.txt`.
- Limits: vanilla-BSA meshes and models used fewer than 2-3 times are not measured; Base Object Swapper swaps, SPID,
  Light Placer lights and season swaps are not modelled; counts are before frustum/occlusion culling; shadow passes
  redraw casters once per cascade. "Shape" = one draw per pass.
- Cell centres used: (3,-3) = tundra just west/south-west of Whiterun, (5,-2) = Whiterun itself. 5x5 = uGridsToLoad 5.

## 1. Grass

### Winning setup (verified)
| Item | Value |
|---|---|
| Grass plugins enabled | Freak's Floral Fields (+ Patch "Grass Bounds"), Freak's Floral Veil, Freak's Floral Solstheim, Spiky grass by Mari (49-byte dummy esp + textures), Complementary Grass Fixes, Landscape Fixes For Grass Mods (incl. `Generic Grass Limiter.esp`), Cathedral 3D plants set |
| Mesh library | `Cathedral - 3D Landscapes and Grass Library` (579 grass nifs); 98 grass nifs in `NGVO - DynDOLOD Output\Meshes\landscape\grass` win over it (top priority), same polycounts |
| skyrim.ini [Grass] | iMinGrassSize=60, iMaxGrassTypesPerTexure=15, iGrassCellRadius=2, fGrassFadeRange=7000, bEnableGrassFade=0 (Floral Fields/Veil ini ask for the same 60/15) |
| skyrimprefs.ini [Grass] | fGrassStartFadeDistance=999999, fGrassMaxStartFadeDistance=7000 |
| GrassControl.ini | Use-grass-cache=true, Only-load-from-cache=true, Extend-grass-distance=true, Extend-grass-count=true, Overwrite-grass-distance=-10000 (negative = no override), Overwrite-grass-fade-range=-0, Overwrite-min-grass-size=-1, Global-grass-scale=1.0, DynDOLOD-Grass-Mode=0, Super-dense-grass=false |
| GrassCacheHelperNG.ini | UseCGID=1, UsingGrassLOD=1, AutoGrassDistanceSettings=0, ForceGrassWorlds=WhiterunWorld |
| NGIO-NG log | v2.0.2, "Indexed 7282 grass cache files for 30 worldspaces", no `_NGIO` override inis |

### Grass cache (verified)
| Worldspace | Files | Size | Avg per cell |
|---|---|---|---|
| Tamriel | 5,570 | 674.3 MB | 124.0 KB (about 3,600-4,100 instances) |
| DLC01SoulCairn | 303 | 57.3 MB | 193.5 KB |
| DLC2SolstheimWorld | 800 | 37.2 MB | 47.6 KB |
| MarkarthWorld | 124 | 15.8 MB | 130.4 KB |
| All 30 worldspaces | 7,282 | 809.6 MB | 113.9 KB |

Random 200 Tamriel cells: avg 3,584 instances and 15.5 mesh batches per cell.

### Grass around Whiterun (cache instances x mesh triangles, before culling)
| Centre | Cells | Instances | Batches (cell x mesh) | Triangles | Vertices |
|---|---|---|---|---|---|
| (5,-2) | 3x3 | 20k | 146 | 3.1 M | 4.9 M |
| (5,-2) | 5x5 | 129k | 497 | 19.8 M | 31.3 M |
| (5,-2) | 7x7 | 359k | 1,101 | 55.3 M | 87.2 M |
| (5,-2) | 9x9 | 672k | 1,949 | 102.4 M | 161.3 M |
| (5,-2) | 13x13 | 1,343k | 3,815 | 201.9 M | 317.8 M |
| (3,-3) | 3x3 | 69k | 203 | 10.7 M | 16.8 M |
| (3,-3) | 5x5 | 223k | 576 | 34.5 M | 54.4 M |
| (3,-3) | 7x7 | 451k | 1,172 | 68.7 M | 108.1 M |
| (3,-3) | 9x9 | 740k | 1,984 | 111.3 M | 175.1 M |
| (8,-4) | 5x5 | 108k | 559 | 15.9 M | 25.0 M |
| (8,-4) | 9x9 | 362k | 1,691 | 50.4 M | 78.9 M |

Share by mesh, 11x11 around (5,-2), 993k instances: ComplexGrassDrJ11 colour variants (_yg, _og, _sg, _r, _d, _y, _d_tall)
= about 874k instances (88%). Then alpinebluegrassdrj_y 36k, deadpinedrj03 16k, dandelion03puffdrj 16k, linumlewisiidrj 10k.

### Grass mesh weight (winning files)
| Mesh | Triangles | Vertices |
|---|---|---|
| ComplexGrassDrJ11 and all colour/tall variants | 162 | 256 |
| ComplexGrassSnDrJ10 / DrJ10 | 137 | 197 |
| ComplexGrassDrJ16 | 65 | 92 |
| ComplexGrassDrJ15 | 21 | 30 |
| alpinebluegrassdrj(_y) | 25 | 55 |
| deadpinedrj03 | 59 | 118 |
| dandelion03puffdrj | 180 | 228 |
| tundragrassobj04 | 62 | 80 |
| tundragrassobj03 | 257 | 282 |
| clovers3d_* | 80 | 134 |
| nettledrj | 404 | 622 |
| greentreedrj21 | 612 | 882 |
| sorbusshrubdrj | 864 | 936 |
| fieldgrass01 / ferngrass01 (vanilla-scale) | 12 / 9 | 18 / 15 |
Full list: `grass_nif_tris.txt`.

### Open question (not verifiable from files)
Effective grass radius. Overwrite-grass-distance is negative, so NGIO derives the radius from the INI:
(fGrassStartFadeDistance + fGrassFadeRange) / 4096, clamped 2..32. With the prefs value 999999 that is the 32-cell clamp;
if the engine clamps to fGrassMaxStartFadeDistance (7000) it is ceil(14000/4096) = 4 cells (9x9). The measured 6,137 draws
per frame rule out 32 cells in practice, so the 9x9 row (about 100 M grass triangles, about 1,950 batches before culling)
is the most likely live state. Confirm in game (CS/NGIO debug or by flying the camera) before acting.
Also inconsistent: GrassCacheHelper `UsingGrassLOD=1` while NGIO `DynDOLOD-Grass-Mode=0`.

## 2. Trees and flora

Winning tree set: Nature of the Wild Lands (BSA, 821 tree nifs, avg 238 KB compressed), plus Ulvenwald (849 loose nifs)
via Shadow's NotWL - Ulvenwald Patch. New TREE refs in 9x9 around Whiterun: Skyrim.esm 1,742 (re-meshed by NotWL),
Update.esm 233, NotWL 141, Ulvenwald 44, Lux Via 39.

| NotWL mesh (sampled from BSA) | Triangles | Shapes |
|---|---|---|
| pine_common_big01_summer | 9,171 | 2 |
| pine_common_big02_summer | 8,254 | 2 |
| pine_common_big03_summer | 9,796 | 2 |
| pine_common_medium01_summer | 6,025 | 2 |
| pine_field_big01_summer | 9,034 | 2 |
| spruce_common_big01_summer | 10,552 | 2 |
| scots_pine_cluster_big01_summer | 24,549 | 2 |
| alder_cluster_big01_summer | 25,023 | 2 |
| oak_big_wide01_summer | 17,314 | 3 |
| conifer_split01_summer | 12,718 | 3 |
| reach_tree_rock01 | 13,231 | 4 |
| birch_slim_big01sum | 6,274 | 2 |
| elm_forest_big01_summer | 6,712 | 2 |
| whiterun_temple_tree01_spring | 55,130 | 3 |
| yellow_shrub02_summer / yellow_shrub01 | 3,245 / 5,169 | 1 |
| nettle01_summer | 2,052 | 1 |
| tundra_shrub02/03/05/07/08 | 1,236 / 1,728 / 1,452 / 462 / 696 | 1 |
| 3D LOD: pine_common_big01/02/03 passthru_lod | 1,609 / 1,459 / 4,698 | 5 |
| 3D LOD: pine_field_big01 passthru_lod | 1,723 | 5 |

Ulvenwald (752 tree/plant nifs parsed): mean 10,468 tris; 63 files over 20k, 10 over 50k (MotherOakClump01 73,995 tris,
12 shapes, 8 MB); `trees\Whiterun` folder mean 4,920 tris but 4-16 shapes per tree. Full list: `ulvenwald_nif_tris.txt`.

Comparison: a vanilla pine is roughly 2-4k triangles in 2 shapes. NotWL pines are about 2.5-4x that with the same
2 shapes; clusters and oaks are 6-10x. Ulvenwald trees are similar in triangles but cost 2-8x the draws.

## 3. Placed objects and draw-call drivers near Whiterun

### New references per plugin (5x5 cells)
| Plugin | (3,-3) | (5,-2) | Main types |
|---|---|---|---|
| Skyrim.esm | 1,769 | 1,552 | STAT 977/911, TREE 506/291 |
| Update.esm | 187 | 157 | TREE |
| JKs Skyrim.esp | 356 | 356 | STAT 282, ACTI 24, TREE 19, FLOR 17 |
| DynDOLOD.esm + .esp | 209 | 380 | STAT/TREE LOD stand-ins, about half initially disabled |
| Lux Via.esp | 109 | 77 | STAT 71/46, LIGH 17/13, TREE 12 |
| Northern Roads.esp | 74 | 84 | STAT 49/56 |
| Nature of the Wild Lands.esp | 28 | 15 | TREE |
| Lux Orbis.esp | 20 | 21 | LIGH 15/16 |
| All plugins | 2,782 | 2,678 | vanilla share 1,956 / 1,710 |

9x9 around (5,-2): 7,685 new refs, 5,025 vanilla; next: Riverside Treehouse 460, Lux Via 420, JK's 356, Northern Roads 248,
Natural Waterfalls 221, Lux Via - Whiterun Repaired Bridge 151, NotWL 142.
So mods add only about 40-55% more references than vanilla here. The draw count comes from shapes per mesh,
shadow-cascade redraws and grass batches, not from reference count.

### Measured mesh weight of placed objects (winning loose/BSA meshes, before culling)
| Area | Refs measured | Triangles | Shape-draws per pass |
|---|---|---|---|
| (3,-3) 5x5 | 1,880 | 7.50 M | 3,937 |
| (5,-2) 5x5 | 1,714 | 6.58 M | 3,753 |
| (5,-2) 9x9 | 5,644 | 20.93 M | 11,937 |
(About 700 refs per 5x5 on unmodified vanilla-BSA meshes are not included; they are low-poly.)

By winning mod, triangles (M): (3,-3) 5x5 / (5,-2) 5x5 / (5,-2) 9x9
| Mod | 5x5 W | 5x5 city | 9x9 |
|---|---|---|---|
| Nordic Farmfield Stonewalls | 2.20 | 1.70 | 3.66 |
| Nature of the Wild Lands | 1.93 | 1.55 | 6.12 |
| Enhanced Rocks and Mountains - Addon | 0.59 | 0.70 | 2.83 |
| TomatoRim PBR - Landscapes 2K (road meshes) | 0.41 | 0.26 | 1.12 |
| FYX - 3D Whiterun Guard Towers | 0.31 | 0.32 | 0.33 |
| Embers XD | 0.20 | 0.18 | 0.44 |
| ERM - Complex Parallax Materials | 0.15 | - | 0.56 |
| SD's Farmhouse Fences SE - Version 2 | 0.14 | 0.14 | - |
| ElSopa - Barrels Redone | 0.13 | 0.15 | - |
| Riverside Treehouse | - | - | 0.60 |
| Lux Via (BSA) | - | 0.11 | 0.51 |

By winning mod, shape-draws per pass, 9x9: NotWL 2,273; ERM Addon 1,532; Mesh Improvement Compilation 664; Lux 619;
TMD Epic Waterfalls 559; ERM Complex Parallax 520; TomatoRim Landscapes 480; Riverside Treehouse 348;
Whiterun City Walls - Collision Redone 318; Nordic Farmfield Stonewalls 308; Reimagined Mountain Flowers 308; Lux Via 279.

Heaviest individual meshes (count in 9x9 x triangles)
| Mesh | Count | Tris each | Shapes | Winner |
|---|---|---|---|---|
| architecture/whiterun/wrfarmfence/wrfencebase64ramp01 | 73 | 12,940 | 1 | Nordic Farmfield Stonewalls |
| .../wrfencebasestr01 | 65 | 10,454 | 1 | Nordic Farmfield Stonewalls |
| .../wrfencebaseend01 | 60 | 8,887 | 1 | Nordic Farmfield Stonewalls |
| .../wrfencebase64shiftl01 | 26 | 16,199 | 1 | Nordic Farmfield Stonewalls |
| .../wrfencebasesupport01 | 27 | 10,298 | 1 | Nordic Farmfield Stonewalls |
| .../wrfencebase4way01 (5x5: 9) | - | 17,961 | 1 | Nordic Farmfield Stonewalls |
| landscape/trees/nettle01_summer | 426 | 2,052 | 1 | NotWL |
| landscape/trees/pine_common_big03_summer | 72 | 9,796 | 2 | NotWL |
| landscape/trees/yellow_shrub02_summer | 202 | 3,245 | 1 | NotWL |
| landscape/trees/reach_tree_rock01 | 49 | 13,231 | 4 | NotWL |
| landscape/tundra/rocktundraland02 | 24 | 13,983 | 8 | ERM Addon |
| landscape/tundra/rocktundraland01 | 30 | 10,124 | 2 | ERM Addon |
| landscape/roads/roadstraight02 | 14 | 19,936 | 2 | TomatoRim PBR - Landscapes 2K |
| clutter/barrel01 | 73 | 3,096 | 2 | ElSopa - Barrels Redone |
| effects/fxfirewithembers01 (5x5: 13) | - | 12,164 | 5 | Embers XD |
| architecture/whiterun/wrscaffold/wrscafguardtower01 (5x5: 16) | - | 10,152 | 6 | FYX - 3D Whiterun Guard Towers |
| wrscafguardtower02 (5x5: 3) | - | 37,562 | 6 | FYX - 3D Whiterun Guard Towers |
| architecture/farmhouse/fencewoven01 (5x5: 14) | - | 9,866 | 3 | SD's Farmhouse Fences SE - Version 2 |
| plants/floracabbage01 (5x5: 55) | - | 1,090 | 4 | Cabbage - A Cabbage Mod |

Related, not placed near Whiterun in this census but same family: `Nordic Stonewalls` farmhouse stonewall meshes are
58,509 tris (stonewall01), 93,182 tris (stonewalllong01); 25 nifs, mean 22,385 tris.

## 4. Shadows and lights (content only)

| Item | Finding |
|---|---|
| New LIGH refs, 5x5 (3,-3) | 43 total vs 9 vanilla: Lux Via 17, Lux Orbis 15 |
| New LIGH refs, 9x9 (5,-2) | 124: Lux Via 57, Lux Orbis 28, Riverside Treehouse 16, Lux Via Whiterun bridge 4 |
| Shadow-casting LIGH refs in the whole 15x14-cell box | 0 new refs whose defining record has a shadow flag (overrides that add the flag in a later plugin are not detected) |
| Window Shadows Ultimate (+ Patch Hub) | 1.0 MB plugin, 242 nifs, interiors; not an exterior cost |
| Shadows Of Sunlight - In Small Exterior World Spaces | 7 KB plugin, small worldspaces only |
| Light Placer configs | CS Lights 42 json, Tiny Light Placer Hub 21, Lux CS Patch 9 (mesh-attached, non-shadow point lights) |
| Lux Via brazier LOD statics | lux_qwafeewrbrazier01_lod 3,336 tris x 23 in 5x5 at Whiterun |

Exterior shadow cost is therefore the sun cascades redrawing the geometry above, not added shadow lights (inference).

## 5. Heavy additions with a lighter route
| Mod folder | Why heavy | Lighter route |
|---|---|---|
| `Cathedral - 3D Landscapes and Grass Library` + `Freak's Floral Fields` (+ Veil) | 162-tri clump is 88% of tundra grass; 20-35 M tris per 5x5 | mesh-only swap of ComplexGrassDrJ11* to the library's 65-tri DrJ16-class clump (no cache rebuild), or rebuild cache at iMinGrassSize 80-90 (about 0.56x / 0.44x instances), and pin Overwrite-grass-distance |
| `Nordic Farmfield Stonewalls` | 9-18k tris per fence-base piece, 1.7-2.2 M per 5x5 | disable (falls back to Mesh Improvement Compilation wrfence meshes, about 1.5k tris) or decimate |
| `Nordic Stonewalls` (+ `Nordic Stonewalls PBR`) | 58-93k tris per wall segment | disable or decimate |
| `Enhanced Rocks and Mountains - Addon` / `ERM - Enhanced Rocks and Mountains` | 10-14k tris and up to 8 shapes per tundra rock | none known as an installer option; candidates for shape merging |
| `FYX - 3D Whiterun Guard Towers` | 10-37k tris, 6 shapes | disable |
| `Embers XD` | 12k tris, 5 shapes per fire | installer has lower-detail flame options (not verified from the archive) |
| `Ulvenwald` | 4-16 shapes per tree | only 44 refs in 9x9 here; low priority |
| `SD's Farmhouse Fences SE - Version 2` | 9.9k tris per woven fence | disable |

Files in this folder: `grass_nif_tris.txt`, `ulvenwald_nif_tris.txt`, `notwl_nif_tris.txt`, `notwl_bsa.txt`, `refscan.json`,
`basescan.json`, `baseagg.txt` and the scripts named above.

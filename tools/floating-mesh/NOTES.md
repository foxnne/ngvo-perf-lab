# Floating object in sky - investigation notes (offline, read-only on modlist)

## Files here
- scan.py: plugin parser -> refs.pkl (all Tamriel REFR overrides + base EDID/MODL), 923 plugins (848 active + CC from Skyrim.ccc)
- common.py / cam.py: heightmap sampling, camera model
- overlay2.png: validation overlay (red = terrain horizon computed from heightmap, yellow = Western Watchtower base/top, green = object)

## Camera model (VALIDATED against screenshot)
- pos (19157,-7419,-2970 assumed z: ground -3669 + 700), yaw 270 = looking -X (west), screen right = +Y (north).
- Pitch: camera looks UP 3 deg (Skyrim negative X-angle = up), NOT down. With "down" the horizon/tower are ~210 px off.
- FOV 65 is the 16:9-referenced horizontal FOV (Hor+ on 21.5:9): focal = 2009 px. (65 as true horizontal -> 2700 px and 4:3 ref -> 1507 px both fail the tower test.)
- Validation: heightmap horizon silhouette overlays the mountain skyline to within a few px across the full frame; Western Watchtower (388,-14841) projects on the tower.
- Ray through pixel (2755,468): dir = (-0.8765, 0.4551, 0.1569) -> 27.4 deg north of west, 9.0 deg above horizontal.
  (The brief's 15.6/7.5 deg figures were based on wrong focal/pitch.)
- Scale: 45 px = 1.28 deg; object N units wide sits at ~ N*44.6 units.
- Object looks like a bird-shaped / two-wing sliver (see crop_a.png, crop_b.png).

## Results so far
- Cone scan (cone.py, last override wins, 331k Tamriel REFRs from 923 plugins): NO placed reference origin within 4.5 deg of the ray
  at any distance; nearest are an XMarker and DynDOLOD cell markers (invisible). Ray climbs fast: 1700 units above ground at 10k, 6000+ at 20k.
- Bounding-sphere test (sphere.py, OBND*scale): only large thing the ray passes through is Tree of Life.esp:000003 (the huge tree at frame right).
  Projected its NIF (nif.py) onto the frame: wireframe matches the tree/vines exactly (overlay_tree.png) -> validates camera + NIF reader,
  and shows NO tree geometry at the object pixel. Not the tree.
- No hawk activators (FXbirdOPrey*) within 26k units. NAT-ENB cloud refs all DIS in winning override.
- Next: object LOD .bto projection, DynDOLOD dynamic refs.
- Object LOD: parsed all 692 Tamriel object .bto (bto.py) and projected every vertex: nothing within 400x150 px of the object
  (nearest LOD geometry is on the ground band y>=590). Trees folder only has Tamriel.lst (no .btt). NOT object LOD.
- sessions_sheet.png: object identical in shape/position in ~22 frames from 8 sessions -> static mesh; drawn in front of volumetric clouds, fogged.
  Shape = thin ellipse + hook (two discs/rings edge-on).
- Zero-OBND bases near ray: only markers. BOS _SWAP.ini transforms: none in Whiterun area.
- ini: uGridsToLoad=5 (loaded cells x2..6,y-4..0), uLargeRefLODGridSize=9.
- Next: brute-force projection of actual meshes of all enabled refs around (stray geometry far from origin).
- brute_all.py: projected the REAL meshes (loose + BSA via bsa.py, pure-python LZ4) of every Tamriel REFR (enabled or not; quick reject
  by mesh radius) with a point-in-triangle test at 5 pixels across the object: the only triangles covering it belong to NAT-ENB cloud/mist
  planes (all Initially Disabled in the winning override; huge planes, not a 45 px object) -> no placed static/tree/activator mesh is there.
- bto_tri.py: same triangle test on all 692 object LOD .bto: nothing.
- ACHR/PHZD/PGRE in Tamriel: none within 8 deg of ray.
- Grass cache (NGVO - Grass Cache, 2026-11-02, cgid parser in cgid.py; positions are half-floats wrapped mod 49152): no instance near the pixel.
  Side finding: stale cache, e.g. cell (-9,-18) grass 250..740 units off current terrain; (3,-12),(6,-8..-11),(-3,-17) ~250-400.
- Object shape on 10x zoom (zoom.png): two pointed-oval "leaves" with a stem blob = looks like a horizontal leaf card seen from ~9 deg below.

## BREAKTHROUGH (save file)
- Harness loads the LAST SAVE each session (profiles\foxnne-nsfw\saves\preRestart_auri.ess, 2026-11-15) then coc's. ess.py/ess_scan.py parse
  change forms. A MOVED reference sits 0.22 deg from the object ray at 19,500 units:
  DynDOLOD.esp:057209 (runtime 6E057209 in the save), base DynDOLOD.esm 'mineralpoolsmwater01_water_shadow_DynDOLOD_BASERECORD'
  (water\mineralpoolsmwater01_water_shadow.nif), save position (2022,1409,-11), ~5900 above ground, change flags 0x3 (moved).
  Expected apparent width 45 px -> ~440 units = a small mineral-pool water mesh. TO VERIFY: plugin position, mesh projection.
- CONFIRMED by projection (match.py -> match_a.png / match_b.png): mesh water\mineralpoolsmwater01_water_shadow.nif
  (loose file from mod "Real Water for Volcanic Mineral Pools - Base Object Swapper", LE-format NiTriShape) placed at the SAVE position
  (2022.48, 1409.21, -11.40), rot Z 194.8 deg projects to x 2725..2771, y 469..477 = exactly the object, and the outline (pool ellipse + hook,
  plus the small 'L2_Skeleton' blob) reproduces the shape. Depth ~17.3k, 19.5k from camera, ~5,900 units above the tundra.
- Plugin position of DynDOLOD.esp:057209 is the Shadowrend pool in Eastmarch (133200,-25569,-11623), cell (32,-7); it is a DynDOLOD dynamic LOD
  copy (EDID ccbgssse018shadowrendesl&00081F_Tamriel_DynDOLOD_REFERENCE) of ccBGSSSE018-Shadowrend.esl:00081F. It is the ONLY DynDOLOD
  dynamic ref in the save whose position differs from the plugin (moved 134,425 units). Change flags 0x3 (MOVE|HAVOK_MOVE).

## ROOT CAUSE (confirmed offline)
- "ECSS - Shadowrend Patch.esp" (in mod "Skyrim Extended Cut - Saints and Seducers", file dated 2026-11-12, active since the 2026-11-12
  plugins.txt backups; runtime FE2F7) overrides ccBGSSSE018-Shadowrend.esl:00081F (MSTT ccBGSSSE018_MineralPoolSmWater01Shadow) and MOVES it
  out of Tamriel cell (32,-7) into interior ECSSGroveOfReflection01 (ECSS.esp:038CD9) at (2022.5, 1409.2, -11.4), rot 195 = the save coords.
- DynDOLOD output (generated 2026-11-08, before the patch was active; DynDOLOD.esp has no ECSS master) still holds dynamic LOD ref
  DynDOLOD.esp:057209 for the Tamriel placement, tied to the source by DynDOLOD_NG_Tamriel.txt line 3498
  "356873,DynDOLOD.esp,0,1,1,1,,2079,ccbgssse018-shadowrend.esl,...". DynDOLOD NG copies the source's coordinates at runtime, so the LOD
  copy is drawn in Tamriel at the interior coordinates -> pool water + skeleton floating ~5,900 units over the tundra west of Whiterun.
- Base DynDOLOD.esm:0607DD (mineralpoolsmwater01_water_shadow_DynDOLOD_BASERECORD) is used by this one ref only.
- Runtime ids in CURRENT load order (computed, 923 plugins): DynDOLOD.esp = 6D -> ref 6D057209 (it was 6E057209 in the save), DynDOLOD.esm = 1A.
- Limitation found: scan.py only tracks overrides inside Tamriel groups, so a later plugin moving a ref into an interior is not seen as "moved".

## Fix options (not applied)
A. BOS one-liner (new empty mod, file e.g. foxnne_DynDOLOD_ShadowrendLOD_SWAP.ini):  [References]  0x57209~DynDOLOD.esp|0x3B~Skyrim.esm
B. Regenerate DynDOLOD (at least dynamic LOD) for the current load order (proper fix; also refreshes other stale LOD).
C. Remove line 3498 from DynDOLOD_NG_Tamriel.txt (untested whether NG validates the file).

## Housekeeping
- refs.pkl / meshidx.pkl / *.pkl are regenerable (scan.py ~3 s, meshidx.py ~1 min) and were deleted at the end.

# Tamriel 16-bit terrain height map - working notes

## Loader facts (TerrainShadows.cpp / ShadowUpdate.cs.hlsl)
- xLODGen-style name: `<WS>.Terrain.HeightMap.<minX>.<minY>.<maxX>.<maxY>.<zMin>.<zMax>.dds` (stem must split into exactly 9 '.' fields, fields 1,2 = Terrain, HeightMap), found in any SUBDIRECTORY of `Data\textures\Terrain\`.
- pos0.x = minX*4096, pos1.x = (maxX+1)*4096, pos0.y = (maxY+1)*4096 (NORTH edge), pos1.y = minY*4096; pos0.z/pos1.z fixed at -/+32767*8 = -/+262136; zRange = zMin*8..zMax*8.
- Shader: `terrainHeight = lerp(PosRange.x, PosRange.y, TexHeight[px])` (PosRange = pos0.z..pos1.z), then normalised by zRange into an R16G16_UNORM shadow-height texture.
- UV: Offset adds +0.5/W in u, -0.5/H in v => texel column i centre = world x minX*4096 + i*128; texel row r centre = world y minY*4096 + (H-1-r)*128. Row 0 is north. Each cell contributes its 32x32 south-west vertices.
- File is loaded with DirectXTex LoadFromDDSFile(DDS_FLAGS_NONE) and the SRV uses the texture's own format, so any single-channel UNORM format works.
- `heightmaps[metadata.worldspace] = metadata` : when two files exist for one worldspace the LAST one enumerated wins (only a warning is logged). Enumeration order = directory_iterator order (NTFS: name order; under MO2 usvfs not guaranteed).

## Shipped files
- Tamriel: 3808x3008 FourCC BC4U, 1 mip, 5,727,360 bytes.
- MarkarthWorld / DLC1HunterHQWorld: legacy DDS header, DDPF_LUMINANCE (0x20000), 16 bpp, mask 0xFFFF, no DX10 header -> DirectXTex maps to DXGI_FORMAT_R16_UNORM. All other shipped maps are BC4U.

## Step 1 - shipped BC4 Tamriel precision
- 8-bit endpoint step = 524272/255 = 2056 game units.
- Only 38 distinct endpoint values (109..146), 69 distinct decoded values incl. BC4 interpolants; 85% of 4x4 blocks are completely flat.
- Gaps between distinct heights: min 294 (1/7 interpolant), median 1615, max 2056. Where adjacent texels differ, the median jump is 2056 units.
- Hypothesis CONFIRMED: the caster is terraced in ~2056-unit steps (half a cell of height per step).

## Step 2 - LAND from the active load order (profile foxnne-nsfw)
- `build_land.py` (reuses tes5.py record header/subrecord iterator and build_catalogue.read_profile; own slim plugin index and WRLD group walker because tes5.Plugin skips nested groups). 856 active plugins parsed in load order, 224 have a WRLD group, 0 missing files, run time ~6 s.
- Tamriel: 11,186 cells with LAND = every cell of -57..61 x -43..50 (119 x 94), so no fill value was needed (WRLD DNAM default land height is -27000, water -14000).
- Winning LAND: Skyrim.esm 8265, Update.esm 728, Northern Roads.esp 528, LFFGM 334, NR-LFFGM patch 333, Complementary Grass Fixes 243, Dawnguard 164, ... (full table in build_land.log). 2,919 LAND forms are overridden by at least one later plugin.
- Two cells, (-44,37) and (-43,36) (Castle Volkihar island), contain TWO different LAND forms: Skyrim.esm's and one added by Dawnguard.esm under another form ID. The later plugin (Dawnguard) is used; it matches all four neighbours exactly (seam 0) whereas the Skyrim.esm one would leave 1300-4300 unit seams. The shipped map used the Skyrim.esm one there.
- Edge agreement: 22,159 adjacent cell pairs checked, 81 pairs / 507 vertices disagree. Four pairs are large (2280-5240 units) and all are sea floor west of Volkihar (cells -48..-47, 37..39, z -17000..-23000, far under water at -14000; Dawnguard.esm vs Skyrim.esm data). All other mismatches are <= 96 units (43 pairs touch land above water; mostly 8-24 units, vanilla and landscape-mod seams).
- Heights: min -37032 (cell 58,40), max 39392 at cell (13,-13), world (54528,-52352) = Throat of the World; the eight highest cells are all (12..14,-12..-14). 27% of vertices lie below -14000 (sea), 6% within 400 units of it.

## Step 3 - grid and orientation
- 3808x3008, texel (col i, row r) = vertex at world x -57*4096+i*128, y -43*4096+(3007-r)*128.
- Correlation with the decoded shipped BC4 map: identity 0.99909; flipH 0.734; flipV -0.675; rot180 -0.692; the four transposed variants (central 3008x3008 crop) |r| < 0.02. Shifts of +-1/+-2 texels and +-31..33 texels all correlate lower than (0,0).
- Shipped vs ours: mean |diff| 1052, median 1076, p99 2036, max 5612 units. The difference is one-sided: shipped - ours has mean -1052 (p1 -2036, p99 -28). The shipped map equals floor((h/8+32767)/257) of our grid (truncation to 8 bits) in 99.80% of texels (mean residual 4 units). The other 0.2% are almost all exactly one 8-bit step off (BC4 block error). Only 215 texels in 4 cells differ by more: (-44,37) (Volkihar duplicate LAND), (12,48), (14,-14), (18,5).
- So the shipped map was generated from essentially this same terrain, but truncated to 8 bits: on average 1052 units too LOW, terraced in 2056-unit steps.

## Step 4 - output
- MarkarthWorld shipped 16-bit map compared with MarkarthWorld LAND: raw == height/8 + 32767 for 100.00% of 142,336 covered texels (cells without LAND are 0). Same convention used here. Through the loader's lerp this decodes to height - 4 (range -3.4..-4.6), i.e. within 16-bit quantisation.
- Output: `mod\textures\terrain\HeightMaps\Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds`, 22,909,056 bytes, legacy DDS header copied from the Markarth file (DDPF_LUMINANCE 16 bpp mask 0xFFFF -> DXGI_FORMAT_R16_UNORM), 3808x3008, no mips.
- zMin/zMax computed from the data are -4629/4924, identical to the shipped name, so the file name is IDENTICAL to the shipped one. No second-name problem; it simply has to win the file conflict.
- No other Tamriel height map exists in any mod/overwrite/Stock Game (only the disabled "pre-merge" copies of Bottled Shaders); `textures\heightmaps\` only holds a readme.

## Step 5 - verification
- Own reader, 1000 random LAND vertices located through the loader's Scale/Offset maths: error -4.48..-3.48, max |err| 4.48 (limit 8). Whole grid max |err| 4.60.
- 10 texels fall 3.4 units below zRange.x after decoding (clamped in the UNORM shadow texture; deepest sea floor, irrelevant).
- Profile west-east through the Throat summit (41,088 units): shipped 14 levels / 26 steps of 2056, longest flat 4352 units; new 301 levels. Files: profile_throat_before_after.png / .txt.

## Housekeeping
- Deleted regenerable intermediates (two 46 MB .npy grids, probe scripts). To rebuild: step1_bc4.py, build_land.py, step3_assemble.py, step4_write_verify.py in that order.

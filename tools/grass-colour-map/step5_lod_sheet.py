"""Before/after sheets for a few terrain LOD tiles (Whiterun tundra west of the city), from two sources:
  vanilla = the terrain LOD textures the game shows today (Cleaned Skyrim SE Textures, Skyrim - Textures7.bsa)
  xlodgen = the old, disabled 'NGVO - xLodGen Output' (what regenerated terrain LOD roughly looks like)
Runs tint_terrain_lod.py straight on the BSAs (strength 0 = untouched 'before'), writes out/mockup_lod_tiles_<set>.png and
removes its temporary tiles again."""
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
ROOT = r'C:\Modlists\NGVO 8.0 Beta\mods'
SETS = {'vanilla': os.path.join(ROOT, 'Cleaned Skyrim SE Textures', 'Skyrim - Textures7.bsa'),
        'xlodgen': os.path.join(ROOT, 'NGVO - xLodGen Output', 'NGVO - xLodGen Output1 - Textures.bsa')}
TILES = ['4.-4.-4', '8.-8.-8', '32.-32.-32']
SZ = 512
tmp = os.path.join(OUT, 'work', 'lod_sheet')
for label, bsa in SETS.items():
    for st in ('0.0', '0.5', '1.0'):
        d = os.path.join(tmp, '%s_s%s' % (label, st))
        subprocess.run([sys.executable, os.path.join(HERE, 'tint_terrain_lod.py'), '--bsa', bsa, '--out', d, '--cells', '-4', '-4', '-1', '-1',
                        '--strength', st, '--png', '--format', 'BC1_UNORM'], check=True, stdout=subprocess.DEVNULL)
    sheet = Image.new('RGB', (SZ * 3 + 16, (SZ + 22) * len(TILES)), (20, 20, 20))
    dr = ImageDraw.Draw(sheet)
    for r, t in enumerate(TILES):
        for c, (st, lab) in enumerate((('0.0', 'before'), ('0.5', 'strength 0.5'), ('1.0', 'strength 1.0'))):
            p = os.path.join(tmp, '%s_s%s' % (label, st), 'Tamriel.%s.png' % t)
            if not os.path.exists(p):
                continue
            sheet.paste(Image.open(p).convert('RGB').resize((SZ, SZ), Image.LANCZOS), (c * (SZ + 8), r * (SZ + 22) + 20))
            dr.text((c * (SZ + 8) + 4, r * (SZ + 22) + 4), '%s  Tamriel.%s  %s' % (label, t, lab), fill=(255, 255, 0))
    sheet.save(os.path.join(OUT, 'mockup_lod_tiles_%s.png' % label))
    print('wrote mockup_lod_tiles_%s.png' % label)
shutil.rmtree(tmp, ignore_errors=True)

"""Mean colour of opaque texels (alpha > 0.5) of PNGs decoded by texconv, plus the DXGI format of the source DDS.
Values reported as stored (sRGB-encoded 0..255) and as display-linear Rec.709 luminance.
"""
import struct, sys, os, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
S = r'C:\Users\foxnn\AppData\Local\Temp\claude\3faf89cbf3e7ed47\f00ecae3-865a-43f6-bdb9-8828c99c0a95\scratchpad\treelod'

def dds_format(path):
    d = open(path, 'rb').read(148)
    fourcc = d[84:88]
    if fourcc == b'DX10':
        return 'DXGI %d' % struct.unpack_from('<I', d, 128)[0], struct.unpack_from('<II', d, 12)
    return fourcc.decode('latin1') or 'uncompressed', struct.unpack_from('<II', d, 12)

def lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def stats(label, arr):
    a = arr[..., 3] / 255.0 if arr.shape[-1] == 4 else np.ones(arr.shape[:2])
    m = a > 0.5
    if m.sum() == 0: print('  %-58s no opaque texels' % label); return None
    px = arr[..., :3][m].astype(np.float64)
    Y = (lin(px) @ np.array([0.2126, 0.7152, 0.0722]))
    mean = px.mean(0)
    print('  %-58s opaque=%4.1f%%  sRGB mean=(%5.1f %5.1f %5.1f)  linear Y mean=%.4f  median=%.4f' % (label, 100 * m.mean(), mean[0], mean[1], mean[2], Y.mean(), np.median(Y)))
    return Y.mean()

def load(p):
    return np.asarray(Image.open(p).convert('RGBA'))

if __name__ == '__main__':
    M = r'C:\Modlists\NGVO 8.0 Beta\mods'
    for p in [S + r'\notwl\textures\nature_of_the_wild_lands\pine\pine02_summer.dds', S + r'\pbr\textures\pbr\nature_of_the_wild_lands\pine\pine02_summer.dds',
              S + r'\notwl\textures\nature_of_the_wild_lands\pine\bark01.dds', S + r'\pbr\textures\pbr\nature_of_the_wild_lands\pine\bark01.dds',
              S + r'\notwl\textures\nature_of_the_wild_lands\pine\pine02_sk.dds',
              M + r'\NGVO - DynDOLOD Output\textures\DynDOLOD\LOD\DynDOLOD_Tamriel_Alpha.dds',
              M + r'\NGVO - TexGen Output\textures\terrain\lodgen\skyrim.esm\pine_common_big03_summer_00051126_1.dds']:
        print(os.path.basename(os.path.dirname(p)), os.path.basename(p), dds_format(p))
    print('Source textures (full-model tree)')
    a = stats('NotWL vanilla pine02_summer.dds (leaf diffuse)', load(S + r'\png\notwl\pine02_summer.png'))
    b = stats('NotWL PBR pine02_summer.dds (leaf albedo)', load(S + r'\png\pbr\pine02_summer.png'))
    stats('NotWL vanilla pine02_sk.dds (soft-light / subsurface tint)', load(S + r'\png\notwl\pine02_sk.png'))
    stats('NotWL PBR pine02_summer_s.dds (subsurface)', load(S + r'\png\pbr\pine02_summer_s.png'))
    c = stats('NotWL vanilla bark01.dds', load(S + r'\png\notwl\bark01.png'))
    d = stats('NotWL PBR bark01.dds', load(S + r'\png\pbr\bark01.png'))
    atlas = load(S + r'\png\atlas\DynDOLOD_Tamriel_Alpha.png')
    print('Atlas tiles (DynDOLOD_Tamriel_Alpha.dds), rects from LODGen_SSE_ObjectAtlasMap_Tamriel.txt')
    def tile(label, w, h, x, y):
        return stats(label, atlas[y:y + h, x:x + w])
    e = tile('atlas: pine02_summer.dds leaf tile 256x256 (LOD4 crowns)', 256, 256, 3072, 4608)
    f = tile('atlas: pine_common_big03_summer_00051126_1 billboard', 200, 512, 1248, 2560)
    g = tile('atlas: pine_common_big03 trunk_1 (flat trunk)', 140, 512, 7184, 3072)
    print('TexGen billboard files')
    h = stats('TexGen pine_common_big03_summer_00051126_1.dds', load(S + r'\png\bb\pine_common_big03_summer_00051126_1.png'))
    stats('TexGen pine_common_big03_summer_00051126_2.dds', load(S + r'\png\bb\pine_common_big03_summer_00051126_2.png'))
    stats('TexGen pine_common_big03_summer_00051126.dds (standard)', load(S + r'\png\bb\pine_common_big03_summer_00051126.png'))
    print('ratios (linear Y): atlas leaf / vanilla leaf = %.2f ; atlas leaf / PBR leaf = %.2f ; billboard / vanilla leaf = %.2f ; billboard / PBR leaf = %.2f' % (e / a, e / b, f / a, f / b))

"""Second round: settings-only candidates and shader-change prototypes. Builds contact sheets."""
import numpy as np, os
from PIL import Image, ImageDraw
import sim
from sim import bilinear, PAT, render

ZERO = lambda v: {'noise': 4, 'range': [-1, 1, v, v]}
S = {
 'S1_default':            dict(layers=[sim.COV_DEFAULT, sim.TYPE_DEFAULT]),
 'S2_sheetcov_typeB':     dict(layers=[{'noise': 1, 'range': [-0.9, 0.3, 0.25, 0.8]}, ZERO(0.0)], density_scale=0.5),
 'S3_same_uv3':           dict(layers=[{'noise': 1, 'range': [-0.9, 0.3, 0.25, 0.8]}, ZERO(0.0)], density_scale=0.5, uv_size=3.0),
 'S4_sparse_uv3':         dict(layers=[{'noise': 1, 'range': [-0.6, 0.5, 0.0, 0.75]}, ZERO(0.0)], density_scale=0.6, uv_size=3.0),
 'S5_uv3_typeBR_slot0':   dict(layers=[{'noise': 1, 'range': [-0.9, 0.3, 0.25, 0.8]}, {'noise': 0, 'range': [-0.4, 0.4, 0.0, 0.5]}], density_scale=0.5, uv_size=3.0),
 'S6_uv4_alt10k':         dict(layers=[{'noise': 1, 'range': [-0.9, 0.3, 0.25, 0.8]}, ZERO(0.0)], density_scale=0.5, uv_size=4.0, altitude=10000.0),
 'S7_cirrostratus_uv3':   dict(layers=[{'noise': 1, 'range': [-1.0, 0.0, 0.45, 0.9]}, ZERO(0.25)], density_scale=0.15, uv_size=3.0),
 'S8_typeG_altocu_uv1':   dict(layers=[{'noise': 1, 'range': [-0.9, 0.3, 0.25, 0.8]}, ZERO(1.0)], density_scale=0.3, uv_size=1.0),
}

def rot(x, y, deg):
    a = np.radians(deg); return x * np.cos(a) + y * np.sin(a), -x * np.sin(a) + y * np.cos(a)

def lowfield(x, y):  # same family as today's low-layer de-tile slide: cheap sines, km-scale, no texture taps
    qx, qy = x * 0.00025, y * 0.00025
    return (np.sin(qx * 1.53 + 1.7 * np.sin(qy * 2.11 + 0.6)) + 0.6 * np.sin(qy * 4.73 + 2.1),
            np.sin(qy * 1.87 + 1.4 * np.sin(qx * 2.57 + 4.0)) + 0.6 * np.sin(qx * 4.31 + 0.9))

def sh_stretch(stretch=3.0):
    def f(x, y, uv):
        return bilinear(PAT, x * 0.0002331 / uv / stretch, y * 0.0002331 / uv), 1.0
    return f

def sh_full(stretch=3.0, warp=0.12, second=0.37, covmod=0.5):
    def f(x, y, uv):
        k = 0.0002331 / uv
        sx, sy = lowfield(x, y)
        u = x * k / stretch + sx * warp; v = y * k + sy * warp
        p1 = bilinear(PAT, u, v)
        ru, rv = rot(x * k / stretch * second, y * k * second, 17.0)        # second, larger, rotated scale
        p2 = bilinear(PAT, ru + 0.37 + sy * warp, rv + 0.61 - sx * warp)
        pat = np.sqrt(np.clip(p1 * (0.35 + 1.3 * p2), 0, 1) * p1) if False else np.clip(p1 * (0.4 + 1.6 * p2), 0, 1)
        qx, qy = x / 23000.0, y / 31000.0
        cm = 1.0 - covmod * (0.5 + 0.5 * np.sin(qx * 6.283 + 2.0 * np.sin(qy * 6.283 + 1.3)))
        return pat, cm
    return f

SHEET = [{'noise': 1, 'range': [-0.9, 0.3, 0.25, 0.8]}, ZERO(0.0)]
P = {
 'P1_settings_only_uv2':     dict(layers=SHEET, density_scale=0.5, uv_size=2.0),
 'P2_stretch3_uv2':          dict(layers=SHEET, density_scale=0.5, uv_size=2.0, shader=sh_stretch(3.0)),
 'P3_stretch3_warp':         dict(layers=SHEET, density_scale=0.5, uv_size=2.0, shader=sh_full(3.0, 0.12, 0.37, 0.0)),
 'P4_stretch_warp_2scale_covmod': dict(layers=SHEET, density_scale=0.7, uv_size=2.0, shader=sh_full(3.0, 0.12, 0.37, 0.6)),
}

def sheet(name, variants):
    tiles = []
    for k, v in variants.items():
        render(k, **v)
        im = Image.open(os.path.join(sim.HERE, 'sim_%s.jpg' % k))
        im = im.resize((1150, 350), Image.LANCZOS); ImageDraw.Draw(im).text((6, 4), k + '  ' + str({a: b for a, b in v.items() if a not in ('layers', 'shader')}), fill=(255, 255, 0))
        tiles.append(im)
    out = Image.new('RGB', (1150, 350 * len(tiles)))
    for i, t in enumerate(tiles): out.paste(t, (0, 350 * i))
    out.save(os.path.join(sim.HERE, name), quality=88)

if __name__ == '__main__':
    import sys
    if 'S' in sys.argv[1:] or len(sys.argv) == 1: sheet('sheet_settings.jpg', S)
    if 'P' in sys.argv[1:] or len(sys.argv) == 1: sheet('sheet_shader.jpg', P)

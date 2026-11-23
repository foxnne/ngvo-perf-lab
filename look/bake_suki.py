"""Bake Suki's ENB (NLVA) colour look into linear half-float LUTs for the Community Shaders LUT stage.
Source of the look: enbseries/enbpalette.bmp (a 256x16 = 16^3 LUT strip, applied in display space) and the V2 shaping in
enbeffect.fx (intensity contrast = pow on magnitude, colour saturation = pow on the normalised colour; day values 0.94 / 1.38).
Our LUT stage takes linear light and the display encoding (gamma 2.2) follows it, so: grid x_lin -> d = x^(1/2.2) -> grade(d) -> out^2.2.
usage: python bake_suki.py   (writes out/suki_*.dds)"""
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 'C:/Modlists/NGVO 8.0 Beta/look/webapp')
from bake_params import write_dds_half
PAL = np.asarray(Image.open(os.path.join(HERE, 'ref/nlva/insane/enbseries/enbpalette.bmp')).convert('RGB')).astype(np.float32) / 255   # (16, 256, 3)
CUBE = PAL.reshape(16, 16, 16, 3)          # [g, b, r]: row = green, 16-px tile = blue, x in tile = red  (enbeffect.fx E_CC_PALETTE lookup)


def palette(c):
    c = np.clip(c, 0, 1) * 15.0
    i0 = np.floor(c).astype(int).clip(0, 14); f = c - i0
    out = 0
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[..., 0] if dr else 1 - f[..., 0]) * (f[..., 1] if dg else 1 - f[..., 1]) * (f[..., 2] if db else 1 - f[..., 2])
                out = out + w[..., None] * CUBE[i0[..., 1] + dg, i0[..., 2] + db, i0[..., 0] + dr]
    return out


def v2_shape(c, contrast=0.94, saturation=1.38):
    c = c + 1e-6; n = np.linalg.norm(c, axis=-1, keepdims=True); x = c / n
    x = np.power(x, saturation); x = x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-6) * 1.0
    return np.power(n, contrast) * x


def bake(name, strength=1.0, shape=False, N=128, g=2.2):
    X = np.arange(N * N)[None, :].repeat(N, 0); Y = np.arange(N)[:, None].repeat(N * N, 1)
    lat = np.stack([(X % N) / (N - 1.0), Y / (N - 1.0), (X // N) / (N - 1.0)], -1).astype(np.float32)
    d = np.power(lat, 1.0 / g); o = d
    if shape: o = np.clip(v2_shape(o), 0, 1)
    o = palette(o); o = d + (o - d) * strength
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True); p = os.path.join(HERE, 'out', name)
    write_dds_half(p, np.power(np.clip(o, 0, 1), g).astype(np.float32)); print('baked', p)


if __name__ == '__main__':
    bake('suki_palette_100_lin128.dds', 1.0)
    bake('suki_palette_060_lin128.dds', 0.6)
    bake('suki_palette_shape_100_lin128.dds', 1.0, shape=True)
    grey = np.linspace(0, 1, 11)[:, None].repeat(3, 1)
    print('grey ramp in  :', np.round(grey[:, 0], 2).tolist()); print('palette out   :', np.round(palette(grey).mean(-1), 3).tolist())
    for nm, c in (('red', [.6, .2, .2]), ('green', [.25, .5, .2]), ('blue', [.2, .3, .6]), ('skin', [.75, .55, .45]), ('straw', [.7, .62, .42])):
        print('%-6s %s -> %s' % (nm, c, np.round(palette(np.array([c], np.float32))[0], 3).tolist()))

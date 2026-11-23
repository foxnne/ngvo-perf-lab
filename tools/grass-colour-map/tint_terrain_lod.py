"""Post-process terrain LOD diffuse textures with the grass colour map.

  python tint_terrain_lod.py (--in <folder with Tamriel.<level>.<x>.<y>.dds> | --bsa <textures bsa>) --out <folder>
                             [--map <GrassColourMap dds>] [--cells X0 Y0 X1 Y1] [--min-cover 0.01]
                             [--strength 0.6] [--luma-keep 0.5] [--gain 1.0] [--saturation 1.0] [--format BC7_UNORM]
                             [--no-protect | --protect-lo 0.10 --protect-hi 0.25] [--png]

File naming (xLODGen / vanilla): <Worldspace>.<level>.<x>.<y>.dds, level = 4, 8, 16 or 32; (x, y) = south-west cell of the block;
the block covers level x level cells; image row 0 is the block's NORTH edge. *_n.dds (normal maps) are left alone.

Blend, in linear light, per pixel (t = coverage * strength):
    Y      = luminance(terrain)
    target = grass / luminance(grass) * lerp(luminance(grass) * GAIN, Y, LUMA_KEEP)
    out    = lerp(terrain, target, t * protect)        protect = smoothstep(lo, hi, saturation of the terrain texel) * warm * dim:
                                                        grey roads, rock and (bluish, bright) snow keep their colour
i.e. the grass map supplies the hue and, by 1 - LUMA_KEEP, the brightness of grass; LUMA_KEEP of the terrain's own light/dark
detail survives. Everything is a function of the texel and its world position only, so tiles and LOD levels stay seamless.
Alpha (if any) is copied. Output is written in the source's format with a fresh mip chain. Input files are never modified;
--out must differ from --in.
"""
import argparse
import os
import re
import shutil
import sys

import numpy as np

import gcmlib as g

NAME_RE = re.compile(r'^(?P<ws>[^.]+)\.(?P<lvl>\d+)\.(?P<x>-?\d+)\.(?P<y>-?\d+)\.dds$', re.I)
FMT = {(b'DXT1', None): 'BC1_UNORM', (b'DXT3', None): 'BC2_UNORM', (b'DXT5', None): 'BC3_UNORM', ('DX10', 71): 'BC1_UNORM', ('DX10', 72): 'BC1_UNORM_SRGB',
       ('DX10', 77): 'BC3_UNORM', ('DX10', 78): 'BC3_UNORM_SRGB', ('DX10', 98): 'BC7_UNORM', ('DX10', 99): 'BC7_UNORM_SRGB',
       ('DX10', 28): 'R8G8B8A8_UNORM', ('DX10', 29): 'R8G8B8A8_UNORM_SRGB', ('DX10', 87): 'B8G8R8A8_UNORM', ('DX10', 91): 'B8G8R8A8_UNORM_SRGB'}


def lum(c):
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


class GrassMap:
    def __init__(self, path, tmp):
        levels, info = g.read_dds_rgba(path, tmp, all_mips=True)
        m = re.search(r'\.(-?\d+)\.(-?\d+)\.(-?\d+)\.(-?\d+)\.dds$', os.path.basename(path))
        self.minx, self.miny, self.maxx, self.maxy = [int(v) for v in m.groups()]
        self.levels = [np.dstack([g.srgb2lin(l[..., :3]), l[..., 3]]) for l in levels]
        self.unit = (self.maxx - self.minx + 1) * 4096.0 / levels[0].shape[1]

    def sample(self, x, y, px_units):
        """Bilinear sample at world positions from the mip whose texel is closest to (not finer than half) the pixel size."""
        lv = int(np.clip(np.floor(np.log2(max(px_units / self.unit, 1.0)) + 0.5), 0, len(self.levels) - 1))
        m = self.levels[lv]
        h, w = m.shape[:2]
        u = (x - self.minx * 4096.0) / ((self.maxx - self.minx + 1) * 4096.0)
        v = ((self.maxy + 1) * 4096.0 - y) / ((self.maxy - self.miny + 1) * 4096.0)
        inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
        s = g.sample_bilinear(m, u * w - 0.5, v * h - 0.5)
        s[..., 3] *= inside
        return s


def tint(rgb_lin, grass_lin, cover, strength, luma_keep, gain, saturation=1.0, protect=(0.10, 0.25)):
    y = np.maximum(lum(rgb_lin), 1e-5)
    if saturation != 1.0:
        gl = lum(grass_lin)[..., None]
        grass_lin = np.clip(gl + (grass_lin - gl) * saturation, 0, None)
    yg = np.maximum(lum(grass_lin), 1e-5)
    # every term depends on this texel and on the world position only (no neighbourhood), so neighbouring tiles and
    # LOD levels get the same result along their shared edges: no seams
    base = (yg * gain) * (1 - luma_keep) + y * luma_keep
    target = grass_lin / yg[..., None] * base[..., None]
    t = np.clip(cover * strength, 0, 1)
    if protect is not None:
        # leave grey or white terrain alone (roads, rock, snow): the map is too coarse to cut thin roads out by itself
        sm = rgb_lin
        sat = (sm.max(2) - sm.min(2)) / np.maximum(sm.max(2), 1e-4)
        k = np.clip((sat - protect[0]) / max(protect[1] - protect[0], 1e-4), 0, 1)
        t = t * k * k * (3 - 2 * k)
        # snow is slightly blue and bright: require a warm (red >= blue) and not very bright texel as well
        warm = np.clip(((sm[..., 0] - sm[..., 2]) / np.maximum(sm.max(2), 1e-4) + 0.02) / 0.10, 0, 1)
        dim = 1 - np.clip((lum(sm) - 0.35) / 0.25, 0, 1)
        t = t * warm * dim
    t = t[..., None]
    return np.clip(rgb_lin * (1 - t) + target * t, 0, 1)


def process(path, out_dir, gm, a, tmp):
    name = os.path.basename(path)
    m = NAME_RE.match(name)
    lvl, bx, by = int(m.group('lvl')), int(m.group('x')), int(m.group('y'))
    img, info = g.read_dds_rgba(path, tmp)
    h, w = img.shape[:2]
    size = lvl * 4096.0
    px = size / w
    xs = bx * 4096.0 + (np.arange(w) + 0.5) * px
    ys = (by + lvl) * 4096.0 - (np.arange(h) + 0.5) * (size / h)
    X, Y = np.meshgrid(xs, ys)
    s = gm.sample(X, Y, px)
    lin = g.srgb2lin(img[..., :3])
    out = tint(lin, s[..., :3], s[..., 3], a.strength, a.luma_keep, a.gain, a.saturation, None if a.no_protect else (a.protect_lo, a.protect_hi))
    res = np.dstack([np.round(g.lin2srgb(out) * 255), np.round(img[..., 3] * 255)]).astype(np.uint8)
    key = (info['fourcc'].encode('latin1') if info['dxgi'] is None else 'DX10', info['dxgi'])
    fmt = a.format or FMT.get(key)
    if a.format:
        info = dict(info, dxgi=0, mips=2)
    if fmt is None:
        raise RuntimeError('%s: unsupported source format %r' % (name, key))
    srgb_fmt = fmt.endswith('_SRGB')
    raw = os.path.join(tmp, name)
    g.write_dds_rgba8(raw, [res], srgb=srgb_fmt)
    args = ['-f', fmt, '-m', '0' if info['mips'] > 1 else '1', '-o', out_dir]
    if info['dxgi'] is None:
        args.append('-dx9')
    g.texconv(args + [raw])
    os.remove(raw)
    if a.png:
        from PIL import Image
        Image.fromarray(res[..., :3]).save(os.path.join(out_dir, name[:-4] + '.png'))
    changed = float(np.abs(res[..., :3].astype(float) - np.round(img[..., :3] * 255)).mean())
    return dict(name=name, size='%dx%d' % (w, h), fmt=fmt, mips=info['mips'], cover=float(s[..., 3].mean()), change=changed)


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--in', dest='src', help='folder with <Worldspace>.<level>.<x>.<y>.dds')
    ap.add_argument('--bsa', help='read the tiles from textures\\terrain\\<worldspace>\\ inside this BSA instead of --in')
    ap.add_argument('--out', required=True)
    ap.add_argument('--map', default=os.path.join(here, 'out', 'foxnne - Grass Colour Map', 'textures', 'GrassColour', 'GrassColourMaps', 'Tamriel.GrassColourMap.-57.-43.61.50.dds'))
    ap.add_argument('--worldspace', default='Tamriel')
    ap.add_argument('--cells', type=int, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'), help='only blocks touching this cell rectangle')
    ap.add_argument('--min-cover', type=float, default=0.0, help='skip tiles whose mean grass coverage is below this (nothing to tint)')
    ap.add_argument('--strength', type=float, default=0.6)
    ap.add_argument('--luma-keep', type=float, default=0.5, help='0 = take the brightness of the grass, 1 = keep the terrain brightness (hue only)')
    ap.add_argument('--gain', type=float, default=1.0, help='multiplier on the grass brightness')
    ap.add_argument('--saturation', type=float, default=1.0, help='saturation of the grass colour (1 = as baked)')
    ap.add_argument('--no-protect', action='store_true', help='also tint grey / white terrain texels (roads, rock, snow)')
    ap.add_argument('--protect-lo', type=float, default=0.10, help='terrain saturation at and below which nothing is tinted')
    ap.add_argument('--protect-hi', type=float, default=0.25, help='terrain saturation from which the full tint applies')
    ap.add_argument('--format', help='output format for texconv, e.g. BC7_UNORM (default: the source format). Use it when xLODGen wrote '
                                     'uncompressed tiles so the tint goes in before the one and only compression')
    ap.add_argument('--png', action='store_true', help='also write a PNG of every result for viewing')
    a = ap.parse_args()
    if not a.src and not a.bsa:
        sys.exit('give --in or --bsa')
    if a.src and os.path.abspath(a.src).lower() == os.path.abspath(a.out).lower():
        sys.exit('--out must not be the input folder')
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(a.out, '_tmp')
    gm = GrassMap(a.map, tmp)
    bsa = None
    if a.bsa:
        sys.path.insert(0, r'C:\Users\foxnn\dev\skyrimnet-wardrobe')
        import tes5
        bsa = tes5.BSA(a.bsa)
        prefix = 'textures\\terrain\\%s\\' % a.worldspace.lower()
        names = sorted(a.worldspace + n[len(prefix) + len(a.worldspace):] for n in (x.lower() for x in tes5.bsa_list(a.bsa)) if n.startswith(prefix))
    else:
        names = sorted(os.listdir(a.src))
    n = skipped = 0
    for name in names:
        m = NAME_RE.match(name)
        if not m or m.group('ws').lower() != a.worldspace.lower():
            continue
        lvl, bx, by = int(m.group('lvl')), int(m.group('x')), int(m.group('y'))
        if a.cells and (bx > a.cells[2] or bx + lvl - 1 < a.cells[0] or by > a.cells[3] or by + lvl - 1 < a.cells[1]):
            continue
        if a.min_cover > 0:
            xs = (bx + (np.arange(16) + 0.5) / 16 * lvl) * 4096.0
            ys = (by + (np.arange(16) + 0.5) / 16 * lvl) * 4096.0
            X, Y = np.meshgrid(xs, ys)
            if float(gm.sample(X, Y, lvl * 256.0)[..., 3].mean()) < a.min_cover:
                skipped += 1
                continue
        if bsa is not None:
            path = os.path.join(tmp, 'src', name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(bsa.read('textures\\terrain\\%s\\%s' % (a.worldspace.lower(), name.lower())))
        else:
            path = os.path.join(a.src, name)
        r = process(path, a.out, gm, a, tmp)
        if bsa is not None:
            os.remove(path)
        n += 1
        print('%-28s %-9s %-16s mips %2d  mean coverage %.2f  mean change %.1f/255' % (r['name'], r['size'], r['fmt'], r['mips'], r['cover'], r['change']), flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print('%d textures written to %s, %d skipped for no grass (strength %.2f, luma keep %.2f)' % (n, a.out, skipped, a.strength, a.luma_keep))


if __name__ == '__main__':
    main()


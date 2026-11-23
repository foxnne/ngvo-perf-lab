"""Shared helpers for the grass colour map: grid conventions, filters, DDS I/O.

Grid convention (same rectangle and orientation as the terrain height map and the ground-fog water map):
  Tamriel rectangle = cells -57..61 (x) by -43..50 (y), 119 x 94 cells, cell = 4096 game units
  image row 0 = NORTH edge, column 0 = WEST edge, texel = area (not vertex)
  texel (col i, row r) covers world x  minX*4096 + i*T .. +T ,  y  (maxY+1)*4096 - (r+1)*T .. +T   with T = 4096 / TEXELS
  uv of a world position:  u = (x - minX*4096) / ((maxX-minX+1)*4096) ,  v = ((maxY+1)*4096 - y) / ((maxY-minY+1)*4096)
"""
import os
import struct
import subprocess

import numpy as np

MINX, MINY, MAXX, MAXY = -57, -43, 61, 50
CELL = 4096.0
TEXELS = 16                      # texels per cell edge -> 256 game units per texel
NX, NY = MAXX - MINX + 1, MAXY - MINY + 1
W, H = NX * TEXELS, NY * TEXELS
TEXCONV = r'C:\Modlists\NGVO 8.0 Beta\tools\xLODGen\Edit Scripts\Texconvx64.exe'


def srgb2lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(np.asarray(c, np.float64), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def world_to_px(x, y, texels=TEXELS):
    """Continuous pixel coordinates (texel centres at .5)."""
    t = CELL / texels
    return (np.asarray(x) - MINX * CELL) / t, ((MAXY + 1) * CELL - np.asarray(y)) / t


def gauss_kernel(sigma):
    r = max(1, int(np.ceil(3 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    return k / k.sum()


def blur(a, sigma):
    """Separable Gaussian, edge-replicated. a: HxW or HxWxC."""
    if sigma <= 0:
        return a
    # large sigmas: blur a decimated copy, then resample (keeps the cost bounded)
    if sigma > 6:
        f = int(sigma // 3)
        h, w = a.shape[:2]
        hp, wp = (-h) % f, (-w) % f
        pad = [(0, hp), (0, wp)] + [(0, 0)] * (a.ndim - 2)
        ap = np.pad(a, pad, mode='edge')
        small = ap.reshape((ap.shape[0] // f, f, ap.shape[1] // f, f) + ap.shape[2:]).mean(axis=(1, 3))
        small = blur(small, sigma / f)
        return upsample_bilinear(small, f)[:h, :w]
    k = gauss_kernel(sigma)
    r = len(k) // 2
    out = a.astype(np.float64)
    for axis in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode='edge')
        acc = np.zeros_like(out)
        n = out.shape[axis]
        for i, kv in enumerate(k):
            sl = [slice(None)] * out.ndim
            sl[axis] = slice(i, i + n)
            acc += kv * p[tuple(sl)]
        out = acc
    return out


def upsample_bilinear(a, f):
    """Upsample by integer factor f with texel-centre alignment."""
    h, w = a.shape[:2]
    ys = (np.arange(h * f) + 0.5) / f - 0.5
    xs = (np.arange(w * f) + 0.5) / f - 0.5
    return sample_bilinear(a, xs[None, :].repeat(h * f, 0), ys[:, None].repeat(w * f, 1))


def sample_bilinear(a, px, py):
    """a: HxW[xC]; px, py continuous indices where integer = texel centre. Clamped."""
    h, w = a.shape[:2]
    px = np.clip(px, 0, w - 1)
    py = np.clip(py, 0, h - 1)
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx = px - x0
    fy = py - y0
    if a.ndim == 3:
        fx = fx[..., None]
        fy = fy[..., None]
    return (a[y0, x0] * (1 - fx) + a[y0, x1] * fx) * (1 - fy) + (a[y1, x0] * (1 - fx) + a[y1, x1] * fx) * fy


def sample_map(m, x, y):
    """Sample a map laid out by the convention above (any resolution) at world positions, bilinear."""
    h, w = m.shape[:2]
    u = (np.asarray(x) - MINX * CELL) / (NX * CELL)
    v = ((MAXY + 1) * CELL - np.asarray(y)) / (NY * CELL)
    return sample_bilinear(m, u * w - 0.5, v * h - 0.5)


# ---------------------------------------------------------------- DDS

DXGI_RGBA8, DXGI_RGBA8_SRGB, DXGI_BC7, DXGI_BC7_SRGB, DXGI_BC1, DXGI_BC1_SRGB, DXGI_BC3, DXGI_BC3_SRGB = 28, 29, 98, 99, 71, 72, 77, 78


def write_dds_rgba8(path, mips, srgb=True):
    """mips: list of HxWx4 uint8 arrays (level 0 first). DX10 header, R8G8B8A8_UNORM[_SRGB]."""
    h, w = mips[0].shape[:2]
    flags = 0x1 | 0x2 | 0x4 | 0x8 | 0x1000 | (0x20000 if len(mips) > 1 else 0)
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, flags, h, w, w * 4, 0, len(mips))
    pf = struct.pack('<II4sIIIII', 32, 0x4, b'DX10', 0, 0, 0, 0, 0)
    caps = struct.pack('<IIIII', 0x1000 | (0x400008 if len(mips) > 1 else 0), 0, 0, 0, 0)
    dx10 = struct.pack('<IIIII', DXGI_RGBA8_SRGB if srgb else DXGI_RGBA8, 3, 0, 1, 0)
    with open(path, 'wb') as f:
        f.write(hdr + pf + caps + dx10)
        for m in mips:
            f.write(np.ascontiguousarray(m, np.uint8).tobytes())


def dds_info(data):
    h, w, _, _, mips = struct.unpack_from('<IIIII', data, 12)
    fourcc = data[84:88]
    dxgi = struct.unpack_from('<I', data, 128)[0] if fourcc == b'DX10' else None
    return dict(w=w, h=h, mips=max(mips, 1), fourcc=fourcc.decode('latin1'), dxgi=dxgi)


def texconv(args, cwd=None):
    r = subprocess.run([TEXCONV, '-nologo', '-y'] + args, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError('texconv failed: %s\n%s' % (' '.join(args), r.stdout + r.stderr))
    return r.stdout


def read_dds_rgba(path_or_bytes, tmpdir, all_mips=False):
    """Decode any DDS to float RGBA 0..1 (values as stored, i.e. sRGB-encoded for colour textures) through texconv.
    Returns level 0, or the list of all levels."""
    os.makedirs(tmpdir, exist_ok=True)
    if isinstance(path_or_bytes, (bytes, bytearray)):
        src = os.path.join(tmpdir, '_in.dds')
        open(src, 'wb').write(path_or_bytes)
    else:
        src = path_or_bytes
    data = open(src, 'rb').read(148)
    info = dds_info(data)
    # keep the stored code values: tell texconv not to convert between sRGB and linear
    fmt = 'R8G8B8A8_UNORM_SRGB' if info['dxgi'] in (29, 72, 75, 78, 99) else 'R8G8B8A8_UNORM'
    texconv(['-f', fmt, '-o', tmpdir, '-sx', '_rgba', '-dx10'] + ([] if all_mips else ['-m', '1']) + [src])
    out = os.path.join(tmpdir, os.path.splitext(os.path.basename(src))[0] + '_rgba.dds')
    b = open(out, 'rb').read()
    oi = dds_info(b)
    off = 148 if oi['dxgi'] is not None else 128
    levels = []
    w, h = oi['w'], oi['h']
    for _ in range(oi['mips'] if all_mips else 1):
        levels.append(np.frombuffer(b, np.uint8, w * h * 4, off).reshape(h, w, 4).astype(np.float32) / 255.0)
        off += w * h * 4
        w, h = max(1, w // 2), max(1, h // 2)
    os.remove(out)
    return (levels if all_mips else levels[0]), info


#!/usr/bin/env python3
"""Build a world-anchored local cloud map (Physical Sky "Local NDF" asset) for Tamriel from terrain.

Outputs <out>/<asset>/Height.dds, Modeling.dds, localcloud_state.json and PNG previews.
See NOTES.md for the format facts this relies on. Deterministic: same inputs + options -> same bytes.

Internal convention: all 2D arrays are NORTH-UP (row 0 = north edge, col 0 = west edge), in "sky metres"
(game units * 0.01428). The DDS files are written flipped (row 0 = south) because the shader maps v=0 to min Y.
"""
import argparse, json, math, os, struct, zlib
import numpy as np
from PIL import Image

GU2M = 0.01428
CELL = 4096.0
HM_DEFAULT = (r"C:\Users\foxnn\dev\terrain-heightmap\mod\textures\terrain\HeightMaps"
              r"\Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds")
ESP_DEFAULT = r"C:\Modlists\NGVO 8.0 Beta\mods\NAT.ENB - ESP WEATHER PLUGIN\NAT-ENB.esp"
TAMRIEL_WRLD = 0x0000003C
MIST_BASE_LOW24 = 0x0D64BE


# ----------------------------------------------------------------------------- inputs
def load_heightmap(path):
    """R16 height map written by terrain-heightmap: raw = z/8 + 32767, row 0 = north, 128 units per texel."""
    name = os.path.basename(path).split('.')
    min_cx, min_cy, max_cx, max_cy = (int(v) for v in name[3:7])
    b = open(path, 'rb').read(148)
    assert b[:4] == b'DDS '
    h, w = struct.unpack_from('<II', b, 12)
    off = 148 if b[84:88] == b'DX10' else 128
    raw = np.fromfile(path, '<u2', offset=off).reshape(h, w)
    z = (raw.astype(np.float32) - 32767.0) * 8.0
    assert w == (max_cx - min_cx + 1) * 32 and h == (max_cy - min_cy + 1) * 32
    return z, (min_cx, min_cy, max_cx, max_cy)


def load_seeds(path):
    """All REFR records below the Tamriel world group: (x, y, z, scale, is_mist)."""
    b = open(path, 'rb').read()
    out = []

    def walk(s, e, world):
        while s < e:
            sig = b[s:s + 4]
            size = struct.unpack_from('<I', b, s + 4)[0]
            if sig == b'GRUP':
                label, gtype = struct.unpack_from('<Ii', b, s + 8)
                walk(s + 24, s + size, label if gtype == 1 else world)
                s += size
                continue
            flags, fid = struct.unpack_from('<II', b, s + 8)
            if sig == b'REFR' and world == TAMRIEL_WRLD:
                body = b[s + 24:s + 24 + size]
                if flags & 0x40000:
                    body = zlib.decompress(body[4:])
                o, d = 0, {}
                while o < len(body):
                    t = body[o:o + 4]
                    n = struct.unpack_from('<H', body, o + 4)[0]
                    d[t] = body[o + 6:o + 6 + n]
                    o += 6 + n
                if b'NAME' in d and b'DATA' in d:
                    base = struct.unpack('<I', d[b'NAME'][:4])[0]
                    x, y, z = struct.unpack('<3f', d[b'DATA'][:12])
                    sc = struct.unpack('<f', d[b'XSCL'][:4])[0] if b'XSCL' in d else 1.0
                    out.append((x, y, z, sc, (base & 0xFFFFFF) == MIST_BASE_LOW24))
            s += 24 + size

    walk(0, len(b), None)
    out.sort()
    return out


# ----------------------------------------------------------------------------- image helpers
def area_resize(a, w, h):
    """Box-filter resize of a float32 2D array."""
    return np.asarray(Image.fromarray(np.ascontiguousarray(a, np.float32), 'F').resize((w, h), Image.BOX), np.float32)


def blur(a, sigma_px):
    """Gaussian blur via FFT with edge padding (float64 internally for determinism of rounding)."""
    if sigma_px <= 0.05:
        return a.astype(np.float32)
    pad = int(math.ceil(sigma_px * 3.5)) + 1
    p = np.pad(a.astype(np.float64), pad, mode='edge')
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.rfftfreq(p.shape[1])[None, :]
    g = np.exp(-2.0 * (math.pi * sigma_px) ** 2 * (fx * fx + fy * fy))
    r = np.fft.irfft2(np.fft.rfft2(p) * g, s=p.shape)
    return r[pad:-pad, pad:-pad].astype(np.float32)


def convolve(a, kernel):
    """'same' convolution with an odd-sized kernel via FFT, edge padded."""
    kh, kw = kernel.shape
    py, px = kh // 2, kw // 2
    p = np.pad(a.astype(np.float64), ((py, py), (px, px)), mode='edge')
    k = np.zeros_like(p)
    k[:kh, :kw] = kernel
    k = np.roll(k, (-py, -px), (0, 1))
    r = np.fft.irfft2(np.fft.rfft2(p) * np.fft.rfft2(k), s=p.shape)
    return r[py:py + a.shape[0], px:px + a.shape[1]].astype(np.float32)


def shift(a, dcol, drow):
    """Return b with b[r, c] = a[r - drow, c - dcol] (bilinear, |d| <= 1, edge clamped)."""
    p = np.pad(a, 1, mode='edge')
    h, w = a.shape

    def lerp_axis(arr, d, axis):
        i = int(math.floor(-d))
        f = -d - i
        n = arr.shape[axis] - 2
        lo = np.take(arr, np.arange(1 + i, 1 + i + n), axis=axis)
        hi = np.take(arr, np.arange(2 + i, 2 + i + n), axis=axis) if f > 0 else lo
        return lo * (1 - f) + hi * f

    t = lerp_axis(p, drow, 0)
    return lerp_axis(t, dcol, 1)[:h, :w]


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sat(x):
    return np.clip(x, 0.0, 1.0)


def noise_field(shape, dx, wavelengths, seed):
    """Deterministic smooth noise in 0..1 (mean 0.5), sum of band-limited octaves."""
    rng = np.random.Generator(np.random.PCG64(seed))
    total = np.zeros(shape, np.float32)
    amp_sum = 0.0
    for i, wl in enumerate(wavelengths):
        white = rng.standard_normal(shape).astype(np.float32)
        n = blur(white, wl / dx / 2.5)
        n /= max(float(n.std()), 1e-9)
        amp = 0.6 ** i
        total += amp * n
        amp_sum += amp * amp
    total /= math.sqrt(amp_sum)
    return sat(0.5 + total * 0.22)


def write_dds(path, mips, dxgi):
    """Uncompressed DX10-header DDS. mips: list of uint16 arrays (h, w, channels), largest first."""
    h, w, ch = mips[0].shape
    hdr = bytearray(148)
    hdr[0:4] = b'DDS '
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x8 | (0x20000 if len(mips) > 1 else 0)   # CAPS HEIGHT WIDTH PIXELFORMAT PITCH MIPMAPCOUNT
    struct.pack_into('<7I', hdr, 4, 124, flags, h, w, w * ch * 2, 0, len(mips))
    struct.pack_into('<II4s', hdr, 76, 32, 0x4, b'DX10')
    caps = 0x1000 | (0x400008 if len(mips) > 1 else 0)                           # TEXTURE (+ COMPLEX | MIPMAP)
    struct.pack_into('<I', hdr, 108, caps)
    struct.pack_into('<5I', hdr, 128, dxgi, 3, 0, 1, 0)                          # format, TEXTURE2D, misc, arraySize, misc2
    with open(path, 'wb') as f:
        f.write(hdr)
        for m in mips:
            f.write(np.ascontiguousarray(m, '<u2').tobytes())


def mip_chain(img):
    """img float32 (h, w, c) in 0..1 -> list of uint16 mips down to 1x1 (box filter from the previous level)."""
    out = []
    cur = img.astype(np.float32)
    while True:
        out.append(np.round(sat(cur) * 65535.0).astype(np.uint16))
        h, w = cur.shape[:2]
        if h == 1 and w == 1:
            break
        nh, nw = max(h // 2, 1), max(w // 2, 1)
        cur = np.stack([area_resize(cur[..., c], nw, nh) for c in range(cur.shape[2])], -1)
    return out


def save_gray(path, a, lo=0.0, hi=1.0):
    Image.fromarray(np.round(sat((a - lo) / (hi - lo)) * 255).astype(np.uint8), 'L').save(path)


def save_rgb(path, rgb):
    Image.fromarray(np.round(sat(rgb) * 255).astype(np.uint8), 'RGB').save(path)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--heightmap', default=HM_DEFAULT)
    ap.add_argument('--plugin', default=ESP_DEFAULT, help='plugin whose Tamriel REFRs are the cloud/mist seeds')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'))
    ap.add_argument('--mode', default='orographic',
                    choices=['orographic', 'mist', 'mist-separate', 'diag-one-blob', 'diag-two-heights', 'diag-flat-clear'],
                    help="orographic = the original pass-1 map (unchanged). mist = sparse 'collared' banks (NOTES Pass 2). "
                         "mist-separate = soft banks for the 'Separate layer' blend mode (modelingBlend 2, "
                         "NOTES-separate-layer.md). diag-* = small test assets")
    ap.add_argument('--asset', default=None, help='asset folder id ([A-Za-z0-9_-] only); default depends on --mode')
    # ---- pass-2 (mist / diag) options; ignored by --mode orographic
    ap.add_argument('--global-base', type=float, default=1200.0, help='ndfAltitudeOffset of the weather the map is used with (m)')
    ap.add_argument('--global-thickness', type=float, default=900.0, help='ndfAltitudeScale of that weather (m)')
    ap.add_argument('--global-top-frac', type=float, default=0.95, help='procedural baseHeight.y (top of the global slab, 0..1)')
    ap.add_argument('--atlas-texel', type=float, default=8.0, help='cloudMap.localTexelSize the asset is designed for (m)')
    ap.add_argument('--shear-margin', type=float, default=0.0, help='extra width (m) of the clear alpha-1 plateau around each bank')
    ap.add_argument('--banks', type=int, default=60, help='mist: number of banks picked from the seeds (plus the Throat ring)')
    ap.add_argument('--bank-spacing', type=float, default=340.0, help='mist: minimum distance between bank centres (m)')
    ap.add_argument('--bank-coverage', type=float, default=None,
                    help='mist: peak coverage of a bank (default 0.6; mist-separate 0.55)')
    ap.add_argument('--bank-type', type=float, default=None,
                    help='mist: top type of a bank = how much of bottom..top is filled (default 0.4; mist-separate 0.7)')
    ap.add_argument('--worldspace', default='Tamriel')
    ap.add_argument('--width', type=int, default=952, help='output width in texels (height follows the map aspect)')
    ap.add_argument('--z-bottom', type=float, default=-14500.0, help='Physical Sky zBottom of the worldspace (game units)')
    ap.add_argument('--sea-level', type=float, default=-14000.0, help='terrain below this z (game units) is sea')
    ap.add_argument('--wind-from', type=float, default=330.0,
                    help='prevailing wind direction it blows FROM, degrees clockwise from north (0 = northerly)')
    # term strengths (peak coverage contributed by each term, 0 disables)
    ap.add_argument('--orographic', type=float, default=0.70, help='windward upslope cloud strength')
    ap.add_argument('--peaks', type=float, default=0.55, help='cap cloud over high / prominent terrain')
    ap.add_argument('--rain-shadow', type=float, default=0.85, help='coverage suppression in the lee (0..1)')
    ap.add_argument('--fog', type=float, default=0.60, help='low stratus / fog in enclosed basins and low wet ground')
    ap.add_argument('--marine', type=float, default=0.32, help='low marine cloud over the sea')
    ap.add_argument('--seeds', type=float, default=0.50, help='cloud banks at the placed cloud / mist statics')
    ap.add_argument('--seed-radius', type=float, default=16.0, help='blob sigma in metres per unit of reference scale')
    ap.add_argument('--noise', type=float, default=0.35, help='0..1 large-scale break-up of the smooth terms')
    ap.add_argument('--noise-seed', type=int, default=20261118)
    ap.add_argument('--max-coverage', type=float, default=0.85)
    ap.add_argument('--alpha-max', type=float, default=0.90, help='influence where the map asserts cloud')
    ap.add_argument('--alpha-clear', type=float, default=0.65, help='influence where the map asserts clear air (lee)')
    # geometry of the terms (sky metres)
    ap.add_argument('--slope-scale', type=float, default=0.40, help='smoothed upslope (m/m) that gives full orographic cloud')
    ap.add_argument('--advect-length', type=float, default=220.0, help='downwind e-folding length of lift / descent')
    ap.add_argument('--depletion', type=float, default=0.5, help='how fast upwind ranges use up the moisture (0 = off)')
    ap.add_argument('--depletion-length', type=float, default=1400.0, help='upwind fetch (m) that counts for depletion')
    ap.add_argument('--shadow-drop', type=float, default=0.22, help='m of shelter height lost per m downwind of a barrier')
    ap.add_argument('--lcl', type=float, default=300.0, help='cloud base over low ground, m above zBottom')
    ap.add_argument('--marine-base', type=float, default=150.0)
    ap.add_argument('--feather', type=float, default=300.0)
    args = ap.parse_args()
    if args.asset is None:
        args.asset = {'orographic': 'tamriel-orographic', 'mist': 'tamriel-mist-v2',
                      'mist-separate': 'tamriel-mist-separate'}.get(args.mode, args.mode)
    separate = args.mode == 'mist-separate'
    if args.bank_coverage is None:
        args.bank_coverage = 0.55 if separate else 0.6
    if args.bank_type is None:
        args.bank_type = 0.7 if separate else 0.4
    if args.mode != 'orographic':
        return build_pass2(args)

    out_dir = os.path.join(args.out, args.asset)
    os.makedirs(out_dir, exist_ok=True)

    # ---- terrain --------------------------------------------------------------------------
    z, (min_cx, min_cy, max_cx, max_cy) = load_heightmap(args.heightmap)
    x0, x1 = min_cx * CELL, (max_cx + 1) * CELL          # game units, west / east edge
    y0, y1 = min_cy * CELL, (max_cy + 1) * CELL          # south / north edge
    size_m = ((x1 - x0) * GU2M, (y1 - y0) * GU2M)
    center_m = ((x0 + x1) * 0.5 * GU2M, (y0 + y1) * 0.5 * GU2M)
    W = args.width
    Ht = int(round(W * (y1 - y0) / (x1 - x0)))
    dx = size_m[0] / W                                   # metres per output texel
    sea_m = (args.sea_level - args.z_bottom) * GU2M

    H_raw = area_resize((z - args.z_bottom) * GU2M, W, Ht)                    # terrain, m above zBottom
    sea = area_resize((z < args.sea_level).astype(np.float32), W, Ht)         # sea fraction per texel
    Hc = np.maximum(H_raw, sea_m)                                             # sea surface instead of sea floor
    px = lambda metres: metres / dx

    Hl = blur(Hc, px(35.0))        # local terrain
    Hm = blur(Hc, px(50.0))        # slope scale for lift
    Hs = blur(Hc, px(260.0))       # broad terrain level (cloud base follows this)
    Hb = blur(Hc, px(220.0))       # valley-scale mean for basins
    sea_soft = blur(sea, px(60.0))
    sea_near = blur(sea, px(160.0))

    # wind: blowing TOWARDS (east, north)
    th = math.radians(args.wind_from)
    te, tn = -math.sin(th), -math.cos(th)

    # ---- orographic lift: upslope along the wind, carried downwind ------------------------
    d_row, d_col = np.gradient(Hm.astype(np.float64), dx)                    # d/d(south), d/d(east)
    upslope = (te * d_col + tn * (-d_row)).astype(np.float32)                # m/m, + = air forced up
    def downwind(field, length_m, width_m, spread):
        """Carry a field downwind: one-sided exponential along the wind, Gaussian across it (unit sum)."""
        L = px(length_m)
        r = int(math.ceil(L * 3.5))
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float64)
        along = xx * te + (-yy) * tn                                         # downwind distance of the offset (px)
        cross = xx * tn - (-yy) * te
        wid = px(width_m) + spread * np.maximum(along, 0)
        kern = np.where(along >= 0, np.exp(-along / L) * np.exp(-0.5 * (cross / wid) ** 2) / wid, 0.0)
        kern /= kern.sum()
        return convolve(field, kern)                                         # true convolution: source at s affects x = s + offset

    adv = downwind(upslope, args.advect_length, 30.0, 0.3)
    lift = sat(adv / args.slope_scale) ** 1.4
    descent = sat(-adv / args.slope_scale)
    # moisture already rained out on ranges further upwind (mean lift over the upwind fetch)
    spent = downwind(sat(adv / args.slope_scale), args.depletion_length, 120.0, 0.25)
    lift *= np.exp(-args.depletion * spent / 0.25).astype(np.float32) if args.depletion > 0 else 1.0

    # ---- rain shadow: decayed running maximum of terrain along the wind --------------------
    step = 1.0 / max(abs(te), abs(tn))                                       # px, one texel along the dominant axis
    barrier = Hm.copy()
    drop = args.shadow_drop * step * dx
    n_iter = int(math.ceil((float(Hm.max()) - sea_m) / max(drop, 1e-6))) + 2
    for _ in range(min(n_iter, 4000)):
        nb = np.maximum(Hm, shift(barrier, te * step, -tn * step) - drop)
        if float(np.max(nb - barrier)) < 1e-3:
            barrier = nb
            break
        barrier = nb
    shelter = sstep(40.0, 260.0, barrier - Hm)
    lee_raw = sat(np.maximum(shelter, 0.8 * descent)) * (1.0 - lift)

    # ---- peaks: absolute height + prominence -----------------------------------------------
    prom = sat((Hl - Hs) / 140.0)
    high = sstep(380.0, 640.0, Hl)
    peak = sat(0.75 * high + 0.6 * prom * sstep(260.0, 420.0, Hl))
    lee = lee_raw * (1.0 - peak)

    # ---- basins / low wet ground ------------------------------------------------------------
    slope_mag = np.hypot(*np.gradient(blur(Hc, px(90.0)).astype(np.float64), dx)).astype(np.float32)
    flat = 1.0 - sstep(0.10, 0.40, slope_mag)
    land = 1.0 - sat(sea_soft * 1.4)
    basin = sat((Hb - Hl - 12.0) / 45.0) * (1.0 - sstep(60.0, 260.0, Hl))    # enclosed valley floor, not too high
    lowland = ((Hc - sea_m < 45.0) & (sea < 0.5)).astype(np.float32)
    lowfrac = blur(lowland, px(110.0))                                       # broad low ground, not a narrow beach
    wet = (1.0 - sstep(8.0, 60.0, Hl - sea_m)) * sat((lowfrac - 0.22) / 0.35)  # marsh, deltas, estuaries
    fog = sat(np.maximum(basin, wet) * flat) * land

    # ---- sea ---------------------------------------------------------------------------------
    marine = sat(sea_soft * 1.15)

    # ---- seeds -------------------------------------------------------------------------------
    seeds = load_seeds(args.plugin)
    seed_keep = np.ones((Ht, W), np.float64)       # product of (1 - blob)
    mist_keep = np.ones((Ht, W), np.float64)
    seed_zw = np.zeros((Ht, W), np.float64)        # weighted sum of seed altitude
    seed_w = np.zeros((Ht, W), np.float64)
    seed_px = []
    for (sx, sy, sz, sc, is_mist) in seeds:
        c = (sx - x0) / (x1 - x0) * W - 0.5
        rr = (y1 - sy) / (y1 - y0) * Ht - 0.5
        if not (-20 <= c < W + 20 and -20 <= rr < Ht + 20):
            continue
        seed_px.append((c, rr, is_mist))
        sig = px(args.seed_radius * min(max(sc, 0.5), 6.0)) * (1.6 if is_mist else 1.0)
        rad = int(math.ceil(sig * 3.0))
        c0, c1 = max(int(c) - rad, 0), min(int(c) + rad + 2, W)
        r0, r1 = max(int(rr) - rad, 0), min(int(rr) + rad + 2, Ht)
        if c0 >= c1 or r0 >= r1:
            continue
        gy, gx = np.mgrid[r0:r1, c0:c1]
        g = np.exp(-0.5 * (((gx - c) ** 2 + (gy - rr) ** 2) / (sig * sig)))
        (mist_keep if is_mist else seed_keep)[r0:r1, c0:c1] *= 1.0 - 0.85 * g
        if not is_mist:
            seed_zw[r0:r1, c0:c1] += g * (sz - args.z_bottom) * GU2M
            seed_w[r0:r1, c0:c1] += g
    seed_cloud = (1.0 - seed_keep).astype(np.float32)
    seed_mist = (1.0 - mist_keep).astype(np.float32)
    seed_alt = np.where(seed_w > 1e-6, seed_zw / np.maximum(seed_w, 1e-6), 0.0).astype(np.float32)

    # ---- combine coverage --------------------------------------------------------------------
    nz = noise_field((Ht, W), dx, (520.0, 210.0), args.noise_seed)
    brk = 1.0 - args.noise * (1.0 - sat((nz - 0.18) / 0.55))                 # 1-noise .. 1 multiplier
    comp = {
        'orographic': sat(args.orographic * lift * brk),
        'peaks': sat(args.peaks * peak * (0.55 + 0.45 * brk)),
        'fog': sat(args.fog * fog * (0.5 + 0.5 * brk)),
        'marine': sat(args.marine * marine * brk),
    }
    dry = 1.0 - args.rain_shadow * lee
    comp['orographic'] *= dry
    comp['fog'] *= 0.5 + 0.5 * dry
    comp['marine'] *= 0.45 + 0.55 * dry
    comp['seed_cloud'] = sat(args.seeds * seed_cloud)
    comp['seed_mist'] = sat(args.seeds * seed_mist)
    keep = np.ones((Ht, W), np.float32)
    for v in comp.values():
        keep *= 1.0 - v
    cov = np.minimum(1.0 - keep, args.max_coverage)

    # ---- per-term cloud type and vertical window (m above zBottom) ---------------------------
    ground = np.maximum(Hl, sea_m)
    base_oro = np.maximum(args.lcl, Hs + 90.0)
    seed_base = np.maximum(np.where(seed_w > 1e-6, seed_alt - 110.0, base_oro), ground + 10.0)
    #            top type, bottom type, base,                                   thickness
    props = {
        'orographic': (0.55, 0.20, base_oro,                                    520.0),
        'peaks':      (0.45, 0.15, np.maximum(Hs + 30.0, Hl - 170.0),           460.0),
        'fog':        (0.14, 0.05, ground - 12.0,                               220.0),
        'marine':     (0.30, 0.15, np.full((Ht, W), args.marine_base, np.float32), 380.0),
        'seed_cloud': (0.60, 0.25, seed_base,                                   480.0),
        'seed_mist':  (0.14, 0.05, ground - 12.0,                               240.0),
    }
    wsum = np.full((Ht, W), 1e-4, np.float32)
    acc = [np.zeros((Ht, W), np.float32) for _ in range(4)]
    defaults = (0.45, 0.15, np.maximum(args.lcl, Hs + 90.0), 500.0)           # where nothing asserts cloud
    for i in range(4):
        acc[i] += 1e-4 * defaults[i]
    for k, (tt, bt, base, thick) in props.items():
        w = comp[k] * (3.0 if k in ('fog', 'seed_mist') else 1.0)      # ground fog keeps its own base where it mixes
        wsum += w
        for i, v in enumerate((tt, bt, base, thick)):
            acc[i] += w * v
    top_type, bottom_type, base_m, thick_m = (a / wsum for a in acc)
    top_type, bottom_type = blur(top_type, px(30.0)), blur(bottom_type, px(30.0))
    base_m = blur(base_m, px(55.0))
    top_m = base_m + blur(thick_m, px(55.0))

    # ---- influence (alpha) --------------------------------------------------------------------
    assert_cloud = sstep(0.04, 0.40, cov) * args.alpha_max
    assert_clear = lee * args.alpha_clear * (1.0 - sat(marine * 0.6))
    alpha = sat(np.maximum(assert_cloud, assert_clear))

    # ---- vertical window ----------------------------------------------------------------------
    sig_mask = alpha > 0.02
    alt0 = math.floor(float(base_m[sig_mask].min()) / 16.0) * 16.0
    alt1 = math.ceil(float(top_m[sig_mask].max()) / 16.0) * 16.0
    span = max(alt1 - alt0, 16.0)
    h_bottom = sat((base_m - alt0) / span)
    h_top = sat((top_m - alt0) / span)

    # ---- write DDS (flip: row 0 = south) ------------------------------------------------------
    modeling = np.stack([cov, top_type, bottom_type, alpha], -1)[::-1]
    height = np.stack([h_bottom, h_top], -1)[::-1]
    write_dds(os.path.join(out_dir, 'Modeling.dds'), mip_chain(modeling), 11)   # R16G16B16A16_UNORM
    write_dds(os.path.join(out_dir, 'Height.dds'), mip_chain(height), 35)       # R16G16_UNORM

    state = {
        "value": {
            "altitude": alt0, "asset": args.asset,
            "center": [round(center_m[0], 3), round(center_m[1], 3)],
            "enabled": True, "feather": args.feather, "heightSpan": span, "heightWeight": 1.0,
            "modelingAlpha": True, "modelingBlend": 0, "modelingWeight": 1.0, "rotation": 0.0,
            "size": [round(size_m[0], 3), round(size_m[1], 3)],
            "strength": 1.0, "worldspace": args.worldspace,
        },
        "weight": 1.0,
    }
    with open(os.path.join(out_dir, 'localcloud_state.json'), 'w', newline='\n') as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write('\n')

    # ---- previews (north-up) ------------------------------------------------------------------
    pv = os.path.join(out_dir, 'preview')
    os.makedirs(pv, exist_ok=True)
    save_gray(os.path.join(pv, 'modeling_R_coverage.png'), cov)
    save_gray(os.path.join(pv, 'modeling_G_top_type.png'), top_type)
    save_gray(os.path.join(pv, 'modeling_B_bottom_type.png'), bottom_type)
    save_gray(os.path.join(pv, 'modeling_A_influence.png'), alpha)
    save_gray(os.path.join(pv, 'height_R_bottom.png'), h_bottom)
    save_gray(os.path.join(pv, 'height_G_top.png'), h_top)
    save_gray(os.path.join(pv, 'effective_coverage_x_alpha.png'), cov * alpha)
    for k, v in comp.items():
        save_gray(os.path.join(pv, 'term_%s.png' % k), v)
    save_gray(os.path.join(pv, 'term_lee.png'), lee)

    # shaded relief
    g_row, g_col = np.gradient(blur(Hc, px(10.0)).astype(np.float64), dx)
    exag = 2.0
    nxv, nyv, nzv = -g_col * exag, g_row * exag, np.ones_like(g_col)          # normal (east, north, up)
    nl = np.sqrt(nxv * nxv + nyv * nyv + nzv * nzv)
    lx, ly, lz = -0.5, 0.5, 0.707                                             # light from the north-west
    shade = sat((nxv * lx + nyv * ly + nzv * lz) / nl).astype(np.float32)
    t = sat((Hc - sea_m) / (float(Hc.max()) - sea_m))[..., None]
    stops = np.array([[0.30, 0.42, 0.26], [0.50, 0.52, 0.32], [0.55, 0.47, 0.36], [0.80, 0.80, 0.80]], np.float32)
    seg = np.clip(t * 3.0, 0, 2.999)
    i0 = seg.astype(int)[..., 0]
    f = seg - i0[..., None]
    tint = stops[i0] * (1 - f) + stops[i0 + 1] * f
    relief = tint * (0.35 + 0.85 * shade[..., None])
    water = np.array([0.16, 0.27, 0.40], np.float32) * (0.85 + 0.15 * sat((H_raw - sea_m + 120) / 120)[..., None])
    relief = relief * (1 - sea[..., None]) + water * sea[..., None]
    save_rgb(os.path.join(pv, 'relief.png'), relief)

    # overlay 1: what the map adds (white, opacity = coverage * influence)
    op = sat(cov * alpha * 1.25)[..., None]
    save_rgb(os.path.join(pv, 'overlay_clouds_on_relief.png'), relief * (1 - op) + op)

    # overlay 2: diagnostic. white = asserted cloud, magenta = asserted clear air, dots = placed statics
    clear_op = (sat(alpha - assert_cloud) * sat(1.0 - cov * 3.0))[..., None] * 0.6
    diag = relief * (1 - clear_op) + np.array([0.85, 0.15, 0.75], np.float32) * clear_op
    diag = diag * (1 - op) + op
    for (c, rr, is_mist) in seed_px:
        ci, ri = int(round(c)), int(round(rr))
        if 1 <= ci < W - 1 and 1 <= ri < Ht - 1:
            diag[ri - 1:ri + 2, ci - 1:ci + 2] = (0.1, 0.9, 1.0) if is_mist else (1.0, 0.55, 0.0)
    # wind arrow (top-left)
    ac, ar = 60.0, 60.0
    for s in np.linspace(-35, 35, 141):
        ci, ri = int(round(ac + te * s)), int(round(ar - tn * s))
        diag[ri - 1:ri + 2, ci - 1:ci + 2] = (1.0, 1.0, 0.0)
    for s in np.linspace(0, 14, 29):
        for sgn in (-1, 1):
            a = math.atan2(tn, te) + sgn * 2.6
            ci = int(round(ac + te * 35 + math.cos(a) * s))
            ri = int(round(ar - tn * 35 - math.sin(a) * s))
            diag[ri - 1:ri + 2, ci - 1:ci + 2] = (1.0, 1.0, 0.0)
    save_rgb(os.path.join(pv, 'overlay_diagnostic.png'), diag)

    # ---- report -------------------------------------------------------------------------------
    def pct(a, m=None):
        v = a if m is None else a[m]
        return ' '.join('%.2f' % q for q in np.percentile(v, [5, 25, 50, 75, 95, 99, 100]))
    landm = sea < 0.5
    rep = [
        'grid %d x %d texels, %.2f m per texel, mips %d' % (W, Ht, dx, len(mip_chain(height[:1, :1])) and int(math.floor(math.log2(max(W, Ht)))) + 1),
        'extent game units x %.0f..%.0f  y %.0f..%.0f' % (x0, x1, y0, y1),
        'center m %.3f, %.3f  size m %.3f x %.3f' % (center_m + size_m),
        'sea level z %.0f = %.1f m; sea fraction %.3f' % (args.sea_level, sea_m, float(sea.mean())),
        'seeds in Tamriel: %d (%d mist), on map: %d' % (len(seeds), sum(s[4] for s in seeds), len(seed_px)),
        'rain shadow iterations %d' % n_iter,
        'advected upslope percentiles (land): %s' % pct(adv, landm),
        'altitude window %.0f .. %.0f m (heightSpan %.0f)' % (alt0, alt1, span),
        'coverage percentiles 5/25/50/75/95/99/100  all: %s' % pct(cov),
        '                                          land: %s' % pct(cov, landm),
        'alpha percentiles                          all: %s' % pct(alpha),
        'coverage*alpha                             all: %s' % pct(cov * alpha),
        'fraction cov>0.5: %.3f  cov>0.8: %.3f  alpha>0.5: %.3f' % (float((cov > 0.5).mean()), float((cov > 0.8).mean()), float((alpha > 0.5).mean())),
        'term means: ' + ', '.join('%s %.3f' % (k, float(v.mean())) for k, v in comp.items()) + ', lee %.3f' % float(lee.mean()),
    ]

    def probe(name, gx, gy):
        c = int((gx - x0) / (x1 - x0) * W)
        rr = int((y1 - gy) / (y1 - y0) * Ht)
        rep.append('  %-12s terrain %4.0f m  cov %.2f  alpha %.2f  lee %.2f  base %4.0f  top %4.0f  type %.2f' % (
            name, Hl[rr, c], cov[rr, c], alpha[rr, c], lee[rr, c], base_m[rr, c], top_m[rr, c], top_type[rr, c]))
    for name, (gx, gy) in dict(whiterun=(20000, -5000), throat=(54528, -52352), morthal=(-40000, 62000),
                               riften=(172000, -95000), solitude=(-67000, 104000), markarth=(-175000, 5000),
                               windhelm=(134000, 35000), falkreath=(-30000, -87000), sea_north=(0, 180000)).items():
        probe(name, gx, gy)
    txt = '\n'.join(rep)
    print(txt)
    with open(os.path.join(out_dir, 'build_report.txt'), 'w', newline='\n') as f:
        f.write('options: ' + json.dumps(vars(args), sort_keys=True) + '\n' + txt + '\n')


# ----------------------------------------------------------------------------- pass 2: collared banks
# The cloud field has ONE slab (bottom/top) per column and the local map moves that slab by alpha (NOTES Pass 2).
# A low bank under a high global layer therefore needs, going outwards from the bank:
#   core     alpha 1, coverage > 0, heights = bank
#   skirt    alpha 1, coverage 0,   heights = bank            (>= 2 atlas texels, so filtering never mixes cloud into the ramp)
#   ramp     alpha 1, coverage 0,   heights bank -> global    (invisible: nothing to draw)
#   plateau  alpha 1, coverage 0,   heights = global          (>= 2 atlas texels + optional shear margin)
#   fade     alpha 1 -> 0, coverage 0, heights = global       (global clouds fade back in at their own altitude)
def bank_fields(xm, ym, banks, noise=None):
    """xm, ym: metre coordinate grids (east, north). banks: dicts with x, y, r_major, r_minor, angle (rad, major axis
    from east towards north), bottom, top, cov, top_type, bottom_type. Returns coverage, types, bank bottom/top
    (extended outwards) and d = approximate distance (m) outside the nearest bank outline (0 inside)."""
    shape = xm.shape
    keep = np.ones(shape, np.float64)
    tt = np.zeros(shape, np.float64)
    bt = np.zeros(shape, np.float64)
    cw = np.full(shape, 1e-9)
    hb = np.zeros(shape, np.float64)
    ht = np.zeros(shape, np.float64)
    hw = np.zeros(shape, np.float64)
    d = np.full(shape, 1e9)
    for b in banks:
        ca, sa = math.cos(b['angle']), math.sin(b['angle'])
        u = ((xm - b['x']) * ca + (ym - b['y']) * sa) / b['r_major']
        v = (-(xm - b['x']) * sa + (ym - b['y']) * ca) / b['r_minor']
        rho = np.sqrt(u * u + v * v)
        if noise is not None:
            rho = rho * (1.0 + 0.5 * (noise - 0.5))                      # irregular outline
        c = b['cov'] * sstep(0.0, 1.0, (1.0 - rho) / b.get('edge', 0.6))
        keep *= 1.0 - c
        tt += c * b['top_type']
        bt += c * b['bottom_type']
        cw += c
        di = np.maximum(rho - 1.0, 0.0) * b['r_minor']                   # under-estimates along the major axis (safe side)
        d = np.minimum(d, di)
        w = 1.0 / (40.0 + di) ** 4
        hb += w * b['bottom']
        ht += w * b['top']
        hw += w
    cov = 1.0 - keep
    return (cov.astype(np.float32), (tt / cw).astype(np.float32), (bt / cw).astype(np.float32),
            (hb / hw).astype(np.float32), (ht / hw).astype(np.float32), d.astype(np.float32))


def collar(args, cov, top_type, bottom_type, bank_b, bank_t, d):
    """Apply the skirt / ramp / plateau / fade zones. Returns modeling (h, w, 4), bottom_m, top_m, zone widths."""
    t = args.atlas_texel
    skirt, ramp, plateau, fade = 2.0 * t, 2.0 * t, 2.0 * t + args.shear_margin, 4.0 * t
    g_b = args.global_base
    g_t = args.global_base + args.global_top_frac * args.global_thickness
    k = sstep(skirt, skirt + ramp, d)
    bottom = bank_b * (1.0 - k) + g_b * k
    top = bank_t * (1.0 - k) + g_t * k
    alpha = 1.0 - sstep(skirt + ramp + plateau, skirt + ramp + plateau + fade, d)
    on = sstep(0.0, 0.08, cov)                                           # types go to 0 outside banks (safe under Maximum)
    modeling = np.stack([cov, top_type * on, bottom_type * on, alpha], -1).astype(np.float32)
    return modeling, bottom.astype(np.float32), top.astype(np.float32), (skirt, ramp, plateau, fade)


def relief_image(Hc, H_raw, sea, sea_m, dx):
    g_row, g_col = np.gradient(blur(Hc, 10.0 / dx).astype(np.float64), dx)
    nxv, nyv, nzv = -g_col * 2.0, g_row * 2.0, np.ones_like(g_col)
    nl = np.sqrt(nxv * nxv + nyv * nyv + nzv * nzv)
    shade = sat((nxv * -0.5 + nyv * 0.5 + nzv * 0.707) / nl).astype(np.float32)
    t = sat((Hc - sea_m) / (float(Hc.max()) - sea_m))[..., None]
    stops = np.array([[0.30, 0.42, 0.26], [0.50, 0.52, 0.32], [0.55, 0.47, 0.36], [0.80, 0.80, 0.80]], np.float32)
    seg = np.clip(t * 3.0, 0, 2.999)
    i0 = seg.astype(int)[..., 0]
    f = seg - i0[..., None]
    relief = (stops[i0] * (1 - f) + stops[i0 + 1] * f) * (0.35 + 0.85 * shade[..., None])
    water = np.array([0.16, 0.27, 0.40], np.float32) * (0.85 + 0.15 * sat((H_raw - sea_m + 120) / 120)[..., None])
    return relief * (1 - sea[..., None]) + water * sea[..., None]


def write_pass2(args, out_dir, center_m, size_m, modeling, bottom, top, zones, report, relief=None, height_weight=1.0,
                dots=None):
    """modeling / bottom / top are NORTH-UP. Writes DDS (flipped), state JSON, previews, report."""
    os.makedirs(out_dir, exist_ok=True)
    cov, alpha = modeling[..., 0], modeling[..., 3]
    g_b = args.global_base
    g_t = args.global_base + args.global_top_frac * args.global_thickness
    alt0 = math.floor(min(float(bottom.min()), g_b) / 16.0) * 16.0
    alt1 = math.ceil(max(float(top.max()), g_t) / 16.0) * 16.0
    span = max(alt1 - alt0, 16.0)
    height = np.stack([sat((bottom - alt0) / span), sat((top - alt0) / span)], -1)
    write_dds(os.path.join(out_dir, 'Modeling.dds'), mip_chain(modeling[::-1]), 11)
    write_dds(os.path.join(out_dir, 'Height.dds'), mip_chain(height[::-1]), 35)
    state = {
        "value": {
            "altitude": alt0, "asset": args.asset,
            "center": [round(center_m[0], 3), round(center_m[1], 3)],
            "enabled": True, "feather": 0.0, "heightSpan": span, "heightWeight": height_weight,
            "modelingAlpha": True, "modelingBlend": 0, "modelingWeight": 1.0, "rotation": 0.0,
            "size": [round(size_m[0], 3), round(size_m[1], 3)],
            "strength": 1.0, "worldspace": args.worldspace,
        },
        "weight": 1.0,
    }
    with open(os.path.join(out_dir, 'localcloud_state.json'), 'w', newline='\n') as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write('\n')
    pv = os.path.join(out_dir, 'preview')
    os.makedirs(pv, exist_ok=True)
    save_gray(os.path.join(pv, 'modeling_R_coverage.png'), cov)
    save_gray(os.path.join(pv, 'modeling_G_top_type.png'), modeling[..., 1])
    save_gray(os.path.join(pv, 'modeling_B_bottom_type.png'), modeling[..., 2])
    save_gray(os.path.join(pv, 'modeling_A_influence.png'), alpha)
    save_gray(os.path.join(pv, 'height_R_bottom.png'), height[..., 0])
    save_gray(os.path.join(pv, 'height_G_top.png'), height[..., 1])
    # zones: red = cloud, green = alpha (cleared global sky), blue = slab still below the global base
    low = sat((g_b - bottom) / max(g_b - float(bottom.min()), 1.0)) * alpha
    save_rgb(os.path.join(pv, 'zones_cloud_hole_lowslab.png'), np.stack([sat(cov * 1.5), alpha * 0.6, low], -1))
    if relief is not None:
        hole = (alpha * (1.0 - sat(cov * 4.0)))[..., None] * 0.45
        img = relief * (1 - hole) + np.array([0.85, 0.15, 0.75], np.float32) * hole
        op = sat(cov * 1.5)[..., None]
        img = img * (1 - op) + op
        for (c, r, col) in (dots or []):
            ci, ri = int(round(c)), int(round(r))
            if 1 <= ci < img.shape[1] - 1 and 1 <= ri < img.shape[0] - 1:
                img[ri - 1:ri + 2, ci - 1:ci + 2] = col
        save_rgb(os.path.join(pv, 'overlay_banks_on_relief.png'), img)
    # self-check with the shader's blend: the slab the engine will use, and where a tilted slab still carries coverage
    dxm = size_m[0] / modeling.shape[1]
    w = alpha * height_weight
    sb = g_b * (1 - w) + bottom * w
    gy_, gx_ = np.gradient(sb.astype(np.float64), dxm)
    slope = np.hypot(gx_, gy_)
    carried = np.maximum(cov * alpha, 0.65 * (1.0 - alpha))              # local coverage, or worst-case global coverage
    bad = (slope > 1.0) & (carried > 0.01)
    report = list(report) + [
        'grid %d x %d, %.2f m per texel; center m %.3f, %.3f; size m %.3f x %.3f' % (
            modeling.shape[1], modeling.shape[0], dxm, center_m[0], center_m[1], size_m[0], size_m[1]),
        'zones (m) skirt %.0f ramp %.0f plateau %.0f fade %.0f; designed for localTexelSize <= %.0f' % (
            tuple(zones) + (zones[0] / 2.0,)),
        'global slab assumed %.0f .. %.0f m; window altitude %.0f heightSpan %.0f' % (g_b, g_t, alt0, span),
        'area fractions: cloud (cov > 0.02) %.4f, cleared or dimmed global sky (alpha > 0.02) %.4f, alpha == 1 %.4f' % (
            float((cov > 0.02).mean()), float((alpha > 0.02).mean()), float((alpha > 0.999).mean())),
        'self-check: texels where the blended slab is steeper than 1.0 m/m AND can carry coverage: %d (max slope there %.2f)' % (
            int(bad.sum()), float(slope[bad].max()) if bad.any() else 0.0),
        'state json: ' + json.dumps(state, sort_keys=True),
    ]
    txt = '\n'.join(report)
    print(txt)
    with open(os.path.join(out_dir, 'build_report.txt'), 'w', newline='\n') as f:
        f.write('options: ' + json.dumps(vars(args), sort_keys=True) + '\n' + txt + '\n')


def write_separate(args, out_dir, center_m, size_m, shape, bottom, top, ground, report, relief, dots):
    """Asset for the 'Separate layer' blend mode (modelingBlend 2). All inputs NORTH-UP.
    The engine draws a second slab: coverage = R * A * strength * modelingWeight, types = G / B (taken un-weighted),
    bottom/top from Height.dds wherever A > 0. The global slab is not touched, so there are no zones and no collar:
    R, G, B are constant (the bank's peak coverage and types), A carries the whole soft bank outline, and the
    heights are one smooth field (inverse-distance mix of the per-bank bottom/top)."""
    os.makedirs(out_dir, exist_ok=True)
    dxm = size_m[0] / shape.shape[1]
    alpha = shape.astype(np.float32)
    bottom = blur(bottom, 24.0 / dxm).astype(np.float32)
    top = np.maximum(blur(top, 24.0 / dxm), bottom + 60.0).astype(np.float32)
    used = alpha > 0.004
    alt0 = math.floor(float(bottom[used].min()) / 16.0) * 16.0
    alt1 = math.ceil(float(top[used].max()) / 16.0) * 16.0
    span = max(alt1 - alt0, 16.0)
    ones = np.ones_like(alpha)
    modeling = np.stack([ones * args.bank_coverage, ones * args.bank_type, ones * 0.1, alpha], -1).astype(np.float32)
    height = np.stack([sat((bottom - alt0) / span), sat((top - alt0) / span)], -1)
    write_dds(os.path.join(out_dir, 'Modeling.dds'), mip_chain(modeling[::-1]), 11)
    write_dds(os.path.join(out_dir, 'Height.dds'), mip_chain(height[::-1]), 35)
    state = {
        "value": {
            "altitude": alt0, "asset": args.asset,
            "center": [round(center_m[0], 3), round(center_m[1], 3)],
            "enabled": True, "feather": 0.0, "flatAltitude": True, "heightSpan": span, "heightWeight": 1.0,
            "modelingAlpha": True, "modelingBlend": 2, "modelingWeight": 1.0, "rotation": 0.0,
            "size": [round(size_m[0], 3), round(size_m[1], 3)],
            "strength": 1.0, "worldspace": args.worldspace,
        },
        "weight": 1.0,
    }
    with open(os.path.join(out_dir, 'localcloud_state.json'), 'w', newline='\n') as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write('\n')
    eff = alpha * args.bank_coverage
    pv = os.path.join(out_dir, 'preview')
    os.makedirs(pv, exist_ok=True)
    save_gray(os.path.join(pv, 'modeling_A_bank_outline.png'), alpha)
    save_gray(os.path.join(pv, 'effective_coverage_R_x_A.png'), eff)
    save_gray(os.path.join(pv, 'height_R_bottom.png'), height[..., 0])
    save_gray(os.path.join(pv, 'height_G_top.png'), height[..., 1])
    # red = bank top above the ground, green = outline, blue = bank bottom below the ground (bank touches terrain)
    save_rgb(os.path.join(pv, 'bank_vs_ground.png'), np.stack([
        sat((top - ground) / 250.0) * sat(alpha * 3.0), alpha, sat((ground - bottom) / 150.0) * sat(alpha * 3.0)], -1))
    op = sat(eff * 1.8)[..., None]
    img = relief * (1 - op) + op
    for (c, r, col) in (dots or []):
        ci, ri = int(round(c)), int(round(r))
        if 1 <= ci < img.shape[1] - 1 and 1 <= ri < img.shape[0] - 1:
            img[ri - 1:ri + 2, ci - 1:ci + 2] = col
    save_rgb(os.path.join(pv, 'overlay_banks_on_relief.png'), img)
    core = alpha > 0.5
    gy_, gx_ = np.gradient(bottom.astype(np.float64), dxm)
    hslope = np.hypot(gx_, gy_)[used]
    ay_, ax_ = np.gradient(alpha.astype(np.float64), dxm)
    aslope = np.hypot(ax_, ay_)
    report = list(report) + [
        'grid %d x %d, %.2f m per texel; center m %.3f, %.3f; size m %.3f x %.3f' % (
            shape.shape[1], shape.shape[0], dxm, center_m[0], center_m[1], size_m[0], size_m[1]),
        'window altitude %.0f heightSpan %.0f (bank bottoms %.0f .. %.0f, tops %.0f .. %.0f m above zBottom)' % (
            alt0, span, float(bottom[used].min()), float(bottom[used].max()), float(top[used].min()), float(top[used].max())),
        'modeling R %.2f G %.2f B 0.10 constant; A = soft outline. area: A > 0.02 %.4f, A > 0.5 %.4f of the map' % (
            args.bank_coverage, args.bank_type, float((alpha > 0.02).mean()), float(core.mean())),
        'inside A > 0.5: thickness median %.0f m, top above ground median %.0f m, bottom below ground median %.0f m' % (
            float(np.median((top - bottom)[core])), float(np.median((top - ground)[core])),
            float(np.median((ground - bottom)[core]))),
        'smoothness: height slope inside banks median %.3f max %.3f m/m; narrowest full alpha ramp %.0f m '
        '(>= 2 atlas texels needs localTexelSize <= %.0f m)' % (
            float(np.median(hslope)), float(hslope.max()), 1.0 / max(float(aslope.max()), 1e-6),
            0.5 / max(float(aslope.max()), 1e-6)),
        'state json: ' + json.dumps(state, sort_keys=True),
    ]
    txt = '\n'.join(report)
    print(txt)
    with open(os.path.join(out_dir, 'build_report.txt'), 'w', newline='\n') as f:
        f.write('options: ' + json.dumps(vars(args), sort_keys=True) + '\n' + txt + '\n')


def build_pass2(args):
    out_dir = os.path.join(args.out, args.asset)
    z, (min_cx, min_cy, max_cx, max_cy) = load_heightmap(args.heightmap)
    x0, x1 = min_cx * CELL, (max_cx + 1) * CELL
    y0, y1 = min_cy * CELL, (max_cy + 1) * CELL
    full_size = ((x1 - x0) * GU2M, (y1 - y0) * GU2M)
    full_center = ((x0 + x1) * 0.5 * GU2M, (y0 + y1) * 0.5 * GU2M)
    sea_m = (args.sea_level - args.z_bottom) * GU2M

    def grid(center, size, w, h):
        xs = center[0] - size[0] * 0.5 + (np.arange(w) + 0.5) * (size[0] / w)
        ys = center[1] + size[1] * 0.5 - (np.arange(h) + 0.5) * (size[1] / h)      # north-up
        return np.meshgrid(xs, ys)

    if args.mode == 'diag-flat-clear':
        # alpha 1, coverage 0 over the whole province. heightWeight 0: heights untouched, trace range not widened.
        m = np.zeros((64, 64, 4), np.float32)
        m[..., 3] = 1.0
        g_t = args.global_base + args.global_top_frac * args.global_thickness
        flat = np.ones((64, 64), np.float32)
        write_pass2(args, out_dir, full_center, full_size, m, flat * args.global_base, flat * g_t, (0.0, 0.0, 0.0, 0.0),
                    ['diag-flat-clear: A = 1, RGB = 0 everywhere; state heightWeight 0, feather 0'], height_weight=0.0)
        return

    if args.mode in ('diag-one-blob', 'diag-two-heights'):
        cx, cy = 0.0, -10000.0 * GU2M                                    # Whiterun plain, world game units (0, -10000)
        size = (3840.0, 3840.0)
        xm, ym = grid((cx, cy), size, 512, 512)
        common = dict(angle=0.0, cov=0.8, top_type=1.0, bottom_type=0.0, edge=0.35)
        if args.mode == 'diag-one-blob':
            banks = [dict(x=cx, y=cy, r_major=600.0, r_minor=600.0, bottom=400.0, top=700.0, **common)]
        else:
            banks = [dict(x=cx - 500.0, y=cy, r_major=350.0, r_minor=350.0, bottom=300.0, top=500.0, **common),
                     dict(x=cx + 400.0, y=cy, r_major=350.0, r_minor=350.0, bottom=600.0, top=900.0, **common)]
        cov, tt, bt, bb, btop, d = bank_fields(xm, ym, banks)
        args.atlas_texel = 32.0                                          # diagnostics must work at the default texel size
        modeling, bottom, top, zones = collar(args, cov, tt, bt, bb, btop, d)
        rep = ['%s: bank x %.1f y %.1f m (game units %.0f, %.0f) radius %.0f m, bottom %.0f top %.0f, coverage %.2f, type %.1f' % (
            args.mode, b['x'], b['y'], b['x'] / GU2M, b['y'] / GU2M, b['r_major'], b['bottom'], b['top'], b['cov'], b['top_type'])
            for b in banks]
        write_pass2(args, out_dir, (cx, cy), size, modeling, bottom, top, zones, rep)
        return

    # ---- mist: a few banks picked from the placed statics by terrain ---------------------------
    sep = args.mode == 'mist-separate'
    W = args.width
    Ht = int(round(W * (y1 - y0) / (x1 - x0)))
    H_raw = area_resize((z - args.z_bottom) * GU2M, W, Ht)
    sea = area_resize((z < args.sea_level).astype(np.float32), W, Ht)
    Hc = np.maximum(H_raw, sea_m)
    dx = full_size[0] / W
    px = lambda metres: metres / dx
    xm, ym = grid(full_center, full_size, W, Ht)
    Hl, Hs, Hb = blur(Hc, px(35.0)), blur(Hc, px(260.0)), blur(Hc, px(200.0))
    Hf = blur(Hc, px(70.0)).astype(np.float64)
    g_row, g_col = np.gradient(Hf, dx)                                   # d/d(south), d/d(east)
    gE, gN = g_col, -g_row
    slope = np.hypot(gE, gN)
    b_row, b_col = np.gradient(blur(Hc, px(150.0)).astype(np.float64), dx)
    slope_big = np.hypot(b_col, b_row)
    hEE = np.gradient(gE, dx, axis=1)                                    # Hessian of the 70 m terrain in (east, north)
    hNN = -np.gradient(gN, dx, axis=0)
    hEN = np.gradient(gN, dx, axis=1)
    tr, det = hEE + hNN, hEE * hNN - hEN * hEN
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l_lo, l_hi = tr / 2.0 - disc, tr / 2.0 + disc                        # curvatures, l_lo <= l_hi
    prom = Hl - Hs
    score = {
        # foot of a big face: steep at the 150 m scale, locally concave and not itself steep
        'face': sat((slope_big - 0.22) / 0.30) * sat((Hb - Hl + 15.0) / 40.0) * sat((0.60 - slope) / 0.3),
        # crest line: stands above the 260 m mean and is sharply convex across
        'ridge': sat((prom - 40.0) / 110.0) * sat(-l_lo / 0.004),
        # pass: curvatures of opposite sign, on high ground
        'saddle': sat(np.sqrt(np.maximum(-l_lo * l_hi, 0.0)) / 0.003) * sat((prom + 30.0) / 60.0) * (l_hi > 0),
    }
    ok_ground = (sstep(215.0, 260.0, Hl) * (1.0 - sstep(640.0, 720.0, Hl)) * (sea < 0.05)).astype(np.float32)

    def at(a, c, r):
        return float(a[min(max(int(round(r)), 0), Ht - 1), min(max(int(round(c)), 0), W - 1)])

    def direction_of(c, r, lam_field):
        """Unit eigenvector (east, north) of the terrain Hessian for the given eigenvalue field."""
        a, b_, d_ = at(hEE, c, r), at(hEN, c, r), at(hNN, c, r)
        lam = at(lam_field, c, r)
        v = (b_, lam - a) if abs(b_) > 1e-12 else ((1.0, 0.0) if abs(a - lam) < abs(d_ - lam) else (0.0, 1.0))
        n = math.hypot(*v) or 1.0
        return v[0] / n, v[1] / n

    cands = {k: [] for k in score}
    n_seeds = 0
    for (sx, sy, sz, sc, is_mist) in load_seeds(args.plugin):
        c = (sx - x0) / (x1 - x0) * W - 0.5
        r = (y1 - sy) / (y1 - y0) * Ht - 0.5
        # stay inside the playable part of the province
        if not (-195000.0 <= sx <= 195000.0 and -145000.0 <= sy <= 125000.0):
            continue
        n_seeds += 1
        for k in score:
            s = at(score[k], c, r) * at(ok_ground, c, r)
            if s > 0.15:
                cands[k].append((s, sx, sy, sc, k, c, r))
    # terrain-only candidates (no placed static there) on a coarse lattice, at a discount, so that face bases,
    # which the sky statics rarely mark, are represented
    for r in range(6, Ht - 6, 6):
        for c in range(6, W - 6, 6):
            sx = x0 + (c + 0.5) / W * (x1 - x0)
            sy = y1 - (r + 0.5) / Ht * (y1 - y0)
            if not (-195000.0 <= sx <= 195000.0 and -145000.0 <= sy <= 125000.0):
                continue
            for k in score:
                s = 0.6 * at(score[k], c, r) * at(ok_ground, c, r)
                if s > 0.2:
                    cands[k].append((s, sx, sy, 3.0, k, float(c), float(r)))
    for k in cands:
        cands[k].sort(key=lambda t: (-t[0], t[1], t[2]))
    quota = {'face': int(round(args.banks * 0.45)), 'ridge': int(round(args.banks * 0.33))}
    quota['saddle'] = args.banks - quota['face'] - quota['ridge']
    picked = []
    # the Throat of the World: a ring of banks on its flanks where the ground is near 560 m
    tcx, tcy = 54528.0 * GU2M, -52352.0 * GU2M
    for k in range(5):
        az = math.radians(20.0 + 72.0 * k)
        best_p, best_err = None, 1e9
        for rad in range(240, 620, 20):
            xx, yy = tcx + rad * math.sin(az), tcy + rad * math.cos(az)
            c = (xx - (full_center[0] - full_size[0] / 2)) / dx - 0.5
            r = ((full_center[1] + full_size[1] / 2) - yy) / (full_size[1] / Ht) - 0.5
            err = abs(at(Hl, c, r) - 560.0)
            if err < best_err:
                best_p, best_err = (xx, yy, c, r), err
        picked.append((1.0, best_p[0] / GU2M, best_p[1] / GU2M, 3.0, 'throat', best_p[2], best_p[3]))
    if sep:
        # a second, higher ring just under the summit (ground near 680 m), between the azimuths of the first
        for k in range(3):
            az = math.radians(80.0 + 120.0 * k)
            best_p, best_err = None, 1e9
            for rad in range(60, 400, 20):
                xx, yy = tcx + rad * math.sin(az), tcy + rad * math.cos(az)
                c = (xx - (full_center[0] - full_size[0] / 2)) / dx - 0.5
                r = ((full_center[1] + full_size[1] / 2) - yy) / (full_size[1] / Ht) - 0.5
                err = abs(at(Hl, c, r) - 680.0)
                if err < best_err:
                    best_p, best_err = (xx, yy, c, r), err
            picked.append((1.0, best_p[0] / GU2M, best_p[1] / GU2M, 3.0, 'throat', best_p[2], best_p[3]))
    progress = True
    while progress:                                                      # round-robin over the classes, best score first
        progress = False
        for kind in ('face', 'ridge', 'saddle'):
            while quota[kind] > 0 and cands[kind]:
                cand = cands[kind].pop(0)
                if all(math.hypot(cand[1] - p[1], cand[2] - p[2]) * GU2M >= args.bank_spacing for p in picked):
                    picked.append(cand)
                    quota[kind] -= 1
                    progress = True
                    break
    banks, dots, rep = [], [], []
    colors = {'face': (1.0, 0.55, 0.0), 'ridge': (0.1, 0.9, 1.0), 'saddle': (1.0, 1.0, 0.0), 'throat': (1.0, 0.2, 0.2)}
    for (s, sx, sy, sc, kind, c, r) in picked:
        ground = at(Hl, c, r)
        f = min(max(sc, 1.0), 6.0) / 6.0                                 # placed scale -> size factor
        ge, gn_ = at(gE, c, r), at(gN, c, r)
        contour = math.atan2(ge, -gn_)                                   # along the contour line (perpendicular to the gradient)
        if kind == 'face':
            base, thick, rma, rmi, ang = ground + 15.0, 150.0 + 60.0 * s, 130.0 + 70.0 * f, 60.0 + 30.0 * f, contour
        elif kind == 'ridge':
            e = direction_of(c, r, l_hi)                                 # along the crest (least negative curvature)
            base, thick, rma, rmi, ang = ground - 90.0, 170.0, 150.0 + 60.0 * f, 55.0 + 25.0 * f, math.atan2(e[1], e[0])
        elif kind == 'saddle':
            e = direction_of(c, r, l_lo)                                 # through the pass
            base, thick, rma, rmi, ang = ground - 40.0, 140.0, 120.0 + 50.0 * f, 60.0 + 25.0 * f, math.atan2(e[1], e[0])
        else:
            base, thick, rma, rmi, ang = ground - 60.0, 180.0, 170.0, 80.0, contour
        if sep:
            # Separate layer: nothing is blended into the global slab, so banks may be larger and fully feathered.
            # Bottom a little under the smoothed ground at the centre (the flanks fall away below it), top 120..210 m
            # above it; the top type decides how much of that is filled.
            if kind == 'face':
                under, over = 35.0, 150.0 + 60.0 * s
            elif kind == 'ridge':
                under, over = 45.0, 120.0
            elif kind == 'saddle':
                under, over = 30.0, 130.0
            else:
                under, over = 50.0, 150.0
            rma, rmi = rma * 1.5, rmi * 1.6
            base = min(max(ground - under, 200.0), 760.0)
            top = min(max(ground + over, base + 120.0), 900.0)
            banks.append(dict(x=sx * GU2M, y=sy * GU2M, r_major=rma, r_minor=rmi, angle=ang, bottom=base, top=top,
                              cov=1.0, top_type=args.bank_type, bottom_type=0.1, edge=1.0))
        else:
            base = min(max(base, 250.0), 600.0)
            top = min(base + thick, 900.0)
            banks.append(dict(x=sx * GU2M, y=sy * GU2M, r_major=rma, r_minor=rmi, angle=ang, bottom=base, top=top,
                              cov=args.bank_coverage, top_type=args.bank_type, bottom_type=0.1))
        dots.append((c, r, colors[kind]))
        rep.append('  %-6s game units %8.0f %8.0f  ground %4.0f m  bottom %4.0f top %4.0f  radii %3.0f x %3.0f m  score %.2f' % (
            kind, sx, sy, ground, base, top, rma, rmi, s))
    nz = noise_field((Ht, W), dx, (140.0, 60.0), args.noise_seed)
    cov, tt, bt, bb, btop, d = bank_fields(xm, ym, banks, nz)
    if sep:
        head = ['mist-separate: %d placed statics inside the playable box, %d banks written (%s)' % (
            n_seeds, len(banks), ', '.join('%s %d' % (k, sum(1 for p in picked if p[4] == k)) for k in colors))]
        write_separate(args, out_dir, full_center, full_size, cov, bb, btop, Hc, head + rep,
                       relief_image(Hc, H_raw, sea, sea_m, dx), dots)
        return
    modeling, bottom, top, zones = collar(args, cov, tt, bt, bb, btop, d)
    head = ['mist: %d placed statics inside the playable box, %d banks written (%s)' % (
        n_seeds, len(banks), ', '.join('%s %d' % (k, sum(1 for p in picked if p[4] == k)) for k in colors))]
    write_pass2(args, out_dir, full_center, full_size, modeling, bottom, top, zones, head + rep,
                relief=relief_image(Hc, H_raw, sea, sea_m, dx), dots=dots)


if __name__ == '__main__':
    main()

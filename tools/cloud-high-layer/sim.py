"""Offline approximation of the Physical Sky cirrus shell (CirrusDensity, Volumetrics.cs.hlsl:956).

Reimplements NdfNoise.cs.hlsl (Perlin / Perlin-Worley; hash differs, statistics match), CirrusGenerate.cs.hlsl
and the density formula, then renders (a) a top-down opacity map and (b) a pinhole sky view.
Lighting is NOT simulated: white cloud alpha over a flat blue sky. Use for pattern/scale/coverage judgement only.

usage: python sim.py            -> writes sim_<variant>.jpg for every variant in VARIANTS
"""
import numpy as np
from PIL import Image
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
N = 512
PAT = np.asarray(Image.open(r'C:/Users/foxnn/dev/skyrim-community-shaders/features/Physical Sky/Textures/PhysicalSky/cirrus.dds').convert('RGB')).astype(np.float32) / 255.0


def perlin(uv, period, rng_seed):
    rng = np.random.default_rng(rng_seed * 7919 + period)
    ang = rng.random((period, period)) * 2 * np.pi
    p = (uv % 1.0) * period
    c = np.floor(p).astype(int)
    f = p - c
    w = f * f * f * (f * (f * 6 - 15) + 10)

    def g(dx, dy):
        a = ang[(c[..., 1] + dy) % period, (c[..., 0] + dx) % period]
        return np.cos(a) * (f[..., 0] - dx) + np.sin(a) * (f[..., 1] - dy)
    x0 = g(0, 0) * (1 - w[..., 0]) + g(1, 0) * w[..., 0]
    x1 = g(0, 1) * (1 - w[..., 0]) + g(1, 1) * w[..., 0]
    return x0 * (1 - w[..., 1]) + x1 * w[..., 1]


def worley(uv, period, rng_seed):
    rng = np.random.default_rng(rng_seed * 104729 + period)
    pts = rng.random((period, period, 3))
    p = (uv % 1.0) * period
    c = np.floor(p).astype(int)
    f = p - c
    best = np.full(uv.shape[:2], 2.0)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            q = pts[(c[..., 1] + dy) % period, (c[..., 0] + dx) % period]
            d = np.sqrt((dx + q[..., 0] - f[..., 0]) ** 2 + (dy + q[..., 1] - f[..., 1]) ** 2 + (q[..., 2] - 0.5) ** 2)
            best = np.minimum(best, d)
    return 1 - np.clip(best, 0, 1)


def noise_slot(type=1, seed=1337, frequency=16, octaves=4, persistence=0.5, lacunarity=2, contrast=1.0, bias=0.0,
               repetitions=1, responseExponent=1.0):
    ys, xs = np.mgrid[0:N, 0:N]
    uv = np.stack([(xs + 0.5) / N, (ys + 0.5) / N], -1) * repetitions
    s = 0.0; wgt = 1.0; norm = 0.0; period = frequency
    for _ in range(octaves):
        if period > N // (2 * repetitions):
            break
        pv = np.clip(0.5 + perlin(uv, period, seed), 0, 1)
        v = pv if type == 1 else (lambda cell: cell + (1 - cell) * pv)(worley(uv, period, seed))
        s = s + v * wgt; norm += wgt; period *= lacunarity; wgt *= persistence
    v = (s / max(norm, 1e-5) - 0.5) * contrast + 0.5
    v = np.clip(v, 0, 1)
    if responseExponent != 1.0:
        v = v ** responseExponent
    return np.clip(v + bias, 0, 1).astype(np.float32)


# defaults from Ndf.h:118-121 (slot 0 is Alligator noise - not reimplemented, approximated by Perlin freq 4)
SLOTS = [
    noise_slot(type=1, frequency=4, octaves=4, persistence=0.5),
    noise_slot(type=1, frequency=4, octaves=6, persistence=0.6, contrast=1.6, bias=-0.02, repetitions=2, responseExponent=1.8),
    noise_slot(type=1, frequency=32),
    noise_slot(type=2, frequency=12, contrast=1.1, bias=-0.05, responseExponent=2.0),
]


def bilinear(tex, u, v):
    h, w = tex.shape[:2]
    x = (u % 1.0) * w - 0.5; y = (v % 1.0) * h - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None] if tex.ndim == 3 else (x - x0); fy = (y - y0)[..., None] if tex.ndim == 3 else (y - y0)
    a = tex[y0 % h, x0 % w]; b = tex[y0 % h, (x0 + 1) % w]; c = tex[(y0 + 1) % h, x0 % w]; d = tex[(y0 + 1) % h, (x0 + 1) % w]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def weather_map(layers):
    ys, xs = np.mgrid[0:N, 0:N]
    u = (xs + 0.5) / N; v = (ys + 0.5) / N
    out = []
    for L in layers:
        slot = L.get('noise', 2); fr = L.get('frequency', 1.0); off = L.get('offset', [0, 0]); r = L.get('range', [-1, 1, 0, 1])
        val = np.zeros((N, N), np.float32) if slot >= 4 else bilinear(SLOTS[slot], (u + off[0]) * fr, (v + off[1]) * fr)
        val = val * 2 - 1
        out.append(np.clip((val - r[0]) / (r[1] - r[0]), 0, 1) * (r[3] - r[2]) + r[2])
    return np.stack(out, -1).astype(np.float32)


def density(x, y, wm, uv_size=1.0, density_scale=1.0, shader=None):
    """x, y in metres. Returns view optical depth (density*10)."""
    w = np.clip(bilinear(wm, x / 16384.0 / uv_size + 0.5, y / 16384.0 / uv_size + 0.5), 0, 1)
    if shader:
        pat, cov_mul = shader(x, y, uv_size)
    else:
        pat = bilinear(PAT, x * 0.0002331 / uv_size, y * 0.0002331 / uv_size); cov_mul = 1.0
    sq = pat * pat
    t = w[..., 1]; cov = np.clip(w[..., 0] * cov_mul, 0, 1)
    a = np.clip(t * 2, 0, 1); b = np.clip(t * 2 - 1, 0, 1)
    prof = (sq[..., 2] * (1 - a) + sq[..., 0] * a) * (1 - b) + sq[..., 1] * b
    prof = np.maximum(prof, 1e-10) ** (1.9 - cov * 1.8) * np.clip(cov ** 3 * 2, 0, 1)
    return prof * 2 * density_scale * 10


def render(name, layers, uv_size=1.0, density_scale=1.0, altitude=8000.0, shader=None, R=74946.0):
    wm = weather_map(layers)
    # top-down 32 km square, 800 px
    g = (np.arange(800) + 0.5) / 800 * 32768 - 16384
    X, Y = np.meshgrid(g, g)
    top = 1 - np.exp(-density(X, Y, wm, uv_size, density_scale, shader))
    # sky view: looking west (-X), pitch 25 deg, hFOV 100 deg, 1600x700
    W, H = 1600, 700; fov = np.radians(100); pitch = np.radians(25)
    px = (np.arange(W) + 0.5) / W * 2 - 1; py = 1 - (np.arange(H) + 0.5) / H * 2
    PX, PY = np.meshgrid(px * np.tan(fov / 2), py * np.tan(fov / 2) * H / W)
    fwd = np.array([-np.cos(pitch), 0, np.sin(pitch)]); right = np.array([0, 1, 0]); up = np.array([np.sin(pitch), 0, np.cos(pitch)])
    D = fwd[None, None] + PX[..., None] * right + PY[..., None] * up
    D /= np.linalg.norm(D, axis=-1, keepdims=True)
    bq = D[..., 2] * R; cq = -(2 * R * altitude + altitude * altitude)
    t = -bq + np.sqrt(bq * bq - cq)
    opt = density(D[..., 0] * t, D[..., 1] * t, wm, uv_size, density_scale, shader)
    alpha = 1 - np.exp(-opt)
    hz = np.clip(1 - D[..., 2] * 3, 0, 1)[..., None]
    sky = np.array([0.33, 0.50, 0.78]) * (1 - hz) + np.array([0.72, 0.80, 0.90]) * hz
    img = sky * (1 - alpha[..., None]) + alpha[..., None]
    img[D[..., 2] < 0] = [0.25, 0.3, 0.25]
    view = Image.fromarray((np.clip(img, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8))
    topi = Image.fromarray((top * 255).astype(np.uint8)).convert('RGB').resize((700, 700))
    sheet = Image.new('RGB', (W + 700, 700)); sheet.paste(view, (0, 0)); sheet.paste(topi, (W, 0))
    sheet.save(os.path.join(HERE, 'sim_%s.jpg' % name), quality=90)
    print(name, 'mean opacity top-down %.3f' % top.mean(), 'frac>0.1: %.3f' % (top > 0.1).mean())


COV_DEFAULT = {'noise': 1, 'range': [-0.7, 0.7, 0.0, 0.6]}
TYPE_DEFAULT = {'noise': 2, 'range': [-1, 1, 0, 1]}
VARIANTS = {
    'A_default_d1.0': dict(layers=[COV_DEFAULT, TYPE_DEFAULT]),
    'B_typeB_streaks': dict(layers=[COV_DEFAULT, {'noise': 4, 'range': [-1, 1, 0.0, 0.0]}], density_scale=2.0),
    'C_typeR_wisps': dict(layers=[COV_DEFAULT, {'noise': 4, 'range': [-1, 1, 0.5, 0.5]}], density_scale=2.0),
    'D_typeG_only': dict(layers=[COV_DEFAULT, {'noise': 4, 'range': [-1, 1, 1.0, 1.0]}]),
    'E_typeBR_uv3': dict(layers=[{'noise': 1, 'range': [-0.5, 0.7, 0.0, 0.75]}, {'noise': 3, 'range': [-1, 0.2, 0.0, 0.5]}], uv_size=3.0, density_scale=2.0),
    'F_streaks_uv3_sparse': dict(layers=[{'noise': 1, 'range': [-0.3, 0.7, 0.0, 0.8]}, {'noise': 4, 'range': [-1, 1, 0.0, 0.0]}], uv_size=3.0, density_scale=2.0),
    'G_streaks_uv2_alt10k': dict(layers=[{'noise': 1, 'range': [-0.5, 0.7, 0.0, 0.75]}, {'noise': 3, 'range': [-1, 0.2, 0.0, 0.35]}], uv_size=2.0, density_scale=2.0, altitude=10000.0),
}

if __name__ == '__main__':
    only = sys.argv[1:]
    for k, v in VARIANTS.items():
        if only and not any(o in k for o in only):
            continue
        render(k, **v)

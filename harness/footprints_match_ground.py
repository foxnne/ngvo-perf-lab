"""Build the "foxnne - Footprints Match Ground" mod into a staging folder (never into the live modlist).

1. Darken-only footprint decals. Every Dynamic Footprints (Tomato's) and Beast Race Expansion diffuse is rewritten
   with black RGB and an alpha that only covers the pressed part of the print. With the decal's normal alpha blend that
   multiplies the landscape underneath by (1 - alpha): the print is the same material as the ground, just compressed and
   darker, on any landscape texture. The pressed area comes from integrating the print's own normal map into a height
   field (Frankot-Chellappa), so tread, toes and rims stay where the artist put them. Normal maps whose relief is a mound
   rather than a dent (the Sabrecat and Troll sets the beast patch borrows) are flipped.
2. Digitigrade beast prints, generated procedurally (height field -> normal map + darken alpha):
   Khajiit = cat paw (trilobed pad, four toe pads, no heel, no claws); Serval = narrower, longer cat paw;
   Argonian = three forward toes with claw tips, small rear toe, metatarsal pad, no heel.
3. "foxnne - Beast Footprints.esp" (ESL): points the Beast Race Expansion Khajiit and Argonian texture sets at the new
   paws, adds Beast_Serval_* impact data sets for the Serval race, and an ini fragment that uses them.

Usage: python -I footprints_match_ground.py [--out DIR] [--skip-existing] [--only-beast]
Read-only on the modlist; writes only under --out.
"""

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

import numpy as np
from PIL import Image

MODS = r"C:\Modlists\NGVO 8.0 Beta\mods"
TOMATO = os.path.join(MODS, "Dynamic Footprints Skse - Tomato's")
BEAST = os.path.join(MODS, "Dynamic Footprints Beast Race Expansion 2.0")
TOMATO_ESP = os.path.join(TOMATO, "NMN_DynamicFootprints.esp")
BEAST_ESP = os.path.join(BEAST, "Dynamic Footprints - Beast Race Expansion.esp")
TEXCONV = r"C:\Modlists\NGVO 8.0 Beta\tools\SSEEdit\Edit Scripts\Texconvx64.exe"
DEFAULT_OUT = r"C:\Users\foxnn\dev\ngvo-perf-lab\staged\foxnne - Footprints Match Ground"

# Darkening strength (alpha of a black decal) at the bottom of a print, per ground. Mud and forest litter darken most
# when packed; sand mostly shows through the normals; snow decals only remain where the snow is too thin to deform.
GROUND_STRENGTH = {
    "mud": 0.50,
    "forest": 0.40,
    "dirt": 0.34,
    "ash": 0.30,
    "sand": 0.20,
    "snow": 0.14,
}
RIM_SHARE = 0.30


def ground_of(name):
    n = name.lower()
    if "rmud" in n or "mud" in n:
        return "mud"
    if "sand" in n:
        return "sand"
    if "_ash" in n:
        return "ash"
    if "snow" in n:
        return "snow"
    if "ffd" in n or "fdg" in n or "forest" in n:
        return "forest"
    return "dirt"


# ----------------------------------------------------------------------------------------------- plugin reading/writing


def read_records(path):
    data = open(path, "rb").read()
    header_size = struct.unpack_from("<I", data, 4)[0]
    header = data[: 24 + header_size]
    out = []

    def walk(off, end):
        while off < end:
            typ = data[off : off + 4]
            size = struct.unpack_from("<I", data, off + 4)[0]
            if typ == b"GRUP":
                walk(off + 24, off + size)
                off += size
                continue
            head = bytearray(data[off : off + 24])
            flags, fid = struct.unpack_from("<II", data, off + 8)
            body = data[off + 24 : off + 24 + size]
            if flags & 0x40000:
                body = zlib.decompress(body[4:])
                struct.pack_into("<I", head, 8, flags & ~0x40000)
            out.append((typ.decode(), fid, bytes(head), body))
            off += 24 + size

    walk(24 + header_size, len(data))
    return header, out


def subrecords(body):
    o = 0
    big = None
    while o < len(body):
        t = body[o : o + 4]
        s = struct.unpack_from("<H", body, o + 4)[0]
        o += 6
        if t == b"XXXX":
            big = struct.unpack_from("<I", body, o)[0]
            o += 4
            continue
        if big is not None:
            s = big
            big = None
        yield t.decode(), body[o : o + s]
        o += s


def pack_subrecords(items):
    out = bytearray()
    for t, v in items:
        if len(v) > 0xFFFF:
            out += b"XXXX" + struct.pack("<HI", 4, len(v))
            out += t.encode() + struct.pack("<H", 0) + v
        else:
            out += t.encode() + struct.pack("<H", len(v)) + v
    return bytes(out)


def zstr(text):
    return text.encode("latin1") + b"\0"


def edid(body):
    for t, v in subrecords(body):
        if t == "EDID":
            return v.rstrip(b"\0").decode("latin1")
    return ""


def txst_paths(body):
    paths = {}
    for t, v in subrecords(body):
        if re.fullmatch(r"TX0\d", t):
            paths[t] = v.rstrip(b"\0").decode("latin1")
    return paths


def make_record(typ, fid, template_head, items):
    body = pack_subrecords(items)
    head = bytearray(template_head)
    head[0:4] = typ.encode()
    struct.pack_into("<I", head, 4, len(body))
    struct.pack_into("<I", head, 12, fid)
    return bytes(head) + body


def make_group(label, records):
    payload = b"".join(records)
    return b"GRUP" + struct.pack("<I", 24 + len(payload)) + label.encode() + struct.pack("<iHHI", 0, 0, 0, 0) + payload


def make_plugin(path, masters, groups, next_object):
    count = sum(len(r) for _, r in groups) + len(groups)
    items = [("HEDR", struct.pack("<fII", 1.71, count, next_object)), ("CNAM", zstr("foxnne"))]
    items.append(("SNAM", zstr("Digitigrade beast footprints and Serval sets for Dynamic Footprints. Generated by footprints_match_ground.py.")))
    for m in masters:
        items += [("MAST", zstr(m)), ("DATA", struct.pack("<Q", 0))]
    body = pack_subrecords(items)
    # type, data size, flags (ESL), form id, version control, form version 44, unknown
    tes4 = b"TES4" + struct.pack("<IIIIHH", len(body), 0x200, 0, 0, 44, 0) + body
    with open(path, "wb") as f:
        f.write(tes4)
        for label, recs in groups:
            f.write(make_group(label, recs))


# ------------------------------------------------------------------------------------------------------- height fields


def integrate(p, q):
    """Least-squares height from gradients (Frankot-Chellappa); p = dH/dx (columns), q = dH/dy (rows)."""
    h, w = p.shape
    u = 2 * np.pi * np.fft.fftfreq(w)[None, :]
    v = 2 * np.pi * np.fft.fftfreq(h)[:, None]
    d = u * u + v * v
    d[0, 0] = 1
    H = (-1j * u * np.fft.fft2(p) - 1j * v * np.fft.fft2(q)) / d
    H[0, 0] = 0
    return np.real(np.fft.ifft2(H))


def normals_to_gradients(n, green):
    """Gradients (dH/dx, dH/drow) of a normal map. green=-1 is the game's convention (measured on TomatoRim PBR
    landscape and vanilla-style maps: red = -dH/dx, green = +dH/drow is NOT integrable there, green = -dH/drow is);
    green=+1 is the OpenGL convention most of the Dynamic Footprints maps were authored in."""
    nx = n[..., 0] * 2 - 1
    ny = n[..., 1] * 2 - 1
    nz = np.clip(n[..., 2] * 2 - 1, 0.15, 1)
    return -nx / nz, green * ny / nz


def integrability_error(p, q):
    H = integrate(p, q)
    gy, gx = np.gradient(H)
    return float(np.mean((gx - p) ** 2 + (gy - q) ** 2) / max(np.mean(p * p + q * q), 1e-9)), H


def gradients_to_normals(H, max_slope=1.4):
    """Normal map in the game's convention (red = -dH/dx, green = +dH/dy with y up the image)."""
    gy, gx = np.gradient(H)
    strength = max_slope / max(float(np.percentile(np.hypot(gx, gy), 99.5)), 1e-6)
    p, q = gx * strength, gy * strength
    n = np.stack([-p, -q, np.ones_like(p)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def blur(a, radius):
    """Gaussian blur through the FFT (periodic edges; prints never touch the texture border)."""
    if radius <= 0:
        return a
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    kernel = np.exp(-2 * (np.pi * radius) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * kernel)).astype(np.float32)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def depression_from_normal(normal_rgba, support_alpha):
    """Returns (dent 0..1, rim 0..1, flip_red, flip_green) for a print normal map; support_alpha bounds the print.
    The flips turn the map into the game's convention with the print as a dent."""
    small = normal_rgba[::2, ::2] if normal_rgba.shape[0] > 512 else normal_rgba
    errors = {g: integrability_error(*normals_to_gradients(small, g))[0] for g in (-1, 1)}
    green = min(errors, key=errors.get)
    H = integrate(*normals_to_gradients(normal_rgba, green))
    support = smoothstep(0.02, 0.25, blur(support_alpha, 4))
    outside = support < 0.05
    ref = np.median(H[outside]) if outside.any() else np.median(H)
    rel = (H - ref) * support
    lo, hi = np.percentile(rel, 0.5), np.percentile(rel, 99.5)
    orient = -1 if hi > -lo else 1  # the strongest relief must be the dent, not a mound
    if orient < 0:
        rel = -rel
        lo, hi = -hi, -lo
    dent = np.clip(-rel / max(-lo, 1e-6), 0, 1)
    rim = np.clip(rel / max(hi, 1e-6), 0, 1)
    # Re-encode orient*H in the game convention: red flips when the relief flips; green also follows the convention.
    flip_red = orient < 0
    flip_green = (orient * green) > 0
    return dent, rim, flip_red, flip_green


def darken_rgba(dent, rim, strength, feather):
    alpha = strength * np.power(dent, 0.8) + RIM_SHARE * strength * rim
    alpha = np.clip(alpha * feather, 0, 1)
    rgba = np.zeros(dent.shape + (4,), np.float32)
    rgba[..., 3] = alpha
    return rgba


def edge_feather(shape, margin=0.06):
    h, w = shape
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    e = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    return smoothstep(0.0, margin, e)


# -------------------------------------------------------------------------------------------- procedural beast prints
# Texture convention (same as the Dynamic Footprints sets): toes point down the image (+v), the left print has its
# medial side on the image's left.


def grid(size):
    v, u = np.mgrid[0:size, 0:size].astype(np.float32)
    return (u + 0.5) / size * 2 - 1, (v + 0.5) / size * 2 - 1


def ellipse(u, v, cu, cv, ru, rv, angle=0.0, soft=0.25):
    c, s = np.cos(angle), np.sin(angle)
    du, dv = u - cu, v - cv
    x = (du * c + dv * s) / ru
    y = (-du * s + dv * c) / rv
    r = np.sqrt(x * x + y * y)
    return 1 - smoothstep(1 - soft, 1 + soft * 0.4, r)


def capsule(u, v, a, b, r0, r1, soft=0.3):
    a = np.array(a, np.float32)
    b = np.array(b, np.float32)
    ab = b - a
    t = np.clip(((u - a[0]) * ab[0] + (v - a[1]) * ab[1]) / (ab @ ab), 0, 1)
    px = a[0] + ab[0] * t
    py = a[1] + ab[1] * t
    d = np.sqrt((u - px) ** 2 + (v - py) ** 2)
    r = r0 + (r1 - r0) * t
    return 1 - smoothstep(1 - soft, 1 + soft * 0.4, d / r)


def value_noise(size, cells, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((cells + 1, cells + 1)).astype(np.float32)
    img = Image.fromarray((g * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
    return np.asarray(img, np.float32) / 255 * 2 - 1


def cat_paw(size, mirror, narrow=1.0, stretch=1.0, seed=1):
    u, v = grid(size)
    if mirror:
        u = -u
    u = u / narrow
    v = v / stretch
    # Plantar pad: a rounded trapezoid, narrow toward the toes (+v) and wide at the back, with a three-lobed rear edge
    # (middle lobe furthest back) and a slightly two-lobed front edge.
    pv = -0.10
    taper = np.clip(1.0 - 0.45 * (v - pv + 0.22) / 0.44, 0.55, 1.15)
    pad_main = ellipse(u / taper, v, 0.0, pv, 0.30, 0.20, soft=0.22)
    lobes = np.maximum.reduce([ellipse(u, v, cu, cv, 0.12, 0.11, soft=0.35) for cu, cv in ((-0.21, -0.24), (0.0, -0.29), (0.21, -0.24))])
    front = np.maximum(ellipse(u, v, -0.08, 0.06, 0.11, 0.08, soft=0.4), ellipse(u, v, 0.08, 0.06, 0.11, 0.08, soft=0.4))
    pad = np.clip(np.maximum.reduce([pad_main, 0.95 * lobes, 0.9 * front]), 0, 1)
    # Toe pads: medial-middle toe leads (left print: medial = image left).
    toes = [(-0.42, 0.26, 0.13, 0.16, -0.35), (-0.15, 0.47, 0.13, 0.17, -0.1), (0.15, 0.45, 0.13, 0.17, 0.1), (0.42, 0.24, 0.12, 0.15, 0.35)]
    toe = np.zeros_like(u)
    for cu, cv, ru, rv, ang in toes:
        toe = np.maximum(toe, ellipse(u, v, cu, cv, ru, rv, ang, soft=0.3))
    # Fur and skin between the pads press a little: one soft outline of the whole paw.
    outline = blur(np.maximum(pad, toe), size * 0.025)
    outline = smoothstep(0.05, 0.45, outline)
    dent = np.maximum(0.25 * outline, np.maximum(0.95 * pad, 1.0 * toe))
    return finish(dent, size, seed)


def argonian_foot(size, mirror, seed=7):
    u, v = grid(size)
    if mirror:
        u = -u
    base = (0.0, -0.14)
    dent = np.zeros_like(u)
    claws = np.zeros_like(u)
    # Three separate forward toes, the middle one longest, outer ones splayed; each ends in a claw that digs in.
    for angle, length, width in ((-0.44, 0.44, 0.068), (0.0, 0.56, 0.074), (0.42, 0.42, 0.064)):
        dx, dy = np.sin(angle), np.cos(angle)
        root = (base[0] + dx * 0.16, base[1] + dy * 0.16)
        tip = (base[0] + dx * length, base[1] + dy * length)
        dent = np.maximum(dent, 0.8 * capsule(u, v, root, tip, width * 0.8, width * 0.65, soft=0.35))
        # knuckle pads read as beads along the toe
        for t in (0.5, 0.75, 0.97):
            pc = (base[0] + dx * length * t, base[1] + dy * length * t)
            dent = np.maximum(dent, ellipse(u, v, pc[0], pc[1], width, width * 1.15, angle, soft=0.35))
        claw_tip = (tip[0] + dx * 0.13, tip[1] + dy * 0.13)
        claws = np.maximum(claws, capsule(u, v, (tip[0] + dx * 0.03, tip[1] + dy * 0.03), claw_tip, width * 0.42, width * 0.06, soft=0.25))
    # Short rear toe on the medial side, pointing back, with a small claw.
    rear_root, rear_tip = (-0.07, -0.20), (-0.17, -0.31)
    dent = np.maximum(dent, 0.85 * capsule(u, v, rear_root, rear_tip, 0.045, 0.04, soft=0.35))
    rdx, rdy = rear_tip[0] - rear_root[0], rear_tip[1] - rear_root[1]
    norm = np.hypot(rdx, rdy)
    claws = np.maximum(claws, capsule(u, v, rear_tip, (rear_tip[0] + rdx / norm * 0.07, rear_tip[1] + rdy / norm * 0.07), 0.02, 0.004, soft=0.25))
    # Metatarsal pad where the toes meet; no heel (the foot stands on its toes).
    dent = np.maximum(dent, 0.9 * ellipse(u, v, 0.0, -0.15, 0.14, 0.12, soft=0.3))
    # A little webbing between the toe roots only.
    dent = np.maximum(dent, 0.25 * ellipse(u, v, 0.0, 0.0, 0.13, 0.07, soft=0.5))
    dent = np.maximum(dent, 1.3 * claws)
    return finish(dent, size, seed)


def finish(dent, size, seed):
    dent = np.clip(dent, 0, 1.4)
    noise = 0.07 * value_noise(size, 48, seed) + 0.04 * value_noise(size, 160, seed + 1)
    height = -blur(dent, size * 0.006) * (1 + noise)
    # Displaced soil: a low rim just outside the print.
    spread = blur(dent, size * 0.03)
    rim = np.clip(spread - blur(dent, size * 0.008) * 1.2, 0, None)
    rim = rim / max(rim.max(), 1e-6) * 0.22 * (1 + 0.5 * value_noise(size, 30, seed + 2))
    height = height + rim
    dent01 = np.clip(-np.minimum(height, 0) / max(-height.min(), 1e-6), 0, 1)
    rim01 = np.clip(np.maximum(height, 0) / max(height.max(), 1e-6), 0, 1)
    return height, dent01, rim01


# ---------------------------------------------------------------------------------------------------- texture writing


def save_dds(rgba, path, tmp, fmt="BC7_UNORM"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    png = os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + ".png")
    Image.fromarray(np.clip(rgba * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(png)
    cmd = [TEXCONV, "-nologo", "-y", "-f", fmt, "-m", "0", "-alpha", "-o", os.path.dirname(path), png]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"texconv failed for {path}: {r.stdout}{r.stderr}")
    os.remove(png)
    made = os.path.join(os.path.dirname(path), os.path.splitext(os.path.basename(path))[0] + ".DDS")
    if os.path.exists(made) and os.path.basename(made) != os.path.basename(path):
        tmp_name = path + ".tmp"
        os.replace(made, tmp_name)
        os.replace(tmp_name, path)


def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA"), np.float32) / 255


def tex_path(rel):
    return os.path.join(TOMATO, "textures", rel.replace("/", "\\"))


# --------------------------------------------------------------------------------------------------------------- main


def convert_existing(out, tmp, skip_existing, report):
    pairs = {}
    for esp in (TOMATO_ESP, BEAST_ESP):
        _, recs = read_records(esp)
        for typ, fid, head, body in recs:
            if typ != "TXST":
                continue
            paths = txst_paths(body)
            if "TX00" in paths and "TX01" in paths:
                pairs.setdefault(paths["TX00"].lower(), (paths["TX00"], paths["TX01"]))
    cache = {}
    flipped = set()
    written = 0
    for _, (diffuse, normal) in sorted(pairs.items()):
        src_d, src_n = tex_path(diffuse), tex_path(normal)
        if not (os.path.exists(src_d) and os.path.exists(src_n)):
            report.append(f"missing source: {diffuse} / {normal}")
            continue
        dst = os.path.join(out, "textures", diffuse)
        if skip_existing and os.path.exists(dst):
            continue
        d = load_rgba(src_d)
        key = normal.lower()
        if key not in cache:
            n = load_rgba(src_n)
            if n.shape[:2] != d.shape[:2]:
                n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize(d.shape[1::-1], Image.LANCZOS), np.float32) / 255
            src_full = load_rgba(src_n)
            dent, rim, flip_red, flip_green = depression_from_normal(n, d[..., 3])
            cache[key] = (dent, rim)
            if flip_red or flip_green:
                flipped.add(f"{normal} (red {'flipped' if flip_red else 'kept'}, green {'flipped' if flip_green else 'kept'})")
                fixed = src_full.copy()
                if flip_red:
                    fixed[..., 0] = 1 - fixed[..., 0]
                if flip_green:
                    fixed[..., 1] = 1 - fixed[..., 1]
                save_dds(fixed, os.path.join(out, "textures", normal), tmp)
        dent, rim = cache[key]
        if dent.shape != d.shape[:2]:
            dent = np.asarray(Image.fromarray(dent).resize(d.shape[1::-1]), np.float32)
            rim = np.asarray(Image.fromarray(rim).resize(d.shape[1::-1]), np.float32)
        support = smoothstep(0.0, 0.3, blur(d[..., 3], 3))
        rgba = darken_rgba(dent, rim, GROUND_STRENGTH[ground_of(diffuse)], support * edge_feather(dent.shape))
        save_dds(rgba, dst, tmp)
        written += 1
    report.append(f"darken-only diffuse written: {written}; normal maps converted to the game convention as dents: {len(flipped)}")
    for n in sorted(flipped):
        report.append(f"  flipped {n}")


BEAST_GROUNDS = ["Ash", "Dirt", "Dirt01", "DirtPath", "FDG", "FFD", "FMDS", "RD", "RMud", "Sand", "Snow", "VTD1", "VTD2"]
BEAST_KINDS = {
    # name: (generator, decal size in game units)
    "Khajiit": (lambda size, mirror: cat_paw(size, mirror, 1.0, 1.0, 11), 14.0),
    "Serval": (lambda size, mirror: cat_paw(size, mirror, 0.82, 1.12, 23), 13.0),
    "Argonian": (lambda size, mirror: argonian_foot(size, mirror, 37), 19.0),
}


def build_beasts(out, tmp, report):
    size = 512
    for kind, (gen, _) in BEAST_KINDS.items():
        for side, mirror in (("L", False), ("R", True)):
            hi = gen(size * 2, mirror)
            height = np.asarray(Image.fromarray(hi[0].astype(np.float32)).resize((size, size), Image.LANCZOS), np.float32)
            dent = np.asarray(Image.fromarray(hi[1].astype(np.float32)).resize((size, size), Image.LANCZOS), np.float32).clip(0, 1)
            rim = np.asarray(Image.fromarray(hi[2].astype(np.float32)).resize((size, size), Image.LANCZOS), np.float32).clip(0, 1)
            n = gradients_to_normals(height)
            normal = np.concatenate([n, np.ones(n.shape[:2] + (1,), np.float32)], -1)
            save_dds(normal, os.path.join(out, "textures", "NMN_Footprints", "foxnne", f"Beast_{kind}_{side}_n.dds"), tmp)
            feather = edge_feather(dent.shape)
            for ground in BEAST_GROUNDS:
                rgba = darken_rgba(dent, rim, GROUND_STRENGTH[ground_of(ground)], feather)
                save_dds(rgba, os.path.join(out, "textures", "NMN_Footprints", "foxnne", f"Beast_{kind}_{ground}_{side}.dds"), tmp)
            preview = np.clip(0.55 - height * 0.35, 0, 1)
            Image.fromarray((preview * 255).astype(np.uint8)).save(os.path.join(out, "_preview", f"Beast_{kind}_{side}.png"))
    report.append("beast prints written: Khajiit, Serval, Argonian (L/R normal + 13 grounds each)")


def dodt_with_size(dodt, size):
    b = bytearray(dodt)
    struct.pack_into("<ffff", b, 0, size, size, size, size)
    return bytes(b)


def build_plugin(out, report):
    header, recs = read_records(BEAST_ESP)
    by_id = {fid: (typ, head, body) for typ, fid, head, body in recs}
    by_edid = {edid(body): fid for typ, fid, head, body in recs}
    masters = ["Skyrim.esm", "Dragonborn.esm", "Dynamic Footprints - Beast Race Expansion.esp"]
    self_index = len(masters) << 24
    txsts, ipcts, ipdss = [], [], []
    next_object = 0x800

    def retexture(body, kind, ground, side):
        items = []
        for t, v in subrecords(body):
            if t == "EDID" and kind == "Serval":
                v = zstr(f"Beast_Serval_{ground}_{side}_01_TXST")
            elif t == "TX00":
                v = zstr(f"NMN_Footprints\\foxnne\\Beast_{kind}_{ground}_{side}.dds")
            elif t == "TX01":
                v = zstr(f"NMN_Footprints\\foxnne\\Beast_{kind}_{side}_n.dds")
            elif t == "DODT":
                v = dodt_with_size(v, BEAST_KINDS[kind][1])
            items.append((t, v))
        return items

    for kind in ("Khajiit", "Argonian"):
        for ground in BEAST_GROUNDS:
            for side in ("L", "R"):
                fid = by_edid.get(f"Beast_{kind}_{ground}_{side}_01_TXST")
                if fid is None:
                    continue  # the beast patch has no such set (Argonian has no FMDS / VTD1 / VTD2)
                typ, head, body = by_id[fid]
                txsts.append(make_record("TXST", fid, head, retexture(body, kind, ground, side)))

    # Serval: new TXST -> IPCT -> IPDS chains cloned from the Khajiit ones.
    for ground in BEAST_GROUNDS:
        for side in ("L", "R"):
            src_ipds = by_edid.get(f"Beast_Khajiit_{ground}_{side}_01")
            src_ipct = by_edid.get(f"Beast_Khajiit_{ground}_{side}_01_IPCT")
            src_txst = by_edid.get(f"Beast_Khajiit_{ground}_{side}_01_TXST")
            if None in (src_ipds, src_ipct, src_txst):
                report.append(f"serval: missing Khajiit source records for {ground} {side}")
                continue
            txst_id = self_index | next_object
            ipct_id = self_index | (next_object + 1)
            ipds_id = self_index | (next_object + 2)
            next_object += 3
            typ, head, body = by_id[src_txst]
            txsts.append(make_record("TXST", txst_id, head, retexture(body, "Serval", ground, side)))
            typ, head, body = by_id[src_ipct]
            items = []
            for t, v in subrecords(body):
                if t == "EDID":
                    v = zstr(f"Beast_Serval_{ground}_{side}_01_IPCT")
                elif t == "DNAM":
                    v = struct.pack("<I", txst_id)
                items.append((t, v))
            ipcts.append(make_record("IPCT", ipct_id, head, items))
            typ, head, body = by_id[src_ipds]
            items = []
            for t, v in subrecords(body):
                if t == "EDID":
                    v = zstr(f"Beast_Serval_{ground}_{side}_01")
                elif t == "PNAM":
                    material, impact = struct.unpack("<II", v)
                    v = struct.pack("<II", material, ipct_id)
                items.append((t, v))
            ipdss.append(make_record("IPDS", ipds_id, head, items))

    path = os.path.join(out, "foxnne - Beast Footprints.esp")
    make_plugin(path, masters, [("TXST", txsts), ("IPCT", ipcts), ("IPDS", ipdss)], next_object)
    report.append(f"plugin: {len(txsts)} TXST ({len(txsts) - len(ipcts)} overrides), {len(ipcts)} IPCT, {len(ipdss)} IPDS -> {path}")

    # Serval ini fragment: same shape as the beast patch, pointing at the Serval sets.
    src_ini = os.path.join(BEAST, "SKSE", "Plugins", "NMN_DynamicFootprints", "Patches", "Beast_ServalKhajiit", "Humanoids.ini")
    text = open(src_ini, encoding="utf-8", errors="replace").read()
    text = re.sub(r"Beast_Khajiit_", "Beast_Serval_", text)
    text = "; foxnne - Footprints Match Ground: Serval Khajiit use their own narrow paw prints (Beast_Serval_*).\n" + text
    dst_ini = os.path.join(out, "SKSE", "Plugins", "NMN_DynamicFootprints", "Patches", "Beast_ServalKhajiit", "Humanoids.ini")
    os.makedirs(os.path.dirname(dst_ini), exist_ok=True)
    open(dst_ini, "w", encoding="utf-8", newline="\r\n").write(text)
    report.append(f"ini: {dst_ini}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--only-beast", action="store_true")
    args = ap.parse_args()
    out = args.out
    if os.path.abspath(out).lower().startswith(os.path.abspath(MODS).lower()):
        sys.exit("refusing to write into the live modlist; stage elsewhere and install with the mod tools")
    os.makedirs(os.path.join(out, "_preview"), exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory() as tmp:
        build_beasts(out, tmp, report)
        build_plugin(out, report)
        if not args.only_beast:
            convert_existing(out, tmp, args.skip_existing, report)
    with open(os.path.join(out, "_preview", "report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()

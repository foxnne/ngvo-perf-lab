"""Grass type table: GRAS records of the load order, the winning mesh and diffuse texture of every model in the cache,
and the mean visible colour of each.

Colour per mesh = area-weighted mean over the mesh surface of  diffuse(uv) * hue(vertex colour)  for the texels that pass the
alpha test, exactly the albedo the fork's RunGrass.hlsl builds:
    baseColor = Tex(uv)  (uv.y * 0.5 for "complex grass" atlases whose lower half is a normal map)
    vertexColor = srgb->linear(instanceColourScale * meshVertexColour) ; vertexAO = max channel ; vertexColor /= vertexAO
    albedo = baseColor * vertexColor
The max-channel ("AO") part, which only darkens the ambient term, is reported separately (ao).

Writes out/work/grass_types.json and out/grass_colour_table.{md,csv,png}.
"""
import json
import os
import struct
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r'C:\Users\foxnn\dev\skyrimnet-wardrobe')
sys.path.insert(0, r'C:\Users\foxnn\dev\giant-tree-wind')
import tes5  # noqa: E402
import nifio  # noqa: E402
from build_catalogue import read_profile  # noqa: E402

ROOT = r'C:\Modlists\NGVO 8.0 Beta'
PROFILE = 'foxnne-nsfw'
OUT = os.path.join(HERE, 'out')
WORK = os.path.join(OUT, 'work')
TEXCONV = os.path.join(ROOT, 'tools', 'xLODGen', 'Edit Scripts', 'Texconvx64.exe')
SAMPLES = 60000
rng = np.random.default_rng(7)


def srgb2lin(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(np.asarray(c, np.float64), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


class Sources:
    def __init__(self):
        self.mods, self.active, self.order = read_profile(ROOT, PROFILE)
        self.dirs = [('<overwrite>', os.path.join(ROOT, 'overwrite'))] + [(m, os.path.join(ROOT, 'mods', m)) for m in self.mods] + \
                    [('<Stock Game>', os.path.join(ROOT, 'Stock Game', 'Data'))]
        self.bsas = None

    def loose(self, rel):
        for label, d in self.dirs:
            p = os.path.join(d, rel)
            if os.path.isfile(p):
                return label, p
        return None

    def from_bsa(self, rel):
        if self.bsas is None:
            self.bsas = []
            for label, d in self.dirs:
                try:
                    for e in os.scandir(d):
                        if e.name.lower().endswith('.bsa'):
                            self.bsas.append((label, e.path, None))
                except OSError:
                    pass
        rel = rel.lower()
        for i, (label, path, names) in enumerate(self.bsas):
            if names is None:
                try:
                    names = set(n.lower() for n in tes5.bsa_list(path))
                except Exception:  # noqa
                    names = set()
                self.bsas[i] = (label, path, names)
            if rel in names:
                return label + ' [' + os.path.basename(path) + ']', tes5.BSA(path).read(rel)
        return None

    def get(self, rel):
        hit = self.loose(rel)
        if hit:
            return hit[0], open(hit[1], 'rb').read(), hit[1]
        hit = self.from_bsa(rel)
        if hit:
            return hit[0], hit[1], None
        return None


def load_gras(src):
    """Winning GRAS records by form key, plus the run-time index of every active plugin."""
    index = {}
    for label, d in src.dirs:
        try:
            for e in os.scandir(d):
                if e.name.lower().endswith(('.esp', '.esm', '.esl')) and e.is_file():
                    index.setdefault(e.name.lower(), e.path)
        except OSError:
            pass
    gras, runtime = {}, {}
    full = light = 0
    missing = []
    for name in src.order:
        ln = name.lower()
        base = ln in ('skyrim.esm', 'update.esm', 'dawnguard.esm', 'hearthfires.esm', 'dragonborn.esm') or ln.startswith('cc')
        if ln not in src.active and not base:
            continue
        if ln not in index:
            missing.append(name)
            continue
        pl = tes5.Plugin(index[ln], name)
        try:
            pl.load({b'GRAS'})
        except Exception as e:  # noqa
            print('  plugin error', name, e)
            continue
        if pl.is_light:
            runtime[ln] = 0xFE000000 | (light << 12)
            light += 1
        else:
            runtime[ln] = full << 24
            full += 1
        for fid, flags, body in pl.records.get(b'GRAS', []):
            rec = dict(plugin=name)
            for st, sd in tes5.iter_subrecords(body):
                if st == b'EDID':
                    rec['edid'] = tes5.zstr(sd)
                elif st == b'MODL':
                    rec['model'] = tes5.zstr(sd).lower()
                elif st == b'DATA' and len(sd) >= 32:
                    dens, mins, maxs, _p, uw, _p2, wt, prange, hrange, crange, wave, fl = struct.unpack_from('<BBBBHHIffffB', sd)
                    rec.update(density=dens, min_slope=mins, max_slope=maxs, units_from_water=uw, water_type=wt, pos_range=prange,
                               height_range=hrange, colour_range=crange, wave=wave, flags=fl)
            gras[pl.formkey(fid)] = rec
    print('plugins: %d full + %d light active, %d missing %s; GRAS records %d' % (full, light, len(missing), missing[:5], len(gras)))
    return gras, runtime


_tex_cache = {}


def load_texture(src, rel):
    """Returns (rgba float array 0..1 sRGB-encoded as stored, info) or None."""
    rel = rel.lower().replace('/', '\\')
    if not rel.startswith('textures\\'):
        i = rel.find('textures\\')
        rel = rel[i:] if i >= 0 else 'textures\\' + rel
    if rel in _tex_cache:
        return _tex_cache[rel]
    hit = src.get(rel)
    if not hit:
        _tex_cache[rel] = None
        return None
    label, data, path = hit
    fourcc = data[84:88]
    dxgi = struct.unpack_from('<I', data, 128)[0] if fourcc == b'DX10' else None
    h, w, _, _, mips = struct.unpack_from('<IIIII', data, 12)
    tmp = os.path.join(WORK, 'tex_tmp')
    os.makedirs(tmp, exist_ok=True)
    img = None
    try:
        import io
        img = Image.open(io.BytesIO(data))
        img.load()
        img = img.convert('RGBA')
    except Exception:  # noqa
        import subprocess
        f = os.path.join(tmp, 'in.dds')
        open(f, 'wb').write(data)
        subprocess.run([TEXCONV, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-m', '1', '-o', tmp, f], capture_output=True)
        img = Image.open(os.path.join(tmp, 'in.png')).convert('RGBA')
        img.load()
    arr = np.asarray(img, np.float32) / 255.0
    fmt = fourcc.decode('latin1').strip('\0 ') if dxgi is None else 'DXGI%d' % dxgi
    info = dict(rel=rel, source=label, w=w, h=h, mips=mips, fmt=fmt)
    # the fork's complex-grass test: bottom-left texel is a unit normal with z > 0
    t = arr[h - 1, 0, :3] * 2 - 1
    info['complex'] = bool(t[2] > 0 and abs(float(np.linalg.norm(t)) - 1.0) < 0.1)
    _tex_cache[rel] = (arr, info)
    return _tex_cache[rel]


def mesh_colour(src, model):
    hit = src.get(os.path.join('meshes', model))
    if not hit:
        return dict(error='mesh not found')
    label, data, path = hit
    nif = nifio.Nif(data)
    res = dict(mesh_source=label, shapes=[])
    acc_col = np.zeros(3)
    acc_w = 0.0
    acc_a = 0.0
    acc_ao = 0.0
    acc_raw = np.zeros(3)
    area_total = 0.0
    lo = np.full(3, 1e9)
    hi = np.full(3, -1e9)
    for i in range(len(nif.blocks)):
        if nif.block_type(i) not in nifio.SHAPE_TYPES:
            continue
        d = nif.shape(i)
        if 'v' not in d or 'uv' not in d:
            continue
        sh = nif.lighting_shader(d['shader']) if d['shader'] >= 0 and nif.block_type(d['shader']) == 'BSLightingShaderProperty' else None
        if sh is None or sh['texset'] < 0:
            res['shapes'].append(dict(name=d['name'], error='no lighting shader/texture set'))
            continue
        texs = nif.texture_set(sh['texset'])
        thr = 0.0
        if d['alpha'] >= 0:
            ap = nif.alpha_property(d['alpha'])
            thr = ap['threshold'] / 255.0 if ap['test'] else 0.0
        tex = load_texture(src, texs[0])
        if tex is None:
            res['shapes'].append(dict(name=d['name'], error='texture not found: ' + texs[0]))
            continue
        arr, info = tex
        v = nif.to_root(i, d['v'])
        lo = np.minimum(lo, v.min(0))
        hi = np.maximum(hi, v.max(0))
        tri = d['tris']
        a, b, c = v[tri[:, 0]], v[tri[:, 1]], v[tri[:, 2]]
        areas = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        if areas.sum() <= 0:
            continue
        pick = rng.choice(len(tri), SAMPLES, p=areas / areas.sum())
        r1 = np.sqrt(rng.random(SAMPLES))
        r2 = rng.random(SAMPLES)
        w0, w1, w2 = 1 - r1, r1 * (1 - r2), r1 * r2
        uv = d['uv']
        suv = uv[tri[pick, 0]] * w0[:, None] + uv[tri[pick, 1]] * w1[:, None] + uv[tri[pick, 2]] * w2[:, None]
        if info['complex']:
            suv = suv * np.array([1.0, 0.5])
        th, tw = arr.shape[:2]
        px = np.floor((suv[:, 0] % 1.0) * tw).astype(int) % tw
        py = np.floor((suv[:, 1] % 1.0) * th).astype(int) % th
        if info['complex']:
            py = np.minimum(py, th // 2 - 1)
        tx = arr[py, px]
        has_vc = 'c' in d
        if has_vc:
            vc = d['c'].astype(np.float64) / 255.0
            svc = vc[tri[pick, 0]] * w0[:, None] + vc[tri[pick, 1]] * w1[:, None] + vc[tri[pick, 2]] * w2[:, None]
        else:
            svc = np.ones((SAMPLES, 4))
        alpha = tx[:, 3]  # the pixel shader's Color.w is the distance fade, not the mesh vertex alpha (that drives wind)
        passed = alpha >= thr if thr > 0 else alpha > 0.02
        wgt = passed.astype(np.float64) if thr > 0 else alpha.astype(np.float64)
        vlin = srgb2lin(svc[:, :3])
        ao = vlin.max(1)
        hue = vlin / np.maximum(ao, 1e-5)[:, None]
        col = srgb2lin(tx[:, :3]) * hue
        area = float(areas.sum())
        frac = float(wgt.mean())
        acc_col += (col * wgt[:, None]).sum(0) / SAMPLES * area
        acc_raw += (srgb2lin(tx[:, :3]) * wgt[:, None]).sum(0) / SAMPLES * area
        acc_ao += float((ao * wgt).sum()) / SAMPLES * area
        acc_w += frac * area
        area_total += area
        res['shapes'].append(dict(name=d['name'], tris=int(len(tri)), verts=int(d['nvert']), area=round(area, 1), alpha_pass=round(frac, 3),
                                  alpha_threshold=round(thr * 255), vertex_colours=has_vc,
                                  vc_flag=bool(sh['f2'] >> 5 & 1), double_sided=bool(sh['f2'] >> 4 & 1),
                                  vc_mean_srgb=[round(float(x), 3) for x in (svc[:, :3].mean(0))] if has_vc else None,
                                  diffuse=info['rel'], tex_source=info['source'], tex_size='%dx%d' % (info['w'], info['h']), tex_fmt=info['fmt'],
                                  complex=info['complex'], textures=[t for t in texs if t]))
    if acc_w > 0:
        lin = acc_col / acc_w
        res.update(linear=[float(x) for x in lin], srgb=[float(x) for x in lin2srgb(lin)],
                   linear_tex_only=[float(x) for x in acc_raw / acc_w], ao=acc_ao / acc_w,
                   visible_area=acc_w, mesh_area=area_total,
                   bbox_lo=[float(x) for x in lo], bbox_hi=[float(x) for x in hi])
    else:
        res['error'] = res.get('error') or 'no usable shape'
    return res


def main():
    t0 = time.time()
    src = Sources()
    types = json.load(open(os.path.join(WORK, 'types.json')))
    gras, runtime = load_gras(src)
    inv = {}
    for name, base in runtime.items():
        inv[base] = name
    out = {}
    unresolved = mismatch = stale = 0
    shift = set()
    by_local = {}
    for k in gras:
        by_local.setdefault(k[0], []).append(k)
    for model, t in types.items():
        recs = []
        for fid_s, n in t['formids'].items():
            fid = int(fid_s, 16)
            base = fid & 0xFFFFF000 if fid >> 24 == 0xFE else fid & 0xFF000000
            local = fid & 0xFFF if fid >> 24 == 0xFE else fid & 0xFFFFFF
            plug = inv.get(base)
            rec = gras.get((local, plug)) if plug else None
            if rec is None or rec.get('model') != model:
                # the cache is older than the current load order (light-plugin indices have shifted since it was generated):
                # resolve by local form ID + model path instead
                cands = [k for k in by_local.get(local, []) if gras[k].get('model') == model]
                if len(cands) >= 1:
                    stale += 1
                    plug = cands[0][1]
                    rec = gras[cands[0]]
                    shift.add(((base >> 12) & 0xFFF, (runtime.get(plug, 0) >> 12) & 0xFFF, plug, len(cands)))
            if rec is None or rec.get('model') != model:
                # the cache is older than the current load order (light-plugin indices have shifted since it was generated):
                # resolve by local form ID + model path instead
                cands = [k for k in by_local.get(local, []) if gras[k].get('model') == model]
                if len(cands) >= 1:
                    stale += 1
                    plug = cands[0][1]
                    rec = gras[cands[0]]
                    shift.add(((base >> 12) & 0xFFF, (runtime.get(plug, 0) >> 12) & 0xFFF, plug, len(cands)))
            if rec is None:
                unresolved += 1
                recs.append(dict(formid=fid_s, instances=n, plugin=plug, error='GRAS not found'))
                continue
            if rec.get('model') != model:
                mismatch += 1
            recs.append(dict(formid=fid_s, instances=n, origin=plug, winner=rec['plugin'], edid=rec.get('edid'), model=rec.get('model'),
                             density=rec.get('density'), colour_range=rec.get('colour_range'), pos_range=rec.get('pos_range'),
                             height_range=rec.get('height_range'), wave=rec.get('wave'), flags=rec.get('flags')))
        m = mesh_colour(src, model)
        n = t['inst']
        m.update(model=model, instances=n, tamriel=t['worlds'].get('tamriel', 0), cells=t['cells'], mean_scale2=t['s2'] / max(n, 1),
                 mean_colour_scale=t['w'] / max(n, 1), cache_flags=list(t['flags']), records=recs)
        out[model] = m
        if 'error' in m:
            print('  !!', model, m['error'], [s.get('error') for s in m.get('shapes', [])])
    print('form IDs in the cache not resolved to a GRAS record: %d; resolved but with another model path: %d' % (unresolved, mismatch))
    print('form IDs resolved by local ID + model because the cached light index is stale: %d; (cached index, current index, plugin, candidates): %s' % (stale, sorted(shift)))
    json.dump(out, open(os.path.join(WORK, 'grass_types.json'), 'w'), indent=1)
    print('done %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()



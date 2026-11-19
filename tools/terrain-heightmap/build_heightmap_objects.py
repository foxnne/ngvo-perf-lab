"""Build a Tamriel terrain height map that includes large mountain / cliff / rock statics.

Method: every enabled placed reference (winning override of the active load order) whose base model belongs to a
selected class is transformed with its full mesh (position, Skyrim rotation, scale) and sampled top-down at the texel
centres of the existing height map grid (128 units). Per object and texel the vertical crossings are turned into solid
intervals [bottom, top] using the triangle facing, so undersides are known; an interval only raises the surface when
its bottom is within --gap of the surface below it (landscape or an already accepted object). That keeps bridges,
arches and overhanging lips out. Result = max(landscape, filtered object surface).

Read-only on the modlist. Usage: python build_heightmap_objects.py [options]   (see --help)
"""
import os, sys, time, math, pickle, struct, argparse, json, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FM = r'C:\Users\foxnn\dev\floating-mesh'            # scan.py / nif.py / bsa.py (plugin, NIF and BSA readers)
sys.path.insert(0, FM)
sys.path.insert(0, HERE)

MINCX, MINCY, MAXCX, MAXCY = -57, -43, 61, 50
W, H = (MAXCX - MINCX + 1) * 32, (MAXCY - MINCY + 1) * 32      # 3808 x 3008
X0, Y0 = MINCX * 4096.0, MINCY * 4096.0                        # texel (i, j) centre = X0 + i*128, Y0 + j*128 (j south-up)
TEX = 128.0
DEFAULT_LAND = os.path.join(HERE, 'mod', 'textures', 'terrain', 'HeightMaps', 'Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds')
SEP = os.sep

# class -> list of regexes on the model path relative to meshes\ (lower case, backslashes)
CLASSES = {
    'mountains': [r'^landscape\\mountains\\', r'^landscape\\unique\\(markarthcliff|hhmountainridge)'],
    'cliffs':    [r'^landscape\\rocks\\rockcliff', r'^landscape\\rocks\\rock(caveentrance|animalden)', r'^dlc01\\landscape\\rocks\\'],
    'dirtcliffs': [r'^landscape\\dirtcliffs\\'],
    'ice':       [r'^landscape\\ice\\(glacier|iceberg)'],
    'landforms': [r'^landscape\\tundra\\rocktundraland', r'^landscape\\volcanic\\volcanicplateau'],
    'rocks':     [r'^landscape\\rocks\\(wetrocks\\)?rock(l|m|s|pile)'],
    'arches':    [r'^landscape\\unique\\solituderockarch'],          # off by default (see notes)
}
DEFAULT_CLASSES = 'mountains,cliffs,dirtcliffs,ice,landforms,rocks'


def classify(model, classes):
    for c in classes:
        for rx in CLASSES[c]:
            if re.search(rx, model):
                return c
    return None


def norm_model(m):
    m = os.path.normpath(m.lower())
    if m.startswith('meshes' + SEP):
        m = m[7:]
    return m


def ref_matrix(rx, ry, rz):
    """Skyrim REFR rotation (radians, clockwise positive about each axis): world = Rx @ Ry @ Rz @ local, i.e. the Z
    rotation is applied to the mesh first, then Y, then X. Verified against the landscape with check_rotation.py
    (floating-mesh/nif.py uses Rz @ Ry @ Rx, which is only right for untilted references)."""
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, sx], [0, -sx, cx]])
    Ry = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    Rz = np.array([[cz, sz, 0], [-sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz


# ----------------------------------------------------------------------------------------------- inputs
def load_refs(rescan=False):
    import scan
    p = os.path.join(HERE, 'refs.pkl')
    if rescan or not os.path.exists(p):
        scan.OUT = p
        scan.main()
    return pickle.load(open(p, 'rb'))


def mesh_index(rescan=False):
    import scan
    p = os.path.join(HERE, 'meshidx.pkl')
    if not rescan and os.path.exists(p):
        return pickle.load(open(p, 'rb'))
    mods, active, order, pl = scan.read_profile()
    idx = {}; bsas = []
    srcs = [os.path.join(scan.ROOT, 'overwrite')] + [os.path.join(scan.ROOT, 'mods', m) for m in mods] + [os.path.join(scan.ROOT, 'Stock Game', 'Data')]
    for s in srcs:
        for sub in ('landscape', os.path.join('dlc01', 'landscape')):
            base = os.path.join(s, 'meshes', sub)
            for dp, dn, fn in os.walk(base):
                rel = os.path.relpath(dp, os.path.join(s, 'meshes')).lower()
                for f in fn:
                    if f.lower().endswith('.nif'):
                        idx.setdefault(os.path.normpath(os.path.join(rel, f.lower())), os.path.join(dp, f))
        try:
            bsas += [os.path.join(s, e) for e in os.listdir(s) if e.lower().endswith('.bsa')]
        except OSError:
            pass
    d = dict(idx=idx, bsas=bsas)
    pickle.dump(d, open(p, 'wb'))
    return d


class MeshStore:
    """Model path -> (verts Nx3 float32, tris Mx3 int32) of all visible shapes merged, root space. Cached on disk."""
    def __init__(self, rescan=False):
        self.mi = mesh_index(rescan)
        self.cache_path = os.path.join(HERE, 'meshcache.pkl')
        self.cache = {} if rescan or not os.path.exists(self.cache_path) else pickle.load(open(self.cache_path, 'rb'))
        self.bsa_idx = None
        self.dirty = False

    def _bsa(self, model):
        import bsa
        if self.bsa_idx is None:
            self.bsa_idx = {}; self.bsa_obj = {}
            for p in self.mi['bsas']:
                if 'mesh' not in os.path.basename(p).lower() and 'Stock Game' in p:
                    continue
                try:
                    b = bsa.BSA(p)
                except Exception:
                    continue
                self.bsa_obj[p] = b
                for k in b.files:
                    if k.startswith('meshes' + SEP) and k.endswith('.nif'):
                        self.bsa_idx.setdefault(k[7:], p)
        p = self.bsa_idx.get(model)
        return (self.bsa_obj[p].read(os.path.join('meshes', model)), p) if p else (None, None)

    def get(self, model):
        if model in self.cache:
            return self.cache[model]
        import nif
        src = self.mi['idx'].get(model); origin = src
        try:
            if src is None:
                src, origin = self._bsa(model)
            if src is None:
                res = None
            else:
                sh, _, _ = nif.shapes(src)
                vs, ts, n = [], [], 0
                for s in sh:
                    if s['hidden'] or not len(s['v']) or not len(s['tris']):
                        continue
                    vs.append(s['v']); ts.append(s['tris'].astype(np.int32) + n); n += len(s['v'])
                res = (np.concatenate(vs).astype(np.float32), np.concatenate(ts), origin) if vs else None
        except Exception as e:
            print('  mesh error', model, repr(e)[:100])
            res = None
        self.cache[model] = res; self.dirty = True
        return res

    def save(self):
        if self.dirty:
            pickle.dump(self.cache, open(self.cache_path, 'wb'), protocol=4)


def read_land(path):
    b = open(path, 'rb').read()
    h, w = struct.unpack_from('<II', b, 12)
    assert (w, h) == (W, H), (w, h)
    raw = np.frombuffer(b, '<u2', w * h, 128).reshape(h, w)
    return (raw.astype(np.float32) - 32767.0) * 8.0          # row 0 = north


def select_refs(d, classes, min_footprint, store, bbox=None):
    refs, bases = d['refs'], d['bases']
    def disabled(r, depth=0):
        if r['flags'] & 0x820:
            return True
        x = r.get('xesp')
        if x and depth < 4:
            ph = refs.get(x[0])
            if ph:
                pd = disabled(ph[-1], depth + 1)
                return (not pd) if (x[1] & 1) else pd
        return False
    out = []; stats = {}
    for fk, hist in refs.items():
        r = hist[-1]
        if 'data' not in r:
            continue
        b = bases.get(r.get('base'))
        if not b or not b[2] or b[0] not in ('STAT', 'MSTT', 'ACTI'):
            continue
        m = norm_model(b[2])
        c = classify(m, classes)
        if not c:
            continue
        st = stats.setdefault(c, dict(refs=0, disabled=0, small=0, nomesh=0, used=0))
        st['refs'] += 1
        if disabled(r):
            st['disabled'] += 1; continue
        px, py, pz, rx, ry, rz = r['data']
        if bbox and not (bbox[0] - 8000 <= px <= bbox[2] + 8000 and bbox[1] - 8000 <= py <= bbox[3] + 8000):
            continue
        mesh = store.get(m)
        if mesh is None:
            st['nomesh'] += 1; continue
        s = r.get('scale') or 1.0
        v = mesh[0]
        ext = (v.max(0) - v.min(0)) * s
        if max(ext[0], ext[1]) < min_footprint:
            st['small'] += 1; continue
        st['used'] += 1
        out.append((m, c, (px, py, pz), (rx, ry, rz), s, fk))
    return out, stats


# ----------------------------------------------------------------------------------------------- rasteriser
def raster_ref(v, tris, pos, rot, scale, rot_fn=ref_matrix):
    """Return (texel flat index (south-up), top, bottom) of the solid intervals of one placed mesh."""
    R = rot_fn(*rot)
    w = (v.astype(np.float64) * scale) @ R.T + np.asarray(pos, np.float64)
    fx = (w[:, 0] - X0) / TEX; fy = (w[:, 1] - Y0) / TEX; z = w[:, 2]
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ax, ay, bx, by, cx, cy = fx[a], fy[a], fx[b], fy[b], fx[c], fy[c]
    ix0 = np.maximum(np.ceil(np.minimum(np.minimum(ax, bx), cx)), 0).astype(np.int64)
    ix1 = np.minimum(np.floor(np.maximum(np.maximum(ax, bx), cx)), W - 1).astype(np.int64)
    iy0 = np.maximum(np.ceil(np.minimum(np.minimum(ay, by), cy)), 0).astype(np.int64)
    iy1 = np.minimum(np.floor(np.maximum(np.maximum(ay, by), cy)), H - 1).astype(np.int64)
    den = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    nw = ix1 - ix0 + 1; nh = iy1 - iy0 + 1
    keep = (nw > 0) & (nh > 0) & (np.abs(den) > 1e-9)
    if not keep.any():
        return None
    k = np.flatnonzero(keep)
    cnt = nw[k] * nh[k]
    tot = int(cnt.sum())
    t = np.repeat(k, cnt)
    start = np.repeat(np.cumsum(cnt) - cnt, cnt)
    loc = np.arange(tot) - start
    wr = nw[t]
    px = ix0[t] + loc % wr
    py = iy0[t] + loc // wr
    dx = px - ax[t]; dy = py - ay[t]
    e1x = bx[t] - ax[t]; e1y = by[t] - ay[t]; e2x = cx[t] - ax[t]; e2y = cy[t] - ay[t]
    dn = den[t]
    u = (dx * e2y - e2x * dy) / dn
    vv = (e1x * dy - dx * e1y) / dn
    ins = (u >= -1e-7) & (vv >= -1e-7) & (u + vv <= 1 + 1e-7)
    if not ins.any():
        return None
    t = t[ins]; u = u[ins]; vv = vv[ins]
    zz = z[a[t]] + u * (z[b[t]] - z[a[t]]) + vv * (z[c[t]] - z[a[t]])
    tex = py[ins] * W + px[ins]
    up = den[t] > 0
    o = np.lexsort((-zz, tex))
    tex, zz, up = tex[o], zz[o], up[o]
    n = len(tex)
    first = np.ones(n, bool); first[1:] = tex[1:] != tex[:-1]
    prev_down = np.zeros(n, bool); prev_down[1:] = ~up[:-1]
    is_top = first | (up & prev_down)
    # next down-facing crossing at or below each entry (strictly after it in sort order)
    idx = np.where(~up, np.arange(n), n)
    nd = np.minimum.accumulate(idx[::-1])[::-1]              # first down index >= i
    nd_after = np.empty(n, np.int64); nd_after[:-1] = nd[1:]; nd_after[-1] = n
    ti = np.flatnonzero(is_top)
    j = np.where(up[ti], nd[ti], nd_after[ti])               # a down-facing top (seen from inside) is treated as solid below
    ok = j < n
    same = np.zeros(len(ti), bool)
    same[ok] = tex[j[ok]] == tex[ti[ok]]
    bot = np.full(len(ti), -1e9, np.float32)
    bot[same] = zz[j[same]]
    return tex[ti].astype(np.int32), zz[ti].astype(np.float32), bot


_MESH = None
def _init(meshes):
    global _MESH
    _MESH = meshes


def _work(chunk):
    T, Z, B, R = [], [], [], []
    for ri, m, pos, rot, s in chunk:
        v, tris = _MESH[m][0], _MESH[m][1]
        r = raster_ref(v, tris, pos, rot, s)
        if r is None:
            continue
        T.append(r[0]); Z.append(r[1]); B.append(r[2]); R.append(np.full(len(r[0]), ri, np.int32))
    if not T:
        return None
    return np.concatenate(T), np.concatenate(Z), np.concatenate(B), np.concatenate(R)


def rasterise_all(sel, store, workers):
    from multiprocessing import Pool
    meshes = {m: store.get(m) for m in {s[0] for s in sel}}
    jobs = [(i, s[0], s[2], s[3], s[4]) for i, s in enumerate(sel)]
    jobs.sort(key=lambda j: -len(meshes[j[1]][1]) * j[4] ** 2)        # heavy first
    chunks = [jobs[i::max(1, len(jobs) // 60)] for i in range(max(1, len(jobs) // 60))]
    out = []
    if workers <= 1:
        _init(meshes)
        out = [_work(c) for c in chunks]
    else:
        with Pool(workers, initializer=_init, initargs=(meshes,)) as p:
            for i, r in enumerate(p.imap_unordered(_work, chunks)):
                out.append(r)
    out = [o for o in out if o is not None]
    return [np.concatenate([o[k] for o in out]) for k in range(4)]


# ----------------------------------------------------------------------------------------------- compose
def minfilter(a, r):
    if r <= 0:
        return a.copy()
    p = np.pad(a, r, mode='edge'); n = 2 * r + 1
    t = p[:, 0:a.shape[1]].copy()
    for k in range(1, n):
        np.minimum(t, p[:, k:k + a.shape[1]], out=t)
    o = t[0:a.shape[0]].copy()
    for k in range(1, n):
        np.minimum(o, t[k:k + a.shape[0]], out=o)
    return o


def maxfilter(a, r):
    return -minfilter(-a, r)


def support_pass(land_su, tex, top, bot, gap):
    """land_su: south-up float32 grid. Accept intervals resting (within gap) on the current surface; iterate."""
    cur = land_su.ravel().copy()
    used = np.zeros(len(tex), bool)
    it = 0
    while True:
        it += 1
        ok = ~used & (bot <= cur[tex] + gap) & (top > cur[tex])
        if not ok.any() or it > 30:
            break
        np.maximum.at(cur, tex[ok], top[ok])
        used |= ok
        used |= top <= cur[tex]
    rejected = ~used & (top > cur[tex])
    return cur.reshape(land_su.shape), rejected, it


def compose(land, tex, top, bot, gap, filt, radius):
    """land: north-up grid. Returns final (north-up), raw surface (north-up, before filtering), info."""
    land_su = land[::-1].copy()
    surf_su, rejected, iters = support_pass(land_su, tex, top, bot, gap)
    surf = surf_su[::-1]
    if filt == 'none' or radius <= 0:
        fin = surf.copy()
    else:
        er = minfilter(surf, radius)
        if filt == 'open':
            er = np.minimum(maxfilter(er, radius), surf)
        fin = np.maximum(land, er)
    fin = np.round(fin / 8.0) * 8.0
    return fin, surf, dict(rejected=rejected, iters=iters)


def write_dds(out_dir, world, grid, template):
    zmin = int(math.floor(grid.min() / 8.0)); zmax = int(math.ceil(grid.max() / 8.0))
    raw = np.round(grid / 8.0) + 32767
    assert raw.min() >= 0 and raw.max() <= 65535
    name = '%s.Terrain.HeightMap.%d.%d.%d.%d.%d.%d.dds' % (world, MINCX, MINCY, MAXCX, MAXCY, zmin, zmax)
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):                            # never leave two maps of one worldspace in the folder
        if f.lower().startswith(world.lower() + '.terrain.heightmap.') and f != name:
            os.remove(os.path.join(out_dir, f))
    hdr = bytearray(open(template, 'rb').read(128))          # legacy L16 header (-> DXGI_FORMAT_R16_UNORM), same as the 16-bit land map
    struct.pack_into('<II', hdr, 12, grid.shape[0], grid.shape[1])
    struct.pack_into('<I', hdr, 20, grid.shape[0] * grid.shape[1] * 2)
    p = os.path.join(out_dir, name)
    with open(p, 'wb') as f:
        f.write(hdr); f.write(raw.astype('<u2').tobytes())
    return p, zmin, zmax


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--classes', default=DEFAULT_CLASSES, help='comma list of: ' + ', '.join(CLASSES) + ' (default %(default)s)')
    ap.add_argument('--min-footprint', type=float, default=512.0, help='skip objects whose scaled horizontal extent is smaller (units)')
    ap.add_argument('--gap', type=float, default=256.0, help='max air gap under an object part for it to count as terrain (units)')
    ap.add_argument('--filter', choices=['erode', 'open', 'none'], default='open',
                    help="spike filter on the combined surface: open = morphological opening (min then max over (2r+1)^2 texels, capped by the raw surface; removes anything narrower than 2r+1 texels, default); erode = min only (most conservative, shrinks objects by r texels); none. Landscape is never lowered.")
    ap.add_argument('--radius', type=int, default=1, help='filter radius in texels (default 1)')
    ap.add_argument('--land', default=DEFAULT_LAND, help='16-bit landscape height map used as the base')
    ap.add_argument('--out-dir', default=os.path.join(HERE, 'mod-objects', 'textures', 'terrain', 'HeightMaps'))
    ap.add_argument('--workers', type=int, default=min(24, os.cpu_count() or 4))
    ap.add_argument('--rescan', action='store_true', help='re-read plugins and mesh index instead of the cached pickles')
    ap.add_argument('--layers', default=os.path.join(HERE, 'objects_layers.npz'), help='npz with land/raw surface/final for the validation script')
    a = ap.parse_args()
    t0 = time.time()
    classes = [c for c in a.classes.split(',') if c]
    for c in classes:
        assert c in CLASSES, c
    land = read_land(a.land)
    d = load_refs(a.rescan)
    store = MeshStore(a.rescan)
    sel, stats = select_refs(d, classes, a.min_footprint, store)
    store.save()
    print('selected refs: %d  (%.1fs)' % (len(sel), time.time() - t0))
    for c, s in stats.items():
        print('  %-10s %s' % (c, s))
    tex, top, bot, rid = rasterise_all(sel, store, a.workers)
    print('object/texel intervals: %d (%.1fs)' % (len(tex), time.time() - t0))
    fin, surf, info = compose(land, tex, top, bot, a.gap, a.filter, a.radius)
    rej = info['rejected']
    path, zmin, zmax = write_dds(a.out_dir, 'Tamriel', fin, a.land)
    dl = fin - land; ds = surf - land
    rep = dict(output=path, zmin_field=zmin, zmax_field=zmax, classes=classes, min_footprint=a.min_footprint, gap=a.gap, filter=a.filter, radius=a.radius,
               refs_used=len(sel), class_stats=stats, intervals=int(len(tex)), intervals_rejected_unsupported=int(rej.sum()), support_iterations=info['iters'],
               texels_total=int(fin.size),
               raw_surface=dict(raised=int((ds > 0).sum()), raised_gt128=int((ds > 128).sum()), mean_raise=float(ds[ds > 0].mean()), max_raise=float(ds.max()), max_height=float(surf.max())),
               final=dict(raised=int((dl > 0).sum()), raised_gt128=int((dl > 128).sum()), raised_gt512=int((dl > 512).sum()), raised_gt2000=int((dl > 2000).sum()),
                          mean_raise=float(dl[dl > 0].mean()), median_raise=float(np.median(dl[dl > 0])), p99_raise=float(np.percentile(dl[dl > 0], 99)),
                          max_raise=float(dl.max()), max_height=float(fin.max()), land_max=float(land.max()), min_height=float(fin.min())),
               seconds=round(time.time() - t0, 1))
    # the project-level report/layers feed validate_objects.py; variant builds (--layers "") keep their report beside the DDS tree
    json.dump(rep, open(os.path.join(HERE, 'objects_report.json') if a.layers else os.path.join(a.out_dir, '..', '..', '..', 'objects_report.json'), 'w'), indent=1)
    print(json.dumps(rep, indent=1))
    if a.layers:
        np.savez_compressed(a.layers, land=land, surf=surf, final=fin)
        np.savez_compressed(os.path.join(HERE, 'objects_intervals.npz'), tex=tex, top=top, bot=bot, rid=rid, rejected=rej)
        pickle.dump(sel, open(os.path.join(HERE, 'objects_sel.pkl'), 'wb'))


if __name__ == '__main__':
    main()

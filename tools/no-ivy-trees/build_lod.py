"""Build DynDOLOD 3D tree LOD models (passthru) for the No Ivy Trees meshes that have none.

usage:  python -I build_lod.py [--preview] [--simplified] [stem ...]

DEFAULT (what is installed): UNSIMPLIFIED. These trees are placed only 86 times, so the LOD keeps every vertex and triangle
of the full model (leaves + decorations -> shapes 'crown', bark -> shape 'trunk'), as a static nif: BSFadeNode + BSTriShape +
shader + texture set (+ NiAlphaProperty on crowns) only; no collision, BSX, extra data or tree anim blocks. Shader / alpha
blocks are the NWL passthru LOD ones (crown: two-sided, alpha test 64; trunk: opaque). Vertex colour flat 201 as the NWL LODs.
Bark UVs are the full model's and tile far outside 0..1, so LODGen cannot put the bark on the object LOD atlas and uses the
bark texture directly (leaf UVs are inside 0..1). Nothing in the file depends on the LOD level (LOD4 / 8 / 16 alike).
--simplified builds the earlier decimated variant described below instead.

Reads the full models in mods\\foxnne - No Ivy Trees\\meshes\\landscape\\trees (never written), writes
mods\\foxnne - No Ivy Trees\\meshes\\dyndolod\\lod\\trees\\<stem>_<crc32 of the full nif, lower case>passthru_lod.nif
and work\\lod_report.json (+ work\\lodview_<stem>.png with --preview: full | LOD, two side views, no alpha).
Stems that already have a LOD for their current CRC from elsewhere (the 3 upstream copies) are skipped.

Same approach and block template as C:\\Users\\foxnn\\dev\\aspen-lod\\tools\\build_aspen_lod.py (imported):
  crown  one shape 'crown' per leaf texture set. The full model's leaves are separate 3/4/5-vertex cards; a subset is kept
         (evenly along a Morton curve, silhouette cards always kept, big branch cards at twice the rate) and grown about
         its centre to keep the canopy area. Kept vertices are the full model's own bytes (uv, normal, tangent, colour
         201); only positions change. 5-vertex cards lose their centre vertex (2 triangles) except every 20th.
         Shader / alpha blocks = NWL passthru LOD crown (no Soft_Lighting, vc 0.788, alpha test 64 like the upstream LODs).
  trunk  one shape 'trunk': ground-touching bark tubes rebuilt as 5-sided tubes up to the first fork, limbs and boughs
         as chains of 4-vertex spikes. Bark texture of the full model, UVs mirrored inside 0..1. vc 201.
  The small 'decorations' shape (mushrooms / mistletoe, 125-344 triangles, < 70 units) is left out.
No vertex colour data other than the flat 201. Nothing is brightened.
"""
import sys, os, json, struct, zlib, glob, collections
sys.path.insert(0, r'C:\Users\foxnn\dev\giant-tree-wind')
sys.path.insert(0, r'C:\Users\foxnn\dev\snow-audit\tools')
sys.path.insert(0, r'C:\Users\foxnn\dev\aspen-lod\tools')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import nifio
import build_aspen_lod as A
import niflib

MODDIR = r'C:\Modlists\NGVO 8.0 Beta\mods\foxnne - No Ivy Trees\meshes'
SRC = os.path.join(MODDIR, 'landscape', 'trees')
OUT = os.path.join(MODDIR, 'dyndolod', 'lod', 'trees')
WORK = r'C:\Users\foxnn\dev\no-ivy-trees\work'

CROWN_FRAC, CROWN_MIN, CROWN_MAX = 0.40, 1200, 2600     # crown triangle budget = clamp(frac * full leaf tris, min, max)
BIG_CARD, BIG_RATIO = 180.0, 2.0
MAX_SCALE = 1.8
FULL_EVERY = 20
ALPHA = 64
FORK_RATIO = 1.6
STEM_MAX_WIDTH = 220.0           # Tree Wind: a 3D trunk piece is narrower than 240 (world units) ...
STEM_MIN_ASPECT = 3.06           # ... and taller than 3 x its width (and than 64 model units)
SLICE = 60.0                     # trunk slice height: at least one full vertex ring per slice (30 gave half rings, false forks)
LEAN_MAX = 1.5                   # tube ends where the slice centre moves sideways faster than this x its rise
BOUGH_MAX = 16
A.TRUNK_RINGS_MAX = 9


def card_list(s):
    """-> list of dict(idx (vertex indices, outline first), tris_lod, tris_full, centre, size)"""
    P, tris = s['P'], s['tris']
    lab = A.components(tris, P)
    tl = lab[tris[:, 0]]
    order = np.argsort(tl, kind='stable')
    bounds = np.r_[0, np.nonzero(np.diff(tl[order]))[0] + 1, len(order)]
    cards = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        t = tris[order[a:b]]
        idx = np.unique(t)
        full = np.searchsorted(idx, t)
        lod = full
        if len(idx) == 5 and len(t) == 4:
            cnt = np.bincount(full.ravel(), minlength=5)
            c = int(np.argmax(cnt))
            if cnt[c] == 4:                                              # fan around a centre vertex: keep the outline
                ring = {}
                for tr in full:
                    k = list(tr).index(c)
                    ring[int(tr[(k + 1) % 3])] = int(tr[(k + 2) % 3])   # oriented edge opposite the centre
                r = [next(iter(ring))]
                while len(r) < 4 and ring.get(r[-1]) is not None and ring[r[-1]] not in r:
                    r.append(ring[r[-1]])
                if len(r) == 4:
                    lod = np.array([[r[0], r[1], r[2]], [r[0], r[2], r[3]]])
        p = P[idx]
        cards.append(dict(idx=idx, full=full, lod=lod, centre=p.mean(0), size=float(np.linalg.norm(p.max(0) - p.min(0)))))
    return cards


def pick_even(cen, n_keep, lo, hi):
    n = len(cen)
    if n_keep >= n:
        return list(range(n))
    order = np.argsort(A.morton(cen, lo, hi), kind='stable')
    return sorted(set(int(order[int((k + 0.5) * n / n_keep)]) for k in range(n_keep)))


def build_crown(full, log):
    leaves = [s for s in full['shapes'] if s['leafy'] and 'decor' not in s['name'].lower()]
    allP = np.concatenate([s['P'] for s in leaves])
    lo, hi = allP.min(0), allP.max(0)
    rmax = float(np.hypot(allP[:, 0], allP[:, 1]).max())
    src_tris = sum(len(s['tris']) for s in leaves)
    budget = int(np.clip(CROWN_FRAC * src_tris, CROWN_MIN, CROWN_MAX))
    groups = collections.OrderedDict()
    stats = []
    for s in leaves:
        cards = card_list(s)
        cen = np.array([c['centre'] for c in cards])
        big = np.array([c['size'] > BIG_CARD for c in cards])
        tpc = np.array([len(c['lod']) for c in cards], float)
        share = budget * len(s['tris']) / src_tris

        def total(f):
            return (tpc[~big].sum() * min(1, f) + tpc[big].sum() * min(1, BIG_RATIO * f)) * (1 + 2.0 / FULL_EVERY / 2)
        f = 1.0
        if total(1.0) > share:
            a, b = 0.0, 1.0
            for _ in range(40):
                f = (a + b) / 2
                a, b = (f, b) if total(f) < share else (a, f)
            f = a
        keep = set()
        for mask, frac in ((~big, min(1, f)), (big, min(1, BIG_RATIO * f))):
            ids = np.nonzero(mask)[0]
            if len(ids):
                keep |= set(int(ids[k]) for k in pick_even(cen[ids], max(1, int(round(len(ids) * frac))), lo, hi))
        forced = {int(np.argmax(cen[:, 2])), int(np.argmin(cen[:, 2]))}
        ang = np.floor((np.arctan2(cen[:, 1], cen[:, 0]) + np.pi) / (2 * np.pi) * 16).astype(int) % 16
        rad = np.hypot(cen[:, 0], cen[:, 1])
        for k in range(16):
            m = np.nonzero(ang == k)[0]
            if len(m):
                forced.add(int(m[np.argmax(rad[m])]))
        keep |= forced
        kept = sorted(keep)
        area_frac = sum(cards[k]['size'] ** 2 for k in kept) / sum(c['size'] ** 2 for c in cards)
        scale = float(min(MAX_SCALE, 1.0 / np.sqrt(area_frac)))
        key = tuple(t.lower() for t in s['tex'][:2])
        g = groups.setdefault(key, dict(tex=s['tex'], raw=[], tris=[], nv=0))
        nfull = 0
        for j, k in enumerate(kept):
            c = cards[k]
            tr = c['lod']
            if tr is not c['full'] and j % FULL_EVERY == FULL_EVERY // 2:
                tr = c['full']; nfull += 1
            used = np.unique(tr)
            idx = c['idx'][used]
            P = c['centre'] + scale * (s['P'][idx] - c['centre'])
            P = np.clip(P, lo, hi)
            r = np.hypot(P[:, 0], P[:, 1])
            over = r > rmax
            P[over, :2] *= (rmax / r[over])[:, None]
            raw = np.array(s['raw'])[idx].copy()
            raw[:, 0:12] = np.asarray(P, '<f4').view(np.uint8).reshape(len(P), 12)
            raw[:, 28:32] = (A.CROWN_VC, A.CROWN_VC, A.CROWN_VC, 255)
            g['raw'].append(raw); g['tris'].append(np.searchsorted(used, tr) + g['nv']); g['nv'] += len(P)
        stats.append(dict(shape=s['name'], source_tris=int(len(s['tris'])), cards=len(cards), kept=len(kept), big_cards=int(big.sum()),
                          full_geometry_cards=nfull, scale=round(scale, 3)))
    log['crown'] = dict(budget=budget, sources=stats)
    return [dict(tex=g['tex'], raw=np.concatenate(g['raw']), tris=np.concatenate(g['tris'])) for g in groups.values()]


def limb_axis(pv):
    cen = pv.mean(0)
    w, vec = np.linalg.eigh(np.cov((pv - cen).T))
    ax = vec[:, -1]
    t = (pv - cen) @ ax
    radial = np.linalg.norm((pv - cen) - np.outer(t, ax), axis=1)
    return dict(pv=pv, cen=cen, ax=ax, t=t, length=float(np.ptp(t)), radius=float(np.median(radial)))


def build_trunk(full, log):
    bark = [s for s in full['shapes'] if not s['leafy']]
    assert len(bark) == 1, 'expected one bark shape'
    s = bark[0]
    P, tris = s['P'], s['tris']
    H = float(max(x['P'][:, 2].max() for x in full['shapes']))
    lab = A.components(tris, P)
    # a trunk modelled as a root flare piece + a stem piece (alder_forest_slim, elm_forest_*): join the stem to the flare
    ext = {int(c): (P[lab == c][:, 2].min(), P[lab == c][:, 2].max()) for c in np.unique(lab)}
    joined = []
    for g, (g0, g1) in list(ext.items()):
        if not (g0 < 0.1 * H and g1 - g0 <= 0.3 * H):
            continue
        pg = P[lab == g]
        top = pg[pg[:, 2] > g1 - 0.15 * (g1 - g0)][:, :2].mean(0)
        best = None
        for c, (c0, c1) in ext.items():
            if c == g or c0 < 0.05 * H or not (max(g1 - 0.1 * H, (g0 + g1) / 2) <= c0 <= g1 + 10 and c1 - c0 > 0.3 * H):
                continue
            pc = P[lab == c]
            d = float(np.linalg.norm(pc[pc[:, 2] <= c0 + 30][:, :2].mean(0) - top))
            if d < 80 and (best is None or d < best[0]):
                best = (d, c)
        if best:
            lab[lab == best[1]] = g
            joined.append(round(best[0], 1))
    log['trunk_joined'] = joined
    tlab = lab[tris[:, 0]]
    mesh = A.Mesh()
    tlog, boughs = [], []
    rcap = 1e9
    for c in np.unique(lab):
        vm = lab == c
        pv = P[vm]
        z0, z1 = pv[:, 2].min(), pv[:, 2].max()
        if not (z0 < 0.1 * H and z1 - z0 > 0.3 * H):
            boughs.append(limb_axis(pv))
            continue
        edges = np.linspace(z0, z1, max(8, int((z1 - z0) / SLICE)) + 1)
        zs, cs, rs = [], [], []
        for a, b in zip(edges[:-1], edges[1:]):
            q = pv[(pv[:, 2] >= a) & (pv[:, 2] <= b)]
            if len(q) >= 6:
                cen = q[:, :2].mean(0)
                zs.append(q[:, 2].mean()); cs.append(cen); rs.append(np.median(np.linalg.norm(q[:, :2] - cen, axis=1)))
        zs, cs, rs = np.array(zs), np.array(cs), np.array(rs)
        # first fork: the slice radius jumps above the thinnest slice below it (and stays there)
        ztop, fork = z1, False
        for i in range(2, len(zs) - 1):
            if zs[i] < z0 + 0.15 * (z1 - z0):
                continue
            ref = rs[:i].min()
            lean = np.linalg.norm(cs[i] - cs[i - 1]) > LEAN_MAX * (zs[i] - zs[i - 1])   # the stem turns into a limb
            if lean or (rs[i] > FORK_RATIO * ref and rs[i + 1] > FORK_RATIO * ref):
                ztop, fork = float(zs[i - 1]), True
                break
        m = zs <= ztop + 1e-6
        zs_, cs_, rs_ = zs[m], cs[m], rs[m]
        K = int(np.clip(round((ztop - z0) / A.TRUNK_RING_SPACING) + 1, 4, A.TRUNK_RINGS_MAX))
        zr = z0 + (ztop - z0) * (np.linspace(0, 1, K) ** 1.25)
        cen = np.c_[np.interp(zr, zs_, cs_[:, 0]), np.interp(zr, zs_, cs_[:, 1]), zr]
        rad = np.minimum.accumulate(np.interp(zr, zs_, rs_) * A.TRUNK_RADIUS_SCALE)
        if not fork:
            rad[-1] = max(rad[-1] * 0.5, 0.5)
        cen[0, 2] = z0 - A.TRUNK_SINK * H
        rcap = min(rcap, float(rad[-1])) if fork else rcap

        def width(k):
            x = np.r_[cen[:k, 0] - rad[:k], cen[:k, 0] + rad[:k]]
            y = np.r_[cen[:k, 1] - rad[:k], cen[:k, 1] + rad[:k]]
            return max(np.ptp(x), np.ptp(y))
        # Tree Wind's 3D trunk test (narrower than 240, taller than 3 x width): cut a leaning top into a spike when a short
        # cut is enough; a trunk that is simply too thick is left whole (it will not register, the crown then stays still)
        keep = K
        while keep > 3 and (width(keep) > A.TRUNK_MAX_WIDTH or (cen[keep - 1, 2] - cen[0, 2]) < 3.3 * width(keep)):
            keep -= 1
        passes = not (width(keep) > A.TRUNK_MAX_WIDTH or (cen[keep - 1, 2] - cen[0, 2]) < 3.3 * width(keep))
        if not passes or keep < max(4, K - 2) or fork:
            if not (passes and keep == K):
                passes = False if keep < K else passes
            keep = K
        A.add_tube(mesh, cen[:keep], rad[:keep])
        if keep < K:
            A.add_spike(mesh, cen[keep - 1].copy(), rad[keep - 1], cen[-1].copy())
        tlog.append(dict(z=[round(float(z0), 1), round(float(z1), 1)], tube_top=round(ztop, 1), fork=fork, rings=int(keep),
                         base_radius=round(float(rad[0]), 1), top_radius=round(float(rad[-1]), 1), width=round(float(width(keep)), 1),
                         tree_wind_trunk=bool(passes)))
        if fork:                                                         # limbs above the fork: connected pieces of what is left
            tt = tris[(tlab == c)]
            tt = tt[(P[tt][:, :, 2] > ztop).all(1)]
            if len(tt):
                used = np.unique(tt)
                sub = A.components(np.searchsorted(used, tt), P[used])
                for k in np.unique(sub):
                    q = P[used][sub == k]
                    if len(q) >= 8:
                        boughs.append(limb_axis(q))
    cand = [b for b in boughs if b['length'] >= A.BOUGH_MIN_LEN_FRAC * H and b['radius'] >= A.BOUGH_MIN_RADIUS]
    cand.sort(key=lambda b: -b['length'] * b['radius'])
    for b in cand[:BOUGH_MAX]:
        pv, t, ax = b['pv'], b['t'], b['ax']
        nseg = int(np.clip(round(b['length'] / A.BOUGH_SEG_LEN), 1, 3))
        ts = np.linspace(t.min(), t.max(), nseg + 1)
        win = 0.12 * b['length']
        pts, rads = [], []
        for x in ts:
            m = np.abs(t - x) <= win
            if m.sum() < 4:
                m = np.zeros(len(t), bool)
                m[np.argsort(np.abs(t - x))[:6]] = True
            q = pv[m]
            c0 = q.mean(0)
            dd = (q - c0) - np.outer((q - c0) @ ax, ax)
            pts.append(c0); rads.append(np.median(np.linalg.norm(dd, axis=1)) * A.TRUNK_RADIUS_SCALE)
        pts, rads = np.array(pts), np.array(rads)
        if rads[-1] > rads[0] or (abs(rads[-1] - rads[0]) < 1e-6 and pts[-1][2] < pts[0][2]):
            pts, rads = pts[::-1], rads[::-1]
        rads = np.clip(np.minimum.accumulate(rads), 1.0, rcap)
        for i in range(nseg):
            A.add_spike(mesh, pts[i], rads[i], pts[i + 1])
    log['trunk'] = dict(tubes=tlog, limb_pieces=len(boughs), limbs_built=len(cand[:BOUGH_MAX]), source_tris=int(len(tris)))
    return dict(tex=s['tex'], P=np.concatenate(mesh.P), uv=np.concatenate(mesh.uv), N=np.concatenate(mesh.N),
                Tu=np.concatenate(mesh.Tu), Tv=np.concatenate(mesh.Tv), tris=np.concatenate(mesh.tris))


def assemble(tpl, crowns, trunk, conv):
    strings = ['Scene Root', 'crown', 'trunk']
    blocks = [None]
    children = []
    for c in crowns:
        i = len(blocks)
        children.append(i)
        blocks.append(('BSTriShape', A.shape_block(tpl, 1, tpl.crown_flags, i + 1, i + 3, c['raw'], c['tris'])))
        blocks.append(('BSLightingShaderProperty', A.shader_block(tpl.crown_shader, tpl.crown_ls, i + 2)))
        blocks.append(('BSShaderTextureSet', A.texset_block(c['tex'][:2])))
        blocks.append(('NiAlphaProperty', A.alpha_block(tpl.crown_alpha, ALPHA)))
    i = len(blocks)
    children.append(i)
    d = [trunk['Tu'], trunk['Tv']]
    raw = A.pack_vertices(trunk['P'], trunk['uv'], trunk['N'], d[conv[0][0]] * conv[0][1], d[conv[1][0]] * conv[1][1],
                          (A.TRUNK_VC, A.TRUNK_VC, A.TRUNK_VC, 255))
    blocks.append(('BSTriShape', A.shape_block(tpl, 2, tpl.flat_flags, i + 1, -1, raw, trunk['tris'])))
    blocks.append(('BSLightingShaderProperty', A.shader_block(tpl.flat_shader, tpl.flat_ls, i + 2)))
    blocks.append(('BSShaderTextureSet', A.texset_block(trunk['tex'][:2])))
    blocks[0] = ('BSFadeNode', A.root_block(tpl, children))
    return A.write_nif(tpl, blocks, strings)


def build_full(full, log):
    """Unsimplified: every vertex and triangle of the full model's shapes, byte for byte, except the vertex colour, which
    is set to the flat LOD value (201). Leaf / decoration shapes (alpha tested) -> 'crown', bark -> 'trunk'."""
    shapes = []
    H = float(max(x['P'][:, 2].max() for x in full['shapes']))
    for s in full['shapes']:
        raw = np.array(s['raw']).copy()
        assert raw.shape[1] == A.VSIZE and len(raw) < 65536 and len(s['tris']) < 65536
        assert np.allclose(raw[:, 0:12].copy().view('<f4').reshape(-1, 3), s['P'], atol=1e-3), 'shape not in root space'
        vc = A.CROWN_VC if s['leafy'] else A.TRUNK_VC
        raw[:, 28:32] = (vc, vc, vc, 255)
        if s['leafy']:
            shapes.append(dict(kind='crown', leafy=True, tex=s['tex'], raw=raw, tris=np.asarray(s['tris']), source=s['name']))
            continue
        # Bark: the stem goes into the one-sided 'trunk' shape (Tree Wind kind Trunk: it registers the tree), the rest of
        # the bark into a two-sided 'trunk' shape (Tree Wind kind Crown at LOD4: it follows the stem like the leaves).
        tris = np.asarray(s['tris'])
        st = find_stem(s['P'], tris, H, log)
        if st is not None and st.any() and not st.all():
            parts = [('stem', st), ('limbs', ~st)]
        else:
            parts = [('stem' if st is not None else 'limbs', np.ones(len(tris), bool))]
        for kind, m in parts:
            used = np.unique(tris[m])
            r, t = raw[used], np.searchsorted(used, tris[m])
            if kind == 'stem':
                r, t = no_card_order(r, t)
            shapes.append(dict(kind=kind, leafy=False, tex=s['tex'], raw=r, tris=t, source=s['name']))
    shapes.sort(key=lambda x: ('crown', 'stem', 'limbs').index(x['kind']))
    log['shapes'] = [dict(source=x['source'], kind=x['kind'], tris=int(len(x['tris'])), verts=int(len(x['raw']))) for x in shapes]
    return shapes


def piece_ok(pv):
    """Tree Wind's 3D-trunk piece test (TreeShapes.cpp BendWeights::Get, world units at LOD4) with a margin."""
    w = max(np.ptp(pv[:, 0]), np.ptp(pv[:, 1])); h = np.ptp(pv[:, 2])
    return len(pv) >= 6 and w < STEM_MAX_WIDTH and h > 256 and h > STEM_MIN_ASPECT * w


def find_stem(P, tris, H, log):
    """Triangle mask of the stem: the tallest connected run of bark between two heights, starting near the ground, that
    passes Tree Wind's trunk-piece test. Triangles are taken whole (no geometry is cut): the stem ends where the
    bark gets too wide (root flare below, first big fork above)."""
    lab = A.components(tris, P)
    tl = lab[tris[:, 0]]
    tz0, tz1 = P[tris][:, :, 2].min(1), P[tris][:, :, 2].max(1)
    best = None
    for c in np.unique(lab):
        pc = P[lab == c]
        z0, z1 = pc[:, 2].min(), pc[:, 2].max()
        if z0 > 0.3 * H or z1 - z0 < 256 or np.hypot(*pc[pc[:, 2] <= z0 + 60][:, :2].mean(0)) > 200:
            continue
        tc = np.nonzero(tl == c)[0]
        for lo in [z0 - 1] + [z0 + d for d in range(20, 340, 20) if z0 + d < z1]:
            for hi in np.arange(z1 + 1, lo + 256, -10.0):
                if best is not None and hi - lo <= best[0]:
                    break
                sel = tc[(tz0[tc] >= lo) & (tz1[tc] <= hi)]
                if len(sel) < 4:
                    continue
                used = np.unique(tris[sel])
                sub = A.components(np.searchsorted(used, tris[sel]), P[used])
                k = sub[np.argmin(P[used][:, 2])]                        # the piece that holds the lowest vertex
                pv = P[used][sub == k]
                if piece_ok(pv) and pv[:, 2].min() < min(lo + 60, 0.3 * H) and np.ptp(pv[:, 2]) > (best[0] if best else 0):
                    keep = sel[sub[np.searchsorted(used, tris[sel][:, 0])] == k]
                    best = (float(np.ptp(pv[:, 2])), keep, pv)
                    break
    if best is None:
        log['stem'] = None
        return None
    pv = best[2]
    log['stem'] = dict(z=[round(float(pv[:, 2].min()), 1), round(float(pv[:, 2].max()), 1)],
                       centre=[round(float(pv[:, 0].mean()), 1), round(float(pv[:, 1].mean()), 1)],
                       width=round(float(max(np.ptp(pv[:, 0]), np.ptp(pv[:, 1]))), 1), verts=int(len(pv)))
    m = np.zeros(len(tris), bool)
    m[best[1]] = True
    return m


def card_quads(P, scale):
    """Port of IsCardQuad over 4 consecutive vertices (model units = world / scale) + the partner rule (centres < 8)."""
    Q = P / scale
    cands = []
    i = 0
    while i + 3 < len(Q):
        p = Q[i:i + 4][np.argsort(Q[i:i + 4, 2], kind='stable')]
        low, high = p[:2], p[2:]
        h = (high[0, 2] + high[1, 2] - low[0, 2] - low[1, 2]) * 0.5
        ok = not (h < 32 or low[1, 2] - low[0, 2] > 0.1 * h or high[1, 2] - high[0, 2] > 0.1 * h)
        if ok:
            wl = np.hypot(*(low[0, :2] - low[1, :2])); wh = np.hypot(*(high[0, :2] - high[1, :2]))
            off = np.hypot(*((low[0, :2] + low[1, :2] - high[0, :2] - high[1, :2]) * 0.5))
            ok = wl > 0.5 and wl < h and wh <= wl * 1.5 + 1 and off < 0.25 * h + 1
        if ok:
            cands.append(Q[i:i + 4, :2].mean(0)); i += 4
        else:
            i += 1
    n = 0
    for a in range(len(cands)):
        if any(a != b and np.hypot(*(cands[a] - cands[b])) < 8 for b in range(len(cands))):
            n += 1
    return n


def no_card_order(raw, tris):
    """Vertex order of the stem in which no 4 consecutive vertices read as a flat trunk card to Tree Wind (a card would
    register as a second trunk). Order only: positions, attributes and triangles are unchanged."""
    P = raw[:, :12].copy().view('<f4').reshape(-1, 3).astype(float)
    rng = np.random.RandomState(7)
    order = np.arange(len(raw))
    for _ in range(50):
        if card_quads(P[order], 1.0) == 0 and card_quads(P[order], 4.0) == 0:
            break
        order = rng.permutation(len(raw))
    else:
        raise AssertionError('no card-free vertex order found')
    inv = np.empty(len(order), np.int64)
    inv[order] = np.arange(len(order))
    return raw[order], inv[tris]


def assemble_full(tpl, shapes):
    strings = ['Scene Root', 'crown', 'trunk']
    blocks = [None]
    children = []
    for c in shapes:
        i = len(blocks)
        children.append(i)
        if c['leafy']:
            blocks.append(('BSTriShape', A.shape_block(tpl, 1, tpl.crown_flags, i + 1, i + 3, c['raw'], c['tris'])))
            blocks.append(('BSLightingShaderProperty', A.shader_block(tpl.crown_shader, tpl.crown_ls, i + 2)))
            blocks.append(('BSShaderTextureSet', A.texset_block(c['tex'][:2])))
            blocks.append(('NiAlphaProperty', A.alpha_block(tpl.crown_alpha, ALPHA)))
        else:
            sh = bytearray(A.shader_block(tpl.flat_shader, tpl.flat_ls, i + 2))
            if c['kind'] == 'limbs':                                     # Double_Sided: Tree Wind then reads it as crown
                f2 = struct.unpack_from('<I', sh, tpl.flat_ls['flags_offset'] + 4)[0]
                struct.pack_into('<I', sh, tpl.flat_ls['flags_offset'] + 4, f2 | 0x10)
            blocks.append(('BSTriShape', A.shape_block(tpl, 2, tpl.flat_flags, i + 1, -1, c['raw'], c['tris'])))
            blocks.append(('BSLightingShaderProperty', bytes(sh)))
            blocks.append(('BSShaderTextureSet', A.texset_block(c['tex'][:2])))
    blocks[0] = ('BSFadeNode', A.root_block(tpl, children))
    return A.write_nif(tpl, blocks, strings)


def preview(stem, full, lod_path):
    from PIL import Image, ImageDraw
    n = nifio.Nif(open(lod_path, 'rb').read())
    lod = [(n.shape(i)['name'], n.to_root(i, n.shape(i)['v']), n.shape(i)['tris']) for i in range(len(n.blocks)) if n.block_type(i) in nifio.SHAPE_TYPES]
    ful = [(s['name'], s['P'], s['tris']) for s in full['shapes']]
    allp = np.concatenate([p for _, p, _ in ful])
    lo, hi = allp.min(0), allp.max(0)
    S = 520
    sc = (S - 20) / max(hi - lo)
    im = Image.new('RGB', (S * 4, S), (235, 235, 235))
    d = ImageDraw.Draw(im, 'RGBA')
    for col, (shapes, ax) in enumerate(((ful, 0), (lod, 0), (ful, 1), (lod, 1))):
        for name, p, t in sorted(shapes, key=lambda x: 'trunk' not in x[0].lower()):
            fill = (90, 60, 40, 255) if 'trunk' in name.lower() else (30, 110, 30, 70)
            x = col * S + S / 2 + (p[:, ax] - (lo[ax] + hi[ax]) / 2) * sc
            y = S - 10 - (p[:, 2] - lo[2]) * sc
            for tr in t:
                d.polygon([(x[k], y[k]) for k in tr], fill=fill)
    im.save(os.path.join(WORK, 'lodview_%s.png' % stem))


def main(argv):
    do_prev = '--preview' in argv
    simplified = '--simplified' in argv
    want = [a.lower() for a in argv if not a.startswith('--')]
    tpl = A.Template()
    existing = [f.lower() for f in os.listdir(OUT)]
    report = []
    for path in sorted(glob.glob(os.path.join(SRC, '*.nif'))):
        stem = os.path.basename(path)[:-4].lower()
        if want and stem not in want:
            continue
        full = A.load_full(path)
        name = '%s_%08xpassthru_lod.nif' % (stem, full['crc'])
        log = collections.OrderedDict(stem=stem, crc='%08x' % full['crc'], file=name)
        mine = os.path.join(OUT, name)
        marker = any(f == name for f in existing) and not is_ours(mine)
        if marker:
            print('%-40s skipped: upstream LOD present' % stem)
            continue
        for old in existing:                                             # stale builds of ours for another CRC
            if old.startswith(stem + '_') and old != name and is_ours(os.path.join(OUT, old)):
                os.remove(os.path.join(OUT, old))
        if not simplified:
            shapes = build_full(full, log)
            data = assemble_full(tpl, shapes)
            with open(mine, 'wb') as f:
                f.write(data)
            log['bytes'] = len(data)
            log['crown_tris'] = sum(x['tris'] for x in log['shapes'] if x['kind'] == 'crown')
            log['trunk_tris'] = sum(x['tris'] for x in log['shapes'] if x['kind'] != 'crown')
            log['full_tris'] = int(sum(len(x['tris']) for x in full['shapes']))
            report.append(log)
            print('%-34s crown %5d bark %5d (full %5d) %7d B  stem %s  %s' % (stem, log['crown_tris'], log['trunk_tris'], log['full_tris'], len(data), log.get('stem'), [(x['kind'], x['tris']) for x in log['shapes']]))
            if do_prev:
                preview(stem, full, mine)
            continue
        leaf = next(s for s in full['shapes'] if s['leafy'])
        conv, _ = A.tangent_convention(dict(leaf, v=leaf['P']))
        crowns = build_crown(full, log)
        trunk = build_trunk(full, log)
        data = assemble(tpl, crowns, trunk, conv)
        with open(mine, 'wb') as f:
            f.write(data)
        log['bytes'] = len(data)
        log['crown_tris'] = int(sum(len(c['tris']) for c in crowns)); log['trunk_tris'] = int(len(trunk['tris']))
        fa = np.concatenate([s['P'] for s in full['shapes']])
        la = np.concatenate([trunk['P']] + [c['raw'][:, :12].copy().view('<f4').reshape(-1, 3) for c in crowns])
        log['height'] = [round(float(fa[:, 2].max()), 1), round(float(la[:, 2].max()), 1)]
        log['radius'] = [round(float(np.hypot(fa[:, 0], fa[:, 1]).max()), 1), round(float(np.hypot(la[:, 0], la[:, 1]).max()), 1)]
        log['full_tris'] = int(sum(len(s['tris']) for s in full['shapes']))
        report.append(log)
        t = log['trunk']
        print('%-34s crown %4d trunk %3d (full %5d) %6d B  h %s r %s  tubes %s limbs %d/%d  crown %s' % (
            stem, log['crown_tris'], log['trunk_tris'], log['full_tris'], len(data), log['height'], log['radius'],
            [(x['rings'], x['fork'], x['base_radius'], x['tree_wind_trunk']) for x in t['tubes']], t['limbs_built'], t['limb_pieces'],
            [(x['kept'], x['cards'], x['scale']) for x in log['crown']['sources']]))
        if do_prev:
            preview(stem, full, mine)
    json.dump(report, open(os.path.join(WORK, 'lod_report.json'), 'w'), indent=1)
    print('wrote', len(report))


def is_ours(path):
    """our LODs have a shape named 'trunk'; the upstream ones have 'DoNothing FlatTrunk' cards"""
    try:
        return b'DoNothing FlatTrunk' not in open(path, 'rb').read(4096)
    except OSError:
        return False


if __name__ == '__main__':
    main(sys.argv[1:])

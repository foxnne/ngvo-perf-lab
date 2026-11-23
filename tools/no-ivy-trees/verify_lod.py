"""Re-check the 3D tree LODs in mods\\foxnne - No Ivy Trees\\meshes\\dyndolod\\lod\\trees (read-only).

usage:  python -I verify_lod.py

Per LOD file: re-open with niflib (parse, byte round trip, every block reachable), block types (static only), file name CRC vs
the current full nif, per shape name / triangles / vertices / shader flags / alpha threshold / textures, UV range, vertex colour
(must be one flat value), degenerate triangles, bounds vs the full model, and whether every referenced texture exists in the
active mod list (loose or BSA). Then triangle totals of the 3 upstream reference LODs and the WardenWood pine LODs.
"""
import sys, os, struct, zlib, glob
sys.path.insert(0, r'C:\Users\foxnn\dev\giant-tree-wind')
sys.path.insert(0, r'C:\Users\foxnn\dev\snow-audit\tools')
sys.path.insert(0, r'C:\Users\foxnn\dev\aspen-lod\tools')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import niflib, geom
import build_aspen_lod as A

MODDIR = r'C:\Modlists\NGVO 8.0 Beta\mods\foxnne - No Ivy Trees\meshes'
SRC = os.path.join(MODDIR, 'landscape', 'trees')
OUT = os.path.join(MODDIR, 'dyndolod', 'lod', 'trees')
PINES = r'C:\Modlists\NGVO 8.0 Beta\mods\foxnne - WardenWood Pines\meshes\dyndolod\lod\trees'
ALLOWED = {'BSFadeNode', 'BSTriShape', 'BSLightingShaderProperty', 'BSShaderTextureSet', 'NiAlphaProperty'}
_tex = {}


def tex_where(t):
    k = t.lower()
    if k not in _tex:
        mod, _, _ = A.resolve_loose(k)
        if mod:
            _tex[k] = 'loose:' + mod
        else:
            b = A.find_in_bsa(k)
            _tex[k] = ('bsa:' + os.path.basename(b)) if b else None
    return _tex[k]


def inspect(path):
    data = open(path, 'rb').read()
    n = niflib.Nif(data)
    assert n.tobytes() == data, 'round trip differs'
    assert len(n.reachable()) == len(n.blocks), 'unreachable blocks'
    out = dict(bytes=len(data), types=sorted(set(n.btypes)), shapes=[], P=[])
    for i, t in enumerate(n.btypes):
        if t not in niflib.SHAPE_TYPES:
            continue
        s = n.shape(i)
        b = n.blocks[i]
        k = b.find(struct.pack('<HHI', s['ntri'], s['nvert'], s['dsize']))
        raw = np.frombuffer(b, np.uint8, s['nvert'] * 32, k + 8).reshape(-1, 32)
        P = raw[:, 0:12].copy().view('<f4').reshape(-1, 3)
        uv = raw[:, 16:20].copy().view('<f2').reshape(-1, 2).astype(float)
        vc = raw[:, 28:32]
        tris = np.frombuffer(b, '<u2', s['ntri'] * 3, k + 8 + s['nvert'] * 32).reshape(-1, 3)
        e1, e2 = P[tris[:, 1]] - P[tris[:, 0]], P[tris[:, 2]] - P[tris[:, 0]]
        degen = int((np.linalg.norm(np.cross(e1, e2), axis=1) < 1e-6).sum())
        thr = n.blocks[s['alpha']][-1] if s['alpha'] >= 0 else None
        out['shapes'].append(dict(name=s['name'], ntri=s['ntri'], nvert=s['nvert'], f1=s.get('f1'), f2=s.get('f2'), alpha=thr, skin=s['skin'],
                                  tex=[x for x in s['textures'] if x], uv=(float(uv.min()), float(uv.max())),
                                  vc=sorted(set(map(tuple, vc.tolist()))), degen=degen, idx_ok=bool(tris.max() < s['nvert']), vsize=s['dsize'] // max(1, s['nvert']) if False else None))
        out['P'].append(P)
        out['shapes'][-1]['P'] = P; out['shapes'][-1]['tris'] = tris
    return out


def tree_wind(shapes):
    """Port of TreeShapes.cpp Classify + the trunk registration / crown following of BendWeights::Get (Tree Mod Support on),
    on the nif as written (LODGen may reorder or weld vertices; that is not modelled). World units at LOD4."""
    import build_lod as B
    trunks, ncard, kinds = [], 0, []
    for s in shapes:
        two, soft = bool(s['f2'] >> 4 & 1), bool(s['f2'] >> 25 & 1 or s['f2'] >> 26 & 1)
        vc = bool(s['f2'] >> 5 & 1)
        kind = 'none' if not vc else 'crown' if two and soft else 'trunk' if not (two or soft) else 'crown(LOD4 only)' if two else 'none'
        kinds.append(kind)
        if kind == 'trunk':
            P = s['P'].astype(float)
            ncard += B.card_quads(P, 1.0) + B.card_quads(P, 4.0)
            lab = A.components(s['tris'].astype(np.int64), P)
            for c in np.unique(lab):
                pv = P[lab == c]
                w = max(np.ptp(pv[:, 0]), np.ptp(pv[:, 1])); h = np.ptp(pv[:, 2])
                if len(pv) >= 6 and w < 240 and h > 64 and h > 3 * w:
                    trunks.append((float(pv[:, 0].mean()), float(pv[:, 1].mean()), float(pv[:, 2].min()), float(pv[:, 2].max()), float(w)))
    tot = ok = 0
    for s, kind in zip(shapes, kinds):
        if not kind.startswith('crown'):
            continue
        P = s['P'].astype(float)
        lab = A.components(s['tris'].astype(np.int64), P)
        order = np.argsort(lab, kind='stable')
        cuts = np.r_[0, np.nonzero(np.diff(lab[order]))[0] + 1, len(order)]
        for a, b in zip(cuts[:-1], cuts[1:]):
            pv = P[order[a:b]]
            tot += len(pv)
            if trunks:
                wide = np.ptp(pv[:, 0]) > 1600 or np.ptp(pv[:, 1]) > 1600
                if wide:
                    d = np.min([np.hypot(pv[:, 0] - t[0], pv[:, 1] - t[1]) for t in trunks], axis=0)
                    ok += int((d < 480).sum())
                else:
                    cx, cy = pv[:, 0].mean(), pv[:, 1].mean()
                    ok += len(pv) * (min(np.hypot(cx - t[0], cy - t[1]) for t in trunks) < 480)
    return kinds, trunks, ncard, (100.0 * ok / tot if tot else 0.0)


def main():
    bad = 0
    wind = []
    ours = ref = 0
    rows = []
    for full in sorted(glob.glob(os.path.join(SRC, '*.nif'))):
        stem = os.path.basename(full)[:-4].lower()
        fd = open(full, 'rb').read()
        crc = '%08x' % (zlib.crc32(fd) & 0xFFFFFFFF)
        name = '%s_%spassthru_lod.nif' % (stem, crc)
        path = os.path.join(OUT, name)
        if not os.path.isfile(path):
            print('MISSING', name); bad += 1
            continue
        r = inspect(path)
        upstream = any('FlatTrunk' in s['name'] for s in r['shapes'])
        f = A.load_full(full)
        fp = np.concatenate([s['P'] for s in f['shapes']])
        lp = np.concatenate(r['P'])
        ftris = sum(len(s['tris']) for s in f['shapes'])
        tris = sum(s['ntri'] for s in r['shapes'])
        problems = []
        if set(r['types']) - ALLOWED:
            problems.append('block types %s' % (set(r['types']) - ALLOWED))
        for s in r['shapes']:
            if s['skin'] >= 0: problems.append('skin')
            if not s['idx_ok']: problems.append('index out of range')
            if s['alpha'] is not None and (s['uv'][0] < -1e-3 or s['uv'][1] > 1 + 1e-3): problems.append('alpha shape uv %s outside 0..1' % (s['uv'],))
            if len(s['vc']) != 1 and not upstream: problems.append('vertex colours not flat: %d values' % len(s['vc']))
            if s['degen'] and not upstream: problems.append('%d degenerate tris in %s' % (s['degen'], s['name']))
            for t in s['tex']:
                if not tex_where(t): problems.append('texture not found: ' + t)
        if not upstream and abs(lp[:, 2].max() - fp[:, 2].max()) > 1: problems.append('height differs')
        if not upstream:
            if tris != ftris: problems.append('triangle count differs from the full model')
            key = lambda X: set(map(tuple, np.round(np.asarray(X, float), 2).tolist()))
            if key(fp) != key(lp): problems.append('vertex positions differ from the full model')
        kinds, trunks, ncard, cov = tree_wind(r['shapes'])
        wind.append((upstream, stem, len(trunks), ncard, cov))
        bad += len(problems) if not upstream else 0
        print('%s  %s  %d B  %d tris (full %d, %.0f%%)  height %.0f/%.0f  radius %.0f/%.0f  %s' % (
            'REF ' if upstream else 'OURS', name, r['bytes'], tris, ftris, 100.0 * tris / ftris, lp[:, 2].max(), fp[:, 2].max(),
            np.hypot(lp[:, 0], lp[:, 1]).max(), np.hypot(fp[:, 0], fp[:, 1]).max(), 'PROBLEMS: %s' % problems if problems else 'ok'))
        print('      Tree Wind (predicted, LOD4): kinds %s; registered trunks %d %s; false trunk cards %d; crown/limb vertices following a trunk %.0f%%' % (
            kinds, len(trunks), [tuple(round(x) for x in t) for t in trunks], ncard, cov))
        for s in r['shapes']:
            print('      %-20s tris %4d verts %4d  f1 %08x f2 %08x  alpha %s  vc %s  uv %.3f..%.3f' % (
                s['name'], s['ntri'], s['nvert'], s['f1'], s['f2'], s['alpha'], s['vc'][0][:3] if len(s['vc']) == 1 else '%d values' % len(s['vc']), s['uv'][0], s['uv'][1]))
            for t in s['tex']:
                print('          %-70s %s' % (t, tex_where(t)))
        rows.append((upstream, tris, r['bytes']))
    extra = set(f.lower() for f in os.listdir(OUT)) - set('%s_%08xpassthru_lod.nif' % (os.path.basename(p)[:-4].lower(), zlib.crc32(open(p, 'rb').read()) & 0xFFFFFFFF) for p in glob.glob(os.path.join(SRC, '*.nif')))
    print('files in the LOD folder: %d, not matching a current full nif: %s' % (len(os.listdir(OUT)), sorted(extra) or 'none'))
    for lab, up in (('ours', False), ('upstream reference', True)):
        t = [x[1] for x in rows if x[0] == up]; b = [x[2] for x in rows if x[0] == up]
        print('%-20s n %d  tris %d..%d  bytes %d..%d' % (lab, len(t), min(t), max(t), min(b), max(b)))
    pt, pb = [], []
    for p in sorted(glob.glob(os.path.join(PINES, '*.nif'))):
        r = inspect(p)
        pt.append(sum(s['ntri'] for s in r['shapes'])); pb.append(r['bytes'])
    if pt:
        print('%-20s n %d  tris %d..%d  bytes %d..%d' % ('WardenWood pines', len(pt), min(pt), max(pt), min(pb), max(pb)))
    for up, stem, nt, nc, cov in wind:
        print('wind  %-4s %-36s trunks %d  false cards %d  following %.0f%%' % ('REF' if up else 'OURS', stem, nt, nc, cov))
    print('problems (ours):', bad)


if __name__ == '__main__':
    main()

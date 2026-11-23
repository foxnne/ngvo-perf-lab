"""Build `foxnne - No Ivy Trees` (+ optional Gildergreen pack): loose copies of the winning NotWL standing-tree meshes whose
`decorations` shape uses an ivy atlas, with the ivy leaf + climbing stem triangles removed (other atlas regions - branch
end caps, ferns, fungus, bark patches - stay). A shape that becomes empty is removed with its property blocks.
Also: renamed copies of the 3D tree LOD nifs whose file name carries the CRC32 of the full model.
Writes work/build_report.json. Read-only against the modlist."""
import json, os, shutil, struct, sys, zlib, hashlib
import numpy as np
import vfsidx, niflib, geom, regions
BS = chr(92)
W = vfsidx.WORK
ROOT = r'C:\Users\foxnn\dev\no-ivy-trees\out'
MAIN = os.path.join(ROOT, 'foxnne - No Ivy Trees')
OPT = os.path.join(ROOT, 'foxnne - No Ivy Trees - Gildergreen (optional)')
REMOVE = {'ivy04': {'leafA', 'leafB', 'leafC', 'stemsUp', 'twigsLow'}, 'ivy01': {'leafA', 'leafB', 'leafC', 'leafD', 'stemV', 'stemCurve'}}
SKIP = {'alder_forest_big01_dead_moss.nif': 'uses the ivy01 atlas only for hanging moss tendrils (no ivy leaves)',
        'elm_common_big01_dry_moss.nif': 'uses the ivy01 atlas only for hanging moss tendrils (no ivy leaves)',
        'tree_of_life.nif': "Sir Rumple's Tree of Life: unique giant tree with hanging vines (vinesb_col), not ivy on a forest tree; left alone"}


def fingerprint(nif, i):
    """everything of a block that must not change, as bytes"""
    return bytes(nif.blocks[i])


def process(rel, data):
    nif = niflib.Nif(data)
    assert nif.tobytes() == data, 'round trip not byte identical'
    assert len(nif.reachable()) == len(nif.blocks), 'unreachable blocks in source'
    rep = dict(rel=rel, src_size=len(data), src_crc='%08x' % (zlib.crc32(data) & 0xFFFFFFFF), src_blocks=len(nif.blocks), shapes=[])
    targets = []
    for i, t in enumerate(nif.btypes):
        if t in niflib.SHAPE_TYPES:
            s = nif.shape(i)
            tex = s['textures'][0].lower() if s['textures'] else ''
            if BS + 'ivy' + BS + 'ivy0' in tex:
                targets.append((i, os.path.basename(tex).split('_')[0], s))
    assert targets, 'no ivy atlas shape'
    src_shapes = {i: (nif.shape(i)['name'], nif.shape(i)['nvert'], nif.shape(i)['ntri']) for i, t in enumerate(nif.btypes) if t in niflib.SHAPE_TYPES}
    src_blocks = [bytes(b) for b in nif.blocks]
    src_types = list(nif.btypes)
    detached = []
    edited = {}
    for i, atlas, s in targets:
        assert nif.btypes[i] == 'BSTriShape' and s['skin'] < 0
        L, raw, pos, uv, tris = geom.read(nif, i)
        cls = regions.classify(atlas, uv[tris])
        assert not any(c == 'other' or c.endswith('?') for c in cls), 'unclassified triangles'
        keep = np.array([c not in REMOVE[atlas] for c in cls])
        counts = {}
        for c in cls: counts[c] = counts.get(c, 0) + 1
        d = dict(index=i, name=s['name'], atlas=s['textures'][0], regions=counts, src_nv=L['nvert'], src_nt=L['ntri'])
        if keep.all():
            raise AssertionError('nothing to remove')
        if not keep.any():
            parents = [p for p, t in enumerate(nif.btypes) if t in niflib.NODE_TYPES and i in nif.children(p)]
            assert len(parents) == 1
            nif.detach_child(parents[0], i)
            detached.append(i)
            d.update(action='shape removed', out_nv=0, out_nt=0, parent=parents[0])
        else:
            nv, nt = geom.rebuild(nif, i, keep)
            edited[i] = (nv, nt)
            d.update(action='triangles removed', out_nv=nv, out_nt=nt, kept_regions=sorted(set(c for c in cls if c not in REMOVE[atlas])))
        rep['shapes'].append(d)
    removed = nif.drop_unreachable() if detached else []
    out = nif.tobytes()
    # ---------------- validation on the re-parsed output
    n2 = niflib.Nif(out)
    assert n2.tobytes() == out
    assert len(n2.reachable()) == len(n2.blocks), 'unreachable block in output'
    for i in range(len(n2.blocks)):
        for r in n2.refs(i):
            assert -1 <= r < len(n2.blocks)
    assert n2.strings == niflib.Nif(data).strings and n2.roots == [0] and n2.btypes[0] == src_types[0]
    rem_idx = [i for i, t in removed]
    exp_removed_types = sorted(t for i, t in removed)
    if detached:
        assert set(detached) <= set(rem_idx)
        assert all(t in ('BSTriShape', 'BSLightingShaderProperty', 'BSShaderTextureSet', 'NiAlphaProperty') for t in exp_removed_types), exp_removed_types
    # map old -> new index
    newi = {}
    k = 0
    for i in range(len(src_blocks)):
        if i not in rem_idx:
            newi[i] = k; k += 1
    assert k == len(n2.blocks)
    # every surviving block: same type; same size & bytes except (a) reference fields, (b) the edited shapes, (c) the parent child list
    src = niflib.Nif(data)
    changed_parents = {d['parent'] for d in rep['shapes'] if d['action'] == 'shape removed'}
    same = 0
    for i in range(len(src_blocks)):
        if i in rem_idx: continue
        j = newi[i]
        assert n2.btypes[j] == src_types[i]
        if i in edited:
            continue
        a = bytearray(src_blocks[i]); b = bytearray(n2.blocks[j])
        if i in changed_parents:
            # children lists: source minus detached, remapped
            exp = [newi[c] if c >= 0 else c for c in src.children(i) if c not in detached]
            assert n2.children(j) == exp, 'child list mismatch'
            assert len(b) == len(a) - 4 * len([c for c in src.children(i) if c in detached])
            continue
        assert len(a) == len(b), 'size changed in block %d %s' % (i, src_types[i])
        ro = src.ref_offsets(i)
        assert ro == n2.ref_offsets(j)
        for o in ro:
            r = struct.unpack_from('<i', a, o)[0]
            r2 = struct.unpack_from('<i', b, o)[0]
            assert r2 == (newi[r] if r >= 0 else r), 'ref remap'
            a[o:o + 4] = b'\0\0\0\0'; b[o:o + 4] = b'\0\0\0\0'
        assert a == b, 'bytes changed in block %d %s' % (i, src_types[i])
        same += 1
    # shapes: untouched ones identical counts; edited ones: vertex rows are a subset of the source rows, triangles map back
    out_shapes = {j: (n2.shape(j)['name'], n2.shape(j)['nvert'], n2.shape(j)['ntri']) for j, t in enumerate(n2.btypes) if t in niflib.SHAPE_TYPES}
    for i, (nm, nv, nt) in src_shapes.items():
        if i in rem_idx:
            continue
        j = newi[i]
        if i in edited:
            assert out_shapes[j] == (nm,) + edited[i]
            L1, raw1, pos1, uv1, tris1 = geom.read(src, i)
            L2, raw2, pos2, uv2, tris2 = geom.read(n2, j)
            assert L2['desc'] == L1['desc'] and L2['vsize'] == L1['vsize']
            s1 = src.shape(i); s2 = n2.shape(j)
            assert (s1['f1'], s1['f2'], s1['textures']) == (s2['f1'], s2['f2'], s2['textures'])
            rows1 = {bytes(r) for r in raw1}
            assert all(bytes(r) in rows1 for r in raw2), 'vertex rows not a subset'
            t1 = {tuple(bytes(raw1[v]) for v in t) for t in tris1}
            assert all(tuple(bytes(raw2[v]) for v in t) in t1 for t in tris2), 'triangle not from source'
            assert tris2.max() < L2['nvert'] and len(np.unique(tris2)) == L2['nvert']
            # bound covers all vertices
            c = np.array(struct.unpack_from('<3f', n2.blocks[j], L2['bound'])); r = struct.unpack_from('<f', n2.blocks[j], L2['bound'] + 12)[0]
            assert (np.sqrt(((pos2 - c) ** 2).sum(1)).max() <= r * 1.0001)
        else:
            assert out_shapes[j] == (nm, nv, nt)
    src_v = sum(v for _, v, _ in src_shapes.values()); src_t = sum(t for _, _, t in src_shapes.values())
    out_v = sum(v for _, v, _ in out_shapes.values()); out_t = sum(t for _, _, t in out_shapes.values())
    rem_v = sum(d['src_nv'] - d['out_nv'] for d in rep['shapes']); rem_t = sum(d['src_nt'] - d['out_nt'] for d in rep['shapes'])
    assert out_v == src_v - rem_v and out_t == src_t - rem_t
    rep.update(out_size=len(out), out_crc='%08x' % (zlib.crc32(out) & 0xFFFFFFFF), out_blocks=len(n2.blocks), removed_blocks=exp_removed_types,
               identical_blocks=same, src_verts=src_v, out_verts=out_v, src_tris=src_t, out_tris=out_t, root=n2.btypes[0],
               types=sorted(set(n2.btypes)), other_shapes=[(nm, nv, nt) for i, (nm, nv, nt) in src_shapes.items() if i not in rem_idx and i not in edited])
    return out, rep


def main():
    for d in (MAIN, OPT):
        if os.path.isdir(d): shutil.rmtree(d)
    tg = json.load(open(os.path.join(W, 'targets.json')))
    lods = json.load(open(os.path.join(W, 'lods.json')))
    report = dict(files=[], skipped=[], lods=[])
    for rel, m in sorted(tg.items()):
        if m['kind'] != 'standing': continue
        base = os.path.basename(rel)
        if base in SKIP:
            report['skipped'].append(dict(rel=rel, why=SKIP[base])); continue
        data = vfsidx.read(rel)
        out, rep = process(rel, data)
        dest = OPT if 'whiterun_temple_tree' in base else MAIN
        rep['pack'] = os.path.basename(dest)
        rep['winner'] = list(vfsidx.winner(rel)[:2]); rep['providers'] = vfsidx.get()['all'].get(rel, [])
        p = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(out)
        report['files'].append(rep)
        print('%-44s blocks %d->%d verts %d->%d tris %d->%d  %s' % (base, rep['src_blocks'], rep['out_blocks'], rep['src_verts'], rep['out_verts'], rep['src_tris'], rep['out_tris'],
              '; '.join('%s: %s' % (d['name'], d['action']) for d in rep['shapes'])))
        # 3D LOD copies under the new CRC
        for l in lods.get(rel, {}).get('lods', []):
            old = rep['src_crc']; new = rep['out_crc']
            assert old in os.path.basename(l['rel'])
            ld = vfsidx.read(l['rel'])
            ln = niflib.Nif(ld)
            assert ln.tobytes() == ld
            n_patched = 0
            for i, t in enumerate(ln.btypes):
                if t == 'BSShaderTextureSet':
                    b = ln.blocks[i]
                    for needle in (old.upper().encode(), old.lower().encode()):
                        k = b.find(needle)
                        while k >= 0:
                            b[k:k + 8] = new.upper().encode() if needle.isupper() or not needle.islower() else new.lower().encode()
                            n_patched += 1
                            k = b.find(needle, k + 8)
            lo = ln.tobytes()
            l2 = niflib.Nif(lo)
            assert len(lo) == len(ld) and l2.btypes == niflib.Nif(ld).btypes
            newrel = l['rel'].replace(old, new)
            p = os.path.join(dest, newrel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(lo)
            tex = sorted({s['textures'][0] for i, t in enumerate(l2.btypes) if t in niflib.SHAPE_TYPES for s in [l2.shape(i)] if s['textures']})
            report['lods'].append(dict(full=rel, src=l['rel'], out=newrel, texture_refs_patched=n_patched, textures=tex, pack=os.path.basename(dest)))
            print('    LOD %s -> %s (%d texture paths re-pointed)' % (os.path.basename(l['rel']), os.path.basename(newrel), n_patched))
    json.dump(report, open(os.path.join(W, 'build_report.json'), 'w'), indent=1)
    print(len(report['files']), 'meshes written;', len(report['lods']), 'LOD copies;', len(report['skipped']), 'skipped')


if __name__ == '__main__':
    main()

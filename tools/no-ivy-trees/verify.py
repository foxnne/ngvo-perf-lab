"""Independent re-check of the staged output: re-read every nif from disk, compare with the winning source, check that nothing
else in the profile provides those paths as loose files (our mod sits at the top), compare with the non-vine sibling where one exists,
and draw before/after pictures for a few trees."""
import json, os, sys, zlib, struct, subprocess
import numpy as np
import vfsidx, niflib, geom
BS = chr(92)
OUT = r'C:\Users\foxnn\dev\no-ivy-trees\out'
rep = json.load(open(os.path.join(vfsidx.WORK, 'build_report.json')))
v = vfsidx.get()
bad = 0
for pack in sorted(os.listdir(OUT)):
    pd = os.path.join(OUT, pack)
    if not os.path.isdir(pd): continue
    for dp, dn, fn in os.walk(pd):
        for f in fn:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, pd).lower()
            if not f.endswith('.nif'):
                continue
            data = open(full, 'rb').read()
            n = niflib.Nif(data)
            assert n.tobytes() == data and len(n.reachable()) == len(n.blocks)
            shapes = [(n.shape(i)['name'], n.shape(i)['nvert'], n.shape(i)['ntri'], os.path.basename(n.shape(i)['textures'][0]) if n.shape(i)['textures'] else '') for i, t in enumerate(n.btypes) if t in niflib.SHAPE_TYPES]
            for i, t in enumerate(n.btypes):
                if t in niflib.SHAPE_TYPES: geom.read(n, i)
            prov = v['all'].get(rel, [])
            loose_prov = [p for p in prov if not p.startswith('BSA:')]
            srcw = vfsidx.winner(rel)
            line = '%-34s %-62s %8d B  blocks %2d  root %s  ' % (pack[:34], os.path.basename(rel), len(data), len(n.blocks), n.btypes[0])
            if 'dyndolod' in rel:
                line += 'NEW PATH (LOD copy); existing provider: %s' % (prov or 'none')
                if prov: bad += 1
            else:
                src = niflib.Nif(vfsidx.read(rel))
                has = lambda x: sorted(set(x.btypes) - {'BSTriShape', 'BSLightingShaderProperty', 'BSShaderTextureSet', 'NiAlphaProperty'})
                assert has(src) == has(n), 'non-shape block types differ'
                cnt = lambda x, t: sum(1 for b in x.btypes if b == t)
                for t in ('bhkCollisionObject', 'bhkRigidBody', 'bhkMoppBvTreeShape', 'bhkCompressedMeshShape', 'bhkCompressedMeshShapeData', 'BSXFlags', 'NiNode', 'BSLeafAnimNode'):
                    assert cnt(src, t) == cnt(n, t), t
                line += 'src winner %s/%s; other loose providers: %s' % (srcw[0], srcw[1][:26], loose_prov or 'none')
                if loose_prov: bad += 1
                ivy = [s for s in shapes if 'ivy' in s[3].lower()]
                line += ' | ivy-atlas shape left: %s' % (['%s nv%d nt%d' % s[:3] for s in ivy] or 'none')
            print(line)
print('problems:', bad)
# sibling comparison: <name>_vine vs <name>
for r in rep['files']:
    rel = r['rel']
    for a, b in (('_summer_vine.nif', '_summer.nif'), ('_vineaut.nif', 'aut.nif')):
        if rel.endswith(a):
            sib = rel[:-len(a)] + b
            if vfsidx.winner(sib):
                s = niflib.Nif(vfsidx.read(sib))
                sv = sum(s.shape(i)['nvert'] for i, t in enumerate(s.btypes) if t in niflib.SHAPE_TYPES)
                st = sum(s.shape(i)['ntri'] for i, t in enumerate(s.btypes) if t in niflib.SHAPE_TYPES)
                print('sibling %-40s verts %d tris %d blocks %d | ours %d %d %d' % (os.path.basename(sib), sv, st, len(s.blocks), r['out_verts'], r['out_tris'], r['out_blocks']))

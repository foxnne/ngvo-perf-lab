"""Survey: every winning nif under meshes\\landscape\\trees and meshes\\dyndolod\\lod\\trees: distinct (shape name class, diffuse) so that
climber geometry with a texture not named ivy/vine is not missed."""
import collections, os, re, sys
import vfsidx, niflib
BS = chr(92)
v = vfsidx.get()
rels = sorted(r for r in set(v['loose']) | set(v['bsa']) if r.startswith('meshes' + BS + 'landscape' + BS + 'trees' + BS) or r.startswith('meshes' + BS + 'dyndolod' + BS + 'lod' + BS + 'trees' + BS)
              or r.startswith('meshes' + BS + 'landscape' + BS + 'plants' + BS))
tex = collections.defaultdict(lambda: [0, set(), set()])
bad = collections.Counter()
for rel in rels:
    try:
        n = niflib.Nif(vfsidx.read(rel))
    except Exception as e:
        bad[(vfsidx.winner(rel)[1], str(e)[:50])] += 1
        continue
    lod = 'dyndolod' in rel
    for i, t in enumerate(n.btypes):
        if t in niflib.SHAPE_TYPES:
            try: s = n.shape(i)
            except Exception as e:
                bad[(vfsidx.winner(rel)[1], 'shape ' + rel)] += 1; continue
            d = (s['textures'][0] if s['textures'] else '-').lower()
            if lod: d = 'LOD:' + re.sub(r'_[0-9a-f]{8}', '_#', os.path.basename(d))
            k = (vfsidx.winner(rel)[1], d)
            tex[k][0] += 1
            tex[k][1].add(re.sub(r'[:\d_ ]+$', '', s['name']).lower()[:24])
            tex[k][2].add(rel)
print(len(rels), 'nifs', dict(bad))
for (m, d), (c, names, files) in sorted(tex.items()):
    if d.startswith('LOD:'): continue
    print('%-28s %4d %-90s %s' % (m[:28], c, d, sorted(names)[:5]))

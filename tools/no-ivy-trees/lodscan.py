"""Tree LOD assets for the standing ivy trees: 3D LOD nifs (meshes\\dyndolod\\lod\\trees\\<name>_<crc>passthru_lod.nif), their CRC vs the
winning full model, shapes/textures; billboards (textures\\terrain\\lodgen\\...)."""
import json, os, sys, zlib, re
import vfsidx, niflib
BS = chr(92)
W = vfsidx.WORK
tg = json.load(open(os.path.join(W, 'targets.json')))
v = vfsidx.get()
allrel = set(v['loose']) | set(v['bsa'])
lodrels = [r for r in allrel if r.startswith('meshes' + BS + 'dyndolod' + BS + 'lod' + BS + 'trees' + BS)]
out = {}
for rel, m in sorted(tg.items()):
    if m['kind'] != 'standing': continue
    base = os.path.basename(rel)[:-4]
    data = vfsidx.read(rel)
    crc = '%08x' % (zlib.crc32(data) & 0xFFFFFFFF)
    cands = [r for r in lodrels if re.match(re.escape(base) + r'_[0-9a-f]{8}(passthru)?_lod(_\d)?\.nif$', os.path.basename(r))]
    print('%s  crc %s  %s' % (base, crc, 'NO 3D LOD' if not cands else ''))
    out[rel] = dict(crc=crc, lods=[])
    for c in sorted(cands):
        w = vfsidx.winner(c)
        n = niflib.Nif(vfsidx.read(c))
        sh = []
        for i, t in enumerate(n.btypes):
            if t in niflib.SHAPE_TYPES:
                s = n.shape(i)
                sh.append((s['name'], s['nvert'], s['ntri'], s['textures'][0] if s['textures'] else ''))
        match = crc in os.path.basename(c)
        out[rel]['lods'].append(dict(rel=c, mod=w[1], src=w[0], match=match, shapes=sh))
        print('    %s [%s %s] crc-match=%s' % (os.path.basename(c), w[0], w[1][:30], match))
        for s in sh:
            print('        %-28s nv%-6d nt%-6d %s' % (s[0][:28], s[1], s[2], s[3]))
json.dump(out, open(os.path.join(W, 'lods.json'), 'w'), indent=1)

"""Offline audit: which loose tree meshes (winners in the enabled mod list) have no matching DynDOLOD 3D tree LOD model
(meshes/dyndolod/lod/trees/<stem>_<CRC32 of the full nif>[passthru]_lod.nif)? Vanilla trees in BSAs are not covered.
usage: python tree_lod_audit.py"""
import os, zlib, collections
I = 'C:/Modlists/NGVO 8.0 Beta'
names = [l.strip()[1:] for l in open(I + '/profiles/foxnne-nsfw/modlist.txt', encoding='utf-8-sig') if l.startswith('+')]
win = {}; lods = set()
for n in names:                      # top of modlist.txt = highest priority: first seen wins
    for sub in os.listdir(os.path.join(I, 'mods', n)) if os.path.isdir(os.path.join(I, 'mods', n)) else []:
        if sub.lower() != 'meshes': continue
        root = os.path.join(I, 'mods', n, sub)
        for dp, dn, fn in os.walk(root):
            rel = os.path.relpath(dp, root).replace(os.sep, '/').lower()
            if rel.startswith('dyndolod/lod/trees'):
                for f in fn: lods.add(f.lower())
            elif 'tree' in rel:
                for f in fn:
                    if f.lower().endswith('.nif'):
                        k = rel + '/' + f.lower()
                        if k not in win: win[k] = (n, os.path.join(dp, f))
print('loose tree-folder meshes (winners):', len(win), ' 3D tree LOD files (loose):', len(lods))
miss = collections.defaultdict(list); ok_n = 0
for k, (n, p) in sorted(win.items()):
    b = os.path.basename(k)
    if 'dyndolod' in k or '/lod/' in k or b.endswith('_lod.nif') or '_lod_' in b: continue
    stem = b[:-4]; crc = '%08x' % (zlib.crc32(open(p, 'rb').read()) & 0xFFFFFFFF)
    if any(l.startswith(stem + '_' + crc) for l in lods): ok_n += 1; continue
    other = [l for l in lods if l.startswith(stem + '_')]
    miss[n].append((k, crc, 'LOD exists for a different version of this mesh' if other else 'no LOD model'))
print('with matching 3D LOD:', ok_n, '  without:', sum(len(v) for v in miss.values()))
for n, v in sorted(miss.items(), key=lambda x: -len(x[1])):
    print('==', n, len(v))
    for k, crc, why in v[:14]: print('    %-72s %s  %s' % (k, crc, why))

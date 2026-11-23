import os, sys, re, json
sys.path.insert(0, r'C:\Users\foxnn\dev\biome-flora\tools')
import flib, tes5, vfsidx
BS = chr(92)
v = vfsidx.get()
allrel = set(v['loose']) | set(v['bsa'])
keys = ['oak_big01', 'oak_big_wide01', 'oak_druids01', 'elm_big_wide01', 'elm_big_split0', 'elm_forest_big0', 'elm_forest_medium01', 'alder_forest_slim01', 'whiterun_temple', 'oak_big_slim01', 'alder_cluster_medium03']
for r in sorted(allrel):
    b = os.path.basename(r)
    if ('lod' in r) and any(k in b for k in keys):
        print('MESH', r, vfsidx.winner(r)[:2])
# textures in all enabled BSAs + loose that look like billboards / lod trunk textures for these trees
mods = flib.enabled_mods()
seen = {}
for m in reversed(mods):
    d = os.path.join(flib.MODS, m)
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if f.lower().endswith('.bsa') and ('wild' in f.lower() or 'notwl' in f.lower() or 'dyndolod' in f.lower()):
            try:
                for n in tes5.bsa_list(os.path.join(d, f)):
                    if any(k in os.path.basename(n) for k in keys) and ('lod' in n):
                        seen[n] = 'BSA ' + f
            except Exception as e:
                print('bsa err', f, e)
    for sub in ('textures' + BS + 'terrain' + BS + 'lodgen', 'textures' + BS + 'dyndolod' + BS + 'lod' + BS + 'trees'):
        dd = os.path.join(d, sub)
        if os.path.isdir(dd):
            for dp, dn, fn in os.walk(dd):
                for f in fn:
                    if any(k in f.lower() for k in keys):
                        seen[os.path.relpath(os.path.join(dp, f), d).lower()] = m
for n, s in sorted(seen.items()):
    print('TEX', n, '|', s)

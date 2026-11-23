"""Decode every .cgid, check exact-length parsing, and write per-type / per-cell statistics.

out/work/survey.npz : per (cell, type) instance counts, sum of scale^2, mean colour scale, for Tamriel
out/work/types.json : per model: instances, cells, form IDs, flags, wave, scale and colour-scale statistics
"""
import json
import os
import sys
import time

import numpy as np

import cgid

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'work')
os.makedirs(OUT, exist_ok=True)

dirs = cgid.find_cache_dir()
print('cache dirs (priority order):', dirs)
gdir = dirs[0]
t0 = time.time()
names = sorted(os.listdir(gdir))
nfiles = nbytes = nempty = nbad = 0
worlds = {}
types = {}
rows = []      # tamriel: cx, cy, type index, count, sum s^2, sum w
tindex = {}
tot_inst = 0
bound_fail = 0
out_max = -1e9
shape_counts = {}
for name in names:
    p = cgid.parse_name(name)
    if not p:
        continue
    path = os.path.join(gdir, name)
    b = open(path, 'rb').read()
    nfiles += 1
    nbytes += len(b)
    try:
        groups = cgid.read_cgid(b)
    except Exception as e:  # noqa
        nbad += 1
        print('BAD', name, e)
        continue
    w = worlds.setdefault(p[0], [0, 0, 0])
    w[0] += 1
    if not groups:
        nempty += 1
        w[2] += 1
    # size identity: 4 + sum(4+len+15) + shapes*36 + inst*32
    for g in groups:
        n = len(g['inst'])
        w[1] += n
        tot_inst += n
        t = types.setdefault(g['model'], dict(inst=0, cells=0, formids={}, flags={}, wave={}, s2=0.0, s=0.0, w=0.0, wmin=9, smin=9, smax=-9, worlds={}))
        t['inst'] += n
        t['cells'] += 1
        t['formids'][g['formid']] = t['formids'].get(g['formid'], 0) + n
        t['flags'][str(g['flags'])] = t['flags'].get(str(g['flags']), 0) + n
        t['wave'][g['wave']] = t['wave'].get(g['wave'], 0) + n
        t['worlds'][p[0]] = t['worlds'].get(p[0], 0) + n
        shape_counts[len(g['shapes'])] = shape_counts.get(len(g['shapes']), 0) + 1
        if n:
            s = 1.0 + g['inst'][:, 13].astype(np.float64)
            cw = g['inst'][:, 3].astype(np.float64)
            t['s2'] += float((s * s).sum())
            t['s'] += float(s.sum())
            t['w'] += float(cw.sum())
            t['wmin'] = min(t['wmin'], float(cw.min()))
            t['smin'] = min(t['smin'], float(s.min()))
            t['smax'] = max(t['smax'], float(s.max()))
            x, y = cgid.world_xy(g['inst'], p[1], p[2])
            x -= p[1] * 4096.0
            y -= p[2] * 4096.0
            out_max = max(out_max, -x.min(), x.max() - 4096, -y.min(), y.max() - 4096)
            if x.min() < -1 or x.max() > 4097 or y.min() < -1 or y.max() > 4097:
                bound_fail += 1
            if p[0] == 'tamriel':
                ti = tindex.setdefault((g['model'], g['formid']), len(tindex))
                rows.append((p[1], p[2], ti, n, float((s * s).sum()), float(cw.sum())))
print('files %d, bytes %d, empty (4-byte) %d, unparsable %d, instances %d, %.1fs' % (nfiles, nbytes, nempty, nbad, tot_inst, time.time() - t0))
print('type groups with an instance outside its own cell square: %d of %d; furthest outside: %.1f units' % (bound_fail, sum(shape_counts.values()), out_max))
print('shapes per type-group histogram:', dict(sorted(shape_counts.items())))
print('worldspaces: files / instances / empty')
for k, v in sorted(worlds.items(), key=lambda kv: -kv[1][1]):
    print('  %-28s %5d %10d %5d' % (k, *v))
tam = sum(v['worlds'].get('tamriel', 0) for v in types.values())
print('models %d; Tamriel instances %d' % (len(types), tam))
for k, v in sorted(types.items(), key=lambda kv: -kv[1]['worlds'].get('tamriel', 0))[:45]:
    n = v['inst']
    print('  %-52s tam %9d all %9d cells %5d ids %2d flags %s wave %s scale %.2f (%.2f..%.2f) cs %.3f (min %.2f)' % (
        k[16:], v['worlds'].get('tamriel', 0), n, v['cells'], len(v['formids']), list(v['flags'])[0], list(v['wave'])[0],
        v['s'] / max(n, 1), v['smin'], v['smax'], v['w'] / max(n, 1), v['wmin']))
json.dump({k: dict(v, formids={'%08X' % a: b for a, b in v['formids'].items()}, wave={str(a): b for a, b in v['wave'].items()})
           for k, v in types.items()}, open(os.path.join(OUT, 'types.json'), 'w'), indent=1)
rows = np.array(rows, np.float64)
keys = sorted(tindex, key=tindex.get)
np.savez_compressed(os.path.join(OUT, 'survey.npz'), rows=rows, models=np.array([k[0] for k in keys]), formids=np.array([k[1] for k in keys], np.uint32))


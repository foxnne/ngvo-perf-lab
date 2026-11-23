"""Shots of the big NotWL trees (oak_big*, elm_big*, oak_druids*) near Riverwood as LOD: the player is moved several cells away,
the free camera looks down at the tree from above (no terrain in the way). usage: python bigtree_shots.py"""
import json, math, os, pickle, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
W = 'C:/Users/foxnn/dev/no-ivy-trees/work/'; BS = chr(92)
refs = pickle.load(open(W + 'refs.pkl', 'rb')); bases = pickle.load(open(W + 'bases.pkl', 'rb'))['bases']
want = ('oak_big01_', 'oak_big_wide01_', 'oak_druids01_', 'elm_big_split0', 'elm_big_wide01_')
RW = (17224.0, -47204.0)
hits = []
for k, r in refs.items():
    b = bases.get(r['base'])
    if not b or not b.get('model'): continue
    stem = b['model'].split(BS)[-1]
    if not stem.startswith(want): continue
    if r.get('world') != ('skyrim.esm', 60): continue
    x, y, z = r['pos'][:3]; hits.append((math.hypot(x - RW[0], y - RW[1]), stem, x, y, z, r.get('scale', 1.0), r.get('world')))
hits.sort(); print(len(hits), 'placements;', 'nearest to Riverwood:')
for h in hits[:8]: print('  %6.0f %s (%.0f, %.0f, %.0f) scale %.2f world %s' % h)
OUT = os.path.join(os.path.dirname(HERE), 'results', 'lod_check_1122')


def cam(x, y, z, tx, ty, tz, fov):
    dx, dy, dz = tx - x, ty - y, tz - z
    cs.call('communityshaders.testbed', {'action': 'camera', 'x': x, 'y': y, 'z': z, 'pitch': math.degrees(math.atan2(-dz, math.hypot(dx, dy))), 'yaw': math.degrees(math.atan2(dx, dy)) % 360, 'fov': fov})


def shot(n, wait=9):
    time.sleep(wait); f = cs.shot('bt-' + n); d = os.path.join(OUT, n + os.path.splitext(f)[1]); shutil.move(f, d); print(n, flush=True)


_, stem, tx, ty, tz, sc, _w = hits[0]
for tag, cells in (('lod_near_5cells', 5), ('lod_mid_10cells', 10), ('lod_far_18cells', 18)):
    cs.world(action='teleport', x=tx, y=ty + cells * 4096, z=tz + 3000); time.sleep(16)
    cam(tx + 2200, ty + 2600, tz + 2600, tx, ty, tz + 700, 28); shot('bt_%s_%s' % (tag, stem[:-4]))
    cam(tx + 5200, ty + 6000, tz + 5200, tx, ty, tz + 500, 28); shot('bt_%s_wide' % tag)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})

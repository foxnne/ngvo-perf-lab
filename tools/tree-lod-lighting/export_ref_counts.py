"""Count tree references per LOD representation in the LODGen export for Tamriel."""
import collections, re, sys
p = r'C:\Modlists\NGVO 8.0 Beta\tools\DynDOLOD\Edit Scripts\Export\LODGen_SSE_Export_Tamriel.txt'
BS = chr(92)
def kind(s):
    s = s.lower()
    if not s: return 'none'
    if s.endswith('.dds'): return 'billboard'
    if 'passthru_lod' in s: return '3d-passthru'
    if s.endswith('.nif'): return '3d-other'
    return 'other'
cnt = collections.Counter(); per = collections.defaultdict(collections.Counter)
whiterun = collections.Counter()
for l in open(p, encoding='utf-8', errors='replace'):
    f = l.rstrip('\n').split('\t')
    if len(f) < 16: continue
    full = f[12].lower()
    if (BS + 'trees' + BS) not in full and 'tree' not in full: continue
    if 'landscape' + BS + 'grass' in full: continue
    k = (kind(f[13]), kind(f[14]), kind(f[15]))
    cnt[k] += 1
    name = full.split(BS)[-1]
    per[k][name] += 1
    try:
        x, y = float(f[2]), float(f[3])
        # Whiterun plains-ish: cells -5..20, -12..6
        if -5 * 4096 < x < 20 * 4096 and -12 * 4096 < y < 6 * 4096:
            whiterun[(k[0], name)] += 1
    except ValueError:
        pass
tot = sum(cnt.values())
print('tree refs', tot)
for k, v in cnt.most_common(): print(v, '%.1f%%' % (100 * v / tot), 'LOD4/8/16 =', k); print('    top:', per[k].most_common(8))
print('Whiterun-area box, by LOD4 kind:')
agg = collections.Counter()
for (k, n), v in whiterun.items(): agg[k] += v
print(agg)
print(sorted(whiterun.items(), key=lambda t: -t[1])[:25])

import re, collections
BS = chr(92)
p = r'C:\Modlists\NGVO 8.0 Beta\tools\DynDOLOD\Logs\DynDOLOD_SSE_Tree_Report.txt'
recs = []; cur = None
for l in open(p, encoding='utf-8', errors='replace'):
    if not l.startswith('\t'):
        cur = {'head': l.strip(), 'lines': []}; recs.append(cur)
    else:
        cur['lines'].append(l.strip())
n = 0
fam3 = collections.Counter(); famb = collections.Counter()
for r in recs:
    d = {}
    for x in r['lines']:
        m = re.match(r'(\w+): (.*)', x)
        if m: d[m.group(1)] = m.group(2)
    if not d.get('Mask', '').startswith('tree') or 'LOD4' not in d: continue
    m = re.search('Meshes' + BS + BS + '(.*?[.]nif)', r['head']); mesh = m.group(1).lower() if m else '?'
    base = mesh.split(BS)[-1].replace('.nif', '')
    fam = re.sub(r'[\d_]*(summer|winter|autumn|aut|sum|dead|dry|snow|vine|moss).*', '', base)
    key = mesh.rsplit(BS, 1)[0] + ' :: ' + fam
    if d['LOD4'].startswith('Level0'):
        fam3[key] += 1
        if n < 4:
            n += 1; print(r['head'][:200]); [print('   ', x[:300]) for x in r['lines']]
    else:
        famb[key] += 1
print('3D at LOD4:', sum(fam3.values())); [print('  ', v, k) for k, v in fam3.most_common()]
print('Billboard at LOD4:', sum(famb.values())); [print('  ', v, k) for k, v in famb.most_common(80)]

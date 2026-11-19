import re,collections
p=r'C:\Modlists\NGVO 8.0 Beta\tools\DynDOLOD\Logs\DynDOLOD_SSE_Tree_Report.txt'
recs=[];cur=None
for l in open(p,encoding='utf-8',errors='replace'):
    if not l.startswith('\t'):
        cur={'head':l.strip(),'lines':[]};recs.append(cur)
    else: cur['lines'].append(l.strip())
c=collections.Counter();ex=collections.defaultdict(list)
for r in recs:
    d={}
    for x in r['lines']:
        m=re.match(r'(\w+): (.*)',x)
        if m: d[m.group(1)]=m.group(2)
    if not d.get('Mask','').startswith('tree'): continue
    status=r['lines'][0] if r['lines'] else ''
    status=re.sub(r'(found|not found) \S.*$',r'\1',status)
    k=(status[:70],d.get('LOD4','')[:30],d.get('LOD8','')[:30],d.get('LOD16','')[:30], 'nm' if '_n.dds' in d.get('Billboard_1','') and 'default_n' not in d.get('Billboard_1','') else 'no-nm')
    c[k]+=1; ex[k].append(r['head'][:110])
for k,v in c.most_common(): print(v,k); print('    e.g.',ex[k][:2])

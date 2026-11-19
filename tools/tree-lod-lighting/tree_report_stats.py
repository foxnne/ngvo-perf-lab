import re,collections,sys
p=r'C:\Modlists\NGVO 8.0 Beta\tools\DynDOLOD\Logs\DynDOLOD_SSE_Tree_Report.txt'
c=collections.defaultdict(collections.Counter)
ex={}
for l in open(p,encoding='utf-8',errors='replace'):
    m=re.match(r'\t(LOD(?:4|8|16|32)): (.*)',l)
    if m:
        v=m.group(2).strip(); lv=v.lower()
        if lv.startswith('billboard'): k=re.sub(r' using .*','',v)
        elif 'passthru' in lv: k='3D passthru_lod nif'
        elif '_lod' in lv: k='3D *_lod nif'
        else: k='other: '+v[:50]
        c[m.group(1)][k]+=1; ex.setdefault(k,v)
for k in c: print(k,c[k].most_common(8))
for k,v in ex.items(): print(k,'=>',v[:260])

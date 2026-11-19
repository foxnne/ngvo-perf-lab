import sys, os, pickle, math, collections; sys.path.insert(0,'.')
from common import *; from cam import *; from nif import *
d=load(); names=d['names']; refs=d['refs']; bases=d['bases']
mi=pickle.load(open('meshidx.pkl','rb'))['idx']
from bsa import BSA
BF=pickle.load(open('bsafound.pkl','rb')) if os.path.exists('bsafound.pkl') else {}
BC={}
def getmesh(m):
    if m in mi: return mi[m]
    p=BF[os.path.join('meshes',m)]
    if p not in BC: BC[p]=BSA(p)
    return BC[p].read(os.path.join('meshes',m))

c=Cam(pitch=3.0); TX,TY=2755,468
XR=(float(sys.argv[1]),float(sys.argv[2])); YR=(float(sys.argv[3]),float(sys.argv[4]))
todo=collections.defaultdict(list); nomodel=collections.Counter(); notloose=collections.Counter()
for fk,h in refs.items():
    r=h[-1]
    if 'data' not in r or r['flags']&0x820: continue
    x,y,z=r['data'][:3]
    if not (XR[0]<=x<XR[1] and YR[0]<=y<YR[1]): continue
    b=bases.get(r.get('base'))
    if not b or not b[2]: nomodel[b[:2] if b else None]+=1; continue
    m=os.path.normpath(b[2].lower())
    if m.startswith('meshes'+os.sep): m=m[7:]
    if m not in mi:
        notloose[m]+=1
        if os.path.join('meshes',m) not in BF: continue
    todo[m].append((fk,r,b))
print('models loose',len(todo),'refs',sum(map(len,todo.values())),'not loose models',len(notloose),'refs',sum(notloose.values()),'nomodel',sum(nomodel.values()))
pickle.dump(notloose,open('notloose.pkl','wb'))
hits=[]; noshape=[]
for m,lst in todo.items():
    try: sh,blk,_=shapes(getmesh(m))
    except Exception as e: print('ERR',m,e); continue
    if any(t in ('NiTriShape','NiTriStrips') for t,_,_ in blk): print('OLDFMT',m)
    sh=[s for s in sh if len(s['v'])]
    if not sh: noshape.append(m); continue
    for fk,r,b in lst:
        R=ref_matrix(*r['data'][3:]); s0=r.get('scale') or 1.0; pos=np.array(r['data'][:3])
        for s in sh:
            w=(s['v']*s0)@R.T+pos; dd=w-c.pos; zz=dd@c.f
            ok=zz>50
            X=W/2+c.focal*(dd@c.r)/np.where(ok,zz,1); Y=H/2-c.focal*(dd@c.u)/np.where(ok,zz,1)
            mk=ok&(abs(X-TX)<35)&(abs(Y-TY)<20)
            if mk.any():
                hits.append((int(mk.sum()),'%s:%06X'%fk,names[r['pi']],b[1],m,s['name'],[int(v) for v in pos],float(zz[mk].min()),float(zz[mk].max()),mi.get(m) or BF[os.path.join('meshes',m)]))
for h in sorted(hits,reverse=True): print(h)
print('hits',len(hits))
print('noshape',len(noshape),noshape[:40])

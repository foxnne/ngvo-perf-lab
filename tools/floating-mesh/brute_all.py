"""Project real meshes (loose or BSA) of ALL Tamriel refs (incl. initially disabled) and report any geometry at the target pixel.
Quick reject by per-model bounding radius vs distance of ref origin from the pixel ray."""
import sys, os, pickle, math, collections; sys.path.insert(0,'.')
from common import *; from cam import *; from nif import *
from bsa import BSA
d=load(); names=d['names']; refs=d['refs']; bases=d['bases']
M=pickle.load(open('meshidx.pkl','rb')); mi=M['idx']
bidx={}; BC={}
for p in M['bsas']:
    try: b=BSA(p)
    except Exception as e: continue
    BC[p]=b
    for k in b.files:
        if k.startswith('meshes'+os.sep) and k.endswith('.nif'): bidx.setdefault(k[7:],p)
print('bsa meshes',len(bidx),flush=True)
c=Cam(pitch=3.0); TX,TY=2755,468; ray=c.ray(TX,TY)
WX,WY=(float(sys.argv[1]),float(sys.argv[2])) if len(sys.argv)>2 else (35,20)
cache={}
def model(m):
    if m in cache: return cache[m]
    try:
        src=mi[m] if m in mi else BC[bidx[m]].read(os.path.join('meshes',m))
        sh,blk,_=shapes(src)
        sh=[s for s in sh if len(s['v'])]
        rad=max((float(np.linalg.norm(s['v'],axis=1).max()) for s in sh),default=0.0)
        cache[m]=(sh,rad)
    except KeyError:
        cache[m]=None
    except Exception as e:
        cache[m]=None; errs.append((m,str(e)[:60]))
    return cache[m]
PTS=[(x,y) for x in range(2719,2766,4) for y in range(466,483,2)]
errs=[]; hits=[]; stats=collections.Counter()
for fk,h in refs.items():
    r=h[-1]
    if 'data' not in r or r['flags']&0x20: continue
    b=bases.get(r.get('base'))
    if not b or not b[2]: stats['nomodel']+=1; continue
    m=os.path.normpath(b[2].lower())
    if m.startswith('meshes'+os.sep): m=m[7:]
    pos=np.array(r['data'][:3]); v=pos-c.pos; t=v@ray; perp=np.linalg.norm(v-t*ray)
    md=model(m)
    if md is None: stats['unresolved']+=1; continue
    sh,rad=md; s0=r.get('scale') or 1.0
    if perp>rad*s0+max(t,0)*0.03+50 or t<-rad*s0: stats['rejected']+=1; continue
    stats['tested']+=1
    R=ref_matrix(*r['data'][3:])
    for s in sh:
        w=(s['v']*s0)@R.T+pos; dd=w-c.pos; zz=dd@c.f
        ok=zz>50
        X=W/2+c.focal*(dd@c.r)/np.where(ok,zz,1); Y=H/2-c.focal*(dd@c.u)/np.where(ok,zz,1)
        T=s['tris']
        if not len(T): continue
        allok=ok[T].all(1)
        ax,ay,bx,by,cx_,cy_=X[T[:,0]],Y[T[:,0]],X[T[:,1]],Y[T[:,1]],X[T[:,2]],Y[T[:,2]]
        area=np.abs((bx-ax)*(cy_-ay)-(cx_-ax)*(by-ay)); allok=allok&(area>1e-3)
        for (qx,qy) in PTS:
            d1=(qx-bx)*(ay-by)-(ax-bx)*(qy-by); d2=(qx-cx_)*(by-cy_)-(bx-cx_)*(qy-cy_); d3=(qx-ax)*(cy_-ay)-(cx_-ax)*(qy-ay)
            inside=allok&~(((d1<0)|(d2<0)|(d3<0))&((d1>0)|(d2>0)|(d3>0)))
            if inside.any():
                ti=np.where(inside)[0]
                hits.append((int(inside.sum()),(qx,qy),'%s:%06X'%fk,'>'.join(names[x['pi']] for x in h),b[1],m,s['name'],[int(v) for v in pos],r.get('scale'),hex(r['flags']),round(float(zz[T[ti]].min())),round(float(zz[T[ti]].max())),ti[:6].tolist()))
        partial=(ok[T].any(1)&~allok).sum()
        if partial: stats['tris_crossing_near_plane']+=int(partial)
print(stats); print('errs',len(errs),errs[:10])
unres=collections.Counter()
for h in sorted(hits,reverse=True): print(h)
print('hits',len(hits))

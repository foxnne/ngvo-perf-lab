import sys, os, glob, collections; sys.path.insert(0,'.')
from nif import *; from cam import *
D=r"C:\Modlists\NGVO 8.0 Beta\mods\NGVO - DynDOLOD Output\Meshes\terrain\Tamriel\Objects"
c=Cam(pitch=3.0); TX,TY=2755,468
hits=[]; types=collections.Counter(); nfiles=0
for f in sorted(glob.glob(os.path.join(D,'*.bto'))):
    n=os.path.basename(f).split('.'); lvl,cx,cy=int(n[1]),int(n[2]),int(n[3])
    org=np.array([cx*4096.,cy*4096.,0.])
    try: sh,blocks,strings=shapes(f)
    except Exception as e: print('ERR',f,e); continue
    nfiles+=1
    for t,_,_ in blocks: types[t]+=1
    for s in sh:
        if not len(s['v']): continue
        w=s['v']+org; d=w-c.pos; zz=d@c.f
        X=W/2+c.focal*(d@c.r)/np.where(zz>1,zz,1); Y=H/2-c.focal*(d@c.u)/np.where(zz>1,zz,1)
        m=(zz>100)&(abs(X-TX)<60)&(abs(Y-TY)<40)
        if m.any():
            # triangles with any vertex in window
            tm=m[s['tris']].any(1)
            hits.append((os.path.basename(f),s['block'],s['name'],s['parent'],int(m.sum()),int(tm.sum()),float(zz[m].min()),float(zz[m].max()),w[m].min(0).round(),w[m].max(0).round(),float(X[m].min()),float(X[m].max()),float(Y[m].min()),float(Y[m].max())))
print(nfiles,'files',types)
for h in hits: print(h)

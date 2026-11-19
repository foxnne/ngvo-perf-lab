import sys, os, glob, collections; sys.path.insert(0,'.')
from nif import *; from cam import *
D=r"C:\Modlists\NGVO 8.0 Beta\mods\NGVO - DynDOLOD Output\Meshes\terrain\Tamriel\Objects"
c=Cam(pitch=3.0)
PTS=[(2737,470),(2745,469),(2755,468),(2765,470),(2772,471)]
for f in sorted(glob.glob(os.path.join(D,'*.bto'))):
    n=os.path.basename(f).split('.'); lvl,cx,cy=int(n[1]),int(n[2]),int(n[3])
    org=np.array([cx*4096.,cy*4096.,0.])
    sh,blocks,strings=shapes(f)
    for s in sh:
        if not len(s['v']): continue
        w=s['v']+org; d=w-c.pos; zz=d@c.f; ok=zz>50
        X=W/2+c.focal*(d@c.r)/np.where(ok,zz,1); Y=H/2-c.focal*(d@c.u)/np.where(ok,zz,1)
        T=s['tris']; allok=ok[T].all(1)
        ax,ay,bx,by,cx_,cy_=X[T[:,0]],Y[T[:,0]],X[T[:,1]],Y[T[:,1]],X[T[:,2]],Y[T[:,2]]
        area=np.abs((bx-ax)*(cy_-ay)-(cx_-ax)*(by-ay)); allok&=area>1e-3
        for qx,qy in PTS:
            d1=(qx-bx)*(ay-by)-(ax-bx)*(qy-by); d2=(qx-cx_)*(by-cy_)-(bx-cx_)*(qy-cy_); d3=(qx-ax)*(cy_-ay)-(cx_-ax)*(qy-ay)
            ins=allok&~(((d1<0)|(d2<0)|(d3<0))&((d1>0)|(d2>0)|(d3>0)))
            if ins.any():
                ti=np.where(ins)[0]
                print(os.path.basename(f),(qx,qy),s['block'],s['name'],int(ins.sum()),'depth',zz[T[ti]].min().round(),zz[T[ti]].max().round(),'world',w[T[ti]].reshape(-1,3).min(0).round(),w[T[ti]].reshape(-1,3).max(0).round(),'tri',ti[:5].tolist())
print('done')

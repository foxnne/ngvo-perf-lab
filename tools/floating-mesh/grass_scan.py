import sys, os, re, collections; sys.path.insert(0,'.')
from common import *; from cam import *; from cgid import *
hm=load_hm(); c=Cam(pitch=3.0); TX,TY=2755,468
R=int(sys.argv[1]) if len(sys.argv)>1 else 10
near=[]; high=collections.Counter(); highex={}; tot=0
for cx in range(4-R,4+R+1):
    for cy in range(-2-R,-2+R+1):
        p=os.path.join(GD,'tamrielx%04dy%04d.cgid'%(cx,cy)) if True else None
        p=os.path.join(GD,'tamrielx%sy%s.cgid'%(('%04d'%cx) if cx>=0 else '-%03d'%-cx, ('%04d'%cy) if cy>=0 else '-%03d'%-cy))
        if not os.path.exists(p): continue
        try: blocks=parse(p)
        except Exception as e: print('ERR',p,e); continue
        for name,bb,inst in blocks:
            if not len(inst): continue
            P=inst[:,:3].astype(float); tot+=len(P)
            P[:,0]+=49152*np.round((cx*4096+2048-P[:,0])/49152); P[:,1]+=49152*np.round((cy*4096+2048-P[:,1])/49152)
            g=ground(hm,P[:,0],P[:,1]); agl=P[:,2]-g
            m=np.abs(agl)>250
            if m.any():
                high[(cx,cy,name)]+=int(m.sum()); highex[(cx,cy,name)]=(P[m][0].round(),float(agl[m].min()),float(agl[m].max()))
            d=P-c.pos; zz=d@c.f; ok=zz>50
            X=W/2+c.focal*(d@c.r)/np.where(ok,zz,1); Y=H/2-c.focal*(d@c.u)/np.where(ok,zz,1)
            k=ok&(abs(X-TX)<60)&(abs(Y-TY)<40)
            for i in np.where(k)[0]: near.append((cx,cy,name,P[i].round(),float(agl[i]),float(zz[i]),float(X[i]),float(Y[i]),inst[i].round(2).tolist()))
print('instances',tot)
print('NEAR TARGET PIXEL:')
for n in near: print(n)
print('cells/types with |agl|>250:',len(high))
for k,v in sorted(high.items(),key=lambda kv:-kv[1])[:40]: print(v,k,highex[k])

import sys, math; sys.path.insert(0,'.')
from nif import *; from cam import *
def ray_tris(o, d, V, T):
    """Moller-Trumbore, returns (tri idx, t, u, v) for all hits."""
    a=V[T[:,0]]; e1=V[T[:,1]]-a; e2=V[T[:,2]]-a
    p=np.cross(d,e2); det=(e1*p).sum(1)
    ok=np.abs(det)>1e-12
    inv=np.where(ok,1/np.where(ok,det,1),0)
    s=o-a; u=(s*p).sum(1)*inv
    q=np.cross(s,e1); v=(q@d)*inv; t=(e2*q).sum(1)*inv
    m=ok&(u>=0)&(v>=0)&(u+v<=1)&(t>1)
    i=np.where(m)[0]
    return i,t[i],u[i],v[i]
if __name__=='__main__':
    p=r"C:\Modlists\NGVO 8.0 Beta\mods\Sir Rumple's Tree of Life\Meshes\Landscape\Trees\Tree of Life\Tree_of_Life.nif"
    sh,blocks,strings=shapes(p)
    c=Cam(pitch=3.0)
    pos=np.array([13439,-1612,-4774.]); R=ref_matrix(0,0,math.radians(45))
    for s in sh:
        w=s['v']@R.T+pos
        seen={}
        for px in range(2719,2766,2):
            for py in range(468,481,1):
                i,t,u,v=ray_tris(c.pos,c.ray(px,py),w,s['tris'])
                for k,tt in zip(i,t): seen.setdefault(int(k),[]).append((px,py,round(float(tt))))
        print(s['name'],'tris hit:',len(seen))
        for k,l in seen.items():
            tri=s['tris'][k]; print('   tri',k,'npix',len(l),'t',min(x[2] for x in l),max(x[2] for x in l),'verts world',w[tri].round().tolist(),'local',s['v'][tri].round().tolist())

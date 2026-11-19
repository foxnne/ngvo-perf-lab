from common import *; from cam import *
import sys
d=load(); hm=load_hm(); names=d['names']; refs=d['refs']; bases=d['bases']; cells=d['cells']
c=Cam(pitch=3.0); ray=c.ray(2755,468)
MAXANG=float(sys.argv[1]) if len(sys.argv)>1 else 3.0
rows=[]
for fk,h in refs.items():
    r=h[-1]
    # merge: last override wins entirely, but data must exist
    if 'data' not in r: continue
    P=np.array(r['data'][:3]); v=P-c.pos; dist=np.linalg.norm(v)
    if dist<1500 or dist>300000: continue
    ang=math.degrees(math.acos(max(-1,min(1,v@ray/dist))))
    if ang>MAXANG: continue
    g=float(ground(hm,P[0],P[1])); b=bases.get(r.get('base'),('?','?','?',0,0))
    px,py,_=c.project(P)
    rows.append((ang,dist,P,g,fk,r,b,h,px,py))
rows.sort(key=lambda t:t[0])
for ang,dist,P,g,fk,r,b,h,px,py in rows:
    fl=r['flags']; tags=''.join(t for m,t in [(0x20,'DEL '),(0x800,'DIS '),(0x400,'pers '),(0x8000,'VWD '),(0x10000,'FULLLOD '),(0x200,'hid?')] if fl&m)
    print('%5.2f deg d=%6d px=(%4d,%4d) agl=%6d pos=(%d,%d,%d) %s:%06X [%s] %s %s | %s scale=%s %s xesp=%s' % (ang,dist,px,py,P[2]-g,P[0],P[1],P[2],fk[0],fk[1],'>'.join(names[x['pi']] for x in h),b[0],b[1],b[2],r.get('scale'),tags,r.get('xesp')))

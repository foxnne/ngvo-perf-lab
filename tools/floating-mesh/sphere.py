from common import *; from cam import *
import sys
d=load(); hm=load_hm(); names=d['names']; refs=d['refs']; bases=d['bases']
c=Cam(pitch=3.0); ray=c.ray(2755,468)
t=np.arange(0,300000,2000.0); P=c.pos+np.outer(t,ray)
print('ray profile t, z, ground:', [(int(a),int(b),int(g)) for a,b,g in zip(t[::5],P[::5,2],ground(hm,P[::5,0],P[::5,1]))])
out=[]
for fk,h in refs.items():
    r=h[-1]
    if 'data' not in r: continue
    b=bases.get(r.get('base'))
    ob=b[5] if b and b[5] else None
    s=r.get('scale') or 1.0
    rad=(max(np.linalg.norm([max(abs(ob[i]),abs(ob[i+3])) for i in range(3)]),50) if ob and any(ob) else 3000)*s
    Pp=np.array(r['data'][:3]); v=Pp-c.pos; tt=v@ray
    if tt<200: continue
    perp=np.linalg.norm(v-tt*ray)
    slack=tt*math.radians(1.5)
    if perp<rad+slack:
        out.append((perp/ (rad+1),perp,rad,tt,fk,r,b,h))
out.sort(key=lambda o:o[3])
for q,perp,rad,tt,fk,r,b,h in out:
    fl=r['flags']; tags=''.join(t for m,t in [(0x20,'DEL '),(0x800,'DIS '),(0x400,'pers '),(0x8000,'VWD '),(0x10000,'FULLLOD ')] if fl&m)
    b=b or ('?','?','?',0,0,None)
    print('t=%6d perp=%6d rad=%6d need_w=%5d | %s:%06X [%s] %s %s | %s obnd=%s scale=%s pos=%s rot=%s %s' % (tt,perp,rad,tt*0.0224,fk[0],fk[1],'>'.join(names[x['pi']] for x in h),b[0],b[1],b[2],b[5],r.get('scale'),[int(x) for x in r['data'][:3]],[round(math.degrees(x)) for x in r['data'][3:]],tags))

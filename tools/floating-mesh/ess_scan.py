import sys, struct, zlib, math, collections; sys.path.insert(0,'.')
from ess import *; from common import *; from cam import *
d=load(); hm=load_hm(); bases=d['bases']; refs=d['refs']
info,formids,forms=parse(sys.argv[1]); MAXA=float(sys.argv[2]) if len(sys.argv)>2 else 6
c=Cam(pitch=3.0); ray=c.ray(2741,474)
def fk(fid):
    if fid is None: return None
    hi=fid>>24
    if hi==0xFF: return ('<created>',fid&0xFFFFFF)
    if hi==0xFE:
        i=(fid>>12)&0xFFF; return (info['light'][i].lower() if i<len(info['light']) else '?', fid&0xFFF)
    return (info['plugins'][hi].lower() if hi<len(info['plugins']) else '?', fid&0xFFFFFF)
stats=collections.Counter(); out=[]
for refid,cflags,t,ver,l2,data in forms:
    if t not in (0,1,2,3,4,5,6,7,8,9,10,11): continue
    if l2:
        try: data=zlib.decompress(data)
        except Exception: stats['zerr']+=1; continue
    created=(refid>>22)==2
    if cflags&0x8: it=6
    elif created: it=5
    elif cflags&0x3: it=4
    else: stats['noinit']+=1; continue
    if len(data)<27: stats['short']+=1; continue
    cell=(data[0]<<16)|(data[1]<<8)|data[2]
    pos=struct.unpack_from('<6f',data,3)
    base=None
    if it==5 and len(data)>=31: base=resolve((data[28]<<16)|(data[29]<<8)|data[30],formids)
    if not all(math.isfinite(x) and abs(x)<1e6 for x in pos[:3]): stats['badpos']+=1; continue
    stats['it%d'%it]+=1
    P=np.array(pos[:3]); v=P-c.pos; dist=np.linalg.norm(v)
    if dist<1: continue
    ang=math.degrees(math.acos(max(-1,min(1,v@ray/dist))))
    fid=resolve(refid,formids); cellf=resolve(cell,formids)
    if base is None and fid is not None and not created:
        h=refs.get(fk(fid)); base_k=h[-1].get('base') if h else None
    else: base_k=fk(base)
    b=bases.get(base_k)
    out.append((ang,dist,t,it,'%08X'%(fid or 0),fk(fid),[round(x) for x in pos[:3]],[round(math.degrees(x)) for x in pos[3:]],'cell %08X'%(cellf or 0),fk(cellf),hex(cflags),base_k,b[:3] if b else None,round(P[2]-float(ground(hm,P[0],P[1])))))
print(stats)
out.sort(key=lambda o:o[0])
for o in out:
    if o[0]<=MAXA: print(o)
import pickle; pickle.dump(out,open('ess_out.pkl','wb'))

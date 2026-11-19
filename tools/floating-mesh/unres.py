import sys, os, pickle, collections; sys.path.insert(0,'.')
from common import *; from cam import *
from bsa import BSA
d=load(); names=d['names']; refs=d['refs']; bases=d['bases']
M=pickle.load(open('meshidx.pkl','rb')); mi=M['idx']; bidx=set()
for p in M['bsas']:
    try: b=BSA(p)
    except Exception as e: print('BSA unreadable',os.path.basename(p),e); continue
    bidx|={k[7:] for k in b.files if k.startswith('meshes'+os.sep)}
c=Cam(pitch=3.0); ray=c.ray(2755,468)
cnt=collections.Counter(); ex={}
for fk,h in refs.items():
    r=h[-1]; b=bases.get(r.get('base'))
    if 'data' not in r or not b or not b[2]: continue
    m=os.path.normpath(b[2].lower())
    if m.startswith('meshes'+os.sep): m=m[7:]
    if m in mi or m in bidx: continue
    P=np.array(r['data'][:3]); v=P-c.pos; t=v@ray; perp=np.linalg.norm(v-t*ray)
    cnt[(b[1],m,names[b[3]])]+=1
    e=ex.get((b[1],m,names[b[3]]))
    if e is None or perp<e[0]: ex[(b[1],m,names[b[3]])]=(round(perp),round(t),'%s:%06X'%fk,[round(x) for x in P],hex(r['flags']),names[r['pi']])
for k,v in sorted(cnt.items(),key=lambda kv:ex[kv[0]][0]): print(v,k,ex[k])

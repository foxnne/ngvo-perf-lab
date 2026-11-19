import sys, os, pickle, math; sys.path.insert(0,'.')
from common import *; from cam import *; from nif import *
from bsa import BSA
from PIL import Image, ImageDraw
d=load(); names=d['names']; refs=d['refs']; bases=d['bases']
M=pickle.load(open('meshidx.pkl','rb')); mi=M['idx']
def getmesh(m):
    if m in mi: return mi[m]
    for p in M['bsas']:
        try: b=BSA(p)
        except Exception: continue
        k=os.path.join('meshes',m)
        if k in b.files: print('  from',p); return b.read(k)
c=Cam(pitch=3.0)
im=Image.open(r'C:\Users\foxnn\dev\ngvo-perf-lab\results\sky_sweep\terrainlod-plains\00_sunlit__h12.png').convert('RGB'); dr=ImageDraw.Draw(im)
cols=[(255,0,0),(0,255,0),(0,0,255),(255,255,0)]
for a,col in zip(sys.argv[2:],cols):
    pl,fid=a.split(':'); fk=(pl,int(fid,16)); h=refs[fk]
    for i,r in enumerate(h): print(a,names[r['pi']],hex(r['flags']),[round(x) for x in r['data'][:3]],[round(math.degrees(x)) for x in r['data'][3:]],r.get('scale'),r.get('xesp'),bases.get(r['base'])[:3])
    r=h[int(os.environ.get('OV','-1'))]; b=bases[r['base']]
    m=os.path.normpath(b[2].lower())
    sh,blk,strs=shapes(getmesh(m))
    print('  blocks',[t for t,_,_ in blk])
    R=ref_matrix(*r['data'][3:]); s0=r.get('scale') or 1.0; pos=np.array(r['data'][:3])
    for s in sh:
        w=(s['v']*s0)@R.T+pos; dd=w-c.pos; zz=dd@c.f
        X=W/2+c.focal*(dd@c.r)/zz; Y=H/2-c.focal*(dd@c.u)/zz
        print('  shape',s['name'],len(s['v']),'verts', len(s['tris']),'tris; screen bbox',X.min().round(),X.max().round(),Y.min().round(),Y.max().round(),'local bbox',s['v'].min(0).round(),s['v'].max(0).round())
        for t in s['tris']:
            if (zz[t]>10).all(): dr.polygon([(X[i],Y[i]) for i in t],outline=col)
im.resize((1720,720)).save(sys.argv[1]+'.png')
im.crop((2455,300,3055,640)).resize((1200,680)).save(sys.argv[1]+'_crop.png')

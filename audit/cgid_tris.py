import re,os,sys,collections
d="C:/Modlists/NGVO 8.0 Beta/mods/NGVO - Grass Cache/grass"
tri={}
for l in open('grass_nif_tris.txt'):
    p=l.split(None,4)
    if p[0]=='ERR': continue
    n=os.path.basename(p[4].strip()).lower()
    if n not in tri or 'DynDOLOD' in p[4]: tri[n]=(int(p[0]),int(p[1]))
pat=re.compile(rb"andscape.[ -~]+?[.]nif")
def parse(f):
    b=open(os.path.join(d,f),'rb').read(); ms=list(pat.finditer(b)); out=collections.Counter()
    for i,m in enumerate(ms):
        end=ms[i+1].start()-5 if i+1<len(ms) else len(b)
        out[os.path.basename(m.group().decode().replace(chr(92),'/')).lower()]+=max(0,end-m.end()-51)/30.0
    return out,len(ms)
def fn(x,y):
    fx=("-%03d"%-x) if x<0 else "%04d"%x; fy=("-%03d"%-y) if y<0 else "%04d"%y
    return "tamrielx%sy%s.cgid"%(fx,fy)
cx,cy=int(sys.argv[1]),int(sys.argv[2])
for R in (1,2,3,4,6):
    tot=collections.Counter();k=0;miss=0
    for x in range(cx-R,cx+R+1):
        for y in range(cy-R,cy+R+1):
            if os.path.exists(os.path.join(d,fn(x,y))):
                c,n=parse(fn(x,y));tot+=c;k+=n
    inst=sum(tot.values()); t=sum(v*tri.get(n,(0,0))[0] for n,v in tot.items()); vv=sum(v*tri.get(n,(0,0))[1] for n,v in tot.items())
    unk=sum(v for n,v in tot.items() if n not in tri)
    print("R=%d (%dx%d cells): instances %.0fk, batches %d, triangles %.1fM, vertices %.1fM, inst w/o tri data %.0f"%(R,2*R+1,2*R+1,inst/1e3,k,t/1e6,vv/1e6,unk))

# Light-weight grass cache sampler: counts approx instances per grass mesh (bytes between names / 30).
import re,os,sys,random,collections,struct
d=r"C:\Modlists\NGVO 8.0 Beta\mods\NGVO - Grass Cache\grass"
pat=re.compile(rb"andscape.[ -~]+?[.]nif")
def parse(fn):
    b=open(os.path.join(d,fn),'rb').read()
    ms=list(pat.finditer(b))
    out=collections.Counter()
    for i,m in enumerate(ms):
        end=ms[i+1].start()-4 if i+1<len(ms) else len(b)
        out[m.group().decode().lower()]+=max(0,(end-m.end()-51))/30.0
    return out,len(b),len(ms)
def name(x,y): return "tamrielx%04dy%04d.cgid"%(x,y) if True else None
def fn(x,y):
    fx=("-%03d"%-x) if x<0 else "%04d"%x
    fy=("-%03d"%-y) if y<0 else "%04d"%y
    return "tamrielx%sy%s.cgid"%(fx,fy)
cx,cy=int(sys.argv[1]),int(sys.argv[2])
for R in (2,3,5):
    tot=collections.Counter();by=0;n=0;batches=0
    for x in range(cx-R,cx+R+1):
        for y in range(cy-R,cy+R+1):
            f=fn(x,y)
            if os.path.exists(os.path.join(d,f)):
                c,s,k=parse(f);tot+=c;by+=s;n+=1;batches+=k
    print("radius",R,"cells",n,"bytes %.1f MB"%(by/1e6),"approx instances %d"%sum(tot.values()),"mesh-entries(batches)",batches)
    if R in(2,5):
        for k,v in tot.most_common(25): print("   %8d %s"%(v,k))
random.seed(1)
fs=[f for f in os.listdir(d) if f.lower().startswith('tamrielx')]
tot=collections.Counter();by=0;b2=0
for f in random.sample(fs,200):
    c,s,k=parse(f);tot+=c;by+=s;b2+=k
print("random 200 tamriel cells: avg bytes %.0f, avg instances %.0f, avg batches %.1f"%(by/200,sum(tot.values())/200,b2/200))
for k,v in tot.most_common(30): print("   %8d %s"%(v,k))

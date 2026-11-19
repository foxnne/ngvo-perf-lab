import json,collections,os,sys,struct,re
import bsa_list
INST="C:/Modlists/NGVO 8.0 Beta"
d=json.load(open('basescan.json'))
modl={(m,l):(p,w) for m,l,p,w in d['modl']}
enabled=[l[1:].rstrip('\r\n') for l in open(INST+"/profiles/foxnne-nsfw/modlist.txt",encoding='utf-8',errors='replace') if l.startswith('+')]
src=open('nif_tris.py').read().split("for line in sys.stdin")[0]
ns={};exec(src,ns)
ns2={};exec(src.replace("b = open(path, 'rb').read()","b = path"),ns2)
exec(open('bsa_nif_sample.py').read().split("src=open")[0].split("import bsa_list")[1],globals())
bsas={}
def bsa_lookup(path):
    out=[]
    for bn in ["mods/Nature of the Wild Lands/Nature of the Wild Lands.bsa","mods/Lux Via/Lux Via.bsa","mods/JK's Skyrim/JKs Skyrim.bsa","mods/Lux Via/Lux - Resources.bsa"]:
        if bn not in bsas:
            lst,fl=bsa_list.listing(INST+"/"+bn); bsas[bn]=({x[3].replace(chr(92),'/').lower():x for x in lst},fl)
        t,fl=bsas[bn]
        if path in t:
            size,comp,off,name=t[path]; f=open(INST+"/"+bn,'rb'); f.seek(off); b=f.read(size)
            if fl&0x100: b=b[1+b[0]:]
            if comp: b=lz4_frame(b[4:])
            return ns2['parse'](b)+(bn.split('/')[1]+' (BSA)',)
    return None
cache={}
def winner(path):
    if path in cache: return cache[path]
    r=None
    for m in enabled:
        p=INST+"/mods/"+m+"/meshes/"+path
        if os.path.isfile(p):
            try: r=ns['parse'](p)+(m,)
            except Exception as e: r=(0,0,0,0,m+' (parse err)')
            break
    if r is None:
        try: r=bsa_lookup('meshes/'+path)
        except Exception as e: r=None
    cache[path]=r; return r
for (cx,cy,R) in [(3,-3,2),(5,-2,2)]:
    cnt=collections.Counter()
    for k,v in d['bases'].items():
        x,y=map(int,k.split(','))
        if abs(x-cx)<=R and abs(y-cy)<=R:
            for m,l,t,n in v: cnt[(m,l,t)]+=n
    bym=collections.Counter(); typ={}
    for (m,l,t),n in cnt.items():
        if t not in('TREE','STAT','MSTT','FLOR','ACTI','CONT','FURN'): continue
        p=modl.get((m,l),('?',''))[0]; bym[p]+=n; typ[p]=t
    print("\n== center (%d,%d) R=%d: %d refs with models, %d distinct models"%(cx,cy,R,sum(bym.values()),len(bym)))
    tt=0;ss=0;known=0;unk=0
    rows=[]
    for p,n in bym.most_common():
        w=winner(p) if n>=3 or typ[p]=='TREE' else None
        if w: tt+=w[0]*n; ss+=w[2]*n; known+=n
        else: unk+=n
        rows.append((n,typ[p],p,w))
    print("   refs with measured winner mesh: %d -> %.2fM triangles, %d shapes (draws per pass); unmeasured (vanilla BSA or rare): %d refs"%(known,tt/1e6,ss,unk))
    for n,t,p,w in rows[:45]:
        print("   %4d %s %-62s %s"%(n,t,p[:62],("%6d tris %2d shp [%s]"%(w[0],w[2],w[4][:38])) if w else "vanilla BSA / not loose"))
    # per-type weight
    agg=collections.defaultdict(lambda:[0,0,0])
    for n,t,p,w in rows:
        if w: a=agg[t]; a[0]+=n; a[1]+=w[0]*n; a[2]+=w[2]*n
    for t,a in agg.items(): print("   type %s: %d refs, %.2fM tris, %d shapes"%(t,a[0],a[1]/1e6,a[2]))
print("\n#### Top models by total triangles (count x tris)")
for (cx,cy,R) in [(3,-3,2),(5,-2,2),(5,-2,4)]:
    cnt=collections.Counter()
    for k,v in d['bases'].items():
        x,y=map(int,k.split(','))
        if abs(x-cx)<=R and abs(y-cy)<=R:
            for m,l,t,n in v:
                if t in('TREE','STAT','MSTT','FLOR','ACTI','CONT','FURN'): cnt[modl.get((m,l),('?',''))[0]]+=n
    rows=[]
    for p,n in cnt.items():
        w=winner(p) if n>=2 else None
        if w: rows.append((n*w[0],n,w[0],w[2],p,w[4]))
    rows.sort(reverse=True)
    T=sum(r[0] for r in rows); S=sum(r[1]*r[3] for r in rows)
    print("== center (%d,%d) R=%d: measured %.2fM tris, %d shape-draws, %d refs"%(cx,cy,R,T/1e6,S,sum(r[1] for r in rows)))
    bymod=collections.Counter(); bymods=collections.Counter()
    for r in rows: bymod[r[5]]+=r[0]; bymods[r[5]]+=r[1]*r[3]
    print("   by winning mod (tris):",[(k[:40],round(v/1e6,2)) for k,v in bymod.most_common(12)])
    print("   by winning mod (shape-draws):",[(k[:40],v) for k,v in bymods.most_common(12)])
    for r in rows[:18]: print("   %8d = %3d x %6d tris (%d shp) %-58s [%s]"%(r[0],r[1],r[2],r[3],r[4][:58],r[5][:34]))

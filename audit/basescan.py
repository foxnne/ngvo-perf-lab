# Top base objects (TREE/STAT/MSTT/FLOR/ACTI) placed near Whiterun, their winning model path, loose-file winner and triangle/shape counts.
import refscan, struct, collections, os, sys, json
R=refscan
bases=collections.defaultdict(collections.Counter)
orig=R.base_type
cur={}
def bt(pl,nm,base,get):
    r=orig(pl,nm,base,get)
    cur['b']=(pl.resolve(base,nm), r[0]); return r
R.base_type=bt
orig_do=R.do_refs
# wrap cells dict to capture increments
class Cap(collections.defaultdict):
    pass
def main():
    paths=R.plugin_paths(); plugs={}
    def get(name):
        k=name.lower()
        if k not in plugs: plugs[k]=R.Plugin(paths[k]) if k in paths else None
        return plugs[k]
    names=R.active_plugins()
    # 1) collect bases per cell by re-walking with a hook
    class Hook(dict):
        def __missing__(s,xy):
            class P(dict):
                def __missing__(t,nm):
                    class C(collections.Counter):
                        def __setitem__(u,k,v):
                            if 'disabled' not in k and k!='ACHR': bases[xy][cur['b'][0]+(k,)]+=1
                            super().__setitem__(k,v)
                    c=C(); t[nm]=c; return c
            p=P(); s[xy]=p; return p
    cells=Hook()
    for name in names:
        pl=get(name)
        if pl is None or b'WRLD' not in pl.top: continue
        f=pl.f; nm=name.lower(); p,size=pl.top[b'WRLD']; end=p+size; q=p+24; cnt=collections.Counter()
        while q+24<=end:
            f.seek(q); h=f.read(24); t,s,a,b=struct.unpack_from('<4sIII',h)
            if t!=b'GRUP': q+=24+s; continue
            if b==1:
                m,lid=pl.resolve(a,nm)
                if m=='skyrim.esm' and lid==0x3C: R.walk_world(pl,nm,q+24,q+s,cells,cnt,get)
            q+=s
    # 2) winning MODL for base records: scan all active plugins' groups of wanted types in load order
    want={b'TREE',b'STAT',b'MSTT',b'FLOR',b'ACTI',b'CONT',b'FURN'}
    modl={}
    for name in names:
        pl=get(name)
        if pl is None: continue
        nm=name.lower()
        for label,(p,size) in pl.top.items():
            if label not in want: continue
            end=p+size;q=p+24;f=pl.f
            while q+24<=end:
                f.seek(q);h=f.read(24);t,s,flags,fid=struct.unpack_from('<4sIII',h)
                if t==b'GRUP': q+=s; continue
                key=pl.resolve(fid,nm)
                for st,sb in R.subrecords(R.body_of(f,s,flags)):
                    if st==b'MODL': modl[key]=(sb.rstrip(b'\0').decode('latin1').lower().replace(chr(92),'/'),nm); break
                q+=24+s
    json.dump({'bases':{"%d,%d"%k:[[m,l,t,n] for (m,l,t),n in v.items()] for k,v in bases.items()},
               'modl':[[k[0],k[1],v[0],v[1]] for k,v in modl.items()]},open('basescan.json','w'))
    print('cells',len(bases),'models',len(modl))
main()

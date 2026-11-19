"""python flyanalyze.py LABEL  -> where the main thread was during stall frames (>100 ms) vs the whole run."""
import json,os,sys,collections,bisect
HERE=os.path.dirname(os.path.abspath(__file__)); D=os.path.join(os.path.dirname(HERE),'edits','flybench',sys.argv[1])
SYS={'ntdll.dll','KERNELBASE.dll','KERNEL32.DLL','win32u.dll','USER32.dll','ucrtbase.dll','VCRUNTIME140.dll','MSVCP140.dll','msvcp140.dll','combase.dll','d3d11.dll','nvwgf2umx.dll','dxgi.dll','D3D12Core.dll','D3D12.dll'}
fj=json.load(open(os.path.join(D,'frames.json'))); f=fj['frames']['columns']['frameMs']; t=fj['t_start']*1000
fr=[]; 
for ms in f: fr.append((t,t+ms,ms)); t+=ms
# frame recorder start may lag the wall clock a little; align end to recorded duration is good enough
st=[x for x in fr if x[2]>100]
samples=[]
for l in open(os.path.join(D,'stacks.csv')):
    p=l.strip().split(',')
    if len(p)>2 and p[0].isdigit(): samples.append((int(p[0]),p[1:]))
ts=[s[0] for s in samples]
def agg(sel):
    own=collections.Counter(); anym=collections.Counter(); ch=collections.Counter()
    for _,p in sel:
        mods=[x.split('+')[0] for x in p]
        own[next((m for m in mods if m not in SYS and m!='?'),'?')]+=1
        for m in set(mods):
            if m not in SYS and m not in ('SkyrimSE.exe','?'): anym[m]+=1
        seq=[]
        for m in mods:
            if m in SYS: continue
            if not seq or seq[-1]!=m: seq.append(m)
        ch[' < '.join(seq[:6])]+=1
    return own,anym,ch
allo,alla,allc=agg(samples)
sel=[]
for a,b,ms in st:
    i=bisect.bisect_left(ts,a-30); j=bisect.bisect_right(ts,b+30); sel+=samples[i:j]
so,sa,sc=agg(sel)
N=len(samples); n=max(len(sel),1)
print(sys.argv[1],'frames',len(f),'stall frames>100ms',len(st),'total stall ms',round(sum(x[2] for x in st)),'| samples',N,'in stalls',len(sel))
print('stall frames (s into run, ms):',[(round((a-fj['t_start']*1000)/1000,1),round(ms)) for a,b,ms in st][:30])
print('\nmodule present ANYWHERE in stack: stall% vs whole-run%')
keys=sorted(set(list(sa)[:0]+[k for k,_ in sa.most_common(18)]),key=lambda k:-sa[k])
for k in keys: print('  %-34s %5.1f%%  vs %5.1f%%'%(k,100*sa[k]/n,100*alla[k]/N))
print('\ntop owners (first non-system frame) in stalls:'); [print('  %5.1f%% %s (run %.1f%%)'%(100*v/n,k,100*allo[k]/N)) for k,v in so.most_common(8)]
print('\ntop chains in stalls:'); [print('  %5.1f%% %s'%(100*v/n,k[:200])) for k,v in sc.most_common(10)]
vp=os.path.join(D,'vram.json')
if os.path.exists(vp):
    rows=json.load(open(vp)); g='SkyrimSE.exe|buf_geom'
    print('\ngeometry bursts >300MB (s into run, MB created, MB freed):',[(round((r['ts']-fj['t_start']*1000)/1000,1),round(r['created'].get(g,0)),round(r['freed'].get(g,0))) for r in rows if r['created'].get(g,0)>300])

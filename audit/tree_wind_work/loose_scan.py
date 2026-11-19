# Lists every mod (enabled or not) with loose files under meshes/landscape/trees, with modlist priority. Read-only.
import os,sys
root=r'C:\Modlists\NGVO 8.0 Beta'
lines=[l.rstrip('\n') for l in open(root+r'\profiles\foxnne-nsfw\modlist.txt',encoding='utf-8',errors='replace') if l[:1] in '+-']
state={l[1:]:(l[0],i) for i,l in enumerate(lines)}   # i small = higher priority
res=[]
for m in os.listdir(root+r'\mods'):
    d=os.path.join(root,'mods',m,'meshes','landscape','trees')
    if os.path.isdir(d):
        n=0;names=[]
        for dp,dn,fn in os.walk(d):
            for f in fn:
                if f.lower().endswith('.nif'): n+=1;names.append(os.path.relpath(os.path.join(dp,f),d).lower())
        st=state.get(m,('?',99999))
        res.append((st[1],st[0],m,n,names))
res.sort()
import json
json.dump({m:names for _,_,m,_,names in res},open('loose_trees.json','w'))
for pr,s,m,n,names in res: print(pr,s,n,m)
for extra in ['overwrite']:
    d=os.path.join(root,extra,'meshes','landscape','trees'); print(extra,os.path.isdir(d))

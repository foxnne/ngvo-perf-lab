import sys,pickle,os; sys.path.insert(0,'.')
from bsa import BSA
mi=pickle.load(open('meshidx.pkl','rb')); nl=pickle.load(open('notloose.pkl','rb'))
need={os.path.join('meshes',m) for m in nl}
found={}
for p in mi['bsas']:
    try: b=BSA(p)
    except Exception as e: print('skip',os.path.basename(p),e); continue
    hit=[m for m in need if m in b.files and m not in found]
    for m in hit: found[m]=p
    if hit: print(len(hit),os.path.basename(p))
print('missing',len(need-set(found)),sorted(need-set(found))[:30])
pickle.dump(found,open('bsafound.pkl','wb'))

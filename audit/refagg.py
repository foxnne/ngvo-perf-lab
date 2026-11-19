import json,collections,sys
d=json.load(open('refscan.json'))
def agg(cx,cy,R):
    per=collections.defaultdict(collections.Counter)
    for k,v in d['cells'].items():
        x,y=map(int,k.split(','))
        if abs(x-cx)<=R and abs(y-cy)<=R:
            for pn,c in v.items():
                for t,n in c.items(): per[pn][t]+=n
    return per
for (cx,cy,R) in [(3,-3,2),(5,-2,2),(5,-2,4)]:
    per=agg(cx,cy,R)
    tot=collections.Counter()
    for pn,c in per.items(): tot.update(c)
    van=collections.Counter()
    for pn in ('skyrim.esm','update.esm','dawnguard.esm','hearthfires.esm','dragonborn.esm'): van.update(per.get(pn,{}))
    print("\n== center (%d,%d) R=%d (%d cells): total new refs %d, vanilla %d"%(cx,cy,R,(2*R+1)**2,sum(tot.values()),sum(van.values())))
    print("  by type all :",dict(tot.most_common(14)))
    print("  by type vanilla:",dict(van.most_common(14)))
    for pn,c in sorted(per.items(),key=lambda kv:-sum(kv[1].values()))[:22]:
        print("  %6d %-55s %s"%(sum(c.values()),pn,dict(c.most_common(7))))

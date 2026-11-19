import json,sys,time,urllib.request,statistics as st
B='http://127.0.0.1:8920/api/tool/'
def post(t,b):
    r=urllib.request.Request(B+t,data=json.dumps(b).encode(),headers={'Content-Type':'application/json'}); return json.loads(urllib.request.urlopen(r,timeout=30).read())
def rec(sec=20):
    post('communityshaders.frames',{"action":"start"}); time.sleep(sec); post('communityshaders.frames',{"action":"stop"}); time.sleep(1.5)
    d=post('communityshaders.frames',{"action":"read"}); c=d['columns']; f=c['frameMs']; p=c['presentThreadCpuMs']
    q=lambda a,x: sorted(a)[int(len(a)*x)-1]
    return 'frames=%d mean=%.1f med=%.1f p95=%.1f p99=%.1f | presentThreadCpu mean=%.1f | FGflag=%.2f'%(len(f),st.mean(f),st.median(f),q(f,.95),q(f,.99),st.mean(p),sum(1 for x in c['frameGeneration'] if x)/len(f))
if __name__=='__main__':
    print(rec(int(sys.argv[1]) if len(sys.argv)>1 else 20))

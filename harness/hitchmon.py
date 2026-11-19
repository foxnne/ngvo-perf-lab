import sys,time,subprocess,json
sys.path.insert(0,'C:/Modlists/NGVO 8.0 Beta/look/tools')
import cs
out=open(sys.argv[1],'w'); t0=time.time(); last=None; 
def gpu():
    try: return int(subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True).stdout.split(',')[0])
    except Exception: return -1
while time.time()-t0<float(sys.argv[2]):
    t=time.time()
    try: s=cs.world(action='state'); cell=s['cell']['editorID']; hr=s['gameHour']; pos=(round(s['position']['x']),round(s['position']['y']))
    except Exception as e: cell='ERR'; hr=0; pos=(0,0)
    dt=time.time()-t
    rec=dict(ts=int(time.time()*1000),t=round(t-t0,1),cell=cell,pos=pos,hour=round(hr,3),vram=gpu(),apidt=round(dt,2))
    out.write(json.dumps(rec)+'\n'); out.flush(); time.sleep(0.4)

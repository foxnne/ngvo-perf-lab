"""Queue job: with the NAT-CS coverage patch, does Dragonsreach get Helios_<outside weather> (not the SkyrimClear fallback)
and its window sun? Outside: hour 13 + weather X (lock released before entering), then enter. X = SunnyPF, SunnyTU, CloudyTU.
usage: python helios_verify.py TAG"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'interior_ab', TAG); os.makedirs(OUT, exist_ok=True)
bench.launch(); bench.all_on()
rep = []
try:
    for w in ('SunnyPF', 'SunnyTU', 'CloudyTU'):
        for attempt in range(3):
            try: bench.goto('WhiterunExterior04'); break
            except RuntimeError: time.sleep(10)
        time.sleep(8)
        cs.world(action='hour', value=13.0)
        lw = cs.world(action='list_weathers', filter=w); cand = [x for x in (lw.get('weathers') or lw if isinstance(lw, list) else lw.get('weathers', [])) if x.get('editorID') == w]
        if not cand: print('weather not found', w, str(lw)[:300], flush=True); continue
        fid = cand[0].get('formID'); print('sw', w, fid, cs.world(action='console', command='sw %s' % fid.replace('0x', '')), flush=True); time.sleep(20)
        out_w = (cs.world(action='state').get('weather') or {}).get('editorID')
        bench.goto('WhiterunDragonsreach'); time.sleep(6)                 # first entry: Helios may time out right after a load
        bench.goto('WhiterunExterior04'); time.sleep(6)
        bench.goto('WhiterunDragonsreach'); time.sleep(8); cs.world(action='teleport', x=-448.0, y=-128.0, z=-318.0); time.sleep(10)
        in_w = (cs.world(action='state').get('weather') or {}).get('editorID')
        src = cs.shot('hv-%s-%s' % (TAG, w)); time.sleep(0.3); dst = os.path.join(OUT, 'dragonsreach__outside_%s.png' % w); st = None
        if src and os.path.exists(src): shutil.move(src, dst); st = cs.stats(dst)
        r = {'outside_set': w, 'outside_read': out_w, 'inside': in_w, 'stats': st}; rep.append(r); print(json.dumps(r), flush=True)
finally:
    try: cs.world(action='weather', lock=False)
    except Exception: pass
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
bench.finish()

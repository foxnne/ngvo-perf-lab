"""Queue job: where does grass actually draw? Same pose on the Whiterun plains (fov 70 and 25, yaw 250), CS Grass Optimizations
'Grass Render Distance' set live to 2000 / 8000 / 16000 / 24000 / 32000 / 40000, plus density variants at 40000
(MinDensity 1.0 + MinPixelSize 0.5 = no thinning). Shots are diffed afterwards to see which image rows (distances) change.
usage: python grass_slider.py TAG   Output results/grass_slider/TAG/"""
import os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'grass_slider', TAG); os.makedirs(OUT, exist_ok=True)


def get():
    r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': 'GrassOptimizations'}); return r.get('settings', r)


def put(s): cs.call('communityshaders.feature', {'action': 'set', 'shortName': 'GrassOptimizations', 'settings': s})


bench.launch(); bench.all_on()
S0 = None
try:
    bench.goto('WhiterunExterior04')
    cs.world(action='weather', name='SunnyPF', instant=True, lock=True); cs.world(action='hour', value=13.0); time.sleep(20)
    cs.world(action='timescale', value=0.0) if False else None
    bench.console('set timescale to 0'); time.sleep(1)
    p = bench.state_()['position']; S0 = get(); print('live settings:', S0, flush=True)
    variants = [('d%05d' % d, dict(S0, RenderDistanceOverride=float(d))) for d in (2000, 8000, 16000, 24000, 32000, 40000)]
    variants += [('d40000_dense', dict(S0, RenderDistanceOverride=40000.0, MinDensity=1.0, MinPixelSize=0.5, FullDetailPixelSize=1.0, MeshCostBias=0.0)),
                 ('d40000_dense_nolod', dict(S0, RenderDistanceOverride=40000.0, MinDensity=1.0, MinPixelSize=0.5, FullDetailPixelSize=1.0, MeshCostBias=0.0, EnableMeshLOD=False)),
                 ('d40000_noocclusion', dict(S0, RenderDistanceOverride=40000.0, EnableOcclusionCulling=False))]
    for fov, pitch in ((70.0, -5.0), (25.0, -2.0)):
        cs.call('communityshaders.testbed', {'action': 'camera', 'x': p['x'], 'y': p['y'], 'z': p['z'] + 250.0, 'pitch': pitch, 'yaw': 250.0, 'fov': fov}); time.sleep(6)
        for name, s in variants:
            put(s); time.sleep(6)
            src = cs.shot('gs-%s-%s-%d' % (TAG, name, int(fov))); time.sleep(0.4)
            if src and os.path.exists(src): shutil.move(src, os.path.join(OUT, 'fov%02d__%s.png' % (int(fov), name))); print('shot', fov, name, flush=True)
finally:
    try:
        if S0: put(S0)
        bench.console('set timescale to 20'); cs.world(action='weather', lock=False); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
    except Exception: pass
bench.finish()

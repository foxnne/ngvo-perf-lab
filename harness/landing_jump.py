"""Find what makes the picture jump brighter at the camera hand-back after a Sky Above landing (user 2026-11-25: 'fix the cause').
Flies Riverwood <-> Whiterun Stables, records screen brightness at 30 fps, reports the biggest sudden rise (6-frame step)
in the last seconds, once with everything on and once per suspect switched off.  usage: python landing_jump.py [suspects]"""
import json, os, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs, shots
SUSPECTS = sys.argv[1].split(',') if len(sys.argv) > 1 else ['none', 'ScreenSpaceGI', 'NeuralRendering', 'ExponentialHeightFog', 'VolumetricLighting']
FF = r'C:\Users\foxnn\dev\ffmpeg.exe'
VF = ('hwdownload,format=rgbaf16le,zscale=transferin=linear:primariesin=709:matrixin=gbr:rangein=full:npl=100:'
      'transfer=iec61966-2-1:primaries=709:matrix=gbr:range=full,format=gray,scale=320:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG')
tog = lambda f, on: cs.call('communityshaders.feature', {'action': 'toggle', 'shortName': f, 'enabled': on})
dest = ['Whiterun Stables', 'Riverwood']
res = []
for i, sus in enumerate(SUSPECTS):
    if sus != 'none': tog(sus, False); time.sleep(3)
    try:
        p = subprocess.Popen([FF, '-hide_banner', '-f', 'lavfi', '-i', 'ddagrab=output_idx=0:framerate=30:output_fmt=16bit', '-t', '24', '-vf', VF, '-f', 'null', '-'],
                             stderr=subprocess.PIPE, text=True)
        time.sleep(1.5); cs.world(action='fasttravel', name=dest[i % 2])
        err = p.communicate()[1]
        y = [float(l.split('YAVG=')[1]) for l in err.splitlines() if 'YAVG=' in l]
        steps = [(y[k + 6] / max(y[k], 1) , k) for k in range(len(y) - 6)]
        tail = [s for s in steps if s[1] > len(y) * 0.45]
        best = max(tail) if tail else (0, 0)
        res.append({'off': sus, 'jump_ratio': round(best[0], 3), 'at_s': round(best[1] / 30, 2), 'frames': len(y)})
        print(res[-1], flush=True)
        time.sleep(4); bench.settle(maxwait=60)
    finally:
        if sus != 'none': tog(sus, True); time.sleep(3)
json.dump(res, open(os.path.join(shots.ROOT, 'results', 'travel_ft', 'landing_jump_%s.json' % time.strftime('%H%M%S')), 'w'), indent=1)

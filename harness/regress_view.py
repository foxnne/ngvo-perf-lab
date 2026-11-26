"""Locked Riverwood view frame time (the 30.4 ms reference from 16:00 2026-11-25). usage: python regress_view.py [label]"""
import sys, time, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
label = sys.argv[1] if len(sys.argv) > 1 else 'now'
if cs.world(action='state').get('cell', {}).get('editorID') != 'Riverwood':
    bench.console('coc riverwood'); time.sleep(15); bench.settle(maxwait=240)
cs.world(action='weather', name='SunnyPF'); cs.world(action='timescale', value=20); cs.world(action='hour', value=13.0); time.sleep(12); cs.world(action='timescale', value=0)
cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'free', 'x': 16905.05, 'y': -47313.37, 'z': 140.35, 'yaw': 71.19, 'pitch': 34.0, 'fov': 95.0})
time.sleep(14); r = cs.call('communityshaders.inspect', {'kind': 'drawcalls'}); p = cs.call('communityshaders.inspect', {'kind': 'profiler'})
gpu = sum(q.get('gpuAvgMs', 0) for q in p['passes'])
top = sorted(p['passes'], key=lambda q: -q.get('gpuAvgMs', 0))[:4]
print('%-24s %.1f ms | draws %d (lighting %d, utility %d) | CS passes GPU %.1f ms | %s' % (label, r['frame']['avgMs'], r['shaders']['Total']['drawCalls'], r['shaders']['Lighting']['drawCalls'],
      r['shaders']['Utility']['drawCalls'], gpu, ', '.join('%s %.1f' % (q['name'].split('::')[-1][:16], q['gpuAvgMs']) for q in top)), flush=True)
cs.world(action='timescale', value=20); cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})

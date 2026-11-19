"""Break the slow frames of a Tracy capture down by instrumented CPU zone.
usage: python tracyframes.py CAPTURE.tracy [min_ms=50]
Frame boundaries come from the once-per-frame zone 'Main_RenderDepth::thunk'."""
import csv, io, os, subprocess, sys
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ext', 'tracy', 'tracy-csvexport.exe')
cap = sys.argv[1]; MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 50
ZONES = ['Main_RenderDepth::thunk', 'BuildBendWeights', 'Deferred::PrepassPasses', 'LinearLighting::Prepass', 'HiZOcclusion::Prepass', 'Evaluate',
         'ShaderCompilationTask', 'Deferred::EarlyPrepasses', 'Deferred::ReflectionsPrepasses', 'Deferred::DeferredPasses', 'GrassOptimizations', 'Skylighting::RenderOcclusion',
         'Upscaling::PerformUpscaling', 'CSEditor', 'SceneManager', 'FootstepParticles']


def events(f):
    out = subprocess.run([T, '-u', '-f', f, cap], capture_output=True, text=True).stdout
    return [(int(r['ns_since_start']), int(r['exec_time_ns']), r['name'], r['thread']) for r in csv.DictReader(io.StringIO(out))]


ev = {z: events(z) for z in ZONES}
marks = sorted(e[0] for e in ev['Main_RenderDepth::thunk'])
frames = [(a, b - a) for a, b in zip(marks, marks[1:])]
slow = [(s, d) for s, d in frames if d > MIN * 1e6]
print('%d frames, %d over %.0f ms; frame time median %.1f ms' % (len(frames), len(slow), MIN, sorted(d for _, d in frames)[len(frames) // 2] / 1e6))
print('   t(s)  frame   ' + '  '.join(z.split('::')[-1][:12].rjust(12) for z in ZONES[:10]) + '   unaccounted-by-these')
for s, d in slow:
    cols = []; acc = 0
    for z in ZONES[:10]:
        ms = sum(e[1] for e in ev[z] if s <= e[0] < s + d) / 1e6
        cols.append(ms)
    # depth thunk contains BuildBendWeights; PrepassPasses contains the feature prepasses: avoid double counting
    top = cols[0] + cols[2] + cols[5] + cols[7] + cols[8] + cols[9]
    print('%7.1f %6.0f   ' % (s / 1e9, d / 1e6) + '  '.join(('%12.1f' % c) for c in cols) + '   %8.0f' % (d / 1e6 - top))

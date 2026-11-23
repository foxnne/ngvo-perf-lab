"""Read a meter.json sweep (auto exposure + a ladder of pinned exposures) and estimate each scene's metered EV100.
usage: python meter_report.py TAG [TAG...]
For every hour: the central-area median of the auto-exposure frame is located on the pinned ladder, which gives the
EV100 the auto exposure metered. Clip% and black level per rung show where the scene holds together."""
import glob, os, re, sys
import numpy as np
from PIL import Image
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'sky_sweep')
def stats(p):
    a = np.asarray(Image.open(p).convert('RGB').resize((860, 360))).astype(float) / 255; L = a.mean(2)
    c = L[72:288, 172:688]                      # AdaptArea 0.6 x 0.6
    return np.median(c), 100 * (a.max(2) > 0.985).mean(), np.percentile(L, 1), np.percentile(L, 99)
for tag in sys.argv[1:]:
    fs = glob.glob(os.path.join(R, tag, '*.png')); hours = sorted({re.search(r'__h(\d+(?:\.\d+)?)\.png$', f).group(1) for f in fs}, key=float)
    for h in hours:
        auto = [f for f in fs if 'auto_full' in f and f.endswith('__h%s.png' % h)]
        rungs = sorted(((int(re.search(r'pin_([+-]\d+)', f).group(1)), f) for f in fs if 'pin_' in f and f.endswith('__h%s.png' % h)))
        print('== %s  %sh' % (tag, h))
        xs, ys = [], []
        for e, f in rungs:
            m, clip, lo, hi = stats(f); xs.append(e); ys.append(m)
            print('   pin %+3d EV100  centre median %.3f  clip %5.1f%%  p1 %.3f  p99 %.3f' % (e, m, clip, lo, hi))
        if auto:
            m, clip, lo, hi = stats(auto[0])
            # medians fall as the pin rises: interpolate on the monotone part
            ev = float(np.interp(-m, [-y for y in ys], xs)) if ys else float('nan')
            print('   AUTO   centre median %.3f  clip %5.1f%%  -> metered ~ %.1f EV100' % (m, clip, ev))

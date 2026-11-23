"""Print clip/black/median stats for the frames of a sweep. usage: python frame_stats.py TAG"""
import glob, os, sys
import numpy as np
from PIL import Image
d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'sky_sweep', sys.argv[1])
print('%-46s %6s %6s %6s %6s %7s' % ('frame', 'black', 'median', 'p95', 'clip%', 'sunshade'))
for p in sorted(glob.glob(d + '/*.png')):
    a = np.asarray(Image.open(p).convert('RGB').resize((860, 360))).astype(float) / 255; L = a.mean(2); g = L[150:]
    print('%-46s %6.3f %6.3f %6.3f %6.1f %7.1f' % (os.path.basename(p)[:-4], np.percentile(L, 0.5), np.median(L), np.percentile(L, 95), 100 * (a.max(2) > 0.985).mean(), np.percentile(g, 90) / max(np.percentile(g, 10), 1e-3)))

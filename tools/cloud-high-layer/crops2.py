from PIL import Image, ImageFilter
import numpy as np, os, glob
d = r'C:/Users/foxnn/dev/ngvo-perf-lab/results/sky_sweep/clearcover-ilinalta'
for f in sorted(glob.glob(d + '/*__h14.png')):
    n = os.path.basename(f)[:2]
    im = Image.open(f).convert('RGB')
    im.crop((1400, 0, 3120, 700)).save('sky_%s.jpg' % n, quality=92)

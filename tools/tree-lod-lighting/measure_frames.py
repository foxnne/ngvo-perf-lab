"""Mean colour / luminance of hand-picked boxes in the reference frames.
Boxes are full-resolution pixel coords (x0,y0,x1,y1). For tree boxes the 'dark half' (pixels at or below the box median luma)
is also reported, to reduce the influence of sky/ground seen through gaps.
Luminance is Rec.709 on sRGB-decoded values (display-linear), reported 0..1.
"""
from PIL import Image
import numpy as np
base = r'C:/Users/foxnn/dev/ngvo-perf-lab/results/sky_sweep/'
frames = {
    'plains h12': ('nocloudmesh-plains/01_mist_removed_height_fog_on__h12.png', [
        ('distant conifer mass (centre, in front of rock)', (1890, 880, 2050, 960)),
        ('distant conifers right of centre', (2170, 900, 2290, 965)),
        ('distant conifer mass (right, far slope)', (2560, 860, 2750, 950)),
        ('near pines (foreground right, loaded/first ring)', (2620, 1000, 2850, 1090)),
        ('sunlit grass/tundra mid-distance (centre)', (1700, 1010, 2100, 1060)),
        ('sunlit grass near far conifers (right)', (2375, 900, 2465, 930)),
        ('sunlit far slope ground (left of centre)', (1560, 780, 1700, 830)),
    ]),
    'ilinalta h9.5': ('sunlit-ilinalta/00_sunlit__h9.5.png', [
        ('far shore forest band', (2214, 766, 2671, 829)),
        ('mountain-slope forest (very far)', (2300, 657, 2443, 743)),
        ('near island conifer (full model)', (2323, 771, 2414, 920)),
        ('shore pines (mid, full model or first ring)', (2020, 789, 2157, 897)),
        ('sunlit grass on islet', (1963, 923, 2157, 937)),
    ]),
    'ilinalta h14': ('sunlit-ilinalta/00_sunlit__h14.png', [
        ('far shore forest band', (2214, 766, 2671, 829)),
        ('mountain-slope forest (very far)', (2300, 657, 2443, 743)),
        ('near island conifer (full model)', (2323, 771, 2414, 920)),
        ('shore pines (mid, full model or first ring)', (2020, 789, 2157, 897)),
        ('sunlit grass on islet', (1963, 923, 2157, 937)),
    ]),
}
def lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
for name, (f, boxes) in frames.items():
    im = np.asarray(Image.open(base + f).convert('RGB')).astype(np.float64)
    print('==', name)
    for label, (x0, y0, x1, y1) in boxes:
        px = im[y0:y1, x0:x1].reshape(-1, 3)
        l = lin(px); Y = l @ np.array([0.2126, 0.7152, 0.0722])
        dark = Y <= np.median(Y)
        m = px.mean(0); md = px[dark].mean(0)
        print('  %-50s sRGB mean=(%3.0f %3.0f %3.0f) Y=%.4f | dark half sRGB=(%3.0f %3.0f %3.0f) Y=%.4f p10 Y=%.4f' % (
            label, m[0], m[1], m[2], Y.mean(), md[0], md[1], md[2], Y[dark].mean(), np.percentile(Y, 10)))

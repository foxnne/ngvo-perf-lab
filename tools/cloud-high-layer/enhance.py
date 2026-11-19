from PIL import Image, ImageFilter
import numpy as np, os
d = r'C:/Users/foxnn/dev/ngvo-perf-lab/results/sky_sweep/clearcover-ilinalta'
for n in ['02_inmin_0.2__h14', '07_inmin_0.2_cirrus_0.4__h14', '08_inmin_0.2_cirrus_off__h14']:
    im = Image.open(os.path.join(d, n + '.png')).convert('RGB').crop((0, 0, 3440, 760))
    a = np.asarray(im).astype(np.float32)
    lum = a.mean(axis=2)
    blur = np.asarray(Image.fromarray(lum.astype(np.uint8)).filter(ImageFilter.GaussianBlur(60))).astype(np.float32)
    hp = np.clip((lum - blur) * 6 + 128, 0, 255).astype(np.uint8)
    Image.fromarray(hp).resize((1720, 380), Image.LANCZOS).save('hp_%s.png' % n[:2])
    Image.fromarray(hp).crop((1700, 0, 3440, 760)).save('hp_%s_right.png' % n[:2])

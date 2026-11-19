from PIL import Image
import os
d = r'C:/Users/foxnn/dev/ngvo-perf-lab/results/sky_sweep/clearcover-ilinalta'
for n in ['02_inmin_0.2__h14', '07_inmin_0.2_cirrus_0.4__h14', '08_inmin_0.2_cirrus_off__h14']:
    im = Image.open(os.path.join(d, n + '.png')).convert('RGB')
    print(im.size)
    im.resize((1720, 720), Image.LANCZOS).save('view_%s_half.jpg' % n[:2], quality=88)
    im.crop((900, 0, 2620, 720)).save('crop_%s_sky.png' % n[:2])

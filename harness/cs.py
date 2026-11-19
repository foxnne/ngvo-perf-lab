import json, time, urllib.request, os
import numpy as np
from PIL import Image

BASE = 'http://127.0.0.1:8920/api/tool/'


def call(tool, payload, timeout=60):
    req = urllib.request.Request(BASE + tool, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def world(**kw):
    return call('communityshaders.world', kw)


def feat(action, short, settings=None):
    p = {'action': action, 'shortName': short}
    if settings is not None:
        p['settings'] = settings
    return call('communityshaders.feature', p)


def shot(tag):
    r = call('communityshaders.capture', {'kind': 'screenshot', 'tag': tag})
    return r.get('path')


def stats(path):
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255.0
    lum = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
    mx = im.max(axis=2)
    mn = im.min(axis=2)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    return {
        'mean': round(float(lum.mean()), 3),
        'p1': round(float(np.percentile(lum, 1)), 3),
        'p50': round(float(np.percentile(lum, 50)), 3),
        'p99': round(float(np.percentile(lum, 99)), 3),
        'clip%': round(float((mx > 0.98).mean() * 100), 2),
        'sat': round(float(sat.mean()), 3),
    }


def flicker(paths):
    """mean abs diff between consecutive frames, in 0..255 units"""
    arrs = [np.asarray(Image.open(p).convert('RGB')).astype(np.float32) for p in paths]
    d = [float(np.abs(arrs[i + 1] - arrs[i]).mean()) for i in range(len(arrs) - 1)]
    return [round(x, 3) for x in d]

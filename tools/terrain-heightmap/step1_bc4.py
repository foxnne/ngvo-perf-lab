import numpy as np, hmlib
t, raw, fmt = hmlib.read_dds(hmlib.SHIPPED_TAMRIEL)
print(fmt, t.shape)
hgt = hmlib.texel_to_height(t)
np.save('shipped_bc4_heights.npy', hgt.astype(np.float32))
u = np.unique(np.round(raw, 4))
print('distinct decoded values', len(u), 'raw range', u.min(), u.max())
print('height range', hgt.min(), hgt.max())
print('8-bit endpoint step in game units', (hmlib.POS_Z1 - hmlib.POS_Z0) / 255)
d = np.diff(np.unique(np.round(hgt, 2)))
print('gaps between distinct heights: min %.1f median %.1f mean %.1f max %.1f' % (d.min(), np.median(d), d.mean(), d.max()))
# endpoint stats
b = np.frombuffer(open(hmlib.SHIPPED_TAMRIEL, 'rb').read()[128:], np.uint8).reshape(-1, 8)
e0, e1 = b[:, 0].astype(int), b[:, 1].astype(int)
print('blocks', len(b), 'distinct endpoints', len(np.unique(np.r_[e0, e1])), 'min', min(e0.min(), e1.min()), 'max', max(e0.max(), e1.max()))
de = np.abs(e0 - e1)
print('endpoint diff histogram', np.bincount(de)[:8], 'mode8(e0>e1) frac', (e0 > e1).mean())
# per-pixel step between horizontally adjacent texels where it changes
dx = np.abs(np.diff(hgt, axis=1)); nz = dx[dx > 0.5]
print('adjacent-texel changes: frac changing %.3f, min %.1f, median %.1f, p90 %.1f' % (len(nz) / dx.size, nz.min(), np.median(nz), np.percentile(nz, 90)))

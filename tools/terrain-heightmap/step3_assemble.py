import numpy as np, hmlib, os

def load(edid):
    z = np.load('land_%s.npz' % edid)
    return z['cells'], z['heights'], z['src'], z['names'], z['dnam']

def edge_check(cells, H):
    idx = {(int(x), int(y)): i for i, (x, y) in enumerate(cells)}
    mx = 0.0; n = 0; bad = []; tot = 0
    for (x, y), i in idx.items():
        j = idx.get((x + 1, y))
        if j is not None:
            d = np.abs(H[i][:, 32] - H[j][:, 0]); n += 1; tot += (d > 0).sum()
            if d.max() > 0: bad.append((float(d.max()), (x, y), 'E'))
        j = idx.get((x, y + 1))
        if j is not None:
            d = np.abs(H[i][32, :] - H[j][0, :]); n += 1; tot += (d > 0).sum()
            if d.max() > 0: bad.append((float(d.max()), (x, y), 'N'))
    bad.sort(reverse=True)
    return n, bad, tot

def assemble(cells, H, minx, miny, maxx, maxy, fill):
    W, Ht = (maxx - minx + 1) * 32, (maxy - miny + 1) * 32
    g = np.full((Ht, W), np.nan, np.float32)   # g[j, i]: j south->north
    outside = 0
    for (x, y), h in zip(cells, H):
        if not (minx <= x <= maxx and miny <= y <= maxy):
            outside += 1; continue
        g[(y - miny) * 32:(y - miny + 1) * 32, (x - minx) * 32:(x - minx + 1) * 32] = h[:32, :32]
    missing = int(np.isnan(g).sum()) // 1024
    g = np.where(np.isnan(g), fill, g)
    return g[::-1].copy(), outside, missing   # image row 0 = north

if __name__ == '__main__':
    # ---- Markarth: which integer does xLODGen store for a given height?
    cells, H, src, names, dnam = load('markarthworld')
    t, raw, fmt = hmlib.read_dds(hmlib.SHIPPED_DIR + r'\MarkarthWorld.Terrain.HeightMap.-48.-3.-31.5.-3375.2609.dds')
    print('Markarth', fmt, raw.shape, 'raw min/max', raw.min(), raw.max(), '-> (raw-32767)', int(raw.min()) - 32767, int(raw.max()) - 32767)
    g, outside, missing = assemble(cells, H, -48, -3, -31, 5, np.nan)
    ok = ~np.isnan(g)
    d = raw[ok].astype(np.float64) - g[ok] / 8.0
    vals, cnt = np.unique(np.round(d, 3), return_counts=True)
    o = np.argsort(-cnt)[:6]
    print('  Markarth raw - LAND/8: most common', [(float(vals[k]), int(cnt[k])) for k in o], 'covered texels', ok.sum(), 'cells outside', outside, 'missing cells', missing)
    print('  LAND min/max /8 inside rect', np.nanmin(g) / 8, np.nanmax(g) / 8)
    for name, a in (('flipV', raw[::-1]), ('flipH', raw[:, ::-1])):
        dd = a[ok].astype(np.float64) - g[ok] / 8.0
        print('  control %s exact-match frac %.4f' % (name, (np.abs(dd - 32767) < 0.01).mean()))
    print('  identity exact-match frac(raw == h/8+32767) %.4f, (== h/8+32768) %.4f' % ((np.abs(d - 32767) < 0.01).mean(), (np.abs(d - 32768) < 0.01).mean()))

    # ---- Tamriel
    cells, H, src, names, dnam = load('tamriel')
    print('Tamriel cells', len(cells), 'x range', cells[:, 0].min(), cells[:, 0].max(), 'y range', cells[:, 1].min(), cells[:, 1].max(), 'DNAM', dnam)
    n, bad, tot = edge_check(cells, H)
    print('edge pairs checked', n, 'pairs with mismatch', len(bad), 'mismatching vertices', tot, 'max mismatch', bad[0] if bad else 0)
    for b in bad[:15]:
        i = [k for k, (x, y) in enumerate(cells) if (x, y) == b[1]][0]
        print('   ', b, 'cell src', names[src[i]])
    hist = np.bincount((np.array([b[0] for b in bad]) / 8).astype(int)) if bad else []
    print('  mismatch histogram (units of 8):', list(hist[:12]), '...')
    print('heights min %.0f max %.0f ; /8: %.1f %.1f' % (H.min(), H.max(), H.min() / 8, H.max() / 8))
    k = int(np.argmax(H.max(axis=(1, 2)))); print('highest cell', cells[k], H[k].max(), names[src[k]])
    top = np.argsort(-H.max(axis=(1, 2)))[:8]; print('top cells', [(tuple(cells[q]), float(H[q].max())) for q in top])
    k = int(np.argmin(H.min(axis=(1, 2)))); print('lowest cell', cells[k], H[k].min(), names[src[k]])
    # coast: fraction of vertices within +-600 of -14000
    print('vertices below water(-14000): %.3f ; within +-400 of -14000: %.3f' % ((H < -14000).mean(), (np.abs(H + 14000) < 400).mean()))
    g, outside, missing = assemble(cells, H, -57, -43, 61, 50, float(dnam[0]))
    print('grid', g.shape, 'cells outside rect', outside, 'cells missing LAND', missing)
    np.save('tamriel_true_heights.npy', g)
    S = np.load('shipped_bc4_heights.npy').astype(np.float64)
    gd = g.astype(np.float64)
    def corr(a, b):
        a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
    print('orientation test (corr with shipped BC4 map):')
    for nm, a in (('identity', gd), ('flipV', gd[::-1]), ('flipH', gd[:, ::-1]), ('rot180', gd[::-1, ::-1])):
        print('   %-10s %.5f  mean|diff| %.1f' % (nm, corr(a, S), np.abs(a - S).mean()))
    c0 = (3808 - 3008) // 2
    Ssq = S[:, c0:c0 + 3008]; gsq = gd[:, c0:c0 + 3008]
    for nm, a in (('transpose', gsq.T), ('rot90', np.rot90(gsq)), ('rot270', np.rot90(gsq, 3)), ('antitransp', np.rot90(gsq, 2).T)):
        print('   %-10s %.5f  (central 3008x3008 crop)' % (nm, corr(a, Ssq)))
    print('   identity on same crop %.5f' % corr(gsq, Ssq))
    print('sub-texel alignment (mean|diff| for shift of our grid by (dy,dx) texels):')
    for dy in (-2, -1, 0, 1, 2):
        row = []
        for dx in (-2, -1, 0, 1, 2):
            a = gd[2 + dy:3006 + dy, 2 + dx:3806 + dx]; row.append('%.2f' % np.abs(a - S[2:3006, 2:3806]).mean())
        print('   dy=%+d: ' % dy + '  '.join(row))
    diff = np.abs(gd - S)
    print('diff vs shipped: mean %.1f median %.1f p99 %.1f max %.1f' % (diff.mean(), np.median(diff), np.percentile(diff, 99), diff.max()))
    q = (hmlib.POS_Z1 - hmlib.POS_Z0) / 255
    print('fraction of texels with |diff| > 1 full 8-bit step (%.0f): %.4f ; > 2 steps: %.5f' % (q, (diff > q).mean(), (diff > 2 * q).mean()))
    # diff per cell, split by source plugin
    cd = diff.reshape(94, 32, 119, 32).max(axis=(1, 3))[::-1]   # [cy-miny, cx-minx]
    vanilla = {'Skyrim.esm', 'Update.esm', 'Dawnguard.esm', 'HearthFires.esm', 'Dragonborn.esm'}
    mv = []; mm = []
    for (x, y), s in zip(cells, src):
        (mv if names[s] in vanilla else mm).append(cd[y + 43, x + 57])
    print('per-cell max|diff|: vanilla-winning cells mean %.0f max %.0f ; mod-winning cells mean %.0f max %.0f' % (np.mean(mv), np.max(mv), np.mean(mm), np.max(mm)))
    yy, xx = np.unravel_index(np.argmax(diff), diff.shape)
    print('largest diff at px', xx, yy, 'cell', xx // 32 - 57, (3007 - yy) // 32 - 43, 'ours', gd[yy, xx], 'shipped', S[yy, xx])

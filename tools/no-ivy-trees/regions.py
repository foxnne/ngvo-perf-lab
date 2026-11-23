"""Atlas regions of the NotWL ivy atlases (UV space, v down). classify(atlas, uv_centroids) -> array of region names."""
import numpy as np

# name, x0, y0, x1, y1
REG = {
    'ivy04': [('leafA', 0.08, 0.02, 0.42, 0.46), ('leafB', 0.58, 0.02, 0.88, 0.46), ('leafC', 0.04, 0.54, 0.20, 0.72),
              ('stemsUp', 0.38, 0.47, 1.01, 0.69), ('twigsLow', 0.24, 0.63, 0.86, 1.01), ('cap', -0.01, 0.78, 0.21, 1.01)],
    'ivy01': [('leafA', -0.01, 0.05, 0.24, 0.47), ('leafB', 0.27, 0.04, 0.345, 0.24), ('leafC', 0.27, 0.30, 0.34, 0.46),
              ('leafD', 0.04, 0.53, 0.21, 0.95), ('stemV', 0.335, 0.0, 0.50, 0.60), ('fungus', 0.54, 0.0, 0.66, 0.31),
              ('stemCurve', 0.50, 0.0, 0.86, 0.53), ('bark', 0.86, -0.01, 1.01, 0.26), ('cap', 0.89, 0.25, 1.01, 0.46),
              ('ferns', 0.23, 0.48, 0.56, 0.88), ('tendrils', 0.19, 0.83, 0.52, 1.01), ('twigBall', 0.62, 0.46, 1.01, 1.01)],
}
REMOVE = {'ivy04': {'leafA', 'leafB', 'leafC'}, 'ivy01': {'leafA', 'leafB', 'leafC', 'leafD'}}


def classify(atlas, uvtri):
    """uvtri: (n,3,2). a triangle belongs to the first region that contains all three corners (else centroid; else 'other')."""
    n = len(uvtri)
    out = np.array(['other'] * n, dtype=object)
    done = np.zeros(n, bool)
    for name, x0, y0, x1, y1 in REG[atlas]:
        inside = ((uvtri[:, :, 0] >= x0) & (uvtri[:, :, 0] <= x1) & (uvtri[:, :, 1] >= y0) & (uvtri[:, :, 1] <= y1)).all(1)
        m = inside & ~done
        out[m] = name
        done |= m
    c = uvtri.mean(1)
    for name, x0, y0, x1, y1 in REG[atlas]:
        m = ~done & (c[:, 0] >= x0) & (c[:, 0] <= x1) & (c[:, 1] >= y0) & (c[:, 1] <= y1)
        out[m] = name + '?'
        done |= m
    return out

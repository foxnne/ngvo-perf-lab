"""Ray-cast the terrain height map from a known camera pose: per pixel world x, y of the terrain hit and its distance."""
import numpy as np

import gcmlib as g


def cast(hm, cam, yaw_deg, pitch_deg, fov_h_deg, w, h, max_dist=420000.0):
    """hm: height map 128 units per texel, row 0 north, Tamriel rectangle. Returns (X, Y, dist) arrays, dist = inf on a miss.
    yaw: 0 = north, 90 = east (clockwise from above); pitch negative = looking down; fov_h = horizontal field of view of the image."""
    yaw, pitch = np.radians(yaw_deg), np.radians(pitch_deg)
    f = np.array([np.sin(yaw) * np.cos(pitch), np.cos(yaw) * np.cos(pitch), np.sin(pitch)])
    r = np.array([np.cos(yaw), -np.sin(yaw), 0.0])
    u = np.cross(r, f)
    t = np.tan(np.radians(fov_h_deg) / 2)
    xs = ((np.arange(w) + 0.5) / w * 2 - 1) * t
    ys = (1 - (np.arange(h) + 0.5) / h * 2) * t * h / w
    d = f[None, None, :] + xs[None, :, None] * r[None, None, :] + ys[:, None, None] * u[None, None, :]
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    dist = np.full((h, w), np.inf)
    alive = np.ones((h, w), bool)
    s = 96.0
    prev_s = 0.0
    prev_dz = np.full((h, w), 1.0)
    while s < max_dist and alive.any():
        px = cam[0] + d[..., 0] * s
        py = cam[1] + d[..., 1] * s
        pz = cam[2] + d[..., 2] * s
        hz = g.sample_map(hm, px[alive], py[alive])
        dz = pz[alive] - hz
        hit = dz <= 0
        if hit.any():
            pd = prev_dz[alive][hit]
            frac = pd / np.maximum(pd - dz[hit], 1e-6)           # linear refinement between the last two steps
            idx = np.where(alive)
            dist[idx[0][hit], idx[1][hit]] = prev_s + (s - prev_s) * frac
        tmp = prev_dz[alive]
        tmp[:] = dz
        prev_dz[alive] = tmp
        na = alive.copy()
        na[alive] = ~hit
        alive = na
        prev_s = s
        s += max(48.0, s * 0.012)
    X = cam[0] + d[..., 0] * dist
    Y = cam[1] + d[..., 1] * dist
    return X, Y, dist

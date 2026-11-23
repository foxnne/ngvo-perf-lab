"""BSTriShape geometry access (SSE): vertices, uvs, triangles; rebuild a shape block with a subset of triangles."""
import struct
import numpy as np
import niflib


def layout(nif, i):
    b = nif.blocks[i]
    offs, pos = nif._av(b)
    bound = pos
    pos += 16 + 12
    desc_off = pos
    desc = struct.unpack_from('<Q', b, pos)[0]
    pos += 8
    ntri, nvert, dsize = struct.unpack_from('<HHI', b, pos)
    counts_off = pos
    pos += 8
    vsize = (desc & 0xF) * 4
    vflags = (desc >> 44) & 0xFFF
    L = dict(bound=bound, desc=desc, counts_off=counts_off, ntri=ntri, nvert=nvert, dsize=dsize, vsize=vsize, vflags=vflags, vdata=pos,
             uv_off=((desc >> 8) & 0xF) * 4, fullprec=bool(vflags & 0x400), has_uv=bool(vflags & 0x2))
    if dsize == 0:
        L['tris'] = pos
        L['tail'] = pos
    else:
        if dsize != nvert * vsize + ntri * 6:
            raise niflib.UnknownType('data size %d != %d*%d + %d*6' % (dsize, nvert, vsize, ntri))
        L['tris'] = pos + nvert * vsize
        L['tail'] = L['tris'] + ntri * 6
    psize = struct.unpack_from('<I', b, L['tail'])[0]
    if psize != 0 or L['tail'] + 4 != len(b):
        raise niflib.UnknownType('particle data / trailing bytes in %s (psize %d, %d left)' % (nif.btypes[i], psize, len(b) - L['tail'] - 4))
    return L


def read(nif, i):
    L = layout(nif, i)
    b = bytes(nif.blocks[i])
    raw = np.frombuffer(b, np.uint8, L['nvert'] * L['vsize'], L['vdata']).reshape(L['nvert'], L['vsize'])
    pos = raw[:, :12].copy().view('<f4').reshape(-1, 3).astype(float)  # SSE: positions are always full floats
    uv = raw[:, L['uv_off']:L['uv_off'] + 4].copy().view('<f2').reshape(-1, 2).astype(float) if L['has_uv'] else None
    tris = np.frombuffer(b, '<u2', L['ntri'] * 3, L['tris']).reshape(-1, 3).astype(np.int64)
    return L, raw, pos, uv, tris


def rebuild(nif, i, keep_tri_mask):
    """keep only the triangles in the mask; unused vertices dropped; bounding sphere recomputed. -> (nvert, ntri) new"""
    L, raw, pos, uv, tris = read(nif, i)
    kt = tris[keep_tri_mask]
    used = np.zeros(L['nvert'], bool)
    used[kt.ravel()] = True
    remap = np.cumsum(used) - 1
    nraw = raw[used]
    ntris = remap[kt].astype('<u2')
    b = nif.blocks[i]
    nv, nt = int(used.sum()), len(kt)
    p = pos[used]
    c = (p.min(0) + p.max(0)) / 2
    r = float(np.sqrt(((p - c) ** 2).sum(1).max()))
    nb = bytearray(b[:L['vdata']]) + nraw.tobytes() + ntris.tobytes() + struct.pack('<I', 0)
    struct.pack_into('<4f', nb, L['bound'], c[0], c[1], c[2], r)
    struct.pack_into('<HHI', nb, L['counts_off'], nt, nv, nv * L['vsize'] + nt * 6)
    nif.blocks[i] = nb
    return nv, nt

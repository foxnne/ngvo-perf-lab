"""Minimal Skyrim SE NIF reader: node hierarchy transforms + BSTriShape vertices (world-space in nif root frame)."""
import struct, numpy as np

def read_nif(path_or_bytes):
    b = open(path_or_bytes, 'rb').read() if isinstance(path_or_bytes, str) else path_or_bytes
    nl = b.index(b'\n'); pos = nl + 1
    ver, endian, uver, nblocks = struct.unpack_from('<IBII', b, pos); pos += 13
    bsver = struct.unpack_from('<I', b, pos)[0]; pos += 4
    for _ in range(3):
        n = b[pos]; pos += 1 + n
    ntypes = struct.unpack_from('<H', b, pos)[0]; pos += 2
    types = []
    for _ in range(ntypes):
        n = struct.unpack_from('<I', b, pos)[0]; types.append(b[pos + 4:pos + 4 + n].decode()); pos += 4 + n
    tidx = struct.unpack_from('<%dH' % nblocks, b, pos); pos += 2 * nblocks
    sizes = struct.unpack_from('<%dI' % nblocks, b, pos); pos += 4 * nblocks
    nstr, maxlen = struct.unpack_from('<II', b, pos); pos += 8
    strings = []
    for _ in range(nstr):
        n = struct.unpack_from('<I', b, pos)[0]; strings.append(b[pos + 4:pos + 4 + n].decode('cp1252', 'replace')); pos += 4 + n
    ngroups = struct.unpack_from('<I', b, pos)[0]; pos += 4 + 4 * ngroups
    blocks = []
    for i in range(nblocks):
        blocks.append((types[tidx[i] & 0x7FFF], pos, sizes[i])); pos += sizes[i]
    return b, blocks, strings, bsver

def avobject(b, pos, strings):
    name = struct.unpack_from('<i', b, pos)[0]; pos += 4
    nex = struct.unpack_from('<I', b, pos)[0]; pos += 4 + 4 * nex
    pos += 4  # controller
    flags = struct.unpack_from('<I', b, pos)[0]; pos += 4
    t = np.array(struct.unpack_from('<3f', b, pos)); pos += 12
    r = np.array(struct.unpack_from('<9f', b, pos)).reshape(3, 3); pos += 36
    s = struct.unpack_from('<f', b, pos)[0]; pos += 4
    pos += 4  # collision
    return (strings[name] if 0 <= name < len(strings) else ''), flags, t, r, s, pos

def tridata(b, p):
    """NiTriShapeData (20.2.0.7 Skyrim): vertices + triangles."""
    p += 4
    nv = struct.unpack_from('<H', b, p)[0]; p += 2
    p += 2
    hasv = b[p]; p += 1
    v = np.frombuffer(b, '<f4', nv * 3, p).reshape(nv, 3).astype(float) if hasv else np.zeros((0, 3)); p += nv * 12 if hasv else 0
    vf = struct.unpack_from('<H', b, p)[0]; p += 2
    p += 4                                  # material CRC
    hasn = b[p]; p += 1
    if hasn:
        p += nv * 12
        if vf & 0x1000: p += nv * 24
    p += 16                                 # center, radius
    hasc = b[p]; p += 1
    if hasc: p += nv * 16
    p += nv * 8 * (vf & 1)
    p += 2 + 4                              # consistency, additional data
    nt = struct.unpack_from('<H', b, p)[0]; p += 2
    p += 4
    hast = b[p]; p += 1
    tris = np.frombuffer(b, '<u2', nt * 3, p).reshape(nt, 3) if hast else np.zeros((0, 3), int)
    assert tris.size == 0 or tris.max() < nv
    return v, tris

NODE_TYPES = ('NiNode', 'BSFadeNode', 'BSLeafAnimNode', 'BSTreeNode', 'BSMultiBoundNode', 'BSOrderedNode', 'BSValueNode', 'BSBlastNode', 'BSDamageStage', 'NiSwitchNode', 'NiBillboardNode', 'BSMasterParticleSystem', 'NiLODNode', 'BSDebrisNode', 'BSRangeNode')

def shapes(path, transpose=False):
    """Yield (name, type, Nx3 vertices in root space, tris Mx3, flags hidden-chain) for each BSTriShape-like block."""
    b, blocks, strings, bsver = read_nif(path)
    parent = {}; local = {}; info = {}
    for i, (typ, pos, size) in enumerate(blocks):
        if typ in NODE_TYPES:
            name, flags, t, r, s, p = avobject(b, pos, strings)
            n = struct.unpack_from('<I', b, p)[0]
            for c in struct.unpack_from('<%di' % n, b, p + 4):
                if c >= 0: parent[c] = i
            local[i] = (t, r, s); info[i] = (name, flags)
        elif typ in ('BSTriShape', 'BSMeshLODTriShape', 'BSSubIndexTriShape', 'BSLODTriShape', 'BSDynamicTriShape', 'NiTriShape', 'NiTriStrips'):
            name, flags, t, r, s, p = avobject(b, pos, strings)
            local[i] = (t, r, s); info[i] = (name, flags)
    def world(i, v):
        hidden = False
        while i is not None:
            t, r, s = local[i]
            if info[i][1] & 1: hidden = True
            R = r.T if transpose else r
            v = (v @ R.T) * s + t
            i = parent.get(i)
        return v, hidden
    out = []
    for i, (typ, pos, size) in enumerate(blocks):
        if typ in ('BSTriShape', 'BSMeshLODTriShape', 'BSSubIndexTriShape', 'BSLODTriShape'):
            name, flags, t, r, s, p = avobject(b, pos, strings)
            p += 16 + 12
            desc = struct.unpack_from('<Q', b, p)[0]; p += 8
            ntri, nvert, dsize = struct.unpack_from('<HHI', b, p); p += 8
            vsize = (desc & 0xF) * 4
            vflags = (desc >> 44) & 0xFFF
            if dsize == 0 or nvert == 0:
                continue
            raw = np.frombuffer(b, np.uint8, nvert * vsize, p).reshape(nvert, vsize)
            if vflags & 0x400 or bsver < 130:
                v = raw[:, :12].copy().view('<f4').reshape(nvert, 3).astype(float)
            else:
                v = raw[:, :6].copy().view('<f2').reshape(nvert, 3).astype(float)
            tris = np.frombuffer(b, '<u2', ntri * 3, p + nvert * vsize).reshape(ntri, 3)
            wv, hidden = world(i, v)
            out.append(dict(name=name, type=typ, v=wv, tris=tris, hidden=hidden, block=i, parent=info.get(parent.get(i), ('',))[0], bsver=bsver))
        elif typ == 'NiTriShape':
            name, flags, t, r, s, p = avobject(b, pos, strings)
            dref = struct.unpack_from('<i', b, p)[0]
            v = np.zeros((0, 3)); tris = np.zeros((0, 3), int)
            if 0 <= dref < len(blocks) and blocks[dref][0] == 'NiTriShapeData':
                try: v, tris = tridata(b, blocks[dref][1])
                except Exception as e: pass
            wv, hidden = world(i, v) if len(v) else (v, False)
            out.append(dict(name=name, type=typ, v=wv, tris=tris, hidden=hidden, block=i, parent=info.get(parent.get(i), ('',))[0], bsver=bsver))
        elif typ == 'NiTriStrips':
            out.append(dict(name=info[i][0], type=typ, v=np.zeros((0, 3)), tris=np.zeros((0, 3), int), hidden=False, block=i, parent='', bsver=bsver))
    return out, blocks, strings

def ref_matrix(rx, ry, rz):
    """Skyrim REFR rotation (radians, clockwise-positive, applied Z*Y*X extrinsic as the game does): local->world."""
    import math
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, sx], [0, -sx, cx]])
    Ry = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    Rz = np.array([[cz, sz, 0], [-sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

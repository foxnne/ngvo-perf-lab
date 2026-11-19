# Light-weight NIF shape/vertex/triangle counter (SSE NIFs). Reads file paths from stdin.
# Output: tris verts shapes bytes path
import struct, sys, os

def parse(path):
    b = open(path, 'rb').read()
    p = b.index(b'\n') + 1
    ver, endian, uver, nblocks = struct.unpack_from('<IBII', b, p); p += 13
    bsver, = struct.unpack_from('<I', b, p); p += 4
    def bstr(p):
        n = b[p]; return p + 1 + n
    p = bstr(p)
    if bsver > 130: p += 4
    p = bstr(p); p = bstr(p)
    if bsver == 130: p = bstr(p)
    ntypes, = struct.unpack_from('<H', b, p); p += 2
    types = []
    for _ in range(ntypes):
        n, = struct.unpack_from('<I', b, p); p += 4
        types.append(b[p:p + n].decode('latin1')); p += n
    idx = struct.unpack_from('<%dH' % nblocks, b, p); p += 2 * nblocks
    sizes = struct.unpack_from('<%dI' % nblocks, b, p); p += 4 * nblocks
    nstr, maxlen = struct.unpack_from('<II', b, p); p += 8
    for _ in range(nstr):
        n, = struct.unpack_from('<I', b, p); p += 4 + n
    ngroups, = struct.unpack_from('<I', b, p); p += 4 + 4 * ngroups
    tris = verts = shapes = 0
    for i in range(nblocks):
        t = types[idx[i] & 0x7FFF]
        q = p
        try:
            if t in ('BSTriShape', 'BSDynamicTriShape', 'BSMeshLODTriShape', 'BSSubIndexTriShape', 'BSLODTriShape'):
                if t == 'BSLODTriShape':
                    pass  # NiTriShape-derived, counted via its data block
                else:
                    q += 4
                    ned, = struct.unpack_from('<I', b, q); q += 4 + 4 * ned
                    q += 4 + 4 + 12 + 36 + 4 + 4  # controller, flags, trans, rot, scale, collision
                    q += 16 + 4 + 4 + 4 + 8      # bound, skin, shader, alpha, vertex desc
                    if bsver >= 130:
                        nt, nv = struct.unpack_from('<IH', b, q)
                    else:
                        nt, nv = struct.unpack_from('<HH', b, q)
                    tris += nt; verts += nv; shapes += 1
            elif t in ('NiTriShapeData', 'NiTriStripsData'):
                q += 4
                nv, = struct.unpack_from('<H', b, q); q += 2
                q += 2
                hv = b[q]; q += 1
                if hv: q += 12 * nv
                fl, = struct.unpack_from('<H', b, q); q += 2
                if bsver > 34: q += 4
                hn = b[q]; q += 1
                if hn:
                    q += 12 * nv
                    if fl & 0x1000: q += 24 * nv
                q += 16
                hc = b[q]; q += 1
                if hc: q += 16 * nv
                q += 8 * nv * (fl & 1)
                q += 2 + 4
                nt, = struct.unpack_from('<H', b, q)
                tris += nt; verts += nv; shapes += 1
        except Exception:
            pass
        p += sizes[i]
    return tris, verts, shapes, len(b)

for line in sys.stdin:
    f = line.rstrip('\r\n')
    if not f: continue
    try:
        t, v, s, n = parse(f)
        print('%7d %7d %3d %9d %s' % (t, v, s, n, f))
    except Exception as e:
        print('ERR %s %s' % (e, f))

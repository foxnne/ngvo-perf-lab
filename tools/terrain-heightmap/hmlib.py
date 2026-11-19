"""Shared helpers: DDS read/write for terrain height maps, loader mapping."""
import struct, os
import numpy as np

SHIPPED_DIR = r'C:\Modlists\NGVO 8.0 Beta\mods\Bottled Shaders - foxnne\textures\terrain\HeightMaps'
SHIPPED_TAMRIEL = os.path.join(SHIPPED_DIR, 'Tamriel.Terrain.HeightMap.-57.-43.61.50.-4629.4924.dds')
POS_Z0, POS_Z1 = -32767 * 8.0, 32767 * 8.0   # ParseHeightmapPath xlodgen style


def read_dds(path):
    """Return (array float64 in 0..1 as the GPU would present a UNORM texel, raw integer array, fmt string)."""
    b = open(path, 'rb').read()
    assert b[:4] == b'DDS '
    h, w = struct.unpack_from('<II', b, 12)
    pfflags, fourcc, bits, rmask = struct.unpack_from('<I4sII', b, 80)
    data = b[128:]
    if fourcc in (b'BC4U', b'ATI1'):
        raw = decode_bc4(data, w, h)           # float, exact interpolation of 8-bit endpoints
        return raw / 255.0, raw, 'BC4U'
    if pfflags & 0x20000 and bits == 16 and rmask == 0xFFFF:
        raw = np.frombuffer(data, '<u2', w * h).reshape(h, w)
        return raw / 65535.0, raw, 'L16'
    raise ValueError('unsupported dds %r %d' % (fourcc, bits))


def decode_bc4(data, w, h):
    """BC4 UNORM decode. Returns float64 array in 0..255 units (interpolated values kept fractional,
    as D3D11 hardware does not round BC4 palette entries to 8 bits)."""
    bw, bh = (w + 3) // 4, (h + 3) // 4
    blk = np.frombuffer(data, np.uint8, bw * bh * 8).reshape(bh * bw, 8)
    r0 = blk[:, 0].astype(np.float64)
    r1 = blk[:, 1].astype(np.float64)
    bits = np.zeros(bh * bw, np.uint64)
    for i in range(6):
        bits |= blk[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    pal = np.empty((bh * bw, 8))
    pal[:, 0] = r0
    pal[:, 1] = r1
    gt = r0 > r1
    for i in range(1, 7):
        pal[:, i + 1] = np.where(gt, ((7 - i) * r0 + i * r1) / 7.0, 0)
    for i in range(1, 5):
        pal[:, i + 1] = np.where(gt, pal[:, i + 1], ((5 - i) * r0 + i * r1) / 5.0)
    pal[:, 6] = np.where(gt, pal[:, 6], 0.0)
    pal[:, 7] = np.where(gt, pal[:, 7], 255.0)
    out = np.empty((bh, bw, 4, 4))
    rows = np.arange(bh * bw)
    for p in range(16):
        idx = ((bits >> np.uint64(3 * p)) & np.uint64(7)).astype(np.int64)
        out[:, :, p // 4, p % 4] = pal[rows, idx].reshape(bh, bw)
    return out.transpose(0, 2, 1, 3).reshape(bh * 4, bw * 4)[:h, :w]


def texel_to_height(t):
    """Shader: terrainHeight = lerp(PosRange.x, PosRange.y, TexHeight)."""
    return POS_Z0 + (POS_Z1 - POS_Z0) * t


def write_l16(path, arr_u16, template):
    """Write uncompressed 16-bit luminance DDS reusing the header layout of a shipped 16-bit map."""
    hdr = bytearray(open(template, 'rb').read(128))
    h, w = arr_u16.shape
    struct.pack_into('<II', hdr, 12, h, w)
    struct.pack_into('<I', hdr, 20, w * h * 2)
    with open(path, 'wb') as f:
        f.write(hdr)
        f.write(np.ascontiguousarray(arr_u16, '<u2').tobytes())

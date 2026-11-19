"""Minimal SSE BSA (v105) reader with pure-python LZ4 frame decoding."""
import struct, os

def lz4_block(src, out):
    i, n = 0, len(src)
    while i < n:
        tok = src[i]; i += 1
        ll = tok >> 4
        if ll == 15:
            while True:
                b = src[i]; i += 1; ll += b
                if b != 255: break
        out += src[i:i + ll]; i += ll
        if i >= n: break
        off = src[i] | (src[i + 1] << 8); i += 2
        ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255: break
        ml += 4
        st = len(out) - off
        if off >= ml:
            out += out[st:st + ml]
        else:
            for k in range(ml):
                out.append(out[st + k])

def lz4_frame(data):
    assert data[:4] == b'\x04\x22\x4d\x18'
    flg = data[4]; pos = 6
    if flg & 0x08: pos += 8
    if flg & 0x01: pos += 4
    pos += 1
    out = bytearray()
    while True:
        sz = struct.unpack_from('<I', data, pos)[0]; pos += 4
        if sz == 0: break
        raw = sz & 0x80000000; sz &= 0x7FFFFFFF
        blk = data[pos:pos + sz]; pos += sz
        if raw: out += blk
        else: lz4_block(blk, out)
        if flg & 0x10: pos += 4
    return bytes(out)

class BSA:
    def __init__(self, path):
        self.path = path
        f = self.f = open(path, 'rb')
        magic, ver, off, self.flags, nfold, nfiles, tfl, tfil, fflags = struct.unpack('<4sIIIIIIII', f.read(36))
        assert magic == b'BSA\0' and ver == 105, (path, magic, ver)
        folders = [struct.unpack('<QIIQ', f.read(24)) for _ in range(nfold)]
        recs = []
        for h, cnt, pad, o in folders:
            n = f.read(1)[0]; name = f.read(n)[:-1].decode('cp1252', 'replace').lower()
            for _ in range(cnt):
                fh, size, foff = struct.unpack('<QII', f.read(16))
                recs.append((name, size, foff))
        names = f.read(tfil).split(b'\0')
        self.files = {}
        for (folder, size, foff), nm in zip(recs, names):
            self.files[os.path.normpath(folder + os.sep + nm.decode('cp1252', 'replace').lower())] = (size, foff)
    def read(self, rel):
        size, off = self.files[rel]
        comp = bool(self.flags & 4) ^ bool(size & 0x40000000)
        size &= 0x3FFFFFFF
        self.f.seek(off); data = self.f.read(size)
        if self.flags & 0x100:
            n = data[0]; data = data[1 + n:]
        if comp:
            return lz4_frame(data[4:])
        return data

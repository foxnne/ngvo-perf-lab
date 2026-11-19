"""Read-only SSE BSA (v105) lister/extractor with a pure-Python LZ4 frame decoder.
Usage: python bsa_extract.py list  archive.bsa [substring]
       python bsa_extract.py get   archive.bsa outdir substring [substring...]
"""
import struct, sys, os

BS = chr(92)


def lz4_block(src, out):
    i = 0; n = len(src)
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
        start = len(out) - off
        if off >= ml:
            out += out[start:start + ml]
        else:
            for k in range(ml):
                out.append(out[start + k])
    return out


def lz4_frame(data):
    assert struct.unpack_from('<I', data, 0)[0] == 0x184D2204
    flg = data[4]; p = 6
    if flg & 0x08: p += 8
    if flg & 0x01: p += 4
    p += 1  # header checksum
    out = bytearray()
    while True:
        bs, = struct.unpack_from('<I', data, p); p += 4
        if bs == 0: break
        raw = bs & 0x80000000; bs &= 0x7FFFFFFF
        blk = data[p:p + bs]; p += bs
        if raw: out += blk
        else: lz4_block(blk, out)
        if flg & 0x10: p += 4
    return bytes(out)


class BSA:
    def __init__(self, path):
        self.f = open(path, 'rb'); f = self.f
        magic, ver, off, self.aflags, nfolders, nfiles, lfold, lfile, fflags, pad = struct.unpack('<4sIIIIIIIHH', f.read(36))
        assert magic == b'BSA\0' and ver == 105, (magic, ver)
        folders = [struct.unpack('<QIIQ', f.read(24)) for _ in range(nfolders)]
        self.files = []  # (path, size, offset)
        recs = []
        for h, cnt, _, o in folders:
            n = f.read(1)[0]; name = f.read(n)[:-1].decode('latin1')
            for _ in range(cnt):
                fh, size, offset = struct.unpack('<QII', f.read(16)); recs.append((name, size, offset))
        names = f.read(lfile).split(b'\0')
        for (folder, size, offset), nm in zip(recs, names):
            self.files.append((folder + BS + nm.decode('latin1'), size, offset))

    def read(self, entry):
        path, size, offset = entry
        comp = bool(self.aflags & 4) ^ bool(size & 0x40000000)
        size &= 0x3FFFFFFF
        self.f.seek(offset); data = self.f.read(size)
        if self.aflags & 0x100:
            n = data[0]; data = data[1 + n:]
        if comp:
            return lz4_frame(data[4:])
        return data


if __name__ == '__main__':
    mode, arc = sys.argv[1], sys.argv[2]
    b = BSA(arc)
    if mode == 'list':
        sub = sys.argv[3].lower() if len(sys.argv) > 3 else ''
        for e in b.files:
            if sub in e[0].lower(): print(e[0], e[1] & 0x3FFFFFFF)
    else:
        out = sys.argv[3]; subs = [s.lower() for s in sys.argv[4:]]
        for e in b.files:
            if any(e[0].lower().endswith(s) for s in subs):
                d = b.read(e); dst = os.path.join(out, e[0].replace(BS, '/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, 'wb').write(d); print('wrote', dst, len(d))

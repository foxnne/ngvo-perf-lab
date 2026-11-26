"""Minimal dependency-free reader for TES5/SSE plugin files (ESP/ESM/ESL).

Only what the wardrobe catalogue needs:
  * TES4 header: flags (ESM/ESL/localized), masters
  * top-level GRUPs of selected record types, others are skipped by seeking
  * compressed records (zlib), XXXX oversized fields
  * ARMO / ARMA / OTFT / KYWD / RACE field decoding
  * BSA (v104/v105) file-name listing and loose .STRINGS lookup

Form IDs are returned as "form keys": (local_id, origin_plugin_lowercase).
"""
import struct
import zlib

REC_HDR = struct.Struct('<4sIIIIHH')  # type, size, flags, formid, vc, version, unk
F_COMPRESSED = 0x00040000
F_ESM = 0x1
F_LOCALIZED = 0x80
F_ESL = 0x200
F_NONPLAYABLE = 0x4


class PluginError(Exception):
    pass


def iter_subrecords(data):
    """Yield (type_bytes, payload_bytes) for a record body."""
    pos = 0
    n = len(data)
    big = None
    while pos + 6 <= n:
        typ = data[pos:pos + 4]
        size = struct.unpack_from('<H', data, pos + 4)[0]
        pos += 6
        if typ == b'XXXX':
            big = struct.unpack_from('<I', data, pos)[0]
            pos += size
            continue
        if big is not None:
            size = big
            big = None
        yield typ, data[pos:pos + size]
        pos += size


def zstr(b):
    i = b.find(b'\0')
    if i >= 0:
        b = b[:i]
    try:
        return b.decode('utf-8')
    except UnicodeDecodeError:
        return b.decode('cp1252', 'replace')


class Plugin:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.lname = name.lower()
        self.masters = []
        self.flags = 0
        self.group_bytes = {}   # record type -> bytes of its top-level GRUP
        self.file_size = 0
        self.errors = []
        self.records = {}       # type -> list of (formid, flags, body bytes)

    @property
    def is_light(self):
        return bool(self.flags & F_ESL) or self.lname.endswith('.esl')

    @property
    def localized(self):
        return bool(self.flags & F_LOCALIZED)

    def formkey(self, fid):
        idx = fid >> 24
        if idx < len(self.masters):
            return (fid & 0xFFFFFF, self.masters[idx].lower())
        return (fid & 0xFFFFFF, self.lname)

    def load(self, want):
        """Read header and the top-level groups whose label is in `want` (set of bytes)."""
        with open(self.path, 'rb') as f:
            f.seek(0, 2)
            self.file_size = f.tell()
            f.seek(0)
            hdr = f.read(24)
            if len(hdr) < 24 or hdr[:4] != b'TES4':
                raise PluginError('not a TES4 plugin')
            typ, size, flags, fid, vc, ver, unk = REC_HDR.unpack(hdr)
            self.flags = flags
            body = f.read(size)
            if flags & F_COMPRESSED:
                body = zlib.decompress(body[4:])
            for st, sd in iter_subrecords(body):
                if st == b'MAST':
                    self.masters.append(zstr(sd))
            while True:
                pos = f.tell()
                gh = f.read(24)
                if len(gh) < 24:
                    break
                if gh[:4] != b'GRUP':
                    self.errors.append('expected GRUP at %d, got %r' % (pos, gh[:4]))
                    break
                gsize = struct.unpack_from('<I', gh, 4)[0]
                label = gh[8:12]
                gtype = struct.unpack_from('<I', gh, 12)[0]
                if gsize < 24:
                    self.errors.append('bad GRUP size at %d' % pos)
                    break
                if gtype == 0:
                    self.group_bytes[label] = self.group_bytes.get(label, 0) + gsize
                if gtype == 0 and label in want:
                    blob = f.read(gsize - 24)
                    if len(blob) < gsize - 24:
                        self.errors.append('truncated GRUP %r' % label)
                    self._parse_group(label, blob)
                else:
                    f.seek(pos + gsize)
        return self

    def _parse_group(self, label, blob):
        out = self.records.setdefault(label, [])
        pos = 0
        n = len(blob)
        while pos + 24 <= n:
            typ, size, flags, fid, vc, ver, unk = REC_HDR.unpack_from(blob, pos)
            if typ == b'GRUP':      # nested group: size includes header
                pos += max(size, 24)
                continue
            body = blob[pos + 24:pos + 24 + size]
            pos += 24 + size
            if flags & F_COMPRESSED:
                try:
                    body = zlib.decompress(body[4:])
                except zlib.error as e:
                    self.errors.append('zlib error in %s %08X: %s' % (typ.decode('latin1'), fid, e))
                    continue
            out.append((fid, flags, body))


# ---------------------------------------------------------------- decoders

def decode_edid(body):
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            return zstr(sd)
    return None


def decode_armo(pl, fid, flags, body):
    r = {'edid': None, 'full': None, 'full_string_id': None, 'slots': 0, 'armor_type': None,
         'bod_src': None, 'keywords': [], 'value': None, 'weight': None, 'armor_rating': None,
         'race': None, 'armas': [], 'template': None, 'enchantment': None,
         'ground_model_m': None, 'ground_model_f': None,
         'non_playable': bool(flags & F_NONPLAYABLE), 'has_script': False}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st == b'FULL':
            if pl.localized and len(sd) == 4:
                r['full_string_id'] = struct.unpack('<I', sd)[0]
            else:
                r['full'] = zstr(sd)
        elif st == b'BOD2' and len(sd) >= 8:
            r['slots'], r['armor_type'] = struct.unpack_from('<II', sd)
            r['bod_src'] = 'BOD2'
        elif st == b'BODT' and len(sd) >= 8:
            r['slots'], gflags = struct.unpack_from('<II', sd)
            r['armor_type'] = struct.unpack_from('<I', sd, 8)[0] if len(sd) >= 12 else None
            if gflags & 0x10:
                r['non_playable'] = True
            r['bod_src'] = 'BODT'
        elif st == b'KWDA':
            r['keywords'] = [pl.formkey(x) for x in struct.unpack('<%dI' % (len(sd) // 4), sd[:len(sd) // 4 * 4])]
        elif st == b'DATA' and len(sd) >= 8:
            r['value'], r['weight'] = struct.unpack_from('<if', sd)
        elif st == b'DNAM' and len(sd) >= 4:
            r['armor_rating'] = struct.unpack_from('<i', sd)[0] / 100.0
        elif st == b'RNAM' and len(sd) >= 4:
            r['race'] = pl.formkey(struct.unpack_from('<I', sd)[0])
        elif st == b'MODL' and len(sd) == 4:
            r['armas'].append(pl.formkey(struct.unpack('<I', sd)[0]))
        elif st == b'TNAM' and len(sd) >= 4:
            r['template'] = pl.formkey(struct.unpack_from('<I', sd)[0])
        elif st == b'EITM' and len(sd) >= 4:
            r['enchantment'] = pl.formkey(struct.unpack_from('<I', sd)[0])
        elif st == b'MOD2':
            r['ground_model_m'] = zstr(sd)
        elif st == b'MOD4':
            r['ground_model_f'] = zstr(sd)
        elif st == b'VMAD':
            r['has_script'] = True
    return r


def decode_arma(pl, fid, flags, body):
    r = {'edid': None, 'slots': 0, 'race': None, 'extra_races': [],
         'male_model': None, 'female_model': None, 'male_1st': None, 'female_1st': None}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st in (b'BOD2', b'BODT') and len(sd) >= 4:
            r['slots'] = struct.unpack_from('<I', sd)[0]
        elif st == b'RNAM' and len(sd) >= 4:
            r['race'] = pl.formkey(struct.unpack_from('<I', sd)[0])
        elif st == b'MODL' and len(sd) == 4:
            r['extra_races'].append(pl.formkey(struct.unpack('<I', sd)[0]))
        elif st == b'MOD2':
            r['male_model'] = zstr(sd)
        elif st == b'MOD3':
            r['female_model'] = zstr(sd)
        elif st == b'MOD4':
            r['male_1st'] = zstr(sd)
        elif st == b'MOD5':
            r['female_1st'] = zstr(sd)
    return r


def decode_otft(pl, fid, flags, body):
    r = {'edid': None, 'items': []}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st == b'INAM':
            r['items'] = [pl.formkey(x) for x in struct.unpack('<%dI' % (len(sd) // 4), sd[:len(sd) // 4 * 4])]
    return r


# ---------------------------------------------------------------- strings / BSA

def read_strings_file(path):
    """Return {id: str} from a .STRINGS file (zero-terminated flavour)."""
    with open(path, 'rb') as f:
        data = f.read()
    count, dsize = struct.unpack_from('<II', data)
    base = 8 + count * 8
    out = {}
    for i in range(count):
        sid, off = struct.unpack_from('<II', data, 8 + i * 8)
        s = base + off
        e = data.find(b'\0', s)
        out[sid] = zstr(data[s:e if e >= 0 else len(data)])
    return out


def bsa_list(path):
    """Return list of lowercase 'folder\\file' names in a BSA v104/v105. Raises on other formats."""
    with open(path, 'rb') as f:
        hdr = f.read(36)
        if hdr[:4] != b'BSA\0':
            raise PluginError('not a BSA')
        ver, off, aflags, nfold, nfile, lfold, lfile, fflags = struct.unpack_from('<IIIIIIII', hdr, 4)
        if ver not in (104, 105) or not (aflags & 1 and aflags & 2):
            raise PluginError('unsupported BSA version/flags %d %x' % (ver, aflags))
        frs = 24 if ver == 105 else 16
        f.seek(off)
        fr = f.read(nfold * frs)
        counts = [struct.unpack_from('<I', fr, i * frs + 8)[0] for i in range(nfold)]
        rest = f.read(lfold + nfold + nfile * 16 + lfile)
    pos = 0
    folders = []
    for c in counts:
        ln = rest[pos]
        folders.append(rest[pos + 1:pos + ln].decode('cp1252', 'replace'))
        pos += 1 + ln + c * 16
    names = rest[pos:pos + lfile].split(b'\0')
    out = []
    k = 0
    for folder, c in zip(folders, counts):
        for _ in range(c):
            out.append((folder + '\\' + names[k].decode('cp1252', 'replace')).lower())
            k += 1
    return out


# ---------------------------------------------------------------- BSA extraction (pure python)

def lz4_block(src, dst):
    """Decode one LZ4 block from bytes `src`, appending to bytearray `dst` (which may hold history)."""
    i = 0
    n = len(src)
    while i < n:
        tok = src[i]
        i += 1
        ll = tok >> 4
        if ll == 15:
            while True:
                b = src[i]
                i += 1
                ll += b
                if b != 255:
                    break
        if ll:
            dst += src[i:i + ll]
            i += ll
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        if off == 0:
            raise PluginError('lz4: zero offset')
        start = len(dst) - off
        if off >= ml:
            dst += dst[start:start + ml]
        else:
            chunk = bytes(dst[start:])
            q, r = divmod(ml, off)
            dst += chunk * q + chunk[:r]
    return dst


def lz4_frame(data):
    if data[:4] != b'\x04\x22\x4d\x18':
        raise PluginError('lz4: bad frame magic')
    flg = data[4]
    pos = 6
    if flg & 0x08:
        pos += 8
    if flg & 0x01:
        pos += 4
    pos += 1  # header checksum
    out = bytearray()
    while True:
        bs = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        if bs == 0:
            break
        raw = bs & 0x80000000
        bs &= 0x7FFFFFFF
        blk = data[pos:pos + bs]
        pos += bs
        if raw:
            out += blk
        else:
            lz4_block(blk, out)
        if flg & 0x10:
            pos += 4
    return bytes(out)


class BSA:
    def __init__(self, path):
        self.path = path
        self.files = {}
        with open(path, 'rb') as f:
            hdr = f.read(36)
            if hdr[:4] != b'BSA\0':
                raise PluginError('not a BSA')
            ver, off, aflags, nfold, nfile, lfold, lfile, fflags = struct.unpack_from('<IIIIIIII', hdr, 4)
            if ver not in (104, 105) or not (aflags & 1 and aflags & 2):
                raise PluginError('unsupported BSA version/flags %d %x' % (ver, aflags))
            self.version, self.aflags = ver, aflags
            frs = 24 if ver == 105 else 16
            f.seek(off)
            fr = f.read(nfold * frs)
            counts = [struct.unpack_from('<I', fr, i * frs + 8)[0] for i in range(nfold)]
            rest = f.read(lfold + nfold + nfile * 16 + lfile)
        pos = 0
        recs = []
        for c in counts:
            ln = rest[pos]
            folder = rest[pos + 1:pos + ln].decode('cp1252', 'replace')
            pos += 1 + ln
            for _ in range(c):
                size, offset = struct.unpack_from('<II', rest, pos + 8)
                recs.append((folder, size, offset))
                pos += 16
        names = rest[pos:pos + lfile].split(b'\0')
        for (folder, size, offset), nm in zip(recs, names):
            self.files[(folder + '\\' + nm.decode('cp1252', 'replace')).lower()] = (size, offset)

    def read(self, name):
        size, offset = self.files[name]
        comp = bool(self.aflags & 0x4)
        if size & 0x40000000:
            comp = not comp
        size &= 0x3FFFFFFF
        with open(self.path, 'rb') as f:
            f.seek(offset)
            data = f.read(size)
        if self.aflags & 0x100:
            ln = data[0]
            data = data[1 + ln:]
        if comp:
            data = data[4:]
            data = lz4_frame(data) if self.version == 105 else zlib.decompress(data)
        return data

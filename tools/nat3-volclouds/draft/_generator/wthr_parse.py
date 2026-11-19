"""Read-only parser for WTHR records of Bethesda plugins (Skyrim SE).

    python -I wthr_parse.py        writes nat-cs-wthr-records.json beside this file

Opens the plugins read-only; writes only next to itself. Used by build_pass2.py.
"""
import json
import os
import struct
import zlib

MODLIST = r'C:\Modlists\NGVO 8.0 Beta'
PLUGIN = os.path.join(MODLIST, 'mods', 'NAT.CS III', 'NAT-CS.esp')
SEARCH = [os.path.join(MODLIST, 'mods', 'NAT.CS III'),
          os.path.join(MODLIST, 'mods', 'NAT.ENB - ESP WEATHER PLUGIN'),
          os.path.join(MODLIST, 'Stock Game', 'Data')]
HERE = os.path.dirname(os.path.abspath(__file__))

COLOR_TYPES = ['skyUpper', 'fogNear', 'unknown', 'ambient', 'sunlight', 'sun', 'stars', 'skyLower', 'horizon',
               'effectLighting', 'cloudLodDiffuse', 'cloudLodAmbient', 'fogFar', 'skyStatics', 'waterMultiplier',
               'sunGlare', 'moonGlare']
TOD4 = ['sunrise', 'day', 'sunset', 'night']
CLASS_BITS = [(0x01, 'pleasant'), (0x02, 'cloudy'), (0x04, 'rainy'), (0x08, 'snow')]


def subrecords(body):
    pos, big = 0, None
    while pos + 6 <= len(body):
        sig = body[pos:pos + 4]
        size = struct.unpack_from('<H', body, pos + 4)[0]
        pos += 6
        if sig == b'XXXX':
            big = struct.unpack_from('<I', body, pos)[0]
            pos += size
            continue
        if big is not None:
            size, big = big, None
        yield sig, body[pos:pos + size]
        pos += size


def records(path, want):
    """Yields (sig, formid, flags, body) for TES4 and for records whose signature is in `want`.
    Top-level groups of other record types are skipped without being walked."""
    with open(path, 'rb') as f:
        data = f.read()

    def walk(start, end):
        p = start
        while p + 24 <= end:
            sig = data[p:p + 4]
            size, = struct.unpack_from('<I', data, p + 4)
            if sig == b'GRUP':
                label = data[p + 8:p + 12]
                gtype, = struct.unpack_from('<i', data, p + 12)
                if gtype != 0 or label in want:
                    yield from walk(p + 24, p + size)
                p += size
                continue
            flags, formid = struct.unpack_from('<II', data, p + 8)
            if sig in want or sig == b'TES4':
                body = data[p + 24:p + 24 + size]
                if flags & 0x00040000:
                    body = zlib.decompress(body[4:])
                yield sig, formid, flags, body
            p += 24 + size

    yield from walk(0, len(data))


def masters_of(path):
    for sig, _fid, _fl, body in records(path, set()):
        if sig == b'TES4':
            return [d.rstrip(b'\0').decode('cp1252') for s, d in subrecords(body) if s == b'MAST']
    return []


def find_plugin(name):
    for d in SEARCH:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def spid(formid, masters, own):
    idx = formid >> 24
    origin = masters[idx] if idx < len(masters) else own
    return '0x%X~%s' % (formid & 0xFFFFFF, origin)


def zstr(b):
    return b.split(b'\0', 1)[0].decode('cp1252', 'replace')


def parse_wthr(body, masters, own):
    r = {'sounds': 0}
    textures, speed_x, speed_y = {}, None, None
    nam0 = jn = pn = b''
    for sig, d in subrecords(body):
        if sig == b'EDID':
            r['editorId'] = zstr(d)
        elif sig[1:] == b'0TX' and 0x30 <= sig[0] < 0x30 + 32:
            textures[sig[0] - 0x30] = zstr(d)
        elif sig == b'LNAM':
            r['lnam'] = struct.unpack_from('<I', d)[0]
        elif sig == b'MNAM':
            r['precipitation'] = spid(struct.unpack_from('<I', d)[0], masters, own)
        elif sig == b'NNAM':
            r['visualEffect'] = spid(struct.unpack_from('<I', d)[0], masters, own)
        elif sig == b'RNAM':
            speed_y = list(d)
        elif sig == b'QNAM':
            speed_x = list(d)
        elif sig == b'PNAM':
            pn = d
        elif sig == b'JNAM':
            jn = d
        elif sig == b'NAM0':
            nam0 = d
        elif sig == b'FNAM':
            v = struct.unpack_from('<%df' % (len(d) // 4), d)
            keys = ['dayNear', 'dayFar', 'nightNear', 'nightFar', 'dayPower', 'nightPower', 'dayMax', 'nightMax']
            r['fog'] = dict(zip(keys, [round(x, 4) for x in v]))
        elif sig == b'DATA':
            b = list(d)
            r['data'] = {
                'windSpeed': b[0], 'transDelta': b[3], 'sunGlare': b[4], 'sunDamage': b[5],
                'precipBeginFadeIn': b[6], 'precipEndFadeOut': b[7],
                'thunderBeginFadeIn': b[8], 'thunderEndFadeOut': b[9], 'thunderFrequency': b[10],
                'flags': b[11], 'lightningColor': b[12:15], 'vfxBegin': b[15], 'vfxEnd': b[16],
                'windDirection': b[17], 'windDirRange': b[18],
            }
            r['class'] = [n for bit, n in CLASS_BITS if b[11] & bit]
        elif sig == b'NAM1':
            r['disabledLayers'] = struct.unpack_from('<I', d)[0]
        elif sig == b'SNAM':
            r['sounds'] += 1
        elif sig == b'MODL':
            r['auroraModel'] = zstr(d)
        elif sig == b'TNAM':
            r.setdefault('skyStatics', []).append(spid(struct.unpack_from('<I', d)[0], masters, own))
    r['sizes'] = {'NAM0': len(nam0), 'JNAM': len(jn), 'PNAM': len(pn)}
    # Times of day: JNAM is 32 layers x tod floats. 512 bytes = 4, 1024 = 8.
    tod = 8 if len(jn) == 32 * 8 * 4 else 4
    r['timesOfDay'] = tod
    ntypes = len(nam0) // (4 * tod)
    colors = {}
    for i in range(min(ntypes, len(COLOR_TYPES))):
        colors[COLOR_TYPES[i]] = [list(nam0[(i * tod + t) * 4:(i * tod + t) * 4 + 3]) for t in range(tod)]
    r['colors'] = {k: colors[k] for k in ('sunlight', 'ambient', 'fogNear', 'fogFar', 'skyUpper', 'horizon', 'sun',
                                           'sunGlare') if k in colors}
    nl = len(jn) // (4 * tod) if jn else 0
    disabled = r.get('disabledLayers', 0)
    layers = []
    for i in range(nl):
        tex = textures.get(i, '')
        alpha = [round(x, 3) for x in struct.unpack_from('<%df' % tod, jn, i * 4 * tod)]
        col = None
        if len(pn) >= (i + 1) * 4 * tod:
            col = [list(pn[(i * tod + t) * 4:(i * tod + t) * 4 + 3]) for t in range(tod)]
        if tex:
            layers.append({'i': i, 'tex': tex, 'enabled': not (disabled >> i) & 1, 'alpha': alpha, 'color': col,
                           'speedX': speed_x[i] if speed_x and i < len(speed_x) else None,
                           'speedY': speed_y[i] if speed_y and i < len(speed_y) else None})
    r['layers'] = layers
    return r


def load(plugin=PLUGIN):
    own = os.path.basename(plugin)
    masters = masters_of(plugin)
    out = []
    for sig, formid, _flags, body in records(plugin, {b'WTHR'}):
        if sig != b'WTHR':
            continue
        r = parse_wthr(body, masters, own)
        r['spid'] = spid(formid, masters, own)
        r['formId'] = '%08X' % formid
        out.append(r)
    # Resolve precipitation (SPGD) and visual effect (RFCT) editor ids from the plugin that defines them,
    # letting NAT-CS.esp / NAT-ENB.esp overrides win for the name (the name does not change in an override).
    need = {}
    for r in out:
        for k in ('precipitation', 'visualEffect'):
            if r.get(k):
                need.setdefault(r[k].split('~', 1)[1], set()).add(r[k])
    names = {}
    for origin, keys in need.items():
        path = find_plugin(origin)
        if not path:
            continue
        m = masters_of(path)
        for sig, formid, _fl, body in records(path, {b'SPGD', b'RFCT'}):
            if sig == b'TES4':
                continue
            k = spid(formid, m, origin)
            if k in keys:
                for s, d in subrecords(body):
                    if s == b'EDID':
                        names[k] = zstr(d)
                        break
    for r in out:
        for k in ('precipitation', 'visualEffect'):
            if r.get(k):
                r[k + 'Name'] = names.get(r[k], '')
    return masters + [own], out


if __name__ == '__main__':
    masters, recs = load()
    path = os.path.join(HERE, 'nat-cs-wthr-records.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'source': PLUGIN, 'masters': masters, 'weathers': recs}, f, indent=1)
    print(len(recs), 'WTHR records ->', path)

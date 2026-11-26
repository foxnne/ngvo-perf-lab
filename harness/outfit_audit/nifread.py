"""Light read-only Skyrim SE NIF reader for the outfit audit (pyffi does not handle SSE BSTriShape well).

parse(bytes) -> dict:
  bsver, version, block types, errors
  shapes: [{name, type, nv, ntri, va_flags, has_vc, vc_black_frac, skinned_va, skin_type, partitions[slots],
            has_partition_block, bones[], shader_type, shader_kind, sf1, sf2, textures[], alpha_ref}]
  strings_extra: {name: value} for NiStringExtraData (SMP marker etc.)
  nodes: set of NiNode names
"""
import struct

SHAPE_TYPES = ('BSTriShape', 'BSDynamicTriShape', 'BSSubIndexTriShape', 'BSMeshLODTriShape', 'BSLODTriShape')
SLSF1 = ['Specular', 'Skinned', 'Temp_Refraction', 'Vertex_Alpha', 'Greyscale_To_PaletteColor',
         'Greyscale_To_PaletteAlpha', 'Use_Falloff', 'Environment_Mapping', 'Receive_Shadows', 'Cast_Shadows',
         'Facegen_Detail_Map', 'Parallax', 'Model_Space_Normals', 'Non_Projective_Shadows', 'Landscape',
         'Refraction', 'Fire_Refraction', 'Eye_Environment_Mapping', 'Hair_Soft_Lighting', 'Screendoor_Alpha_Fade',
         'Localmap_Hide_Secret', 'FaceGen_RGB_Tint', 'Own_Emit', 'Projected_UV', 'Multiple_Textures',
         'Remappable_Textures', 'Decal', 'Dynamic_Decal', 'Parallax_Occlusion', 'External_Emittance',
         'Soft_Effect', 'ZBuffer_Test']
SLSF2 = ['ZBuffer_Write', 'LOD_Landscape', 'LOD_Objects', 'No_Fade', 'Double_Sided', 'Vertex_Colors', 'Glow_Map',
         'Assume_Shadowmask', 'Packed_Tangent', 'Multi_Index_Snow', 'Vertex_Lighting', 'Uniform_Scale', 'Fit_Slope',
         'Billboard', 'No_LOD_Land_Blend', 'EnvMap_Light_Fade', 'Wireframe', 'Weapon_Blood', 'Hide_On_Local_Map',
         'Premult_Alpha', 'Cloud_LOD', 'Anisotropic_Lighting', 'No_Transparency_Multisampling', 'Unused01',
         'Multi_Layer_Parallax', 'Soft_Lighting', 'Rim_Lighting', 'Back_Lighting', 'Unused02', 'Tree_Anim',
         'Effect_Lighting', 'HD_LOD_Objects']
SHADER_TYPES = {0: 'Default', 1: 'EnvMap', 2: 'Glow', 3: 'Parallax', 4: 'FaceGen', 5: 'SkinTint', 6: 'HairTint',
                7: 'ParallaxOcc', 8: 'MultiTexLand', 9: 'LODLand', 10: 'Snow', 11: 'MultiLayerParallax',
                12: 'TreeAnim', 13: 'LODObjects', 14: 'SparkleSnow', 15: 'LODObjectsHD', 16: 'Eye', 17: 'Cloud',
                18: 'LODLandNoise', 19: 'MultiTexLandLODBlend', 20: 'FO4Dismemberment'}


def flagnames(v, names):
    return [n for i, n in enumerate(names) if v & (1 << i)]


class R:
    def __init__(self, b, o):
        self.b, self.o = b, o

    def u8(self):
        v = self.b[self.o]; self.o += 1; return v

    def u16(self):
        v, = struct.unpack_from('<H', self.b, self.o); self.o += 2; return v

    def u32(self):
        v, = struct.unpack_from('<I', self.b, self.o); self.o += 4; return v

    def i32(self):
        v, = struct.unpack_from('<i', self.b, self.o); self.o += 4; return v

    def u64(self):
        v, = struct.unpack_from('<Q', self.b, self.o); self.o += 8; return v

    def f(self, n=1):
        v = struct.unpack_from('<%df' % n, self.b, self.o); self.o += 4 * n; return v if n > 1 else v[0]

    def sized(self):
        n = self.u32()
        s = self.b[self.o:self.o + n].decode('latin1').rstrip('\0'); self.o += n; return s


def vc_black_fraction(b, off, nv, vsize, desc):
    """fraction of vertices whose vertex colour RGB is all < 16 (renders black if the shader uses vertex colours)"""
    co = ((desc >> 24) & 0xF) * 4
    if nv == 0 or vsize == 0:
        return None
    black = 0
    alpha0 = 0
    for i in range(nv):
        p = off + i * vsize + co
        r, g, bl, a = b[p], b[p + 1], b[p + 2], b[p + 3]
        if r < 16 and g < 16 and bl < 16:
            black += 1
        if a == 0:
            alpha0 += 1
    return black / nv, alpha0 / nv


def parse(b):
    out = {'errors': [], 'shapes': [], 'strings_extra': {}, 'nodes': set()}
    nl = b.find(b'\n')
    if nl < 0 or not b[:nl].startswith(b'Gamebryo File Format'):
        out['errors'].append('not a nif')
        return out
    r = R(b, nl + 1)
    out['version'] = r.u32(); r.u8()
    if out['version'] != 0x14020007:
        out['errors'].append('unsupported nif version %08X' % out['version'])
        out['bsver'] = None
        return out
    r.u32()
    nblocks = r.u32()
    bsver = out['bsver'] = r.u32()
    r.o += 1 + b[r.o]
    if bsver > 130:
        r.o += 4
    r.o += 1 + b[r.o]
    r.o += 1 + b[r.o]
    if bsver == 130:
        r.o += 1 + b[r.o]
    nt = r.u16()
    types = []
    for _ in range(nt):
        types.append(r.sized())
    tidx = struct.unpack_from('<%dH' % nblocks, b, r.o); r.o += 2 * nblocks
    sizes = struct.unpack_from('<%dI' % nblocks, b, r.o); r.o += 4 * nblocks
    ns = r.u32(); r.u32()
    strings = []
    for _ in range(ns):
        strings.append(r.sized())
    ng = r.u32(); r.o += 4 * ng
    offs = []
    p = r.o
    for s in sizes:
        offs.append(p); p += s
    bt = [types[t & 0x7FFF] for t in tidx]
    out['block_types'] = sorted(set(bt))

    def S(i):
        return strings[i] if 0 <= i < len(strings) else None

    names = {}
    for i, t in enumerate(bt):
        if t in ('NiNode', 'BSFadeNode', 'BSLeafAnimNode', 'NiSwitchNode', 'BSMultiBoundNode', 'BSTreeNode') or t in SHAPE_TYPES:
            nm = S(struct.unpack_from('<i', b, offs[i])[0])
            names[i] = nm
            if 'Node' in t:
                out['nodes'].add(nm)
        elif t == 'NiStringExtraData':
            n, v = struct.unpack_from('<ii', b, offs[i])
            out['strings_extra'][S(n)] = S(v)

    def shader(i):
        d = {'shader_kind': bt[i] if 0 <= i < len(bt) else None, 'shader_type': None, 'sf1': 0, 'sf2': 0,
             'textures': [], 'skin_tint': None}
        if not (0 <= i < len(bt)):
            return d
        q = R(b, offs[i])
        try:
            if bt[i] == 'BSLightingShaderProperty':
                if bsver < 151:
                    d['shader_type'] = q.u32()
                d['shader_name'] = S(q.i32())
                ne = q.u32(); q.o += 4 * ne; q.i32()
                d['sf1'] = q.u32(); d['sf2'] = q.u32()
                q.f(4)
                ts = q.i32()
                q.f(4)
                q.u32()
                d['alpha'], _, d['gloss'] = q.f(3)
                q.f(4)
                q.f(2)
                if d['shader_type'] == 5:
                    d['skin_tint'] = q.f(3)
                if 0 <= ts < len(bt) and bt[ts] == 'BSShaderTextureSet':
                    t = R(b, offs[ts])
                    n = t.i32()
                    d['textures'] = [t.sized() for _ in range(max(0, min(n, 16)))]
            elif bt[i] == 'BSEffectShaderProperty':
                d['shader_name'] = S(q.i32())
                ne = q.u32(); q.o += 4 * ne; q.i32()
                d['sf1'] = q.u32(); d['sf2'] = q.u32()
                q.f(4)
                src = q.sized()
                q.u8(); q.u8(); q.u8(); q.u8()
                q.f(4)
                q.f(4); q.f(1); q.f(1)
                grey = q.sized()
                d['textures'] = [src, grey]
        except (struct.error, IndexError) as e:
            out['errors'].append('shader block %d: %r' % (i, e))
        return d

    def skin(i):
        d = {'skin_type': None, 'partitions': [], 'bones': [], 'has_partition_block': False, 'part_vdata': None}
        if not (0 <= i < len(bt)):
            return d
        d['skin_type'] = bt[i]
        if bt[i] not in ('NiSkinInstance', 'BSDismemberSkinInstance'):
            return d
        q = R(b, offs[i])
        dref = q.i32(); pref = q.i32(); q.i32()
        nb = q.u32()
        bones = [q.i32() for _ in range(nb)]
        d['bones'] = [names.get(x, '?%d' % x) for x in bones]
        if bt[i] == 'BSDismemberSkinInstance':
            np_ = q.i32()
            for _ in range(max(0, min(np_, 64))):
                fl = q.u16(); bp = q.u16()
                d['partitions'].append(bp)
        if 0 <= pref < len(bt) and bt[pref] == 'NiSkinPartition':
            d['has_partition_block'] = True
            q = R(b, offs[pref])
            nparts = q.u32()
            if bsver == 100:
                dsize = q.u32(); vsize = q.u32(); desc = q.u64()
                d['part_vdata'] = (q.o, dsize, vsize, desc)
            d['n_skin_parts'] = nparts
        return d

    for i, t in enumerate(bt):
        if t in ('NiTriShape', 'NiTriStrips'):
            out['shapes'].append({'name': names.get(i) or S(struct.unpack_from('<i', b, offs[i])[0]), 'type': t,
                                  'legacy': True})
            continue
        if t not in SHAPE_TYPES:
            continue
        q = R(b, offs[i])
        try:
            nm = S(q.i32()); ne = q.u32(); q.o += 4 * ne; q.i32()
            q.u32()
            q.o += 12 + 36 + 4 + 4 + 16
            sk, sh, al = q.i32(), q.i32(), q.i32()
            desc = q.u64()
            ntri = q.u32() if bsver >= 130 else q.u16()
            nv = q.u16()
            dsize = q.u32()
            vsize = (desc & 0xF) * 4
            vdata_off = q.o
        except struct.error as e:
            out['errors'].append('shape %d: %r' % (i, e))
            continue
        va = (desc >> 44) & 0xFFF
        s = {'name': nm, 'type': t, 'nv': nv, 'ntri': ntri, 'va_flags': va, 'has_vc': bool(va & 0x20),
             'skinned_va': bool(va & 0x40), 'has_normals': bool(va & 0x8), 'alpha_ref': al, 'vc_black': None}
        s.update(skin(sk))
        s.update(shader(sh))
        try:
            if s['has_vc']:
                if dsize > 0 and vsize > 0:
                    s['vc_black'] = vc_black_fraction(b, vdata_off, nv, vsize, desc)
                elif s.get('part_vdata'):
                    po, pd, pv, pdesc = s['part_vdata']
                    if pv and (pdesc >> 44) & 0x20:
                        s['vc_black'] = vc_black_fraction(b, po, pd // pv, pv, pdesc)
        except IndexError:
            out['errors'].append('vertex colour read failed on %s' % nm)
        s.pop('part_vdata', None)
        out['shapes'].append(s)
    return out


if __name__ == '__main__':
    import sys, json
    d = parse(open(sys.argv[1], 'rb').read())
    for s in d['shapes']:
        s2 = dict(s)
        s2['sf1'] = flagnames(s.get('sf1', 0), SLSF1)
        s2['sf2'] = flagnames(s.get('sf2', 0), SLSF2)
        s2['bones'] = len(s.get('bones', []))
        s2['shader_type'] = SHADER_TYPES.get(s.get('shader_type'), s.get('shader_type'))
        print(json.dumps(s2, default=str))
    print('bsver', d.get('bsver'), 'errors', d['errors'], 'extra', d['strings_extra'])

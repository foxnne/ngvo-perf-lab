"""Minimal SSE NIF/BTO reader: list shapes with shader flags, textures, vertex colour and normal stats.
Usage: python bto_shapes.py file.bto|file.nif [...]
"""
import struct, sys, numpy as np

SLSF1 = ['Specular', 'Skinned', 'Temp_Refraction', 'Vertex_Alpha', 'Greyscale_Palette_Color', 'Greyscale_Palette_Alpha', 'Use_Falloff', 'Environment_Mapping',
         'Recieve_Shadows', 'Cast_Shadows', 'Facegen_Detail', 'Parallax', 'Model_Space_Normals', 'Non_Projective_Shadows', 'Landscape', 'Refraction',
         'Fire_Refraction', 'Eye_Env', 'Hair_Soft_Lighting', 'Screendoor', 'Localmap_Hide_Secret', 'FaceGen_RGB_Tint', 'Own_Emit', 'Projected_UV',
         'Multiple_Textures', 'Remappable', 'Decal', 'Dynamic_Decal', 'Parallax_Occlusion', 'External_Emittance', 'Soft_Effect', 'ZBuffer_Test']
SLSF2 = ['ZBuffer_Write', 'LOD_Landscape', 'LOD_Objects', 'No_Fade', 'Double_Sided', 'Vertex_Colors', 'Glow_Map', 'Assume_Shadowmask',
         'Packed_Tangent', 'Multi_Index_Snow', 'Vertex_Lighting', 'Uniform_Scale', 'Fit_Slope', 'Billboard', 'No_LOD_Land_Blend', 'EnvMap_Light_Fade',
         'Wireframe', 'Weapon_Blood', 'Hide_On_Local_Map', 'Premult_Alpha', 'Cloud_LOD', 'Anisotropic', 'No_Transp_MS', 'Unused01',
         'Multi_Layer_Parallax', 'Soft_Lighting', 'Rim_Lighting', 'Back_Lighting', 'Unused02', 'Tree_Anim', 'Effect_Lighting', 'HD_LOD_Objects']
DEFAULT1 = {'Recieve_Shadows', 'Cast_Shadows', 'ZBuffer_Test', 'Specular'}
DEFAULT2 = {'ZBuffer_Write'}


def names(v, tbl):
    return [tbl[i] for i in range(32) if v >> i & 1]


class Nif:
    def __init__(self, path):
        self.d = open(path, 'rb').read(); d = self.d
        p = d.index(b'\n') + 1
        ver, endian, uver, nblocks, bsver = struct.unpack_from('<IBIII', d, p); p += 17
        self.bsver = bsver
        for _ in range(3):  # author, process script, export script
            n = d[p]; p += 1 + n
        ntypes, = struct.unpack_from('<H', d, p); p += 2
        self.types = []
        for _ in range(ntypes):
            n, = struct.unpack_from('<I', d, p); p += 4; self.types.append(d[p:p + n].decode()); p += n
        self.btype = struct.unpack_from('<%dH' % nblocks, d, p); p += 2 * nblocks
        self.bsize = struct.unpack_from('<%dI' % nblocks, d, p); p += 4 * nblocks
        nstr, maxlen = struct.unpack_from('<II', d, p); p += 8
        self.strings = []
        for _ in range(nstr):
            n, = struct.unpack_from('<I', d, p); p += 4; self.strings.append(d[p:p + n].decode('latin1')); p += n
        ngroups, = struct.unpack_from('<I', d, p); p += 4 + 4 * ngroups
        self.boff = []
        for s in self.bsize:
            self.boff.append(p); p += s
        self.n = nblocks

    def tname(self, i): return self.types[self.btype[i]]
    def s(self, i): return self.strings[i] if 0 <= i < len(self.strings) else ''

    def shader(self, i):
        d = self.d; p = self.boff[i]
        stype, name, nx = struct.unpack_from('<IiI', d, p); p += 12 + 4 * nx + 4
        f1, f2 = struct.unpack_from('<II', d, p); p += 8
        uvo = struct.unpack_from('<4f', d, p); p += 16
        tset, = struct.unpack_from('<i', d, p); p += 4
        em = struct.unpack_from('<4f', d, p); p += 16
        clamp, alpha, refr, gloss = struct.unpack_from('<Ifff', d, p); p += 16
        spec = struct.unpack_from('<4f', d, p); p += 16
        le1, le2 = struct.unpack_from('<ff', d, p)
        return dict(stype=stype, f1=f1, f2=f2, tset=tset, emissive=em, alpha=alpha, gloss=gloss, spec=spec, le1=le1, le2=le2)

    def textures(self, i):
        if i < 0: return []
        d = self.d; p = self.boff[i]
        n, = struct.unpack_from('<I', d, p); p += 4; out = []
        for _ in range(n):
            l, = struct.unpack_from('<I', d, p); p += 4; out.append(d[p:p + l].decode('latin1')); p += l
        return out

    def alpha(self, i):
        if i < 0: return None
        d = self.d; p = self.boff[i]
        name, nx = struct.unpack_from('<iI', d, p); p += 8 + 4 * nx + 4
        flags, thr = struct.unpack_from('<HB', d, p)
        return dict(flags=flags, blend=flags & 1, test=flags >> 9 & 1, threshold=thr)

    def shape(self, i):
        d = self.d; p = self.boff[i]
        name, nx = struct.unpack_from('<iI', d, p); p += 8 + 4 * nx + 4
        flags, = struct.unpack_from('<I', d, p); p += 4
        tr = struct.unpack_from('<3f', d, p); p += 12 + 36
        scale, coll = struct.unpack_from('<fi', d, p); p += 8
        p += 16  # bounding sphere
        skin, shader, alpha = struct.unpack_from('<iii', d, p); p += 12
        desc, = struct.unpack_from('<Q', d, p); p += 8
        ntri, nvert, dsize = struct.unpack_from('<HHI', d, p); p += 8
        vsize = (desc & 0xF) * 4; attrs = desc >> 44
        out = dict(name=self.s(name), shader=shader, alpha=alpha if (alpha >= 0 and self.tname(alpha) == 'NiAlphaProperty') else -1, alpha_ref=alpha, ntri=ntri, nvert=nvert, vsize=vsize, attrs=attrs, scale=scale, tr=tr)
        if dsize == 0 or nvert == 0: return out
        raw = np.frombuffer(d, dtype=np.uint8, count=nvert * vsize, offset=p).reshape(nvert, vsize)
        o = 0
        full = bool(attrs & 0x400) or self.bsver == 100
        if attrs & 0x1:
            if full:
                out['pos'] = raw[:, 0:12].copy().view('<f4'); o = 16
            else:
                out['pos'] = raw[:, 0:6].copy().view('<f2').astype(np.float32); o = 8
        if attrs & 0x2:
            out['uv'] = raw[:, o:o + 4].copy().view('<f2').astype(np.float32); o += 4
        if attrs & 0x4: o += 4
        if attrs & 0x8:
            out['nrm'] = raw[:, o:o + 3].astype(np.float32) / 127.5 - 1.0; o += 4
        if attrs & 0x10: o += 4
        if attrs & 0x20:
            out['col'] = raw[:, o:o + 4].astype(np.float32) / 255.0; o += 4
        tp = p + nvert * vsize
        out['tris'] = np.frombuffer(d, dtype='<u2', count=ntri * 3, offset=tp).reshape(ntri, 3)
        return out


def describe(path, tree_only=False, limit=400):
    nif = Nif(path)
    print('==', path, 'blocks', nif.n)
    shown = 0
    for i in range(nif.n):
        t = nif.tname(i)
        if t not in ('BSSubIndexTriShape', 'BSTriShape', 'BSMeshLODTriShape', 'BSLODTriShape'): continue
        sh = nif.shape(i)
        if sh['shader'] < 0 or nif.tname(sh['shader']) != 'BSLightingShaderProperty':
            print('  [%d] %s %r non-lighting shader %s' % (i, t, sh['name'], nif.tname(sh['shader']) if sh['shader'] >= 0 else None)); continue
        sp = nif.shader(sh['shader']); tex = nif.textures(sp['tset']); al = nif.alpha(sh['alpha'])
        f1 = set(names(sp['f1'], SLSF1)); f2 = set(names(sp['f2'], SLSF2))
        istree = 'tree' in sh['name'].lower() or any('tree' in x.lower() or 'lodgen' in x.lower() for x in tex[:1])
        if tree_only and not istree: continue
        shown += 1
        if shown > limit: break
        line = '  [%d] %s %r v=%d t=%d attrs=0x%x' % (i, t, sh['name'], sh['nvert'], sh['ntri'], sh['attrs'])
        print(line)
        print('      SLSF1:', sorted(f1), ' SLSF2:', sorted(f2))
        print('      type=%d alpha=%.2f gloss=%.1f spec=%s LE1(soft/rim)=%.3f LE2(back)=%.3f emissive=%s alphaProp=%s' % (
            sp['stype'], sp['alpha'], sp['gloss'], tuple(round(x, 2) for x in sp['spec']), sp['le1'], sp['le2'], tuple(round(x, 2) for x in sp['emissive']), al))
        print('      tex:', [x for x in tex if x])
        if 'col' in sh:
            c = sh['col']
            print('      vertex colour mean rgb=(%.3f %.3f %.3f) a=%.3f  min=%.3f max=%.3f  p10/p50/p90 of luma=%s' % (
                c[:, 0].mean(), c[:, 1].mean(), c[:, 2].mean(), c[:, 3].mean(), c[:, :3].min(), c[:, :3].max(),
                np.round(np.percentile(c[:, :3].mean(1), [10, 50, 90]), 3)))
        if 'nrm' in sh and 'pos' in sh:
            n = sh['nrm']; ln = np.linalg.norm(n, axis=1, keepdims=True); n = n / np.maximum(ln, 1e-5)
            print('      vertex normal: mean=(%.2f %.2f %.2f) mean nz=%.2f  frac nz>0.5=%.2f  frac |nz|<0.3 (horizontal)=%.2f  frac nz<-0.3=%.2f' % (
                n[:, 0].mean(), n[:, 1].mean(), n[:, 2].mean(), n[:, 2].mean(), (n[:, 2] > 0.5).mean(), (np.abs(n[:, 2]) < 0.3).mean(), (n[:, 2] < -0.3).mean()))
            # geometric face normals vs vertex normals
            p = sh['pos'][:, :3]; t = sh['tris']
            fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
            fl = np.linalg.norm(fn, axis=1, keepdims=True); ok = fl[:, 0] > 1e-6
            fn = fn[ok] / fl[ok]; vn = n[t[ok, 0]]
            d = np.abs((fn * vn).sum(1))
            print('      |face normal . vertex normal| mean=%.2f (1 = normals follow the card, lower = bent/spherical); face |nz| mean=%.2f' % (d.mean(), np.abs(fn[:, 2]).mean()))
    return nif


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    for a in args:
        describe(a, tree_only='--trees' in sys.argv)

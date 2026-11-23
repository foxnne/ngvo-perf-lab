"""Minimal Skyrim SE NIF (20.2.0.7, bsver 100) reader / block remover.

Blocks are kept byte for byte; only block references are rewritten when blocks are removed. Reference locations are
known per block type (REFS); a file containing a block type that is not in the table is refused (UnknownType).
"""
import struct

NODE_TYPES = {'NiNode', 'BSFadeNode', 'BSLeafAnimNode', 'BSTreeNode', 'BSMultiBoundNode', 'BSOrderedNode', 'BSValueNode',
              'NiBillboardNode', 'BSBlastNode', 'BSDamageStage', 'BSDebrisNode', 'NiSwitchNode', 'BSRangeNode'}
SHAPE_TYPES = {'BSTriShape', 'BSMeshLODTriShape', 'BSSubIndexTriShape', 'BSLODTriShape', 'BSDynamicTriShape'}
NOREF_NET = {'BSXFlags', 'NiStringExtraData', 'NiIntegerExtraData', 'NiFloatExtraData', 'NiBooleanExtraData', 'BSBound',
             'NiStringsExtraData', 'NiIntegersExtraData', 'NiBinaryExtraData', 'BSBehaviorGraphExtraData', 'BSInvMarker',
             'BSFurnitureMarkerNode', 'BSFurnitureMarker', 'NiTextKeyExtraData', 'BSWArray', 'BSDecalPlacementVectorExtraData',
             'NiFloatsExtraData', 'BSDistantObjectLargeRefExtraData'}
NOREF = {'BSShaderTextureSet', 'bhkCompressedMeshShapeData', 'bhkConvexVerticesShape', 'bhkBoxShape', 'bhkCapsuleShape',
         'bhkSphereShape', 'bhkCylinderShape', 'BSMultiBoundAABB', 'BSMultiBoundOBB', 'NiTriShapeData', 'NiTriStripsData',
         'hkPackedNiTriStripsData'} | NOREF_NET


class UnknownType(Exception):
    pass


class Nif:
    def __init__(self, data):
        b = self.data = bytes(data)
        nl = b.index(b'\n')
        self.headline = b[:nl + 1]
        pos = nl + 1
        self.version, self.endian, self.user_version, nblocks = struct.unpack_from('<IBII', b, pos)
        pos += 13
        self.bsver = struct.unpack_from('<I', b, pos)[0]
        pos += 4
        if self.version != 0x14020007 or self.bsver != 100:
            raise UnknownType('version %08x bsver %d' % (self.version, self.bsver))
        s0 = pos
        for _ in range(3):
            pos += 1 + b[pos]
        self.export_strings = b[s0:pos]
        ntypes = struct.unpack_from('<H', b, pos)[0]
        pos += 2
        self.types = []
        for _ in range(ntypes):
            n = struct.unpack_from('<I', b, pos)[0]
            self.types.append(b[pos + 4:pos + 4 + n].decode())
            pos += 4 + n
        self.type_index = list(struct.unpack_from('<%dH' % nblocks, b, pos))
        pos += 2 * nblocks
        sizes = struct.unpack_from('<%dI' % nblocks, b, pos)
        pos += 4 * nblocks
        nstr, self.maxlen = struct.unpack_from('<II', b, pos)
        pos += 8
        self.strings = []
        for _ in range(nstr):
            n = struct.unpack_from('<I', b, pos)[0]
            self.strings.append(b[pos + 4:pos + 4 + n])
            pos += 4 + n
        ngroups = struct.unpack_from('<I', b, pos)[0]
        self.groups = list(struct.unpack_from('<%dI' % ngroups, b, pos + 4))
        pos += 4 + 4 * ngroups
        self.blocks = []
        for i in range(nblocks):
            self.blocks.append(bytearray(b[pos:pos + sizes[i]]))
            pos += sizes[i]
        nroots = struct.unpack_from('<I', b, pos)[0]
        self.roots = list(struct.unpack_from('<%di' % nroots, b, pos + 4))
        pos += 4 + 4 * nroots
        if pos != len(b):
            raise UnknownType('trailing bytes after footer: %d' % (len(b) - pos))
        self.btypes = [self.types[t & 0x7FFF] for t in self.type_index]

    def string(self, i):
        return self.strings[i].decode('cp1252', 'replace') if 0 <= i < len(self.strings) else ''

    def tobytes(self):
        types = [t for t in self.types if t in set(self.btypes)] if set(self.btypes) != set(self.types) else list(self.types)
        tidx = [types.index(t) for t in self.btypes]
        o = bytearray(self.headline)
        o += struct.pack('<IBII', self.version, self.endian, self.user_version, len(self.blocks))
        o += struct.pack('<I', self.bsver) + self.export_strings
        o += struct.pack('<H', len(types))
        for t in types:
            o += struct.pack('<I', len(t)) + t.encode()
        o += struct.pack('<%dH' % len(tidx), *tidx)
        o += struct.pack('<%dI' % len(self.blocks), *[len(x) for x in self.blocks])
        o += struct.pack('<II', len(self.strings), self.maxlen)
        for s in self.strings:
            o += struct.pack('<I', len(s)) + s
        o += struct.pack('<I', len(self.groups)) + struct.pack('<%dI' % len(self.groups), *self.groups)
        for x in self.blocks:
            o += x
        o += struct.pack('<I', len(self.roots)) + struct.pack('<%di' % len(self.roots), *self.roots)
        return bytes(o)

    # ------------------------------------------------------------------ reference locations
    def _net(self, b, pos=0):
        """NiObjectNET -> (ref offsets, end pos). name, extra data list, controller"""
        n = struct.unpack_from('<I', b, pos + 4)[0]
        offs = [pos + 8 + 4 * k for k in range(n)]
        pos += 8 + 4 * n
        offs.append(pos)
        return offs, pos + 4

    def _av(self, b, pos=0):
        offs, pos = self._net(b, pos)
        pos += 4 + 12 + 36 + 4  # flags, translation, rotation, scale
        offs.append(pos)        # collision object
        return offs, pos + 4

    def _list(self, b, pos):
        n = struct.unpack_from('<I', b, pos)[0]
        return [pos + 4 + 4 * k for k in range(n)], pos + 4 + 4 * n

    def node_layout(self, i):
        """-> dict(av_end, children=(count offset, [ref offsets]), refs=[all], end)"""
        b = self.blocks[i]
        t = self.btypes[i]
        offs, pos = self._av(b)
        cpos = pos
        ch, pos = self._list(b, pos)
        ef, pos = self._list(b, pos)
        extra = []
        if t == 'BSTreeNode':
            b1, pos = self._list(b, pos)
            b2, pos = self._list(b, pos)
            extra = b1 + b2
        elif t == 'BSMultiBoundNode':
            extra = [pos]
            pos += 8
        elif t == 'BSOrderedNode':
            pos += 17
        elif t == 'BSValueNode':
            pos += 5
        elif t == 'NiBillboardNode':
            pos += 2
        elif t in ('NiNode', 'BSFadeNode', 'BSLeafAnimNode'):
            pass
        else:
            raise UnknownType(t)
        if pos != len(b):
            raise UnknownType('%s size mismatch %d != %d' % (t, pos, len(b)))
        return dict(count=cpos, children=ch, refs=offs + ch + ef + extra)

    def ref_offsets(self, i):
        b = self.blocks[i]
        t = self.btypes[i]
        if t in NODE_TYPES:
            return self.node_layout(i)['refs']
        if t in SHAPE_TYPES:
            offs, pos = self._av(b)
            pos += 16
            return offs + [pos, pos + 4, pos + 8]
        if t == 'BSLightingShaderProperty':
            offs, pos = self._net(b, 4)
            return offs + [pos + 8 + 16]
        if t in ('BSEffectShaderProperty', 'NiAlphaProperty', 'BSWaterShaderProperty', 'BSSkyShaderProperty'):
            return self._net(b)[0]
        if t in NOREF_NET or t in NOREF:
            return []
        if t in ('bhkCollisionObject', 'bhkSPCollisionObject'):
            if len(b) != 10: raise UnknownType('%s size %d' % (t, len(b)))
            return [0, 6]
        if t in ('bhkRigidBody', 'bhkRigidBodyT'):
            n = struct.unpack_from('<I', b, len(b) - 6)[0]
            if n != 0 or len(b) != 250:
                raise UnknownType('%s size %d constraints %d' % (t, len(b), n))
            return [0]
        if t == 'bhkMoppBvTreeShape':
            return [0]
        if t in ('bhkConvexTransformShape', 'bhkTransformShape'):
            return [0]
        if t == 'bhkCompressedMeshShape':
            if len(b) != 56: raise UnknownType('%s size %d' % (t, len(b)))
            return [0, 52]
        if t == 'bhkListShape':
            return self._list(b, 0)[0]
        if t == 'bhkNiTriStripsShape':
            pos = 4 + 4 + 20 + 4 + 16
            return self._list(b, pos)[0]
        if t == 'bhkPackedNiTriStripsShape':
            if len(b) != 60: raise UnknownType('%s size %d' % (t, len(b)))
            return [56]
        raise UnknownType(t)

    def refs(self, i):
        b = self.blocks[i]
        return [struct.unpack_from('<i', b, o)[0] for o in self.ref_offsets(i)]

    # ------------------------------------------------------------------ queries
    def children(self, i):
        b = self.blocks[i]
        return [struct.unpack_from('<i', b, o)[0] for o in self.node_layout(i)['children']]

    def name(self, i):
        t = self.btypes[i]
        if t in NODE_TYPES or t in SHAPE_TYPES:
            return self.string(struct.unpack_from('<i', self.blocks[i], 0)[0])
        return ''

    def shape(self, i):
        b = self.blocks[i]
        offs, pos = self._av(b)
        pos += 16
        skin, shader, alpha = struct.unpack_from('<3i', b, pos)
        pos += 12
        desc = struct.unpack_from('<Q', b, pos)[0]
        pos += 8
        ntri, nvert, dsize = struct.unpack_from('<HHI', b, pos)
        d = dict(name=self.name(i), skin=skin, shader=shader, alpha=alpha, ntri=ntri, nvert=nvert, dsize=dsize,
                 vflags=(desc >> 44) & 0xFFF, textures=[], shader_type=None)
        if shader >= 0:
            st = self.btypes[shader]
            d['shader_type'] = st
            sb = self.blocks[shader]
            if st == 'BSLightingShaderProperty':
                o, p = self._net(sb, 4)
                d['f1'], d['f2'] = struct.unpack_from('<II', sb, p)
                ts = struct.unpack_from('<i', sb, p + 24)[0]
                if ts >= 0:
                    d['textures'] = self.texset(ts)
            elif st == 'BSEffectShaderProperty':
                o, p = self._net(sb)
                p += 8 + 16
                n = struct.unpack_from('<I', sb, p)[0]
                d['textures'] = [bytes(sb[p + 4:p + 4 + n]).decode('cp1252', 'replace')]
        return d

    def texset(self, i):
        b = self.blocks[i]
        n = struct.unpack_from('<I', b, 0)[0]
        pos = 4
        out = []
        for _ in range(n):
            l = struct.unpack_from('<I', b, pos)[0]
            out.append(bytes(b[pos + 4:pos + 4 + l]).decode('cp1252', 'replace'))
            pos += 4 + l
        return out

    def reachable(self):
        seen = set()
        stack = [r for r in self.roots if r >= 0]
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            for r in self.refs(i):
                if r >= len(self.blocks):
                    raise UnknownType('ref %d out of range in block %d %s' % (r, i, self.btypes[i]))
                if r >= 0 and r not in seen:
                    stack.append(r)
        return seen

    # ------------------------------------------------------------------ edits
    def detach_child(self, parent, child):
        """remove child from a node's children array (array shrinks)"""
        lay = self.node_layout(parent)
        b = self.blocks[parent]
        hit = [o for o in lay['children'] if struct.unpack_from('<i', b, o)[0] == child]
        assert len(hit) == 1
        del b[hit[0]:hit[0] + 4]
        struct.pack_into('<I', b, lay['count'], len(lay['children']) - 1)

    def drop_unreachable(self):
        """delete blocks not reachable from the roots; remap every reference. -> list of removed (index, type)"""
        keep = self.reachable()
        n = len(self.blocks)
        new = {}
        k = 0
        for i in range(n):
            if i in keep:
                new[i] = k
                k += 1
        removed = [(i, self.btypes[i]) for i in range(n) if i not in keep]
        for i in sorted(keep):
            b = self.blocks[i]
            for o in self.ref_offsets(i):
                r = struct.unpack_from('<i', b, o)[0]
                if r >= 0:
                    struct.pack_into('<i', b, o, new[r])
        self.roots = [new[r] if r >= 0 else r for r in self.roots]
        self.blocks = [self.blocks[i] for i in range(n) if i in keep]
        self.btypes = [self.btypes[i] for i in range(n) if i in keep]
        return removed


def summary(nif):
    """structural fingerprint: per block (type, size), shapes with vertex/tri counts"""
    shapes = []
    for i, t in enumerate(nif.btypes):
        if t in SHAPE_TYPES:
            s = nif.shape(i)
            shapes.append((s['name'], s['nvert'], s['ntri'], tuple(s['textures'][:1])))
    return shapes

"""Decoder for NGIO / FasterNGIO grass cache files (Data\\Grass\\<worldspace>x<XXXX>y<YYYY>.cgid).

Layout (worked out from the files; every one of the 7,282 files parses to its exact length):

  u32 nTypes                                  (a 4-byte file holding 0 = "cell has no grass")
  nTypes x {
     u32 len ; char model[len]                 NUL-terminated mesh path relative to meshes\\, e.g. landscape\\Grass\\X.nif
     f32 wavePeriod                            GRAS DATA wave period
     u32 formID                                run-time form ID of the GRAS record (load-order dependent, FExxxyyy for ESL)
     u8  flag[3]                               three grass-parameter bytes. flag[1] follows the GRAS "uniform scaling" bit
                                               (DATA flags & 2); flag[0] is 1 and flag[2] is 0 in every file of this cache,
                                               where every GRAS has "fit to slope" set and "vertex lighting" clear, so which
                                               of the two is which is not determined
     u32 nShapes                               the cell is split into quadrant shapes (BSInstanceTriShape batches)
     nShapes x {
        f32 centre[3] ; f32 halfExtent[3]      world-space bound of the batch
        u32 zero
        u32 nInstances ; u32 halfsPerInstance (always 16)
        nInstances x 16 half floats  = the four float4 instance rows the grass vertex shader receives:
           [0..3]   x, y, z, colourScale       x, y = world position minus a block origin (see world_xy), z = world z;
                                               colourScale multiplies the mesh vertex colour (GRAS colour range)
           [4..7]   rot row0.xyz , rot row2.y
           [8..11]  rot row1.xyz , rot row2.z
           [12..15] rot row2.x , scale-1 , 0 , 0
     }
  }

Conventions: cell (cx, cy) covers world x cx*4096..(cx+1)*4096, y cy*4096..(cy+1)*4096 (y north).
Instance x/y are stored relative to the origin of a 12 x 12 cell block: origin = trunc(c / 12) * 12 * 4096 per axis
(truncation toward zero, so cells -11..11 share origin 0). Found empirically: with it every instance of all 102,872
type groups in the 7,282 files falls inside its own cell square (step1_survey.py). Half floats above 32768 have 32-unit steps, above 16384 16-unit steps, so positions
far from a block origin are that coarse (irrelevant for a 256-unit map).
"""
import os
import re
import struct

import numpy as np

NAME_RE = re.compile(r'^(.*?)x(-?\d+)y(-?\d+)\.cgid$', re.I)


def parse_name(fname):
    m = NAME_RE.match(fname)
    if not m:
        return None
    return m.group(1).lower(), int(m.group(2)), int(m.group(3))


def read_cgid(path_or_bytes):
    """Returns a list of dicts: model, wave, formid, flags (3 bytes), inst (N x 16 float32, as stored),
    shapes (list of (centre, half_extent, count))."""
    b = open(path_or_bytes, 'rb').read() if isinstance(path_or_bytes, str) else path_or_bytes
    n = struct.unpack_from('<I', b, 0)[0]
    pos = 4
    out = []
    for _ in range(n):
        ln = struct.unpack_from('<I', b, pos)[0]
        pos += 4
        model = b[pos:pos + ln].split(b'\0')[0].decode('cp1252').lower()
        pos += ln
        wave, formid = struct.unpack_from('<fI', b, pos)
        pos += 8
        flags = tuple(b[pos:pos + 3])
        pos += 3
        nshapes = struct.unpack_from('<I', b, pos)[0]
        pos += 4
        parts, shapes = [], []
        for _ in range(nshapes):
            v = struct.unpack_from('<6f', b, pos)
            pos += 24
            zero, cnt, per = struct.unpack_from('<III', b, pos)
            pos += 12
            if per != 16 or zero != 0:
                raise ValueError('unexpected shape header zero=%d per=%d' % (zero, per))
            parts.append(np.frombuffer(b, '<f2', cnt * 16, pos).reshape(cnt, 16))
            pos += cnt * 32
            shapes.append((v[:3], v[3:], cnt))
        inst = np.concatenate(parts).astype(np.float32) if parts else np.zeros((0, 16), np.float32)
        out.append(dict(model=model, wave=wave, formid=formid, flags=flags, inst=inst, shapes=shapes))
    if pos != len(b):
        raise ValueError('trailing bytes: parsed %d of %d' % (pos, len(b)))
    return out


def find_cache_dir(root=r'C:\Modlists\NGVO 8.0 Beta', profile='foxnne-nsfw'):
    """Highest-priority enabled mod (or overwrite) that holds Grass\\*.cgid."""
    cands = [os.path.join(root, 'overwrite')]
    with open(os.path.join(root, 'profiles', profile, 'modlist.txt'), encoding='utf-8', errors='replace') as f:
        cands += [os.path.join(root, 'mods', l[1:].rstrip('\r\n')) for l in f if l.startswith('+')]
    hits = []
    for c in cands:
        g = os.path.join(c, 'Grass')
        if os.path.isdir(g) and any(n.lower().endswith('.cgid') for n in os.listdir(g)):
            hits.append(g)
    return hits


def iter_world(grass_dir, world='tamriel'):
    for name in os.listdir(grass_dir):
        p = parse_name(name)
        if p and p[0] == world:
            yield p[1], p[2], os.path.join(grass_dir, name)


def block_origin(c):
    """World-space origin (one axis) that the stored instance x / y of cell coordinate c are relative to."""
    return int(c / 12) * 12 * 4096.0


def world_xy(inst, cx, cy):
    """World x, y (float64 arrays) of the instances of a cell."""
    return inst[:, 0].astype(np.float64) + block_origin(cx), inst[:, 1].astype(np.float64) + block_origin(cy)

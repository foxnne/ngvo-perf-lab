"""Collect LAND VHGT heights for given worldspaces from the active load order of an MO2 profile.
Read-only on the modlist. Output: land_<EDID>.npz (cells Nx2 int, heights Nx33x33 float32, src plugin index, names)."""
import os, sys, struct, zlib, time, ctypes
import numpy as np
sys.path.insert(0, r'C:\Users\foxnn\dev\skyrimnet-wardrobe')
import tes5
from build_catalogue import read_profile

try:  # below-normal priority: a benchmark may be running
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

ROOT = r'C:\Modlists\NGVO 8.0 Beta'
PROFILE = 'foxnne-nsfw'
TARGETS = {'tamriel', 'markarthworld'}
HDR = tes5.REC_HDR
F_DELETED = 0x20


def plugin_index(root, mods):
    """Slim version of build_catalogue.build_index: only top-level plugin files (the original walks meshes trees)."""
    sources = [os.path.join(root, 'overwrite')] + [os.path.join(root, 'mods', m) for m in mods] + [os.path.join(root, 'Stock Game', 'Data')]
    out = {}
    for path in sources:
        try:
            for e in os.scandir(path):
                ln = e.name.lower()
                if ln.endswith(('.esp', '.esm', '.esl')) and e.is_file():
                    out.setdefault(ln, e.path)
        except OSError:
            pass
    return out


def body_of(blob, pos, size, flags):
    b = blob[pos + 24:pos + 24 + size]
    if flags & tes5.F_COMPRESSED:
        b = zlib.decompress(b[4:])
    return b


def decode_vhgt(sd):
    off = struct.unpack_from('<f', sd)[0]
    g = np.frombuffer(sd, np.int8, 1089, 4).reshape(33, 33).astype(np.float64)
    col0 = np.cumsum(g[:, 0])
    rows = np.cumsum(g[:, 1:], axis=1)
    h = np.empty((33, 33))
    h[:, 0] = col0
    h[:, 1:] = col0[:, None] + rows
    return ((h + off) * 8.0).astype(np.float32)


class Collector:
    def __init__(self):
        self.ws_edid = {}      # wrld formkey -> edid lower
        self.ws_dnam = {}      # edid -> (land, water, plugin) last wins
        self.cell_grid = {}    # (edid, cell formkey) -> (x, y) last wins
        self.land = {}         # (edid, land formkey) -> (cell formkey, heights, plugin idx) last wins
        self.land_hist = {}    # (edid, land formkey) -> [(plugin idx, status)...]
        self.stats = {}        # plugin -> counts
        self.errors = []

    def walk_wrld_top(self, pl, pi, blob):
        pos, n = 0, len(blob)
        while pos + 24 <= n:
            typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
            if typ == b'GRUP':
                label, gtype = struct.unpack_from('<II', blob, pos + 8)
                if gtype == 1:
                    edid = self.ws_edid.get(pl.formkey(label))
                    if edid in TARGETS:
                        self.walk_world(pl, pi, blob, pos + 24, pos + size, edid)
                pos += max(size, 24)
                continue
            if typ == b'WRLD':
                body = body_of(blob, pos, size, flags)
                edid = None
                for st, sd in tes5.iter_subrecords(body):
                    if st == b'EDID':
                        edid = tes5.zstr(sd).lower()
                        self.ws_edid.setdefault(pl.formkey(fid), edid)
                    elif st == b'DNAM' and len(sd) >= 8:
                        e = self.ws_edid.get(pl.formkey(fid), edid)
                        self.ws_dnam[e] = struct.unpack_from('<ff', sd) + (pl.name,)
            pos += 24 + size

    def walk_world(self, pl, pi, blob, pos, end, edid):
        while pos + 24 <= end:
            typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
            if typ == b'GRUP':
                label, gtype = struct.unpack_from('<II', blob, pos + 8)
                if gtype in (4, 5, 6):
                    self.walk_world(pl, pi, blob, pos + 24, pos + size, edid)
                elif gtype == 9:
                    self.walk_temp(pl, pi, blob, pos + 24, pos + size, edid, pl.formkey(label))
                pos += max(size, 24)
                continue
            if typ == b'CELL':
                try:
                    body = body_of(blob, pos, size, flags)
                    for st, sd in tes5.iter_subrecords(body):
                        if st == b'XCLC' and len(sd) >= 8:
                            self.cell_grid[(edid, pl.formkey(fid))] = struct.unpack_from('<ii', sd)
                            self.stats[pl.name]['cells'] += 1
                            break
                except zlib.error as e:
                    self.errors.append('%s CELL %08X zlib %s' % (pl.name, fid, e))
            pos += 24 + size

    def walk_temp(self, pl, pi, blob, pos, end, edid, cellkey):
        while pos + 24 <= end:
            typ, size, flags, fid, vc, ver, unk = HDR.unpack_from(blob, pos)
            if typ == b'GRUP':
                pos += max(size, 24)
                continue
            if typ == b'LAND':
                key = (edid, pl.formkey(fid))
                h = None
                why = 'ok'
                if flags & F_DELETED:
                    why = 'deleted'
                else:
                    try:
                        body = body_of(blob, pos, size, flags)
                        for st, sd in tes5.iter_subrecords(body):
                            if st == b'VHGT' and len(sd) >= 4 + 1089:
                                h = decode_vhgt(sd)
                                break
                        else:
                            why = 'no VHGT'
                    except zlib.error as e:
                        why = 'zlib %s' % e
                self.land_hist.setdefault(key, []).append((pi, why))
                if h is not None:
                    self.land[key] = (cellkey, h, pi)
                    self.stats[pl.name]['land'] += 1
                else:
                    self.stats[pl.name]['land_skipped'] += 1
                    self.errors.append('%s LAND %08X in %s: %s (earlier record kept)' % (pl.name, fid, edid, why))
            pos += 24 + size


def main():
    t0 = time.time()
    mods, active, order = read_profile(ROOT, PROFILE)
    idx = plugin_index(ROOT, mods)
    c = Collector()
    names, missing, n_wrld = [], [], 0
    base = ('skyrim.esm', 'update.esm', 'dawnguard.esm', 'hearthfires.esm', 'dragonborn.esm')
    for name in order:
        ln = name.lower()
        if ln not in active and ln not in base:
            continue
        path = idx.get(ln)
        if not path:
            missing.append(name)
            continue
        pl = tes5.Plugin(path, name)
        pi = len(names)
        names.append(name)
        with open(path, 'rb') as f:
            hdr = f.read(24)
            if hdr[:4] != b'TES4':
                c.errors.append('%s: not TES4' % name)
                continue
            typ, size, flags, fid, vc, ver, unk = HDR.unpack(hdr)
            pl.flags = flags
            body = f.read(size)
            for st, sd in tes5.iter_subrecords(body):
                if st == b'MAST':
                    pl.masters.append(tes5.zstr(sd))
            while True:
                pos = f.tell()
                gh = f.read(24)
                if len(gh) < 24:
                    break
                if gh[:4] != b'GRUP':
                    c.errors.append('%s: expected GRUP at %d' % (name, pos))
                    break
                gsize, label, gtype = struct.unpack_from('<I4sI', gh, 4)
                if gtype == 0 and label == b'WRLD':
                    blob = f.read(gsize - 24)
                    c.stats[name] = {'cells': 0, 'land': 0, 'land_skipped': 0}
                    n_wrld += 1
                    c.walk_wrld_top(pl, pi, blob)
                    del blob
                else:
                    f.seek(pos + gsize)
    print('active plugins in load order parsed %d (with WRLD group %d), missing %d, %.1fs' % (len(names), n_wrld, len(missing), time.time() - t0))
    for m in missing:
        print('  MISSING active plugin file:', m)
    print('errors/skips:', len(c.errors))
    for e in c.errors[:60]:
        print('  ERR', e)
    print('DNAM', c.ws_dnam.get('tamriel'), c.ws_dnam.get('markarthworld'))
    for edid in sorted(TARGETS):
        cells, heights, src, landkeys = {}, [], [], []
        alts = []
        dup = []
        for (e, lk), (ck, h, pi) in c.land.items():
            if e != edid:
                continue
            g = c.cell_grid.get((e, ck))
            if g is None:
                print('  no XCLC grid for LAND', lk, 'cell', ck)
                continue
            if g in cells:
                k = cells[g]
                dup.append((g, lk, names[pi], landkeys[k], names[src[k]]))
                if pi >= src[k]:
                    alts.append((g, heights[k], names[src[k]]))
                    heights[k] = h; src[k] = pi; landkeys[k] = lk
                else:
                    alts.append((g, h, names[pi]))
                continue
            cells[g] = len(heights)
            heights.append(h); src.append(pi); landkeys.append(lk)
        print(edid, 'cells with LAND:', len(cells), 'cells with two different LAND forms:', len(dup))
        for d in dup[:30]:
            print('   DUP', d)
        xy = np.array(sorted(cells, key=lambda g: cells[g]), np.int32).reshape(-1, 2)
        np.savez_compressed('land_%s.npz' % edid, cells=xy, heights=np.array(heights, np.float32),
                            src=np.array(src, np.int32), names=np.array(names),
                            alt_cells=np.array([a[0] for a in alts], np.int32).reshape(-1, 2), alt_heights=np.array([a[1] for a in alts], np.float32).reshape(-1, 33, 33), alt_names=np.array([a[2] for a in alts]),
                            dnam=np.array(c.ws_dnam.get(edid, (np.nan, np.nan, ''))[:2], np.float32))
        cnt = {}
        for pi in src:
            cnt[names[pi]] = cnt.get(names[pi], 0) + 1
        print('  winning LAND by plugin:')
        for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
            print('    %5d  %s' % (v, k))
        nover = sum(1 for (e, lk), hist in c.land_hist.items() if e == edid and len(hist) > 1)
        print('  LAND forms present in more than one plugin:', nover)
    print('plugins with Tamriel/Markarth LAND records:')
    for k, v in c.stats.items():
        if v['land'] or v['land_skipped']:
            print('   ', k, v)
    print('done %.1fs' % (time.time() - t0))


main()

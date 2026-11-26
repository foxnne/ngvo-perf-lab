"""Parse active plugins (read-only) for the outfit audit -> results/outfit_audit/cache/records.pkl

Records kept (last loaded override wins, override chain kept for ARMO/ARMA):
  ARMO, ARMA, OTFT, LVLI, RACE, TXST, FLST(only for skin swap lists), NPC_ (EDID/race/skin/outfits only)
  plus EDID -> formkey maps for item types used by SPID Item/Outfit/Skin lines.
Form keys are (local id, origin plugin lower).
"""
import os, pickle, struct, sys, time, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tes5, vfs  # noqa: E402
from tes5 import iter_subrecords, zstr

ITEMISH = {b'WEAP', b'AMMO', b'MISC', b'ALCH', b'BOOK', b'INGR', b'SLGM', b'SCRL', b'KEYM', b'LIGH', b'SPEL'}
WANT = {b'ARMO', b'ARMA', b'OTFT', b'LVLI', b'RACE', b'TXST', b'FLST', b'NPC_', b'KYWD'} | ITEMISH
BASE = {'skyrim.esm', 'update.esm', 'dawnguard.esm', 'hearthfires.esm', 'dragonborn.esm'}


def fk(pl, x):
    return pl.formkey(x)


def dec_arma(pl, body):
    r = {'edid': None, 'slots': 0, 'race': None, 'extra_races': [], 'male_model': None, 'female_model': None,
         'male_1st': None, 'female_1st': None, 'dnam': None, 'skin_m': None, 'skin_f': None, 'swap_m': None,
         'swap_f': None, 'alt_tex': [], 'bod_src': None}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st in (b'BOD2', b'BODT') and len(sd) >= 4:
            r['slots'] = struct.unpack_from('<I', sd)[0]; r['bod_src'] = st.decode()
        elif st == b'RNAM' and len(sd) >= 4:
            r['race'] = fk(pl, struct.unpack_from('<I', sd)[0])
        elif st == b'MODL' and len(sd) == 4:
            r['extra_races'].append(fk(pl, struct.unpack('<I', sd)[0]))
        elif st == b'MOD2':
            r['male_model'] = zstr(sd)
        elif st == b'MOD3':
            r['female_model'] = zstr(sd)
        elif st == b'MOD4':
            r['male_1st'] = zstr(sd)
        elif st == b'MOD5':
            r['female_1st'] = zstr(sd)
        elif st == b'DNAM' and len(sd) >= 4:
            r['dnam'] = tuple(sd[:4])
        elif st in (b'NAM0', b'NAM1', b'NAM2', b'NAM3') and len(sd) >= 4:
            key = {b'NAM0': 'skin_m', b'NAM1': 'skin_f', b'NAM2': 'swap_m', b'NAM3': 'swap_f'}[st]
            v = struct.unpack_from('<I', sd)[0]
            r[key] = fk(pl, v) if v else None
        elif st in (b'MO2S', b'MO3S', b'MO4S', b'MO5S') and len(sd) >= 4:
            n = struct.unpack_from('<I', sd)[0]; p = 4
            for _ in range(min(n, 64)):
                if p + 4 > len(sd):
                    break
                ln = struct.unpack_from('<I', sd, p)[0]; p += 4
                nm = sd[p:p + ln].decode('latin1'); p += ln
                if p + 8 > len(sd):
                    break
                tx, idx = struct.unpack_from('<Ii', sd, p); p += 8
                r['alt_tex'].append((st.decode(), nm, fk(pl, tx) if tx else None, idx))
    return r


def dec_lvli(pl, body):
    r = {'edid': None, 'entries': []}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st == b'LVLO' and len(sd) >= 8:
            r['entries'].append(fk(pl, struct.unpack_from('<I', sd, 4)[0]))
    return r


def dec_race(pl, body):
    r = {'edid': None, 'playable': False, 'armor_race': None, 'skin': None, 'full': None}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st == b'FULL' and not pl.localized:
            r['full'] = zstr(sd)
        elif st == b'DATA' and len(sd) >= 36 and r.get('_data') is None:
            r['_data'] = 1
            r['playable'] = bool(struct.unpack_from('<I', sd, 32)[0] & 1)
        elif st == b'RNAM' and len(sd) >= 4 and r['armor_race'] is None:
            r['armor_race'] = fk(pl, struct.unpack_from('<I', sd)[0])
        elif st == b'WNAM' and len(sd) >= 4 and r['skin'] is None:
            r['skin'] = fk(pl, struct.unpack_from('<I', sd)[0])
    r.pop('_data', None)
    return r


def dec_txst(pl, body):
    r = {'edid': None, 'tex': {}}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st[:2] == b'TX' and st[2:].isdigit():
            r['tex'][st.decode()] = zstr(sd)
    return r


def dec_flst(pl, body):
    r = {'edid': None, 'items': []}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st == b'LNAM' and len(sd) >= 4:
            r['items'].append(fk(pl, struct.unpack_from('<I', sd)[0]))
    return r


def dec_npc(pl, body):
    r = {'edid': None, 'race': None, 'skin': None, 'doft': None, 'soft': None, 'female': False}
    for st, sd in iter_subrecords(body):
        if st == b'EDID':
            r['edid'] = zstr(sd)
        elif st == b'ACBS' and len(sd) >= 4:
            r['female'] = bool(struct.unpack_from('<I', sd)[0] & 1)
        elif st == b'RNAM' and len(sd) >= 4:
            r['race'] = fk(pl, struct.unpack_from('<I', sd)[0])
        elif st == b'WNAM' and len(sd) >= 4:
            r['skin'] = fk(pl, struct.unpack_from('<I', sd)[0])
        elif st == b'DOFT' and len(sd) >= 4:
            r['doft'] = fk(pl, struct.unpack_from('<I', sd)[0])
        elif st == b'SOFT' and len(sd) >= 4:
            r['soft'] = fk(pl, struct.unpack_from('<I', sd)[0])
    return r


def main():
    t0 = time.time()
    v = vfs.load()
    plugins, problems = [], []
    full_i = light_i = 0
    for name in v['plugins_in_order']:
        ln = name.lower()
        hit = v['roots'].get(ln)
        if not hit:
            problems.append((name, 'active plugin file not found'))
            continue
        si, real = hit
        pl = tes5.Plugin(os.path.join(v['sources'][si][1], real), name)
        pl.source = v['sources'][si][0]
        try:
            pl.load(WANT)
        except Exception as e:  # noqa
            problems.append((name, 'parse failure %r' % (e,)))
            continue
        pl.errors and problems.extend((name, e) for e in pl.errors)
        if pl.is_light:
            pl.load_index = 'FE%03X' % light_i; light_i += 1
        else:
            pl.load_index = '%02X' % full_i; full_i += 1
        plugins.append(pl)
    print('parsed %d plugins %.0fs' % (len(plugins), time.time() - t0), flush=True)
    loaded = {p.lname for p in plugins}
    out = {k: {} for k in ('ARMO', 'ARMA', 'OTFT', 'LVLI', 'RACE', 'TXST', 'FLST', 'NPC_', 'KYWD')}
    chain = {'ARMO': {}, 'ARMA': {}}
    edid = {}            # (type, edid lower) -> formkey
    exists = set()       # formkeys of any parsed record type
    types = {}           # formkey -> type
    missing_masters = []
    for pl in plugins:
        for m in pl.masters:
            if m.lower() not in loaded:
                missing_masters.append((pl.name, m))
        for gt, recs in pl.records.items():
            t = gt.decode()
            for fid, fl, body in recs:
                k = pl.formkey(fid)
                exists.add(k); types[k] = t
                try:
                    if t == 'ARMO':
                        r = tes5.decode_armo(pl, fid, fl, body)
                    elif t == 'ARMA':
                        r = dec_arma(pl, body)
                    elif t == 'OTFT':
                        r = tes5.decode_otft(pl, fid, fl, body)
                    elif t == 'LVLI':
                        r = dec_lvli(pl, body)
                    elif t == 'RACE':
                        r = dec_race(pl, body)
                    elif t == 'TXST':
                        r = dec_txst(pl, body)
                    elif t == 'FLST':
                        r = dec_flst(pl, body)
                    elif t == 'NPC_':
                        r = dec_npc(pl, body)
                    else:
                        e = tes5.decode_edid(body)
                        if e:
                            edid[(t, e.lower())] = k
                        if t == 'KYWD':
                            out['KYWD'][k] = e
                        continue
                except Exception as e:  # noqa
                    problems.append((pl.name, '%s %08X decode %r' % (t, fid, e)))
                    continue
                r['_plugin'] = pl.name
                r['_deleted'] = bool(fl & 0x20)
                out[t][k] = r
                if t in chain:
                    chain[t].setdefault(k, []).append(pl.name)
                if r.get('edid'):
                    edid[(t, r['edid'].lower())] = k
        pl.records = None
    meta = {p.lname: {'name': p.name, 'light': p.is_light, 'index': p.load_index, 'source': p.source,
                      'masters': p.masters, 'localized': p.localized} for p in plugins}
    d = {'rec': out, 'chain': chain, 'edid': edid, 'exists': exists, 'types': types, 'plugins': meta,
         'problems': problems, 'missing_masters': missing_masters}
    pickle.dump(d, open(os.path.join(vfs.CACHE, 'records.pkl'), 'wb'), protocol=4)
    print({k: len(x) for k, x in out.items()}, 'problems', len(problems), '%.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()

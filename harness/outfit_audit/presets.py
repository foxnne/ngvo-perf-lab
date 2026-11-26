"""Black-skin helper (read-only): check every RaceMenu preset (.jslot) in the VFS for texture / mesh paths
that no mod provides. RaceMenu applies jslot texture overrides to the body, hands and face; a missing
override texture renders the part black. Also checks the Nyr asset meshes' own texture paths.
Appends to results/outfit_audit/findings.csv rows with category black_skin.
Usage: python -I presets.py   (run after audit.py)
"""
import csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vfs, nifread  # noqa: E402

RES = os.path.join(HERE, '..', '..', 'results', 'outfit_audit')
V = vfs.load()
rows = []


def walk(o, out):
    if isinstance(o, dict):
        for v in o.values():
            walk(v, out)
    elif isinstance(o, list):
        for v in o:
            walk(v, out)
    elif isinstance(o, str) and re.search(r'\.(dds|nif)$', o, re.I):
        out.add(o)


for rel, provs in V['loose'].items():
    if not rel.endswith('.jslot'):
        continue
    si, real = provs[0][0], provs[0][1]
    mod = V['sources'][si][0]
    path = os.path.join(V['sources'][si][1], real)
    try:
        j = json.load(open(path, encoding='utf-8', errors='replace'))
    except Exception as e:  # noqa
        rows.append(('low', 'black_skin', 'jslot_unreadable', os.path.basename(rel), mod, rel, 'preset JSON does not parse: %r' % e))
        continue
    paths = set()
    walk(j, paths)
    for p in sorted(paths):
        q = vfs.norm(p)
        if q.endswith('.dds'):
            ok = vfs.tex_exists(q)
        else:
            ok = bool(vfs.find(q if q.startswith('meshes\\') else 'meshes\\' + q))
        if not ok:
            part = 'hands' if 'hand' in q else ('body' if 'body' in q else ('head' if 'head' in q or 'face' in q else 'other'))
            rows.append(('high' if part in ('hands', 'body') else 'medium', 'black_skin', 'jslot_missing_asset',
                         os.path.basename(rel), mod, rel, 'RaceMenu preset applies %s (%s) which no mod provides; the part renders black if this preset is used' % (p, part)))

# meshes shipped by asset packs that presets point at
for rel in list(V['loose']):
    if rel.startswith('meshes\\nyr\\') and rel.endswith('.nif'):
        d = nifread.parse(vfs.read(rel))
        for s in d['shapes']:
            for i, t in enumerate(s.get('textures') or []):
                if t and i in (0, 1) and not vfs.tex_exists(t):
                    rows.append(('high', 'black_skin', 'asset_mesh_texture_missing', os.path.basename(rel), vfs.find(rel)[1], rel,
                                 'shape %r slot %d texture %s missing' % (s['name'], i, t)))

out = os.path.join(RES, 'findings.csv')
cols = ['severity', 'category', 'check', 'outfit', 'form', 'plugin', 'mod', 'file', 'issue', 'detail', 'fix_route']
with open(out, 'a', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, cols)
    for sev, cat, chk, who, mod, f, issue in rows:
        w.writerow({'severity': sev, 'category': cat, 'check': chk, 'outfit': who, 'mod': mod, 'file': f, 'issue': issue,
                    'fix_route': 'install the missing asset pack files or edit the preset (agent)'})
print('preset findings', len(rows))
for r in rows[:25]:
    print(r)

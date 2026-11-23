"""Queue job: put plugins at exact positions (game and MO2 closed). Backs up plugins.txt and loadorder.txt.
usage: python plugin_order_job.py TAG SPEC.json
SPEC: {"insert_after": [["Anchor.esp", "New.esp", ...], ...], "append": ["Last.esp", ...], "deactivate": ["Old.esp", ...]}"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
spec = json.load(open(sys.argv[2])); P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/'
for fname, active_mark in (('plugins.txt', '*'), ('loadorder.txt', '')):
    p = P + fname; shutil.copy2(p, p + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
    raw = open(p, 'rb').read(); nl = '\r\n' if b'\r\n' in raw else '\n'; L = [l for l in raw.decode('utf-8-sig').split(nl) if l.strip()]
    name = lambda l: l.lstrip('*').strip().lower()
    deact = [d.lower() for d in spec.get('deactivate', [])]
    if fname == 'plugins.txt': L = [(l.lstrip('*') if name(l) in deact else l) for l in L]
    new = set(n.lower() for g in spec.get('insert_after', []) for n in g[1:]) | set(n.lower() for n in spec.get('append', []))
    L = [l for l in L if name(l) not in new]
    for g in spec.get('insert_after', []):
        idx = [i for i, l in enumerate(L) if name(l) == g[0].lower()]
        if not idx: sys.exit('anchor not found in %s: %s' % (fname, g[0]))
        L[idx[0] + 1:idx[0] + 1] = [active_mark + n for n in g[1:]]
    L += [active_mark + n for n in spec.get('append', [])]
    open(p, 'wb').write((nl.join(L) + nl).encode('utf-8')); print(fname, 'ok', len(L), 'lines', flush=True)

"""Queue job: install / enable / disable MO2 mods WITHOUT moving mods that are already listed (game and MO2 closed).
enable_mod.py moves a mod to the top of the list; this job keeps positions, so switching a set of mods off and on
again restores exactly the priorities they had. Backs up modlist.txt.
usage: python mod_state_job.py TAG SPEC.json
SPEC: {"install": [["SRC_DIR", "Mod Name"], ...],                 copy SRC_DIR to mods/Mod Name if that folder is missing
       "above":   "Anchor Mod Name",                                where mods not yet listed go: directly above the anchor
                                                                    (= higher priority); the first entry of "enable" ends highest
       "enable":  ["Mod Name", ...],                                '+', in place if listed, else inserted above the anchor
       "disable": ["Mod Name", ...]}                                '-', in place; a mod that is not listed is skipped"""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
spec = json.load(open(sys.argv[2])); ROOT = 'C:/Modlists/NGVO 8.0 Beta/'; P = ROOT + 'profiles/foxnne-nsfw/modlist.txt'
for src, name in spec.get('install', []):
    dst = ROOT + 'mods/' + name
    if os.path.isdir(dst): print('already installed:', name, flush=True); continue
    if not os.path.isdir(src): sys.exit('missing source folder: ' + src)
    shutil.copytree(src, dst); print('installed:', name, flush=True)
for name in spec.get('enable', []):
    if not os.path.isdir(ROOT + 'mods/' + name): sys.exit('no such mod folder: ' + name)
shutil.copy2(P, P + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
raw = open(P, 'rb').read(); nl = '\r\n' if b'\r\n' in raw else '\n'; L = raw.decode('utf-8-sig').split(nl)
find = lambda name: [i for i, l in enumerate(L) if l[:1] in '+-' and l[1:] == name]
for name in spec.get('enable', []):
    idx = find(name)
    if idx: L[idx[0]] = '+' + name; print('enabled in place:', name)
    else:
        a = find(spec.get('above', ''))
        if not a: sys.exit('anchor not in modlist: %r' % spec.get('above'))
        L.insert(a[0], '+' + name); print('enabled above %s: %s' % (spec['above'], name))
for name in spec.get('disable', []):
    idx = find(name)
    if idx: L[idx[0]] = '-' + name; print('disabled in place:', name)
    else: print('not listed, skipped:', name)
open(P, 'wb').write(nl.join(L).encode()); print('modlist ok', flush=True)

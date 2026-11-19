"""Compare the old install C:/Modlists/NGVO with NGVO 8.0 Beta (read-only). Writes audit/old_install_diff.tsv
columns: class, sizeMB, files, modid, version, enabled_in_old_profiles, name, installationFile
class: SAME (same folder name in new) | NEXUS (not in new, has a Nexus mod id) | LOCAL (not in new, no Nexus id) | SEP (separator)"""
import configparser, ctypes, os, re
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00100000)
OLD = 'C:/Modlists/NGVO'; NEW = 'C:/Modlists/NGVO 8.0 Beta'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audit', 'old_install_diff.tsv')
new = {n.lower() for n in os.listdir(NEW + '/mods')}
new_ids = {}
for n in os.listdir(NEW + '/mods'):
    try:
        t = open(f'{NEW}/mods/{n}/meta.ini', encoding='utf-8', errors='ignore').read()
        m = re.search(r'(?m)^modid=(\d+)', t)
        if m and int(m[1]) > 0: new_ids.setdefault(int(m[1]), n)
    except OSError: pass
enabled = {}
for prof in os.listdir(OLD + '/profiles'):
    try:
        for l in open(f'{OLD}/profiles/{prof}/modlist.txt', encoding='utf-8-sig', errors='ignore'):
            if l.startswith('+'): enabled.setdefault(l[1:].strip().lower(), []).append(prof)
    except OSError: pass


def size(p):
    s = n = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try: s += os.path.getsize(os.path.join(dp, f)); n += 1
            except OSError: pass
    return s, n


rows = []
for name in sorted(os.listdir(OLD + '/mods')):
    p = f'{OLD}/mods/{name}'
    if not os.path.isdir(p): continue
    modid = 0; version = ''; inst = ''
    try:
        t = open(p + '/meta.ini', encoding='utf-8', errors='ignore').read()
        m = re.search(r'(?m)^modid=(-?\d+)', t); modid = int(m[1]) if m else 0
        m = re.search(r'(?m)^version=(.*)', t); version = m[1].strip() if m else ''
        m = re.search(r'(?m)^installationFile=(.*)', t); inst = os.path.basename(m[1].strip()) if m else ''
    except OSError: pass
    if name.endswith('_separator'): cls = 'SEP'
    elif name.lower() in new: cls = 'SAME'
    elif modid > 0: cls = 'NEXUS_IN_NEW_AS:' + new_ids[modid] if modid in new_ids else 'NEXUS'
    else: cls = 'LOCAL'
    s, n = size(p) if cls != 'SAME' and cls != 'SEP' else (0, 0)
    rows.append((cls, s // 1000000, n, modid, version, ','.join(enabled.get(name.lower(), [])), name, inst))
with open(OUT, 'w', encoding='utf-8') as f:
    for r in rows: f.write('\t'.join(str(x) for x in r) + '\n')
import collections
c = collections.Counter(r[0].split(':')[0] for r in rows); sz = collections.Counter()
for r in rows: sz[r[0].split(':')[0]] += r[1]
print(dict(c)); print({k: f'{v / 1000:.1f} GB' for k, v in sz.items()})
print('old profiles:', os.listdir(OLD + '/profiles'))

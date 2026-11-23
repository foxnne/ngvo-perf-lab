"""Queue job (game closed): set ini keys, backing up each file once per run.
usage: python ini_set_job.py TAG "path|section|key|value" ["path|section|key|value" ...]   (path relative to the instance)"""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
R = 'C:/Modlists/NGVO 8.0 Beta'; STAMP = time.strftime('%Y%m%d-%H%M%S'); backed = set()
for spec in sys.argv[2:]:
    rel, section, key, value = spec.split('|'); path = R + '/' + rel
    if path not in backed: shutil.copy2(path, path + '.bak-pre-' + sys.argv[1] + '-' + STAMP); backed.add(path)
    raw = open(path, 'rb').read(); bom = raw.startswith(b'\xef\xbb\xbf'); nl = '\r\n' if b'\r\n' in raw else '\n'
    L = raw.decode('utf-8-sig').split(nl); sec = None; done = False
    for i, l in enumerate(L):
        s = l.strip()
        if s.startswith('[') and s.endswith(']'): sec = s[1:-1].lower(); continue
        if sec == section.lower() and re.match(r'\s*%s\s*=' % re.escape(key), l, re.I):
            L[i] = re.sub(r'=.*$', ('= ' if ' = ' in l else '=') + value, l); done = True; break
    if not done:
        idx = [i for i, l in enumerate(L) if l.strip().lower() == '[%s]' % section.lower()]
        if idx: L.insert(idx[0] + 1, '%s=%s' % (key, value))
        else: L += ['[%s]' % section, '%s=%s' % (key, value)]
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + nl.join(L).encode('utf-8'))
    print(rel, section, key, '->', value, '(added)' if not done else '', flush=True)

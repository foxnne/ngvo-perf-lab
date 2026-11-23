"""Queue job: set one key in a profile ini (game and MO2 closed). usage: python set_ini.py Section Key Value [skyrim.ini|skyrimprefs.ini|skyrimcustom.ini]"""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
sec, key, val = sys.argv[1:4]; FILE = sys.argv[4] if len(sys.argv) > 4 else 'skyrim.ini'
if FILE.lower() not in ('skyrim.ini', 'skyrimprefs.ini', 'skyrimcustom.ini'): sys.exit('unknown ini: ' + FILE)
P = 'C:/Modlists/NGVO 8.0 Beta/profiles/foxnne-nsfw/' + FILE
shutil.copy2(P, P + '.bak-' + time.strftime('%Y%m%d-%H%M%S'))
raw = open(P, 'rb').read(); nl = b'\r\n' if b'\r\n' in raw else b'\n'; t = raw.decode('utf-8-sig', 'replace')
m = re.search(r'(?im)^\[' + re.escape(sec) + r'\]\s*$', t)
if not m: sys.exit('section not found')
end = re.search(r'(?m)^\[', t[m.end():]); a, b = m.end(), (m.end() + end.start() if end else len(t))
body, n = re.subn(r'(?im)^(' + re.escape(key) + r'\s*=\s*)[^\r\n]*', lambda x: x.group(1) + val, t[a:b])
if n == 0: body = nl.decode() + key + '=' + val + body
open(P, 'wb').write((t[:a] + body + t[b:]).encode('utf-8')); print('set [%s] %s=%s (%s)' % (sec, key, val, 'changed' if n else 'added'))

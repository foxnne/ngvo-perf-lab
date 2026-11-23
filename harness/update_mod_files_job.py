"""Queue job (game and MO2 closed): copy a staged folder over an installed mod (backup of replaced files), set meta version.
usage: python update_mod_files_job.py TAG STAGED_DIR "Mod Name" VERSION"""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
if bench.mo2_running(): bench.close_mo2(); time.sleep(5)
tag, src, name, ver = sys.argv[1:5]; dst = 'C:/Modlists/NGVO 8.0 Beta/mods/' + name
bk = 'C:/Users/foxnn/dev/mod-backups/%s-%s' % (re.sub(r'[^A-Za-z0-9]+', '_', name), time.strftime('%Y%m%d-%H%M%S'))
for r, _, fs in os.walk(src):
    for f in fs:
        s = os.path.join(r, f); rel = os.path.relpath(s, src); d = os.path.join(dst, rel)
        if os.path.exists(d): os.makedirs(os.path.dirname(os.path.join(bk, rel)), exist_ok=True); shutil.copy2(d, os.path.join(bk, rel))
        os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s, d); print('updated', rel, flush=True)
mp = dst + '/meta.ini'
if os.path.exists(mp):
    m = open(mp, encoding='utf-8', errors='replace').read(); open(mp, 'w', encoding='utf-8').write(re.sub(r'(?m)^version=.*$', 'version=' + ver, m))
print('backup of replaced files:', bk, flush=True)

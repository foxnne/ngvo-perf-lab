"""Queue job (game closed): switch the installed No Grass In Objects NG DLL to another version from the downloads folder.
The current DLL/PDB are kept in C:/Modlists/backups/ngio-<version-tag>/ the first time. GrassControl.ini is not touched.
usage: python ngio_version.py 2.1.2 | 1.6.14 | 2.0.2 (restore the original)"""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time as _t
for _i in range(30):
    if not bench.running(): break
    _t.sleep(4)
else: sys.exit('game open')
I = 'C:/Modlists/NGVO 8.0 Beta'; DST = I + '/mods/No Grass In Objects/SKSE/Plugins'; BK = 'C:/Modlists/backups/ngio-2.0.2-original'
ARCH = {'2.1.2': 'NGIO - NG 42161 2.1.2 2026-11-19T20-04Z Sx9oEfolX.7z', '1.6.14': 'NGIO - NG (1.6.14) 42161 1.6.14 2026-08-31T05-33Z QRde31FdL.7z'}
v = sys.argv[1]
if not os.path.exists(BK):
    os.makedirs(BK)
    for f in os.listdir(DST): shutil.copy2(os.path.join(DST, f), os.path.join(BK, f))
for f in os.listdir(DST): os.remove(os.path.join(DST, f))
if v == '2.0.2':
    for f in os.listdir(BK): shutil.copy2(os.path.join(BK, f), os.path.join(DST, f))
else:
    tmp = os.path.join(os.environ['TEMP'], 'ngio_extract_' + v.replace('.', '_'))
    if os.path.exists(tmp): shutil.rmtree(tmp)
    r = subprocess.run(['C:/Program Files/7-Zip/7z.exe', 'x', '-y', '-o' + tmp, I + '/downloads/' + ARCH[v]], capture_output=True, text=True)
    if r.returncode: sys.exit(r.stdout[-400:])
    src = os.path.join(tmp, 'SKSE', 'Plugins')
    for f in os.listdir(src): shutil.copy2(os.path.join(src, f), os.path.join(DST, f))
    shutil.rmtree(tmp)
print('NGIO now', v, ':', {f: os.path.getsize(os.path.join(DST, f)) for f in os.listdir(DST)})

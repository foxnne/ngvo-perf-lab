"""Queue job (game and MO2 closed): FFF forest grass for forest cells only.
1. install mod 'foxnne - FFF Forest Grass' with the FULL plugin (LFieldGrass02 -> FFF list + 15 GRAS), plugin right before DynDOLOD.esp
2. FasterNGIO (same args as grass_cache_job: smooth placement) through MO2 into C:/Modlists/_grasscache_forest/Grass
3. swap in the GRAS-only runtime plugin (same name, same form IDs)
4. new cache mod = current active 'foxnne - Grass Cache *' with the forest cells (dev/forest-floor/reports/forest_cells.json) taken from the
   forest build; switch the modlist to it (old cache mod disabled, kept). Stops and restores the modlist on any failure before step 4."""
import json, os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
BS = chr(92); I = 'C:/Modlists/NGVO 8.0 Beta'; P = I + '/profiles/foxnne-nsfw'; FF = 'C:/Users/foxnn/dev/forest-floor'
MOD = 'foxnne - FFF Forest Grass'; ESP = MOD + '.esp'
FULL = FF + '/out/' + MOD; RUNTIME = FF + '/out/' + MOD + ' (runtime)'
OUT = 'C:/Modlists/_grasscache_forest/Grass'; INI = I + '/ModOrganizer.ini'; LNK = os.path.join(HERE, 'launch-fasterngio.lnk')
st = time.strftime('%Y%m%d-%H%M')
for f in ('modlist.txt', 'plugins.txt', 'loadorder.txt'): shutil.copy2(f'{P}/{f}', f'{P}/{f}.bak-forestcache-{st}')
def restore():
    for f in ('modlist.txt', 'plugins.txt', 'loadorder.txt'): shutil.copy2(f'{P}/{f}.bak-forestcache-{st}', f'{P}/{f}')
# 1. install full plugin
dst = I + '/mods/' + MOD
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(FULL, dst)
open(dst + '/meta.ini', 'w').write('[General]\ngameName=SkyrimSE\nmodid=0\nversion=1.0\ncomments=FFF LFieldGrass02 grass records for forest cells (GRAS only at runtime). dev/forest-floor\n')
L = open(f'{P}/modlist.txt', encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[0].endswith('\r') else ''
if not any(l.rstrip('\r')[1:] == MOD for l in L):
    i = [k for k, l in enumerate(L) if l.rstrip('\r') == '+foxnne - FFF Pine Forest'][0]; L.insert(i, '+' + MOD + cr)
    open(f'{P}/modlist.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))
for f, star in (('plugins.txt', True), ('loadorder.txt', False)):
    L = open(f'{P}/{f}', encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[0].endswith('\r') else ''
    L = [l for l in L if l.rstrip('\r').lstrip('*') != ESP]
    i = [k for k, l in enumerate(L) if l.rstrip('\r').lstrip('*') == 'DynDOLOD.esp'][0]; L.insert(i, ('*' if star else '') + ESP + cr)
    open(f'{P}/{f}', 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('installed full plugin', flush=True)
# 2. FasterNGIO
def set_args(value):
    t = open(INI, 'rb').read().decode('utf-8', 'replace')
    m = re.search('(?m)^([0-9]+)' + BS + BS + 'title=FasterNGIO[ \t\r]*$', t); key = m.group(1) + BS + 'arguments='
    lines = t.split('\n'); hit = [i for i, l in enumerate(lines) if l.startswith(key)]
    cr = '\r' if lines[hit[0]].endswith('\r') else ''; lines[hit[0]] = key + value + cr
    shutil.copy2(INI, INI + '.bak-forestcache'); open(INI, 'wb').write('\n'.join(lines).encode('utf-8'))
if os.path.isdir(os.path.dirname(OUT)): shutil.rmtree(os.path.dirname(OUT))
os.makedirs(OUT)
set_args('--out %s --world all --placement smooth --overwrite' % OUT)
ps = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s'); $s.TargetPath='%s'; $s.Arguments='moshortcut://FasterNGIO'; $s.WorkingDirectory='%s'; $s.Save()" % (
    LNK.replace('/', BS), (I + '/ModOrganizer.exe').replace('/', BS), I.replace('/', BS))
subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True)
subprocess.Popen(['explorer.exe', LNK.replace('/', BS)])
def running(): return 'FasterNGIO.exe' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FasterNGIO.exe'], capture_output=True, text=True).stdout
t0 = time.time(); seen = False
try:
    while time.time() - t0 < 2400:
        time.sleep(10); r = running(); seen = seen or r
        if seen and not r: break
        if not seen and time.time() - t0 > 180: break
finally:
    time.sleep(5); bench.close_mo2()
    if not bench.mo2_running(): set_args('')
files = os.listdir(OUT) if os.path.isdir(OUT) else []
tam = [f for f in files if f.lower().startswith('tamriel')]
print('forest build: %d files, %d Tamriel, %.0f s' % (len(files), len(tam), time.time() - t0), flush=True)
# 3. runtime plugin
shutil.copy2(RUNTIME + '/' + ESP, dst + '/' + ESP); print('runtime (GRAS-only) plugin in place', flush=True)
if len(tam) < 4000:
    restore(); sys.exit('forest cache looks incomplete: modlist restored (mod folder left, plugin removed)')
# 4. merge
ml = [l[1:].strip() for l in open(f'{P}/modlist.txt', encoding='utf-8-sig') if l.startswith('+')]
cur = next(m for m in ml if m.startswith('foxnne - Grass Cache '))
new = cur + ' forest'
src_dir = I + '/mods/' + cur + '/Grass'; new_dir = I + '/mods/' + new + '/Grass'
if os.path.exists(I + '/mods/' + new): shutil.rmtree(I + '/mods/' + new)
shutil.copytree(src_dir, new_dir)
cells = json.load(open(FF + '/reports/forest_cells.json')); n = 0; missing = 0
for c in cells:
    x, y = map(int, c.split(','))
    stem = 'Tamrielx%04dy%04d' % (x, y)
    hits = [f for f in tam if f.split('.')[0] == stem]
    if not hits: missing += 1
    for f in hits: shutil.copy2(OUT + '/' + f, new_dir + '/' + f); n += 1
print('merged %d forest cell files into %s (%d forest cells had no file)' % (n, new, missing), flush=True)
L = open(f'{P}/modlist.txt', encoding='utf-8-sig').read().split('\n'); cr = '\r' if L[0].endswith('\r') else ''
i = [k for k, l in enumerate(L) if l.rstrip('\r') == '+' + cur][0]; L[i] = '-' + cur + cr; L.insert(i, '+' + new + cr)
open(f'{P}/modlist.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('modlist switched:', cur, '->', new, flush=True)

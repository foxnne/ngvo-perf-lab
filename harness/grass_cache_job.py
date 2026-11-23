"""Queue job: rebuild the NGIO grass cache with FasterNGIO through Mod Organizer's virtual Data folder, into a NEW mod,
then switch the modlist to it (old cache mod disabled, kept on disk). Game and MO2 must be closed at start.

MO2 refuses (ERROR_ACCESS_DENIED) to spawn a hooked process when it is started from this shell (two failed tries on
2026-11-19), so the tool is started the way the game is: Explorer opens a shortcut to MO2's own 'FasterNGIO' executable
entry (moshortcut://FasterNGIO). The tool's arguments are put into that entry in ModOrganizer.ini and removed afterwards.
usage: python grass_cache_job.py TAG [--placement smooth|vanilla]"""
import os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
BS = chr(92)
INST = 'C:/Modlists/NGVO 8.0 Beta'; OLD = 'NGVO - Grass Cache'; NEW = 'foxnne - Grass Cache ' + time.strftime('%Y-%m-%d')
out = 'C:/Modlists/_grasscache_out/Grass'; final = INST + '/mods/' + NEW + '/Grass'   # no spaces: it goes into MO2's ini unquoted
INI = INST + '/ModOrganizer.ini'; LNK = os.path.join(HERE, 'launch-fasterngio.lnk')
placement = sys.argv[sys.argv.index('--placement') + 1] if '--placement' in sys.argv else 'smooth'
args = '--out %s --world all --placement %s --overwrite' % (out, placement)
if '--extra' in sys.argv: args += ' ' + sys.argv[sys.argv.index('--extra') + 1]
if os.path.isdir(os.path.dirname(out)): shutil.rmtree(os.path.dirname(out))
os.makedirs(out)


def set_args(value):
    t = open(INI, 'rb').read().decode('utf-8', 'replace')
    m = re.search('(?m)^([0-9]+)' + BS + BS + 'title=FasterNGIO[ \t\r]*$', t)
    if not m: sys.exit('no FasterNGIO entry in MO2 executables')
    key = m.group(1) + BS + 'arguments='
    lines = t.split('\n'); hit = [i for i, l in enumerate(lines) if l.startswith(key)]
    if len(hit) != 1: sys.exit('could not find the arguments line of the FasterNGIO entry')
    cr = '\r' if lines[hit[0]].endswith('\r') else ''
    lines[hit[0]] = key + value + cr
    shutil.copy2(INI, INI + '.bak-grasscache'); open(INI, 'wb').write('\n'.join(lines).encode('utf-8'))


def count(): return sum(1 for f in os.listdir(out) if f.lower().endswith('.cgid')) if os.path.isdir(out) else 0
def tool_running():
    return 'FasterNGIO.exe' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq FasterNGIO.exe'], capture_output=True, text=True).stdout


set_args(args)
ps = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s'); $s.TargetPath='%s'; $s.Arguments='moshortcut://FasterNGIO'; $s.WorkingDirectory='%s'; $s.Save()" % (
    LNK.replace('/', BS), (INST + '/ModOrganizer.exe').replace('/', BS), INST.replace('/', BS))
subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True)
print('starting FasterNGIO through MO2 (Explorer shortcut):', args, flush=True)
subprocess.Popen(['explorer.exe', LNK.replace('/', BS)])
t0 = time.time(); seen = False; last = (-1, time.time())
try:
    while time.time() - t0 < 2400:
        time.sleep(10); r = tool_running(); n = count()
        if r: seen = True
        if n != last[0] or int(time.time() - t0) % 60 < 10: print('  %4d s  tool %s  files %d' % (time.time() - t0, 'running' if r else 'not running', n), flush=True)
        if n != last[0]: last = (n, time.time())
        if seen and not r: break
        if not seen and time.time() - t0 > 180: print('the tool never started', flush=True); break
        if r and time.time() - last[1] > 900: print('no new files for 15 min: stopping the tool', flush=True); subprocess.run(['taskkill', '/IM', 'FasterNGIO.exe', '/F'], capture_output=True); break
finally:
    time.sleep(5); bench.close_mo2()
    if not bench.mo2_running(): set_args('')        # leave MO2's entry as it was
n = count(); files = os.listdir(out) if os.path.isdir(out) else []
size = sum(os.path.getsize(os.path.join(out, f)) for f in files) / 1e6; tam = sum(1 for f in files if f.lower().startswith('tamriel'))
print('result: %d cgid files (%d Tamriel), %.0f MB, %.0f s' % (n, tam, size, time.time() - t0), flush=True)
if tam < 4000 or size < 200:
    sys.exit('cache looks incomplete (old: 7,282 files, 5,570 Tamriel, 849 MB): modlist NOT changed; old cache stays active')
if bench.mo2_running(): sys.exit('MO2 still open: modlist NOT changed')
os.makedirs(os.path.dirname(final), exist_ok=True)
if os.path.isdir(final): shutil.rmtree(final)
shutil.move(out, final); print('moved to', final, flush=True)
rc = subprocess.call([sys.executable, os.path.join(HERE, 'enable_mod.py'), NEW]); print('enable', NEW, 'rc', rc, flush=True)
if rc: sys.exit('modlist switch failed at enable')
ML = INST + '/profiles/foxnne-nsfw/modlist.txt'
olds = [l[1:].strip() for l in open(ML, encoding='utf-8-sig') if l.startswith('+') and (l[1:].strip() == OLD or l[1:].strip().startswith('foxnne - Grass Cache ')) and l[1:].strip() != NEW]
for o in olds:
    rc = subprocess.call([sys.executable, os.path.join(HERE, 'disable_mod.py'), 'grasscache', o]); print('disable', o, 'rc', rc, flush=True)
    if rc: sys.exit('modlist switch failed at disable ' + o)
print('grass cache switched to', NEW, flush=True)

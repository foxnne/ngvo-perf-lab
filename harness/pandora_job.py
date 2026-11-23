"""Queue job (game and MO2 closed): update Pandora Behaviour Engine+ and regenerate the behaviour output.
1. Back up the tool mod and the output mod (C:/Users/foxnn/dev/pandora-backup/<stamp>/).
2. Copy the new tool files (staged folder) over `mods/Pandora Behaviour Engine Plus` (meta.ini kept, version updated).
3. Pre-fill C:/Modlists/_pandora_out with the current output (keeps Pandora's saved patch selection), run Pandora through
   MO2 (Explorer + moshortcut, like grass_cache_job) with --auto_run --auto_close --output:<that folder>.
4. On success (Engine.log written, no ERROR/FATAL lines, behaviour files present) swap the folder into
   `mods/NGVO - Pandora Output (NSFW)`; otherwise leave the old output in place.
usage: python pandora_job.py TAG STAGED_DIR VERSION"""
import os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
if bench.mo2_running(): bench.close_mo2(); time.sleep(5)
if bench.mo2_running(): sys.exit('Mod Organizer would not close')
TAG, STAGED, VERSION = sys.argv[1], sys.argv[2], sys.argv[3]
BS = chr(92); INST = 'C:/Modlists/NGVO 8.0 Beta'; INI = INST + '/ModOrganizer.ini'
TOOL = INST + '/mods/Pandora Behaviour Engine Plus'; OUTMOD = INST + '/mods/NGVO - Pandora Output (NSFW)'
OUT = 'C:/Modlists/_pandora_out'; LNK = os.path.join(HERE, 'launch-pandora.lnk'); TITLE = 'Pandora Behaviour Engine+'
BK = 'C:/Users/foxnn/dev/pandora-backup/' + time.strftime('%Y%m%d-%H%M%S')
os.makedirs(BK); shutil.copytree(TOOL, BK + '/tool'); shutil.copytree(OUTMOD, BK + '/output'); print('backed up to', BK, flush=True)
for name in ([] if '--no-install' in sys.argv else os.listdir(STAGED)):
    s, d = os.path.join(STAGED, name), os.path.join(TOOL, name)
    if os.path.isdir(s):
        if os.path.isdir(d): shutil.rmtree(d)
        shutil.copytree(s, d)
    else: shutil.copy2(s, d)
m = open(TOOL + '/meta.ini', encoding='utf-8').read(); m = re.sub(r'(?m)^version=.*$', 'version=' + VERSION, m); open(TOOL + '/meta.ini', 'w', encoding='utf-8').write(m)
print('tool updated to', VERSION, flush=True)
if os.path.isdir(OUT): shutil.rmtree(OUT)
shutil.copytree(OUTMOD, OUT); start_log = os.path.getmtime(OUT + '/Engine.log') if os.path.exists(OUT + '/Engine.log') else 0
def set_args(value):
    t = open(INI, 'rb').read().decode('utf-8', 'replace')
    mm = re.search('(?m)^([0-9]+)' + BS + BS + 'title=' + re.escape(TITLE) + '[ \t\r]*$', t)
    if not mm: sys.exit('no Pandora entry in MO2 executables')
    key = mm.group(1) + BS + 'arguments='; lines = t.split('\n'); hit = [i for i, l in enumerate(lines) if l.startswith(key)]
    cr = '\r' if lines[hit[0]].endswith('\r') else ''; lines[hit[0]] = key + value + cr
    shutil.copy2(INI, INI + '.bak-pandora'); open(INI, 'wb').write('\n'.join(lines).encode('utf-8'))
set_args('--auto_run --auto_close --output:' + OUT.replace('/', BS + BS))
ps = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s'); $s.TargetPath='%s'; $s.Arguments='\"moshortcut://%s\"'; $s.WorkingDirectory='%s'; $s.Save()" % (
    LNK.replace('/', BS), (INST + '/ModOrganizer.exe').replace('/', BS), TITLE, INST.replace('/', BS))
subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True)
def running(): return 'Pandora Behaviour Engine' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout
subprocess.Popen(['explorer.exe', LNK.replace('/', BS)]); t0 = time.time(); seen = False
try:
    while time.time() - t0 < 1800:
        time.sleep(10); r = running(); seen = seen or r
        if int(time.time() - t0) % 60 < 10: print('  %4d s  pandora %s' % (time.time() - t0, 'running' if r else 'not running'), flush=True)
        if seen and not r: break
        if not seen and time.time() - t0 > 180: print('Pandora never started', flush=True); break
    else:
        print('Pandora still running after 30 min: stopping it', flush=True); subprocess.run(['powershell','-NoProfile','-Command',"Get-Process | ? { $_.ProcessName -like 'Pandora*' } | Stop-Process -Force"], capture_output=True)
finally:
    time.sleep(5); bench.close_mo2()
    if not bench.mo2_running(): set_args('')
logp = OUT + '/Engine.log'
log = open(logp, encoding='utf-8', errors='replace').read() if os.path.exists(logp) else ''
fresh = os.path.exists(logp) and os.path.getmtime(logp) > start_log
errs = [l for l in log.splitlines() if re.match(r'\s*(ERROR|FATAL)', l)]
beh = sum(1 for r, _, fs in os.walk(OUT + '/meshes') for f in fs if f.lower().endswith('.hkx')) if os.path.isdir(OUT + '/meshes') else 0
print('log fresh %s, %d error lines, %d hkx files, %.0f s' % (fresh, len(errs), beh, time.time() - t0), flush=True)
for l in errs[:15]: print('  ', l[:200], flush=True)
print('log tail:', *log.splitlines()[-8:], sep='\n  ', flush=True)
if not fresh or errs or beh < 50 or bench.mo2_running():
    sys.exit('Pandora run not clean: output NOT swapped (old output stays; new tool stays installed, backup at %s)' % BK)
shutil.rmtree(OUTMOD); shutil.move(OUT, OUTMOD); print('output swapped into', OUTMOD, flush=True)

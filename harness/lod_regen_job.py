"""Queue job (game and MO2 closed): regenerate TexGen + DynDOLOD for the current grass/trees, unattended (UIA clicks via
dev/lod-regen/dyn/ui.ps1). New output mods 'foxnne - TexGen Output <stamp>' / 'foxnne - DynDOLOD Output <stamp>' replace the active
foxnne outputs at the same list position (old ones disabled, kept). DynDOLOD.esm after FabulousPoser.esl, DynDOLOD.esp + Occlusion.esp last.
usage: python lod_regen_job.py STAMP   (e.g. 2026-11-21b)"""
import os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running() or bench.mo2_running(): sys.exit('game or Mod Organizer open')
STAMP = sys.argv[1]; DYN_ONLY = '--dyndolod-only' in sys.argv; I = 'C:/Modlists/NGVO 8.0 Beta'; P = I + '/profiles/foxnne-nsfw'; DYN = I + '/tools/DynDOLOD'
BS = chr(92)
DD = BS.join(['C:', 'Users', 'foxnn', 'dev', 'lod-regen', 'dyn'])
UI = DD + BS + 'ui.ps1'; CK = DD + BS + 'checks.ps1'
LNK = {'TexGen': DD + BS + 'launch-TexGen.lnk', 'DynDOLOD': DD + BS + 'launch-DynDOLOD.lnk'}


def ps(*a):
    return subprocess.run(['powershell', '-NoProfile', '-File'] + list(a), capture_output=True, text=True).stdout


def dump(proc):
    return ps(UI, '-Proc', proc, '-Dump')


def click(proc, name):
    r = ps(UI, '-Proc', proc, '-Click', name)
    print('  click', name, '->', r.strip()[:120], flush=True)
    return 'clicked' in r


def proc_up(name):
    return name.lower() in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()


def wait_for(proc, pred, timeout, every=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = dump(proc)
        if pred(d):
            return d
        if 'no process' in d and time.time() - t0 > 60:
            return d
        time.sleep(every)
    return None


st = time.strftime('%Y%m%d-%H%M')
for f in ('modlist.txt', 'plugins.txt', 'loadorder.txt'):
    shutil.copy2(f'{P}/{f}', f'{P}/{f}.bak-lodregen-{st}')


def ml():
    return open(f'{P}/modlist.txt', encoding='utf-8-sig').read().split('\n')


def wml(L):
    open(f'{P}/modlist.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))


L = ml(); cr = '\r' if L[0].endswith('\r') else ''
cur_tex = next(l.rstrip('\r')[1:] for l in L if l.startswith('+foxnne - TexGen Output'))
cur_dyn = next(l.rstrip('\r')[1:] for l in L if l.startswith('+foxnne - DynDOLOD Output'))
new_tex, new_dyn = 'foxnne - TexGen Output ' + STAMP, 'foxnne - DynDOLOD Output ' + STAMP
print('replacing', cur_tex, '/', cur_dyn, flush=True)
L = ['-' + l[1:] if l.rstrip('\r')[1:] in ((cur_dyn,) if DYN_ONLY else (cur_tex, cur_dyn)) else l for l in L]; wml(L)
DROP = {'dyndolod.esm', 'dyndolod.esp', 'occlusion.esp'}
for f in ('plugins.txt', 'loadorder.txt'):
    X = open(f'{P}/{f}', encoding='utf-8-sig').read().split('\n')
    X = [l for l in X if l.rstrip('\r').lstrip('*').lower() not in DROP]
    open(f'{P}/{f}', 'w', encoding='utf-8', newline='').write('\n'.join(X))
for d in ('TexGen_Output', 'DynDOLOD_Output'):
    p = DYN + '/' + d
    if os.path.isdir(p) and os.listdir(p):
        sys.exit(d + ' not empty')


def install(src, mod, anchor_old):
    dst = I + '/mods/' + mod
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for e in os.listdir(src):
        shutil.move(os.path.join(src, e), os.path.join(dst, e))
    L = ml(); i = [k for k, l in enumerate(L) if l.rstrip('\r')[1:] == anchor_old][0]
    L.insert(i, '+' + mod + cr); wml(L)


def wait_exit(exe, out_dir, timeout=1800):
    """Wait for the tool to close, then for its output folder to stop changing (TexGen keeps converting after Exit)."""
    t0 = time.time()
    while proc_up(exe):
        if time.time() - t0 > timeout:
            sys.exit(exe + ' still running after Exit; output not moved')
        time.sleep(10)
    last = None
    for _ in range(30):
        n = sum(len(fs) for _, _, fs in os.walk(out_dir))
        if n == last:
            return n
        last = n; time.sleep(10)
    return last

# ---- TexGen
if DYN_ONLY:
    print('TexGen skipped (--dyndolod-only), keeping', cur_tex, flush=True)
if not DYN_ONLY:
    subprocess.Popen(['explorer.exe', LNK['TexGen']]); print('TexGen launched', flush=True)
    d = wait_for('TexGenx64', lambda d: '[TButton] Start' in d or 'PBR textures detected' in d, 600)
    if d and 'PBR textures detected' in d:
        click('TexGenx64', 'OK'); time.sleep(8)
    if not wait_for('TexGenx64', lambda d: '[TButton] Start' in d, 300):
        sys.exit('TexGen main window not found')
    click('TexGenx64', 'Start')
    if not wait_for('TexGenx64', lambda d: 'Exit TexGen' in d, 3600, 20):
        sys.exit('TexGen did not finish')
    click('TexGenx64', 'Exit TexGen')
    print('TexGen output files:', wait_exit('TexGenx64.exe', DYN + '/TexGen_Output'), flush=True)
    time.sleep(5); bench.close_mo2()
    log = open(DYN + '/Logs/TexGen_SSE_log.txt', encoding='utf-8', errors='replace').read()
    if 'TexGen completed successfully' not in log[-20000:]:
        sys.exit('TexGen log has no success line')
    ntxt = sum(f.endswith('.txt') for _, _, fs in os.walk(DYN + '/TexGen_Output/textures/terrain/lodgen') for f in fs)
    if ntxt < 500:
        sys.exit(f'TexGen output has only {ntxt} billboard .txt files; not installing')
    install(DYN + '/TexGen_Output', new_tex, cur_tex); print('TexGen installed as', new_tex, flush=True)
# ---- DynDOLOD
subprocess.Popen(['explorer.exe', LNK['DynDOLOD']]); print('DynDOLOD launched', flush=True)
d = wait_for('DynDOLODx64', lambda d: 'Advanced >>>' in d or 'already exists' in d or '[TButton] OK' in d, 900)
if not d or 'already exists' in d:
    click('DynDOLODx64', 'Exit DynDOLOD'); sys.exit('DynDOLOD refused to start: ' + (d or '')[:300])
if 'Advanced >>>' in d:
    click('DynDOLODx64', 'Advanced >>>'); time.sleep(6)
chk = ps(CK, '-Proc', 'DynDOLODx64')
if "'Level32' = 1" in chk:                     # map-only LOD32 is off for the lighter LOD (2026-11-21)
    click('DynDOLODx64', 'Level32'); time.sleep(2)
print('checkboxes:', ' | '.join(l.strip() for l in ps(CK, '-Proc', 'DynDOLODx64').splitlines()
                                 if any(k in l for k in ('Level32', 'Ultra', 'Occlusion', 'Dynamic'))), flush=True)
click('DynDOLODx64', 'OK')
if not wait_for('DynDOLODx64', lambda d: 'Save and Exit' in d, 7200, 30):
    sys.exit('DynDOLOD did not reach the save dialog')
for _ in range(120):
    if not proc_up('LODGenx64'):
        break
    time.sleep(10)
click('DynDOLODx64', 'Save and Exit')
print('DynDOLOD output files:', wait_exit('DynDOLODx64.exe', DYN + '/DynDOLOD_Output'), flush=True)
time.sleep(5); bench.close_mo2()
log = open(DYN + '/Logs/DynDOLOD_SSE_log.txt', encoding='utf-8', errors='replace').read()[-40000:]
if 'DynDOLOD plugins generated successfully' not in log:
    sys.exit('DynDOLOD log has no success line')
install(DYN + '/DynDOLOD_Output', new_dyn, cur_dyn); print('DynDOLOD installed as', new_dyn, flush=True)
for f, star in (('plugins.txt', True), ('loadorder.txt', False)):
    X = open(f'{P}/{f}', encoding='utf-8-sig').read().split('\n'); c2 = '\r' if X[0].endswith('\r') else ''
    pre = '*' if star else ''
    i = [k for k, l in enumerate(X) if l.rstrip('\r').lstrip('*') == 'FabulousPoser.esl'][0]
    X.insert(i + 1, pre + 'DynDOLOD.esm' + c2)
    while X and X[-1].strip() == '':
        X.pop()
    X += [pre + 'DynDOLOD.esp' + c2, pre + 'Occlusion.esp' + c2]
    open(f'{P}/{f}', 'w', encoding='utf-8', newline='').write('\n'.join(X) + ('\n' if star else ''))
print('LOD regen done', flush=True)

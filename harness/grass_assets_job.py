"""Queue job (game + MO2 closed): regenerate ONLY the Community Shaders Grass Optimizations assets (dyndolod.info/Mods/Community-Shaders):
full TexGen run (about 6 min, new 'foxnne - TexGen Output <stamp>' replaces the active one), then DynDOLOD in advanced mode with
no worldspaces and every option off except grass ('Create assets for CS Optimized Grass'), via a temporary preset. The new grass
files (Meshes/LOD/Grass, Meshes/landscape/grass, textures/DynDOLOD/LOD/DynDOLOD_GrassOptimizations_*) are merged into the ACTIVE
DynDOLOD output mod, which is unticked during the run (docs: no output with already updated NIFs may be active) and re-ticked after.
Profile files and the preset are restored at the end, also on failure.
usage: python grass_assets_job.py STAMP [--skip-texgen]"""
import os, re, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
for _ in range(30):
    if not bench.running(): break
    time.sleep(4)
else: sys.exit('game open')
bench.close_mo2()
STAMP = sys.argv[1]; SKIP_TEX = '--skip-texgen' in sys.argv
I = 'C:/Modlists/NGVO 8.0 Beta'; P = I + '/profiles/foxnne-nsfw'; DYN = I + '/tools/DynDOLOD'
BS = chr(92); DD = BS.join(['C:', 'Users', 'foxnn', 'dev', 'lod-regen', 'dyn'])
UI = DD + BS + 'ui.ps1'; CK = DD + BS + 'checks.ps1'
LNK = {'TexGen': DD + BS + 'launch-TexGen.lnk', 'DynDOLOD': DD + BS + 'launch-DynDOLOD.lnk'}
PRESET = DYN + '/Edit Scripts/DynDOLOD/Presets/DynDOLOD_SSE_Default.ini'


def ps(*a): return subprocess.run(['powershell', '-NoProfile', '-File'] + list(a), capture_output=True, text=True).stdout
def dump(proc): return ps(UI, '-Proc', proc, '-Dump')
def click(proc, name):
    r = ps(UI, '-Proc', proc, '-Click', name); print('  click', name, '->', r.strip()[:120], flush=True); return 'clicked' in r
def proc_up(name): return name.lower() in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
def wait_for(proc, pred, timeout, every=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = dump(proc)
        if pred(d): return d
        if 'no process' in d and time.time() - t0 > 60: return d
        time.sleep(every)
    return None
def wait_exit(exe, out_dir, timeout=1800):
    t0 = time.time()
    while proc_up(exe):
        if time.time() - t0 > timeout: raise SystemExit(exe + ' still running after Exit')
        time.sleep(10)
    last = None
    for _ in range(30):
        n = sum(len(fs) for _, _, fs in os.walk(out_dir))
        if n == last: return n
        last = n; time.sleep(10)
    return last
def ml(): return open(f'{P}/modlist.txt', encoding='utf-8-sig').read().split('\n')
def wml(L): open(f'{P}/modlist.txt', 'w', encoding='utf-8', newline='').write('\n'.join(L))


st = time.strftime('%Y%m%d-%H%M'); SAVED = {}
for f in ('plugins.txt', 'loadorder.txt'):
    SAVED[f] = open(f'{P}/{f}', 'rb').read(); shutil.copy2(f'{P}/{f}', f'{P}/{f}.bak-grassassets-{st}')
shutil.copy2(f'{P}/modlist.txt', f'{P}/modlist.txt.bak-grassassets-{st}')
shutil.copy2(PRESET, PRESET + '.bak-grassassets'); PRESET_ORIG = open(PRESET, 'rb').read()
L = ml(); cr = '\r' if L[1].endswith('\r') else ''
cur_tex = next(l.rstrip('\r')[1:] for l in L if l.startswith('+foxnne - TexGen Output'))
cur_dyn = next(l.rstrip('\r')[1:] for l in L if l.startswith('+foxnne - DynDOLOD Output'))
for d in ('TexGen_Output', 'DynDOLOD_Output'):
    p = DYN + '/' + d
    if os.path.isdir(p) and os.listdir(p): sys.exit(d + ' not empty')
print('active outputs:', cur_tex, '/', cur_dyn, flush=True)
ok = False
try:
    # outputs off while the tools run (plugins.txt is restored afterwards: MO2 drops the DynDOLOD plugins when their mod is off)
    wml(['-' + l[1:] if l.rstrip('\r')[1:] in ((cur_dyn,) if SKIP_TEX else (cur_dyn, cur_tex)) else l for l in ml()])
    for f in ('plugins.txt', 'loadorder.txt'):
        X = open(f'{P}/{f}', encoding='utf-8-sig').read().split('\n')
        X = [l for l in X if l.rstrip('\r').lstrip('*').lower() not in ('dyndolod.esm', 'dyndolod.esp', 'occlusion.esp')]
        open(f'{P}/{f}', 'w', encoding='utf-8', newline='').write('\n'.join(X))
    if not SKIP_TEX:
        subprocess.Popen(['explorer.exe', LNK['TexGen']]); print('TexGen launched', flush=True)
        d = wait_for('TexGenx64', lambda d: '[TButton] Start' in d or 'PBR textures detected' in d, 600)
        if d and 'PBR textures detected' in d: click('TexGenx64', 'OK'); time.sleep(8)
        if not wait_for('TexGenx64', lambda d: '[TButton] Start' in d, 300): raise SystemExit('TexGen main window not found')
        click('TexGenx64', 'Start')
        if not wait_for('TexGenx64', lambda d: 'Exit TexGen' in d, 3600, 20): raise SystemExit('TexGen did not finish')
        click('TexGenx64', 'Exit TexGen')
        print('TexGen output files:', wait_exit('TexGenx64.exe', DYN + '/TexGen_Output'), flush=True)
        time.sleep(5); bench.close_mo2()
        ntxt = sum(f.endswith('.txt') for _, _, fs in os.walk(DYN + '/TexGen_Output/textures/terrain/lodgen') for f in fs)
        if ntxt < 500: raise SystemExit(f'TexGen output has only {ntxt} billboard .txt files; not installing')
        new_tex = 'foxnne - TexGen Output ' + STAMP; dst = I + '/mods/' + new_tex
        if os.path.exists(dst): shutil.rmtree(dst)
        os.makedirs(dst)
        for e in os.listdir(DYN + '/TexGen_Output'): shutil.move(os.path.join(DYN + '/TexGen_Output', e), os.path.join(dst, e))
        L = ml(); i = [k for k, l in enumerate(L) if l.rstrip('\r')[1:] == cur_tex][0]; L.insert(i, '+' + new_tex + cr); wml(L)
        print('TexGen installed as', new_tex, flush=True)
    # ---- DynDOLOD, grass assets only: temporary preset with no worldspaces and all other options off
    s = PRESET_ORIG.decode('latin-1'); head, sep, rest = s.partition('[Skyrim LODGen]')
    def setk(h, k, v): return re.sub(r'(?m)^(%s=)[^\r\n]*' % re.escape(k), lambda m: m.group(1) + v, h)
    for k in ('DoObjectLOD', 'DoTreeLOD', 'DoDynamicLOD', 'DoOcclusion', 'DoTerrainUnderside', 'DoSeasons', 'Level32'): head = setk(head, k, '0')
    head = setk(head, 'DoGrass', '1')
    lines = head.split('\n'); far = next(k for k, l in enumerate(lines) if l.startswith('NearGrid='))
    for k in range(far + 1, len(lines)):
        if re.match(r'^[^=\[\r\n]+=1\r?$', lines[k]): lines[k] = lines[k].replace('=1', '=0')        # worldspace list
    open(PRESET, 'wb').write(('\n'.join(lines) + sep + rest).encode('latin-1'))
    subprocess.Popen(['explorer.exe', LNK['DynDOLOD']]); print('DynDOLOD launched', flush=True)
    d = wait_for('DynDOLODx64', lambda d: 'Advanced >>>' in d or 'already exists' in d or '[TButton] OK' in d, 900)
    if not d or 'already exists' in d:
        click('DynDOLODx64', 'Exit DynDOLOD'); raise SystemExit('DynDOLOD refused to start: ' + (d or '')[:300])
    if 'Advanced >>>' in d: click('DynDOLODx64', 'Advanced >>>'); time.sleep(6)
    chk = ps(CK, '-Proc', 'DynDOLODx64'); print('checkboxes:\n' + chk, flush=True)
    on = [l for l in chk.splitlines() if l.strip().endswith('= 1')]
    bad = [l for l in on if re.search(r"'(Object LOD|Tree LOD|Dynamic LOD|Occlusion data|Terrain underside|Seasons|Level32)'", l, re.I)]
    if bad:
        open(os.path.join(os.path.dirname(HERE), 'results', 'grass_assets_ui_dump.txt'), 'w', encoding='utf-8').write(dump('DynDOLODx64') + '\n\n' + chk)
        click('DynDOLODx64', 'Cancel') or click('DynDOLODx64', 'Exit DynDOLOD')
        raise SystemExit('options other than grass are still ticked: ' + ' | '.join(b.strip() for b in bad)[:400])
    click('DynDOLODx64', 'OK')
    d = wait_for('DynDOLODx64', lambda d: 'Save and Exit' in d or 'Exit DynDOLOD' in d or 'Zip and Exit' in d, 3600, 20)
    if not d: raise SystemExit('DynDOLOD did not reach an exit dialog')
    for _ in range(60):
        if not proc_up('LODGenx64'): break
        time.sleep(10)
    open(os.path.join(os.path.dirname(HERE), 'results', 'grass_assets_end_dialog.txt'), 'w', encoding='utf-8').write(d)
    click('DynDOLODx64', 'Save and Exit') or click('DynDOLODx64', 'Exit DynDOLOD')
    print('DynDOLOD output files:', wait_exit('DynDOLODx64.exe', DYN + '/DynDOLOD_Output'), flush=True)
    time.sleep(5); bench.close_mo2()
    out = DYN + '/DynDOLOD_Output'; files = [os.path.join(d, f) for d, _, fs in os.walk(out) for f in fs]
    grass = [f for f in files if re.search(r'grass', f.replace(BS, '/'), re.I)]
    print('output: %d files, %d grass-related' % (len(files), len(grass)), flush=True)
    if len(grass) < 100: raise SystemExit('too few grass assets in the DynDOLOD output; nothing merged (output left in place)')
    other = [f for f in files if f not in grass and not f.lower().endswith(('.esp', '.esm', '.txt', '.log'))]
    if other: print('note: non-grass files produced and NOT merged:', len(other), other[:5], flush=True)
    dstmod = I + '/mods/' + cur_dyn; n = 0
    for f in grass:
        rel = os.path.relpath(f, out); t = os.path.join(dstmod, rel); os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copy2(f, t); n += 1
    shutil.rmtree(out); os.makedirs(out)
    print('merged', n, 'grass files into', cur_dyn, flush=True); ok = True
finally:
    open(PRESET, 'wb').write(PRESET_ORIG)
    L = ml(); L = [('+' + l[1:]) if l.rstrip('\r')[1:] == cur_dyn else l for l in L]
    if not SKIP_TEX and any(l.rstrip('\r')[1:] == 'foxnne - TexGen Output ' + STAMP and l.startswith('+') for l in L):
        L = [('-' + l[1:]) if l.rstrip('\r')[1:] == cur_tex else l for l in L]
    else:
        L = [('+' + l[1:]) if l.rstrip('\r')[1:] == cur_tex else l for l in L]
    wml(L)
    for f, b in SAVED.items(): open(f'{P}/{f}', 'wb').write(b)
    print('profile and preset restored; grass assets', 'UPDATED' if ok else 'NOT updated', flush=True)

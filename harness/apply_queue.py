"""Apply the staged install queue of 2026-11-17. Refuses to run while the game, MO2 or a suite is running.

usage: python apply_queue.py [--dry]
Installs (staged in C:/Modlists/staging/queue-20261117/mods): Settle + its Clipping Fix merge DLL (above Faster HDT-SMP),
RaceMenu Overlay FPS Helper, Dialogue Ducker, Khajiit Warpaints to Face Paints (+ESL-flagged esp after VWA), and turns
SkyrimNet OmniSight capture back on. Backups: *.bak-pre-queue-20261117.
"""
import os, re, shutil, subprocess, sys
DRY = '--dry' in sys.argv
ROOT = 'C:/Modlists/NGVO 8.0 Beta'; PROF = ROOT + '/profiles/foxnne-nsfw'; STAGE = 'C:/Modlists/staging/queue-20261117/mods'
OMNI = ROOT + '/overwrite/SKSE/Plugins/SkyrimNet/config/OmniSight.yaml'
TAG = '.bak-pre-queue-20261117'
# (mod folder, modlist anchor line it goes directly ABOVE = higher priority); listed lowest priority first
MODS = [('Settle - Seat Collision for SMP Cloth', '+Faster HDT-SMP'),
        ('Settle - FSMP Clothing Clipping Fix Merge', '+Settle - Seat Collision for SMP Cloth'),
        ('Dialogue Ducker', '+Settle - FSMP Clothing Clipping Fix Merge'),
        ("Goat's RaceMenu Overlay FPS Helper", '+Dialogue Ducker'),
        ('Khajiit Warpaints to Face Paints', '+Vanilla Warpaints Absolution')]
PLUGIN = ('KhajiitWarpaintToFacepaint.esp', 'VWA_VanillaWarpaintsAbsolution.esp')   # insert after

tl = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
ps = subprocess.run(['powershell', '-NoProfile', '-Command', "(Get-CimInstance Win32_Process -Filter \"name='python.exe'\").CommandLine"], capture_output=True, text=True).stdout.lower()
busy = [n for n in ('skyrimse.exe', 'modorganizer.exe') if n in tl] + [n for n in ('suite.py', 'suite_extra.py', 'bench.py') if n in ps]
if busy and not DRY: sys.exit('refusing: running ' + ', '.join(busy))
if busy: print('NOTE (dry run): running', busy)


def lines(p):
    return open(p, 'rb').read().decode('utf-8-sig').replace(chr(13), '').split(chr(10))


def save(p, ls, crlf):
    if DRY: return
    if not os.path.exists(p + TAG): shutil.copy2(p, p + TAG)
    with open(p, 'w', encoding='utf-8', newline='') as f: f.write(('\r\n' if crlf else '\n').join(ls))


def crlf(p): return b'\r\n' in open(p, 'rb').read()


ml = PROF + '/modlist.txt'; L = lines(ml)
for name, anchor in MODS:
    src = f'{STAGE}/{name}'; dst = f'{ROOT}/mods/{name}'
    if not os.path.isdir(src) and not os.path.isdir(dst): sys.exit('missing staged mod ' + name)
    if any(x[1:] == name for x in L if x[:1] in '+-'): print('already listed:', name); continue
    i = L.index(anchor); L.insert(i, '+' + name); print(f'modlist: +{name}  above  {anchor}')
    if not DRY and not os.path.isdir(dst): shutil.copytree(src, dst)
save(ml, L, crlf(ml))

for fn, active in (('plugins.txt', True), ('loadorder.txt', False)):
    p = f'{PROF}/{fn}'; L = lines(p); new = ('*' if active else '') + PLUGIN[0]; after = ('*' if active else '') + PLUGIN[1]
    if any(x.lstrip('*').lower() == PLUGIN[0].lower() for x in L): print(fn, 'already has plugin'); continue
    i = [x.lower() for x in L].index(after.lower()); L.insert(i + 1, new); print(f'{fn}: {new} after {after}'); save(p, L, crlf(p))

t = open(OMNI, encoding='utf-8').read()
n = re.sub(r'(?m)^(omnisight:\s*\n\s+enabled:\s*)false', r'\1true', t, count=1)
print('OmniSight:', 'enabled -> true' if n != t else 'no change (already on?)')
if n != t and not DRY:
    shutil.copy2(OMNI, OMNI + TAG); open(OMNI, 'w', encoding='utf-8', newline='').write(n)

# --- queued 2026-11-17 (user): re-enable Combat Pathing Revolution; BTPS prompt back to its default place and 100% size;
#     Floating Subtitles head offset 12 -> 20 so the two stop overlapping
L = lines(ml); changed = False
for name in ('Combat Pathing Revolution AE', 'Combat Pathing Revolution'):
    if '-' + name in L: L[L.index('-' + name)] = '+' + name; changed = True; print('modlist: enabled', name)
    else: print('modlist: not changed (already enabled or missing):', name)
if changed: save(ml, L, crlf(ml))

import json
HUD = ROOT + '/overwrite/SKSE/Plugins/HudNG/Layout.json'
try:
    raw = open(HUD, encoding='utf-8').read(); d = json.loads(raw); hit = None
    for e in d.get('entries', []):
        if e.get('id') == 'btps-prompt': hit = e
    if hit is None: print('HUD NG: no btps-prompt entry found, nothing changed')
    else:
        print('HUD NG btps-prompt: x %s y %s scale %s -> 0, 0, 1' % (hit.get('x'), hit.get('y'), hit.get('scale')))
        hit['x'] = 0.0; hit['y'] = 0.0; hit['scale'] = 1.0
        if not DRY:
            shutil.copy2(HUD, HUD + TAG); open(HUD, 'w', encoding='utf-8').write(json.dumps(d, indent=2))
except Exception as e: print('HUD NG: failed, nothing changed:', e)

FS = ROOT + '/mods/foxnne - carried-over settings/MCM/Settings/FloatingSubtitles.ini'
try:
    t = open(FS, 'rb').read().decode('utf-8-sig'); n2 = re.sub(r'(?m)^(fHeadOffset\s*=\s*)[0-9.]+', r'\g<1>20.000000', t, count=1)
    print('Floating Subtitles fHeadOffset:', re.search(r'(?m)^fHeadOffset\s*=\s*([0-9.]+)', t).group(1), '-> 20' if n2 != t else '(no change)')
    if n2 != t and not DRY: shutil.copy2(FS, FS + TAG); open(FS, 'wb').write(n2.encode('utf-8'))
except Exception as e: print('Floating Subtitles: failed, nothing changed:', e)
print('DRY RUN, nothing written' if DRY else 'APPLIED')

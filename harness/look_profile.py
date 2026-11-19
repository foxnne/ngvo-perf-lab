"""Switch the creative look off (neutral baseline for tuning and reference shots) or put it back. Game and Mod Organizer must be closed.
usage: python look_profile.py neutral | restore | status
neutral: LUT off, Look Grade off, Vignette off (user layer of SettingsUser.json), every Scene Manager Look Grade entry paused.
         Tone mapping, auto exposure, local exposure and all non-look features stay. Originals are saved under configs/look-backup/.
restore: copies the saved originals back."""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
D = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/'
FILES = {'SettingsUser.json': D + 'SettingsUser.json', 'SceneManager.json': D + 'SceneSettings/SceneManager.json'}
BK = os.path.join(os.path.dirname(HERE), 'configs', 'look-backup'); MARK = os.path.join(BK, 'NEUTRAL_ACTIVE')
LOOK = ('Look Grade',)

def entries(o):
    """Every scene entry dict in the Scene Manager document."""
    if isinstance(o, dict):
        if 'feature' in o and 'setting' in o and 'path' in o: yield o
        else:
            for v in o.values(): yield from entries(v)
    elif isinstance(o, list):
        for v in o: yield from entries(v)

def status():
    s = json.load(open(FILES['SettingsUser.json'])); pp = s.get('Post Processing', {})
    sm = json.load(open(FILES['SceneManager.json'])); es = [e for e in entries(sm) if e.get('feature') == 'PostProcessing' and e.get('path', [''])[0] in LOOK]
    return {'neutral_marker': os.path.exists(MARK), 'user_LUT_enabled': pp.get('LUT', {}).get('enabled'), 'user_LookGrade_enabled': pp.get('Look Grade', {}).get('enabled'),
            'user_Vignette_enabled': pp.get('Vignette', {}).get('enabled'), 'scene_grade_entries': len(es), 'scene_grade_entries_paused': sum(bool(e.get('paused')) for e in es)}

cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
if cmd == 'status': print(json.dumps(status(), indent=1)); sys.exit()
if bench.running() or bench.mo2_running(): sys.exit('close the game and Mod Organizer first')
if cmd == 'neutral':
    if os.path.exists(MARK): sys.exit('already neutral (marker present); restore first if you want to re-capture originals')
    os.makedirs(BK, exist_ok=True)
    for name, p in FILES.items(): shutil.copy2(p, os.path.join(BK, name)); shutil.copy2(p, os.path.join(BK, name + time.strftime('.%Y%m%d-%H%M%S')))
    s = json.load(open(FILES['SettingsUser.json'])); pp = s.setdefault('Post Processing', {})
    for eff in ('LUT', 'Look Grade', 'Vignette'): pp.setdefault(eff, {})['enabled'] = False
    json.dump(s, open(FILES['SettingsUser.json'], 'w'), indent=2)
    sm = json.load(open(FILES['SceneManager.json'])); n = 0
    for e in entries(sm):
        if e.get('feature') == 'PostProcessing' and e.get('path', [''])[0] in LOOK and not e.get('paused'): e['paused'] = True; n += 1
    json.dump(sm, open(FILES['SceneManager.json'], 'w'), indent=1)
    open(MARK, 'w').write(time.strftime('%Y-%m-%d %H:%M:%S')); print('neutral: paused', n, 'scene grade entries;', json.dumps(status()))
elif cmd == 'restore':
    if not os.path.exists(MARK): sys.exit('not neutral (no marker)')
    for name, p in FILES.items(): shutil.copy2(os.path.join(BK, name), p)
    os.remove(MARK); print('look restored;', json.dumps(status()))

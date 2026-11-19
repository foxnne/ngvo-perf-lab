"""User decision 2026-11-18: Neural Rendering runs at 75% resolution from now on. Applies it to the saved settings (game closed),
updates the everything-on guard, drops the portrait scale variants and trims the gallery back to current sets."""
import json, os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game is running')
if bench.mo2_running(): bench.close_mo2(); time.sleep(5)
P = 'C:/Modlists/NGVO 8.0 Beta/mods/CS Settings/SKSE/Plugins/CommunityShaders/SettingsUser.json'
shutil.copy2(P, P + '.bak-pre-nr75-20261118')
d = json.load(open(P)); nr = d.setdefault('Neural Rendering', {})
nr.update({'enabled': True, 'alternateFrames': False, 'resolutionScale': 0.75, 'resolutionScaleX': 0.75, 'resolutionScaleY': 0.75})
json.dump(d, open(P, 'w'), indent=2)
b = open(os.path.join(HERE, 'bench.py'), encoding='utf-8').read()
b2 = b.replace("('nr_scale', state['nr_scale'] == 1.0)", "('nr_scale', abs((state['nr_scale'] or 0) - NR_SCALE) < 0.01)")
if b2 != b and 'NR_SCALE =' not in b2:
    b2 = b2.replace('def all_on(strict=True):', 'NR_SCALE = 0.75          # user decision 2026-11-18: Neural Rendering at 75% resolution going forward\n\n\ndef all_on(strict=True):', 1)
    b2 = b2.replace('Neural Rendering on at 100% every frame', 'Neural Rendering on at NR_SCALE every frame')
open(os.path.join(HERE, 'bench.py'), 'w', encoding='utf-8', newline='').write(b2)
f = os.path.join(HERE, 'portrait_scales.txt')
if os.path.exists(f): os.remove(f)
g = open(os.path.join(HERE, 'gallery.py'), encoding='utf-8').read()
g = re.sub(r" \+ \\n       \[\(f'Neural Rendering model preset.*?\n        if os\.path\.isdir.*?\]", '', g, flags=re.S)
open(os.path.join(HERE, 'gallery.py'), 'w', encoding='utf-8', newline='').write(g)
print('applied: NR 75% saved, guard updated', 'NR_SCALE' in b2, flush=True)

"""Queue job: build the Looks Lab (v4) from a baseline manifest and place it under the gallery so the existing local/tailnet page serves it at /lab/.
The lab folder is REPLACED: the set served before (its build stays in look/webapp/v4/dist/<its tag>/) is no longer shown.
Offline: needs neither the game nor the bridge, so it can also be run by hand right after the shoot (python build_lab_job.py TAG).
usage: python build_lab_job.py TAG          e.g. lab-baseline-02 (shot with: baseline_shoot.py lab-baseline-02 --plan baseline_plan_lab.json)"""
import json, os, shutil, subprocess, sys
if len(sys.argv) < 2: sys.exit(__doc__)
TAG = sys.argv[1]; LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
man = os.path.join(LAB, 'results', 'baseline', TAG, 'manifest.json'); v4 = 'C:/Modlists/NGVO 8.0 Beta/look/webapp/v4'
if not os.path.exists(man): sys.exit('no manifest: ' + man)
doc = json.load(open(man, encoding='utf-8')); shots = doc.get('shots', [])
have = [s for s in shots if os.path.exists(os.path.join(os.path.dirname(man), s['file']))]
if not have: sys.exit('manifest lists %d shots, none on disk: nothing to build, the lab is left as it is' % len(shots))
cats = {}
for s in have:
    c = s.get('category') or (s.get('kind') if s.get('kind') in ('interior', 'dungeon') else 'exterior'); cats[c] = cats.get(c, 0) + 1
print('set %s: %d shots on disk of %d in the manifest; per category %s' % (TAG, len(have), len(shots), json.dumps(cats)))
for s in have:
    if s.get('flags'): print('  flagged: %s  %s' % (s['id'], '; '.join(s['flags'])))
r = subprocess.run([sys.executable, os.path.join(v4, 'build.py'), man], cwd=v4, capture_output=True, text=True); print(r.stdout[-1500:], r.stderr[-1500:])
if r.returncode: sys.exit(r.returncode)
src = os.path.join(v4, 'dist', TAG); dst = os.path.join(LAB, 'gallery', 'lab')
if not os.path.exists(os.path.join(src, 'index.html')): sys.exit('build wrote no index.html in ' + src + ': the lab is left as it is')
if os.path.isdir(dst): shutil.rmtree(dst)
shutil.copytree(src, dst); print('lab at', dst, 'files', sum(len(f) for _, _, f in os.walk(dst)))

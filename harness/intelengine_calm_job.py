"""Queue job (game closed): fewer NPC spawns from SkyrimNet IntelEngine stories. Backs up settings.yaml.
usage: python intelengine_calm_job.py TAG"""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
P = r'C:\Modlists\NGVO 8.0 Beta\overwrite\SKSE\Plugins\SkyrimNet\config\plugins\IntelEngine\settings.yaml'
shutil.copy2(P, P + '.bak-pre-calm-' + time.strftime('%Y%m%d-%H%M%S'))
s = open(P, encoding='utf-8').read()
CH = {'type_ambush': 'false', 'type_faction_ambush': 'false', 'quest_faction_battle': 'false', 'check_interval_hours': '8'}
for k, v in CH.items():
    s, n = re.subn(r'(?m)^(\s*%s:\s*).*$' % k, lambda m: m.group(1) + v, s)
    print(k, '->', v, 'lines', n, flush=True)
open(P, 'w', encoding='utf-8').write(s)

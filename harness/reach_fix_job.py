"""Queue job (game closed): enemy melee reach fix. VCD player combat hull Bulky -> Compact; Precision AI reach offset -20
(NPCs step closer before swinging); Precision trails off and truthful in the winning MCM ini. Backs up both files."""
import json, os, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
if bench.running(): sys.exit('game open')
M = 'C:/Modlists/NGVO 8.0 Beta/mods/foxnne - carried-over settings/'; ST = time.strftime('%Y%m%d-%H%M%S')
p = M + 'SKSE/Plugins/VariadicCollisionDynamics/Settings/PlayerState.json'; shutil.copy2(p, p + '.bak-' + ST)
d = json.load(open(p, encoding='utf-8-sig')); print('combat hull', d.get('combat'), '-> Compact'); d['combat'] = 'Compact'; json.dump(d, open(p, 'w', encoding='utf-8'), indent=4)
print('VCD done', flush=True)

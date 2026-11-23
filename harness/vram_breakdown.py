"""Queue job: where does the game's VRAM go? On the plains, read the game's GPU dedicated/shared memory, then switch off one
Community Shaders feature at a time (full settings get -> flip its enable key -> set, wait, measure, restore) and report the delta.
Live toggles may not release every buffer, so deltas are lower bounds. usage: python vram_breakdown.py TAG"""
import json, os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; BS = chr(92)


def gpu():
    ps = ("$p=(Get-Process SkyrimSE).Id; $s=(Get-Counter (" + "'" + BS + "GPU Process Memory(pid_'+$p+'*)" + BS + "Dedicated Usage'),('"
          + BS + "GPU Process Memory(pid_'+$p+'*)" + BS + "Shared Usage'),'" + BS + "GPU Adapter Memory(*)" + BS + "Dedicated Usage' -SampleInterval 1 -MaxSamples 3).CounterSamples;"
          "$d=($s|Where-Object {$_.Path -match 'process' -and $_.Path -match 'dedicated'}|Measure-Object CookedValue -Average).Average;"
          "$h=($s|Where-Object {$_.Path -match 'process' -and $_.Path -match 'shared'}|Measure-Object CookedValue -Average).Average;"
          "$a=($s|Where-Object {$_.Path -match 'adapter'}|Measure-Object CookedValue -Maximum).Maximum;"
          "'{0} {1} {2}' -f [int]($d/1MB),[int]($h/1MB),[int]($a/1MB)")
    o = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.split()
    return dict(game_dedicated=int(o[0]), game_shared=int(o[1]), adapter=int(o[2])) if len(o) == 3 else {'raw': o}


def get(short):
    r = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); return r.get('settings', r)


TESTS = [('NeuralRendering', 'enabled'), ('PhysicalSky', 'enableVolumetricClouds'), ('PhysicalSky', 'enabled'), ('VolumetricLighting', 'ExteriorEnabled'),
         ('ScreenSpaceGI', None), ('Skylighting', None), ('GroundFog', 'Enabled'), ('ExponentialHeightFog', 'enabled'), ('ImageBasedLighting', None),
         ('GrassOptimizations', 'EnableMeshLOD'), ('TreeWind', None), ('HiZOcclusionCulling', None), ('CloudShadows', None), ('LightLimitFix', None),
         ('DynamicCubemaps', None), ('TerrainShadows', None), ('ScreenSpaceShadows', None), ('SnowDeformation', None), ('GroundCover', None)]
rep = []
bench.launch(); bench.all_on(); bench.goto('WhiterunExterior04'); time.sleep(40)
base = gpu(); rep.append(dict(test='baseline', **base)); print(rep[-1], flush=True)
try:
    for short, key in TESTS:
        s = get(short)
        if 'error' in s: print(short, 'not available'); continue
        if key is None:
            key = next((k for k in ('enabled', 'Enabled', 'Enable', 'enable') if k in s), None)
        if key is None or key not in s or s[key] in (False, 0):
            print(short, 'no enable key or already off:', [k for k in s if 'nabl' in k][:6]); continue
        off = dict(s); off[key] = False if isinstance(s[key], bool) else 0
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': off}); time.sleep(20)
        m = gpu()
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s}); time.sleep(12)
        back = gpu()
        r = dict(test='%s.%s off' % (short, key), **m, delta_mb=m.get('game_dedicated', 0) - base.get('game_dedicated', 0), after_restore=back.get('game_dedicated'))
        rep.append(r); print(r, flush=True)
finally:
    json.dump(rep, open(os.path.join(os.path.dirname(HERE), 'results', 'memory', 'vram-%s.json' % TAG), 'w'), indent=1)
bench.all_on(strict=False); bench.finish()

"""Frame-cost attribution by elimination, at fixed standing poses (no code changes, nothing saved).
Each lever is switched for a few seconds, measured, and switched back; its cost is the frame time against the mean
of the baselines measured right before and after it.

usage: python attribute.py TAG [--scenes plains,forest] [--no-launch] [--keep-open] [--shots]
Writes results/attribution-TAG.json and prints a table (ms per real frame; positive = the lever costs that much).
--shots saves a screenshot per lever state under results/attribution-TAG/ for visual comparison.
"""
import copy, json, os, statistics, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]; TAG = ARGS[0]
def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
SCENES = opt('--scenes', 'plains,forest').split(',')
SECONDS_OVERRIDE = opt('--seconds')
OUT = os.path.join(os.path.dirname(HERE), 'results', f'attribution-{TAG}'); os.makedirs(OUT, exist_ok=True)
POSES = {'plains': ('WhiterunExterior04', dict(x=bench.START[0], y=bench.START[1], z=bench.START[2], rx=4.0, rz=247.0)),
         'forest': ('HalfMoonMillExterior', None), 'city': ('WhiterunOrigin', None), 'riften': ('RiftenOrigin', None), 'rift': ('ShorsStone', None)}
SECONDS = int(opt('--seconds', '8'))


def measure():
    cs.call('communityshaders.frames', {'action': 'start'}); time.sleep(SECONDS)
    cs.call('communityshaders.frames', {'action': 'stop'}); time.sleep(1.0)
    f = cs.call('communityshaders.frames', {'action': 'read'}).get('columns', {}).get('frameMs', [])
    return round(statistics.median(f), 3) if f else None


def con(c):
    def on(): bench.console(c)
    return on, on                                   # console toggles: the same command switches back


def feat(short, changes):
    """Bridge sets must carry the whole settings object (a partial set resets the rest)."""
    box = {}
    def on():
        g = cs.call('communityshaders.feature', {'action': 'get', 'shortName': short}); box['orig'] = g.get('settings', g)
        s = copy.deepcopy(box['orig']); s.update(changes)
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': s})
    def off():
        cs.call('communityshaders.feature', {'action': 'set', 'shortName': short, 'settings': box['orig']})
    return on, off


LEVERS = [                                           # (name, what the switched state is, (on, off))
    ('grass', 'grass hidden (tg)', con('tg')),
    ('lod', 'all LOD hidden: terrain, objects, tree LOD (tll)', con('tll')),
    ('trees', 'full trees hidden (tt)', con('tt')),
    ('sky', 'sky hidden (ts)', con('ts')),
    ('water', 'water hidden (tws)', con('tws')),
    ('ssgi', 'Screen Space GI off', feat('ScreenSpaceGI', {'Enabled': False})),
    ('ssgi-quarter', 'Screen Space GI quarter res', feat('ScreenSpaceGI', {'HalfRes': False, 'QuarterRes': True})),
    ('ssr', 'Screen Space Reflections off', feat('ScreenSpaceReflections', {'Enabled': False})),
    ('ssr-64steps', 'SSR 64 steps instead of 128', feat('ScreenSpaceReflections', {'SpecMaxSteps': 64})),
    ('vol-light', 'exterior volumetric lighting off', feat('VolumetricLighting', {'ExteriorEnabled': False})),
    ('ss-shadows', 'Screen Space Shadows off', feat('ScreenSpaceShadows', {'Enable': 0})),
    ('terrain-shadows', 'Terrain Shadows off', feat('TerrainShadows', {'EnableTerrainShadow': False})),
    ('psky', 'Physical Sky off', feat('PhysicalSky', {'enabled': False})),
    ('vol-clouds', 'volumetric clouds off', feat('PhysicalSky', {'enableVolumetricClouds': False})),
    ('cloud-march-perf', 'cloud march at the performance variant (step 1.0, range 24 km, blur 2, half-res shadow)', feat('PhysicalSky', {'marchStepScale': 1.0, 'rayMarchRange': 24.0, 'cloudBlurRadius': 2, 'halfResApShadow': True})),
    ('fg-off', 'frame generation off', feat('Upscaling', {'frameGenerationMode': 0})),
    ('dlss-balanced', 'DLSS Balanced instead of Quality', feat('Upscaling', {'qualityMode': 2})),
    # Neural Rendering, switched live in the same session (cross-run comparisons drifted by several fps over the afternoon)
    ('nr-off', 'Neural Rendering off', feat('NeuralRendering', {'enabled': False})),
    ('nr-75', 'Neural Rendering at 75% resolution', feat('NeuralRendering', {'resolutionScale': 0.75, 'resolutionScaleX': 0.75, 'resolutionScaleY': 0.75})),
    ('nr-50', 'Neural Rendering at 50% resolution', feat('NeuralRendering', {'resolutionScale': 0.5, 'resolutionScaleX': 0.5, 'resolutionScaleY': 0.5})),
    ('nr-everyframe', 'Neural Rendering every frame (alternate frames off; negative = alternate frames helps)', feat('NeuralRendering', {'alternateFrames': False})),
]

if '--no-launch' not in sys.argv: bench.launch()
bench.all_on()                                       # the baseline every lever is measured against must be everything-on
bench.console('tgm')
results = {}
for scene in SCENES:
    cell, pose = POSES[scene]
    bench.goto(cell); bench.exterior_setup()
    if pose: cs.world(action='teleport', **pose)
    time.sleep(12)
    rows = []; base = measure()
    for name, what, (on, off) in LEVERS:
        try:
            on(); time.sleep(4); m = measure()
            if '--shots' in sys.argv:
                try:
                    src = cs.shot(f'attr-{scene}-{name}'); time.sleep(1.0)
                    if src and os.path.exists(src): __import__('shutil').copy2(src, os.path.join(OUT, f'{scene}-{name}' + os.path.splitext(src)[1]))
                except Exception: pass
            off(); time.sleep(4); after = measure()
            ref = (base + after) / 2
            rows.append({'lever': name, 'what': what, 'base_ms': round(ref, 2), 'switched_ms': m, 'cost_ms': round(ref - m, 2), 'fps_base': round(1000 / ref, 1), 'fps_switched': round(1000 / m, 1)})
            print('%-7s %-16s base %6.2f ms  switched %6.2f ms  cost %+6.2f ms  (%4.1f -> %4.1f fps)  %s' % (scene, name, ref, m, ref - m, 1000 / ref, 1000 / m, what), flush=True)
            base = after
        except Exception as e:
            print(scene, name, 'ERROR', str(e)[:120], flush=True)
            try: off()
            except Exception: pass
            time.sleep(4); base = measure()
    results[scene] = rows
    json.dump(results, open(os.path.join(os.path.dirname(HERE), 'results', f'attribution-{TAG}.json'), 'w'), indent=1)
try: cs.world(action='weather', name='SunnyTU', instant=False, lock=False)
except Exception: pass
if '--no-launch' not in sys.argv and '--keep-open' not in sys.argv: bench.quit_game()

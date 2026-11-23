"""Queue job: why does Riften look hazy? Travel to the Rift, leave weather unlocked, and record which weather the game picks at
several hours plus the live fog-related settings (Exponential Height Fog, Volumetric Lighting haze, Ground Fog, Physical Sky aerosols).
usage: python rift_weather.py TAG   Output results/rift_weather-TAG.json"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
TAG = sys.argv[1]; rep = {'samples': []}
bench.launch(); bench.all_on()
bench.console('cow Tamriel 40 -24'); time.sleep(8); bench.settle()
for h in (9, 13, 17, 9, 13, 17):
    bench.console('set gamehour to %d' % h); time.sleep(25)
    w = cs.world(action='state')
    rep['samples'].append(dict(hour=round(w['gameHour'], 1), weather=w['weather'], outgoing=w.get('outgoingWeather'), pct=w.get('weatherPct')))
    print(rep['samples'][-1], flush=True)
    if h == 13: rep.setdefault('shots', []).append(cs.shot('riftweather-%s-%d' % (TAG, len(rep['samples']))))
for f in ('ExponentialHeightFog', 'VolumetricLighting', 'GroundFog'):
    rep[f] = cs.feat('get', f)
ps = cs.feat('get', 'PhysicalSky'); rep['PhysicalSky'] = {k: v for k, v in ps.items() if k.startswith(('aerosol', 'ap', 'fog', 'haze', 'ozone', 'mie'))}
json.dump(rep, open(os.path.join(os.path.dirname(HERE), 'results', 'rift_weather-%s.json' % TAG), 'w'), indent=1)
bench.finish()

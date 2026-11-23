"""Queue job: launch (or attach), god mode off, player camera, and leave the game running for the user. Run LAST and stop the runner afterwards."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, cs
bench.launch()
try: cs.call('communityshaders.testbed', {'action': 'camera', 'mode': 'player'})
except Exception: pass
try: cs.world(action='weather', name='SunnyTU', instant=False, lock=False)
except Exception: pass
print('game left open for the user', flush=True)

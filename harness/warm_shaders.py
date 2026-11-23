"""Queue job: launch once with a long main-menu wait so a full shader recompile (after a hot-reloaded Lighting.hlsl or a
build) can finish and be cached, then quit. usage: python warm_shaders.py TAG"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
env = dict(os.environ, NGVO_MENU_WAIT='2400')
sys.exit(subprocess.call([sys.executable, os.path.join(HERE, 'first_launch.py')], cwd=HERE, env=env))

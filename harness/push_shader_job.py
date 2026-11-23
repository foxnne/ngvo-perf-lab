"""Queue job (game closed): copy fork shader files into the deployed shader mod; they compile on the next launch.
usage: python push_shader_job.py TAG FORKREL [FORKREL...]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench, hot
if bench.running(): sys.exit('game open')
hot.push(sys.argv[2:])

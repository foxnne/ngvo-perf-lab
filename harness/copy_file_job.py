"""Queue job: copy one file into the modlist (game and MO2 closed). usage: python copy_file_job.py TAG SRC DST"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
import time
if bench.running(): sys.exit('game open')
if bench.mo2_running(): bench.close_mo2(); time.sleep(5)
shutil.copy2(sys.argv[2], sys.argv[3]); print('copied', sys.argv[2], '->', sys.argv[3])

"""Keeps per-launch copies of logs that the game overwrites at each start (Hitch Hunter report, AMF, SPS, FasterTextures).
usage: python logkeeper.py   (runs until killed; copies to results/hitchlogs/<launch HHMMSS>-<name>)"""
import os, re, shutil, time
SRC = 'C:/Users/foxnn/Documents/My Games/Skyrim Special Edition/SKSE/'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'hitchlogs')
NAMES = ['HitchHunter_Report_With_Fixes.log', 'HitchHunter_Compare.ini', 'ApocryphaMenuFramework.log', 'SPS.log', 'FasterTextures.log']
while True:
    for n in NAMES:
        p = SRC + n
        try:
            with open(p, errors='ignore') as f: head = f.readline()
            m = re.search(r'(\d\d):(\d\d):(\d\d)', head); key = ''.join(m.groups()) if m else 'x'
            if n.endswith('.ini'): key = time.strftime('%H%M', time.localtime(os.path.getmtime(p)))
            shutil.copy2(p, os.path.join(OUT, f'{time.strftime("%m%d")}-{key}-{n}'))
        except Exception: pass
    time.sleep(20)

"""Waits until Mod Organizer is closed, repoints its download folder to D:, then removes the C: copy (already copied and
verified by robocopy: 3193 files, 0 failed). usage: python repoint_downloads.py"""
import os, shutil, subprocess, sys, time
INI = 'C:/Modlists/NGVO 8.0 Beta/ModOrganizer.ini'
OLD = 'C:/Modlists/NVGO8.0B'; NEW = 'D:/Modlists/NVGO8.0B/downloads'
n_old = len(os.listdir(OLD + '/downloads')); n_new = len(os.listdir(NEW))
if n_new < n_old: sys.exit(f'copy incomplete: {n_new} of {n_old} entries on D:')
while 'modorganizer.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower(): time.sleep(1)
raw = open(INI, 'rb').read()
key = b'download_directory=C:/modlists/NVGO8.0B/downloads'
if key not in raw: sys.exit('download_directory line not as expected; nothing changed')
shutil.copy2(INI, INI + '.bak-pre-downloads-to-D-20261117')
open(INI, 'wb').write(raw.replace(key, b'download_directory=' + NEW.encode()))
print('ini repointed at', time.strftime('%H:%M:%S'))
time.sleep(120)   # let the next MO2 start pick the new path up before the old folder goes
if b'download_directory=' + NEW.encode() not in open(INI, 'rb').read(): sys.exit('ini was rewritten back; C: copy kept')
shutil.rmtree(OLD, ignore_errors=True)
print('C: copy removed:', not os.path.exists(OLD))

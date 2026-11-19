"""Waits for after_d.py to finish, then runs the flicker measurement."""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
def busy():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'after_d.py' }).Count"], capture_output=True, text=True).stdout.strip()
    return out not in ('', '0')
while busy(): time.sleep(30)
time.sleep(45)
p = subprocess.run([sys.executable, 'flicker.py', 'F1'], cwd=HERE, capture_output=True, text=True)
open(os.path.join(os.path.dirname(HERE), 'results', 'flicker-F1.log'), 'w').write(p.stdout + '\n' + p.stderr)

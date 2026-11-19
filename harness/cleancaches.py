"""Clear regenerable caches on C: at background priority. usage: python cleancaches.py [--dry]
- %LOCALAPPDATA%/Temp entries not modified for 2 days (the Claude scratchpad folder is kept)
- .zig-cache / zig-out / zig-pkg in project folders (skipped when git-tracked or a zig process is running)
- Community Shaders build output that is not in use (keeps skyrim-community-shaders/build/PR and PR-Tracy)
Log: audit/cleancaches.log"""
import ctypes, os, shutil, subprocess, sys, time
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00100000)
DRY = '--dry' in sys.argv
LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audit', 'cleancaches.log')
log = open(LOG, 'a', encoding='utf-8'); total = 0


def size(p):
    if os.path.isfile(p):
        try: return os.path.getsize(p)
        except OSError: return 0
    s = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try: s += os.path.getsize(os.path.join(dp, f))
            except OSError: pass
    return s


def remove(p, why):
    global total
    s = size(p)
    if not DRY:
        try:
            if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(p, ignore_errors=True)
            else: os.remove(p)
        except OSError: pass
        s -= size(p) if os.path.exists(p) else 0
    total += s
    if s > 50e6: log.write(f'{s / 1e9:7.2f} GB  {why}  {p}\n'); log.flush()
    return s


log.write(f'=== {time.strftime("%Y-%m-%d %H:%M")} {"DRY" if DRY else "RUN"}\n')
# 1 temp
T = os.path.expandvars(r'%LOCALAPPDATA%\Temp'); cut = time.time() - 2 * 86400; t = 0
for e in os.scandir(T):
    if e.name.lower() == 'claude': continue
    try:
        if e.stat(follow_symlinks=False).st_mtime < cut: t += remove(e.path, 'temp')
    except OSError: pass
log.write(f'temp total {t / 1e9:.2f} GB\n')
# 2 zig
zig_running = any(x in subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower() for x in ('zig.exe', 'zls.exe'))
z = 0
if zig_running: log.write('zig or zls running: zig caches skipped\n')
else:
    for root in (r'C:\Users\foxnn\dev\proj', r'C:\fizzy', r'C:\fizzy-stage', r'C:\src', r'C:\dev'):
        for dp, dn, fn in os.walk(root):
            if dp[len(root):].count(os.sep) > 4: dn[:] = []; continue
            for d in list(dn):
                if d in ('.zig-cache', 'zig-out', 'zig-pkg'):
                    dn.remove(d); p = os.path.join(dp, d)
                    tracked = subprocess.run(['git', '-C', dp, 'ls-files', d], capture_output=True, text=True).stdout.strip()
                    if tracked: log.write(f'git-tracked, kept: {p}\n'); continue
                    z += remove(p, 'zig')
                elif d in ('.git', 'node_modules'): dn.remove(d)
log.write(f'zig total {z / 1e9:.2f} GB\n')
# 3 build output
b = 0
for p in (r'C:\Users\foxnn\dev\skyrim-community-shaders\build\ALL', r'C:\Users\foxnn\dev\skyrim-community-shaders\build\Dev-Fast',
          r'C:\Users\foxnn\dev\scs-nr-hdr\build', r'C:\Users\foxnn\dev\cs-td\build'):
    if os.path.isdir(p): b += remove(p, 'build')
log.write(f'build total {b / 1e9:.2f} GB\nTOTAL {total / 1e9:.2f} GB {"(dry run, nothing deleted)" if DRY else "freed"}\n'); log.close()
print(open(LOG, encoding='utf-8').read()[-2500:])

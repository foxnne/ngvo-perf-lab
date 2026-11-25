r"""Shader hot reload against a running game: no restart.
  python hot.py push features/Physical Sky/Shaders/PhysicalSky/Volumetrics.cs.hlsl [more files]   copy from the fork to the deployed mod, recompile
  python hot.py define PhysicalSky/Volumetrics.cs.hlsl CLOUD_DETILE_AMOUNT 0.4                      change a #define in the DEPLOYED copy, recompile
  python hot.py reload                                                                              just recompile
Also importable: push(files), set_defines(rel, {name: value}), reload(), restore(rel)."""
import os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cs
FORK = 'C:/Users/foxnn/dev/skyrim-community-shaders'; MOD = 'C:/Modlists/NGVO 8.0 Beta/mods/Bottled Shaders - foxnne'
LOG = os.path.expanduser('~/Documents/My Games/Skyrim Special Edition/SKSE/BottledShaders.log')
_orig = {}


def deployed(rel):
    """'PhysicalSky/Volumetrics.cs.hlsl' or a fork path containing 'Shaders/' -> path in the deployed mod."""
    rel = rel.replace(chr(92), '/')
    if 'Shaders/' in rel: rel = rel.split('Shaders/', 1)[1]
    return os.path.join(MOD, 'Shaders', rel)


def status():
    return cs.call('communityshaders.inspect', {'kind': 'shadercache'})


def reload(maxwait=1500):
    """Drop the in-memory cache; unchanged shaders come back from the disk cache, changed sources recompile."""
    before = status(); size0 = os.path.getsize(LOG) if os.path.exists(LOG) else 0; t0 = time.time()
    cs.call('communityshaders.shadercache', {'action': 'clear'}); time.sleep(3)
    quiet = 0; last = None
    while time.time() - t0 < maxwait:
        s = status(); cur = (s.get('compiling'), s.get('completedTasks'))
        # compute (standalone) shaders such as the cloud march compile last and take up to ~10 min; clouds are absent until then
        quiet = quiet + 1 if (not s.get('compiling') and not s.get('standalonePending') and cur == last) else 0; last = cur
        if quiet >= 3: break
        time.sleep(1.5)
    after = status(); errs = []
    try:
        with open(LOG, 'rb') as f: f.seek(size0); tail = f.read().decode('utf-8', 'replace')
        errs = [l.strip()[:260] for l in tail.splitlines() if re.search(r'error X\d+|failed to compile|Failed to compile|compile failed', l)][:12]
    except Exception: pass
    r = {'seconds': round(time.time() - t0, 1), 'failed_before': before.get('currentFailedCount'), 'failed_after': after.get('currentFailedCount'), 'errors': errs}
    print('hot reload', r, flush=True); return r


def push(files):
    for f in files:
        src = f if os.path.isabs(f) else os.path.join(FORK, f); dst = deployed(f)
        if dst not in _orig and os.path.exists(dst): _orig[dst] = open(dst, 'rb').read()
        shutil.copy2(src, dst); print('pushed', os.path.relpath(dst, MOD), flush=True)


def set_defines(rel, defines):
    dst = deployed(rel); t = open(dst, 'rb').read()
    if dst not in _orig: _orig[dst] = t
    s = t.decode('utf-8')
    for name, value in defines.items():
        s, n = re.subn(r'(?m)^(\s*#\s*define\s+' + re.escape(name) + r'\s+)(\S+)', lambda m: m.group(1) + str(value), s, count=1)
        if n != 1: raise SystemExit(f'#define {name} not found in {rel}')
    open(dst, 'wb').write(s.encode('utf-8'))


def restore(rel=None):
    for dst, data in list(_orig.items()):
        if rel is None or dst == deployed(rel): open(dst, 'wb').write(data); del _orig[dst]


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'push': push(sys.argv[2:]); reload()
    elif cmd == 'define': set_defines(sys.argv[2], {sys.argv[3]: sys.argv[4]}); reload()
    elif cmd == 'reload': reload()

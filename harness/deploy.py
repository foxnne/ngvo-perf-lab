"""Deploy a CS fork build into the MO2 mod `Bottled Shaders - foxnne` (game and MO2 must be closed).

usage: python deploy.py PRESET [--dry]     e.g. PR-Tracy or PR
Copies CommunityShaders.dll and every packaged file (package/ + features/*/ from the source tree) that differs, except files we own in the mod:
the Streamline runtime DLLs (newer than the repo's) and the Snow Cover blacklist. Overwritten files are backed up.
"""
import filecmp, os, shutil, sys, time
FORK = 'C:/Users/foxnn/dev/skyrim-community-shaders'
MOD = 'C:/Modlists/NGVO 8.0 Beta/mods/Bottled Shaders - foxnne'
KEEP = ('shaders/upscaling/streamline/', 'shaders/snowcover/blacklist.txt')
preset = sys.argv[1]; dry = '--dry' in sys.argv
aio = f'{FORK}/build/{preset}/aio'; dll = f'{FORK}/build/{preset}/Release/CommunityShaders.dll'
bak = f'C:/Modlists/backups/bottled-deploy-{time.strftime("%Y%m%d-%H%M%S")}'
changed = added = 0
def put(src, rel):
    global changed, added
    dst = os.path.join(MOD, rel)
    if os.path.exists(dst):
        if filecmp.cmp(src, dst, shallow=False): return
        changed += 1
        if not dry:
            b = os.path.join(bak, rel); os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(dst, b)
    else: added += 1
    print(('would copy ' if dry else 'copy ') + rel)
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
# PR presets do not package an AIO folder, so the packaged files come from the source tree:
# package/ (core) overlaid by every features/<Feature>/ folder, the same layout the AIO zip has.
roots = [f'{FORK}/package'] + sorted(os.path.join(f'{FORK}/features', d) for d in os.listdir(f'{FORK}/features') if os.path.isdir(os.path.join(f'{FORK}/features', d)))
seen = {}
for root in roots:
    for r, _, fs in os.walk(root):
        for f in fs:
            src = os.path.join(r, f); rel = os.path.relpath(src, root).replace(chr(92), '/')
            seen[rel.lower()] = (src, rel)
for key, (src, rel) in sorted(seen.items()):
    if key.startswith(KEEP) or key in KEEP or key.endswith('communityshaders.dll') or key.endswith(('.md', '.gitignore')): continue
    put(src, rel)
put(dll, 'SKSE/Plugins/CommunityShaders.dll')
print(f'{changed} changed, {added} added' + ('' if dry else f'; backups in {bak}'))

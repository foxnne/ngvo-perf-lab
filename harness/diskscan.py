"""Disk usage survey of C: at background priority (read-only). usage: python diskscan.py [depth=4]
Writes audit/disk_usage.tsv (bytes, files, path) for every directory down to the depth, largest first."""
import ctypes, os, sys, time
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00100000)
DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 4
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audit', 'disk_usage.tsv')
rows = []; t0 = time.time()


def walk(path, depth):
    total = 0; files = 0
    try: it = list(os.scandir(path))
    except OSError: return 0, 0
    for e in it:
        try:
            if e.is_symlink() or (e.stat(follow_symlinks=False).st_file_attributes & 0x400): continue   # reparse points
            if e.is_dir(follow_symlinks=False):
                s, n = walk(e.path, depth + 1); total += s; files += n
            else:
                total += e.stat(follow_symlinks=False).st_size; files += 1
        except OSError: pass
    if depth <= DEPTH: rows.append((total, files, path))
    return total, files


walk('C:\\', 0)
rows.sort(reverse=True)
with open(OUT, 'w', encoding='utf-8') as f:
    for s, n, p in rows:
        if s > 200e6: f.write(f'{s}\t{n}\t{p}\n')
print('done in %.0f s, %d dirs listed' % (time.time() - t0, len(rows)))

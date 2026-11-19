"""Read the live PresentMon CSV while PresentMon still has it open (needs shared read). usage: python pmread.py [tail_rows]"""
import csv, ctypes, io, msvcrt, os, sys
from ctypes import wintypes
P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'presentmon-live.csv')
def open_shared(path):
    k = ctypes.windll.kernel32; k.CreateFileW.restype = wintypes.HANDLE
    h = k.CreateFileW(path, 0x80000000, 0x7, None, 3, 0x80, None)          # GENERIC_READ, share read|write|delete, OPEN_EXISTING
    if h in (None, wintypes.HANDLE(-1).value, -1): raise OSError(ctypes.GetLastError(), 'cannot open shared')
    return os.fdopen(msvcrt.open_osfhandle(h, os.O_RDONLY), 'r', encoding='utf-8', errors='ignore', newline='')
if __name__ == '__main__':
    import collections
    rows = list(csv.DictReader(open_shared(P)))
    print(len(rows), 'rows; columns:', list(rows[0].keys()) if rows else None)
    if rows:
        print('first', {k: rows[0][k] for k in list(rows[0])[:8]}); print('last ', {k: rows[-1][k] for k in list(rows[-1])[:8]})
        for col in ('FrameType', 'PresentMode', 'AllowsTearing'):
            if col in rows[0]: print(col, collections.Counter(r[col] for r in rows).most_common(4))

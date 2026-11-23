"""Read bytes of the running SkyrimSE.exe at Address Library IDs (read-only). usage: python exe_peek.py ID+0xOFF[:len] ..."""
import struct, sys, ctypes, ctypes.wintypes as wt, subprocess
LIB = r'C:\Modlists\NGVO 8.0 Beta\mods\Address Library for SKSE Plugins\SKSE\Plugins\versionlib-1-6-1170-0.bin'
def load():
    b = open(LIB, 'rb').read(); p = 0
    fmt, = struct.unpack_from('<i', b, p); p += 4; p += 16
    n, = struct.unpack_from('<i', b, p); p += 4 + n
    ps, cnt = struct.unpack_from('<ii', b, p); p += 8
    d = {}; pid = 0; poff = 0
    def rd(f):
        nonlocal p
        v, = struct.unpack_from(f, b, p); p += struct.calcsize(f); return v
    for _ in range(cnt):
        t = rd('<B'); lo = t & 0xF; hi = t >> 4
        if lo == 0: i = rd('<Q')
        elif lo == 1: i = pid + 1
        elif lo == 2: i = pid + rd('<B')
        elif lo == 3: i = pid - rd('<B')
        elif lo == 4: i = pid + rd('<H')
        elif lo == 5: i = pid - rd('<H')
        elif lo == 6: i = rd('<H')
        else: i = rd('<I')
        tmp = poff // ps if hi & 8 else poff; h = hi & 7
        if h == 0: o = rd('<Q')
        elif h == 1: o = tmp + 1
        elif h == 2: o = tmp + rd('<B')
        elif h == 3: o = tmp - rd('<B')
        elif h == 4: o = tmp + rd('<H')
        elif h == 5: o = tmp - rd('<H')
        elif h == 6: o = rd('<H')
        else: o = rd('<I')
        if hi & 8: o *= ps
        d[i] = o; pid = i; poff = o
    return d
def proc():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SkyrimSE.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
    pid = int(out.split(',')[1].strip('"'))
    k = ctypes.WinDLL('kernel32', use_last_error=True); ps = ctypes.WinDLL('psapi', use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE; h = k.OpenProcess(0x0410, False, pid)
    mods = (wt.HMODULE * 4)(); need = wt.DWORD()
    ps.EnumProcessModulesEx(wt.HANDLE(h), mods, ctypes.sizeof(mods), ctypes.byref(need), 3)
    return k, h, mods[0]
if __name__ == '__main__':
    d = load(); k, h, base = proc(); print('ids', len(d), 'base %X' % base)
    for a in sys.argv[1:]:
        spec, _, ln = a.partition(':'); i, _, off = spec.partition('+'); i = int(i); off = int(off or '0', 16); ln = int(ln or 16)
        rva = d[i] + off; buf = (ctypes.c_ubyte * ln)(); got = ctypes.c_size_t()
        k.ReadProcessMemory(wt.HANDLE(h), ctypes.c_void_p(base + rva), buf, ln, ctypes.byref(got))
        print('%s rva %X: %s' % (a, rva, bytes(buf).hex(' ')))

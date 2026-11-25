"""Resolve Community Shaders DLL offsets (the '+X' addresses in HitchSampler reports) to function names with
Windows' dbghelp and the build's PDB. The PDB must be from the build that is deployed (BottledShaders.log is
rewritten at every game start, so resolve a log while that build is still the deployed one).
usage: python cs_symbols.py 845313 4B43BB ...   (hex offsets)    or import: name(offset) -> 'Function+0x12'"""
import ctypes, ctypes.wintypes as w, os, sys

DLL = r'C:\Users\foxnn\dev\skyrim-community-shaders\build\PR-Tracy\Release\CommunityShaders.dll'
BASE = 0x180000000
_ready = None


def _init():
    global _ready
    if _ready is None:
        dh = ctypes.WinDLL('dbghelp', use_last_error=True)
        dh.SymInitializeW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, w.BOOL]
        dh.SymLoadModuleExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint64, w.DWORD, ctypes.c_void_p, w.DWORD]
        dh.SymLoadModuleExW.restype = ctypes.c_uint64
        dh.SymFromAddrW.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64), ctypes.c_void_p]
        dh.SymSetOptions(0x2)  # SYMOPT_UNDNAME
        proc = ctypes.c_void_p(0x5157)  # a unique session handle; no process is attached
        if not dh.SymInitializeW(proc, os.path.dirname(DLL), False) or not dh.SymLoadModuleExW(proc, None, DLL, None, BASE, 0, None, 0):
            raise OSError('dbghelp could not load %s (%d)' % (DLL, ctypes.get_last_error()))
        _ready = (dh, proc)
    return _ready


def name(offset):
    dh, proc = _init()
    buf = ctypes.create_string_buffer(88 + 2 * 512)  # SYMBOL_INFOW: SizeOfStruct @0, NameLen @76, MaxNameLen @80, Name @84
    ctypes.c_ulong.from_buffer(buf, 0).value = 88
    ctypes.c_ulong.from_buffer(buf, 80).value = 511
    disp = ctypes.c_uint64()
    if not dh.SymFromAddrW(proc, BASE + offset, ctypes.byref(disp), buf):
        return '?'
    return '%s+0x%X' % (ctypes.wstring_at(ctypes.addressof(buf) + 84, ctypes.c_ulong.from_buffer(buf, 76).value), disp.value)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        print(a, name(int(a, 16)))

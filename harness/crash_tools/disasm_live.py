import sys, struct, ctypes, ctypes.wintypes as wt, subprocess, os
sys.path.insert(0, r'C:\Users\foxnn\dev\ngvo-perf-lab\harness')
import exe_peek
DUMPBIN = r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\dumpbin.exe'
d = exe_peek.load(); k, h, base = exe_peek.proc()
out = os.path.dirname(os.path.abspath(__file__))
for a in sys.argv[1:]:
    spec, _, ln = a.partition(':'); i, _, off = spec.partition('+'); i = int(i); off = int(off or '0', 16); ln = int(ln, 16)
    rva = d[i] + off; buf = (ctypes.c_ubyte * ln)(); got = ctypes.c_size_t()
    k.ReadProcessMemory(wt.HANDLE(h), ctypes.c_void_p(base + rva), buf, ln, ctypes.byref(got))
    code = bytes(buf)
    hdr = struct.pack('<HHIIIHH', 0x8664, 1, 0, 0, 0, 0, 0)
    sec = struct.pack('<8sIIIIIIHHI', b'.text', 0, 0, len(code), 20 + 40, 0, 0, 0, 0, 0x60500020)
    p = os.path.join(out, 'f%d.obj' % i); open(p, 'wb').write(hdr + sec + code)
    r = subprocess.run([DUMPBIN, '/nologo', '/disasm:nobytes', p], capture_output=True, text=True).stdout
    print('==== id %d rva %X (+0x%X)' % (i, rva, off))
    for line in r.splitlines():
        line = line.strip()
        if ':' in line[:20]:
            try:
                o = int(line.split(':')[0], 16); print('+%04X  %s' % (o + off, line.split(':', 1)[1].strip()))
            except ValueError: pass

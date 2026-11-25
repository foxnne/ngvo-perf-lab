import sys, struct, ctypes, ctypes.wintypes as wt
sys.path.insert(0, r'C:\Users\foxnn\dev\ngvo-perf-lab\harness')
import exe_peek
d = exe_peek.load(); k, h, base = exe_peek.proc()
ps = ctypes.WinDLL('psapi', use_last_error=True)
class MI(ctypes.Structure): _fields_=[('base',ctypes.c_void_p),('size',wt.DWORD),('entry',ctypes.c_void_p)]
def modules():
    mods=(ctypes.c_void_p*2048)(); need=wt.DWORD()
    ps.EnumProcessModulesEx(wt.HANDLE(h), mods, ctypes.sizeof(mods), ctypes.byref(need), 3)
    out=[]
    for m in mods[:need.value//8]:
        if not m: continue
        mi=MI(); ps.GetModuleInformation(wt.HANDLE(h), ctypes.c_void_p(m), ctypes.byref(mi), ctypes.sizeof(mi))
        nm=ctypes.create_unicode_buffer(260); ps.GetModuleBaseNameW(wt.HANDLE(h), ctypes.c_void_p(m), nm, 260)
        out.append((m, mi.size, nm.value))
    return out
MODS=None
def who(a):
    global MODS
    if MODS is None: MODS=modules()
    for b,s,n in MODS:
        if b<=a<b+s: return '%s+%X'%(n,a-b)
    return '?'
def rd(addr, n):
    buf=(ctypes.c_ubyte*n)(); got=ctypes.c_size_t()
    k.ReadProcessMemory(wt.HANDLE(h), ctypes.c_void_p(addr), buf, n, ctypes.byref(got)); return bytes(buf[:got.value])
if __name__=='__main__':
    print('base %X'%base)
    for a in sys.argv[1:]:
        kind,_,rest=a.partition('=')
        if kind=='id':   # id=107498+0x0:16
            spec,_,ln=rest.partition(':'); i,_,off=spec.partition('+'); addr=base+d[int(i)]+int(off or '0',16)
            b=rd(addr,int(ln or 16)); print(a, '%X'%addr, b.hex(' '))
        elif kind=='jmp':  # decode hook at id+off
            spec=rest; i,_,off=spec.partition('+'); addr=base+d[int(i)]+int(off or '0',16)
            b=rd(addr,16)
            for hop in range(4):
                if b[0]==0xE9 or b[0]==0xE8:
                    t=addr+5+struct.unpack_from('<i',b,1)[0]
                elif b[0]==0xFF and b[1]==0x25:
                    t=struct.unpack('<Q',rd(addr+6+struct.unpack_from('<i',b,2)[0],8))[0]
                else: break
                print(a,'hop',hop,'%X'%addr,'->','%X'%t, who(t)); addr=t; b=rd(addr,16)
        elif kind=='q':  # abs qword list: q=ADDR:n
            ad,_,n=rest.partition(':'); ad=int(ad,16)
            b=rd(ad,8*int(n or 1))
            for j in range(0,len(b),8):
                v=struct.unpack_from('<Q',b,j)[0]; print('%X: %016X %s'%(ad+j,v,who(v)))
        elif kind=='vt': # vt=rva:n  qwords at image rva
            ad,_,n=rest.partition(':'); ad=base+int(ad,16)
            b=rd(ad,8*int(n or 1))
            for j in range(0,len(b),8):
                v=struct.unpack_from('<Q',b,j)[0]; print('+%X: %016X %s'%(j,v,who(v)))

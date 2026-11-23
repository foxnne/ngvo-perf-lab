"""Queue job: what is the game's committed memory made of? At the loaded save and on the plains: process private bytes / working
set, GPU process memory counters (dedicated VRAM, shared = system RAM used for GPU resources incl. VRAM overflow), and a
VirtualQueryEx walk of committed memory by type (private / mapped / image) with private regions bucketed by size and the largest
regions listed (big same-size blocks point at specific allocators: engine heap pools, D3D12 heaps, driver, CS buffers).
usage: python mem_probe.py TAG   Output results/memory/probe-TAG.json"""
import ctypes, ctypes.wintypes as W, json, os, subprocess, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
TAG = sys.argv[1]; OUT = os.path.join(os.path.dirname(HERE), 'results', 'memory'); os.makedirs(OUT, exist_ok=True)


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p), ('AllocationProtect', W.DWORD),
                ('PartitionId', W.WORD), ('RegionSize', ctypes.c_size_t), ('State', W.DWORD), ('Protect', W.DWORD), ('Type', W.DWORD)]


def pid():
    o = subprocess.run(['powershell', '-NoProfile', '-Command', '(Get-Process SkyrimSE | Select-Object -First 1).Id'], capture_output=True, text=True).stdout.strip()
    return int(o)


def regions(p):
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.restype = W.HANDLE
    k.VirtualQueryEx.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
    k.VirtualQueryEx.restype = ctypes.c_size_t
    h = k.OpenProcess(0x0400 | 0x0010, False, p)
    addr, m = 0, MBI(); allocs = collections.defaultdict(int); kinds = collections.Counter()
    while k.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(m), ctypes.sizeof(m)):
        if m.State == 0x1000:  # MEM_COMMIT
            t = {0x20000: 'private', 0x40000: 'mapped', 0x1000000: 'image'}.get(m.Type, hex(m.Type))
            kinds[t] += m.RegionSize
            if t == 'private':
                allocs[m.AllocationBase or 0] += m.RegionSize
        addr = (m.BaseAddress or 0) + m.RegionSize
        if addr >= 0x7FFFFFFFFFFF: break
    k.CloseHandle(h)
    buckets = collections.Counter(); bcount = collections.Counter()
    for a, s in allocs.items():
        b = '<1MB' if s < 1 << 20 else '1-16MB' if s < 16 << 20 else '16-64MB' if s < 64 << 20 else '64-256MB' if s < 256 << 20 else '256MB-1GB' if s < 1 << 30 else '>=1GB'
        buckets[b] += s; bcount[b] += 1
    top = sorted(allocs.items(), key=lambda x: -x[1])[:25]
    sizes = collections.Counter(round(s / (1 << 20)) for a, s in allocs.items() if s >= 16 << 20)
    MB = lambda v: round(v / (1 << 20))
    return dict(commit_by_type_mb={k2: MB(v) for k2, v in kinds.items()},
                private_by_alloc_size_mb={b: MB(v) for b, v in buckets.items()}, private_alloc_counts=dict(bcount),
                top_private_allocs_mb=[(hex(a), MB(s)) for a, s in top],
                repeated_alloc_sizes_mb=sorted(((s, n) for s, n in sizes.items() if n >= 3), key=lambda x: -x[0] * x[1])[:15])


def gpu(p):
    ps = ("$c='\\GPU Process Memory(pid_%d*)\\Dedicated Usage','\\GPU Process Memory(pid_%d*)\\Shared Usage','\\GPU Process Memory(pid_%d*)\\Total Committed';"
          "(Get-Counter $c -ErrorAction SilentlyContinue).CounterSamples | ForEach-Object { $_.Path + '=' + [math]::Round($_.CookedValue/1MB) }") % (p, p, p)
    o = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.splitlines()
    r = collections.defaultdict(int)
    for l in o:
        if '=' not in l: continue
        k2, v = l.rsplit('=', 1); r[k2.split('\\')[-1]] += int(v)
    return dict(r)


def proc():
    ps = ("$p=Get-Process SkyrimSE | Select-Object -First 1; $os=Get-CimInstance Win32_OperatingSystem; "
          "'{0} {1} {2}' -f [math]::Round($p.PrivateMemorySize64/1MB), [math]::Round($p.WorkingSet64/1MB), [math]::Round($os.FreePhysicalMemory/1KB)")
    o = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.split()
    return dict(private_mb=int(o[0]), working_set_mb=int(o[1]), system_free_mb=int(o[2]))


rep = []


def rec(name):
    time.sleep(20); p = pid()
    r = dict(step=name, **proc(), gpu_mb=gpu(p), **regions(p)); rep.append(r)
    print(json.dumps(r), flush=True)


bench.launch(); bench.all_on(); rec('0_loaded_save')
try:
    bench.goto('WhiterunExterior04'); rec('plains')
finally:
    json.dump(rep, open(os.path.join(OUT, 'probe-' + TAG + '.json'), 'w'), indent=1)
bench.finish()

"""Attached to a running game: is the hitching RAM paging or VRAM pressure? Samples system Available MB, hard-fault page reads,
the game's GPU dedicated/shared memory and the adapter's dedicated usage, at the current spot and after travelling to the plains.
usage: python mem_pressure.py"""
import os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bench
BS = chr(92)


def counters(n=6):
    c = [BS + 'Memory' + BS + 'Available MBytes', BS + 'Memory' + BS + 'Pages Input/sec', BS + 'Memory' + BS + 'Page Reads/sec',
         BS + 'GPU Process Memory(pid_PID*)' + BS + 'Dedicated Usage', BS + 'GPU Process Memory(pid_PID*)' + BS + 'Shared Usage',
         BS + 'GPU Adapter Memory(*)' + BS + 'Dedicated Usage']
    lst = ','.join("'" + x + "'" for x in c)
    ps = ("$p=(Get-Process SkyrimSE).Id; $c=@(" + lst + ") | ForEach-Object { $_ -replace 'PID', $p }; "
          "(Get-Counter $c -SampleInterval 2 -MaxSamples " + str(n) + ").CounterSamples | Group-Object Path | ForEach-Object { "
          "$_.Name + ' = avg ' + [math]::Round(($_.Group | Measure-Object CookedValue -Average).Average) + ' max ' + "
          "[math]::Round(($_.Group | Measure-Object CookedValue -Maximum).Maximum) }")
    for l in subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.splitlines():
        if '=' in l:
            name, v = l.split(' = ', 1)
            if 'memory(' in name.lower() and 'usage' in name.lower():
                kind = 'adapter' if 'adapter' in name.lower() else 'game'
                print('   %-34s %s (bytes)' % (kind + ' ' + name.rsplit(BS, 1)[-1], v), flush=True)
            else:
                print('   %-34s %s' % (name.rsplit(BS, 1)[-1], v), flush=True)


print('here:'); counters()
if '--plains' in sys.argv:
    bench.goto('WhiterunExterior04'); time.sleep(15)
    print('plains:'); counters()

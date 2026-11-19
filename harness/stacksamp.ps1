param([string]$Out,[int]$Seconds=180,[int]$DelayMs=10,[int]$MaxFrames=40)
# Samples the game's main thread with a full stack walk (module+RVA per frame), wall-clock stamped.
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class SW {
  [DllImport("kernel32.dll")] public static extern IntPtr OpenThread(uint access, bool inherit, uint tid);
  [DllImport("kernel32.dll")] public static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
  [DllImport("kernel32.dll")] public static extern uint SuspendThread(IntPtr h);
  [DllImport("kernel32.dll")] public static extern uint ResumeThread(IntPtr h);
  [DllImport("kernel32.dll")] public static extern bool GetThreadContext(IntPtr h, IntPtr ctx);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
  [DllImport("kernel32.dll", CharSet=CharSet.Ansi)] public static extern IntPtr LoadLibraryA(string n);
  [DllImport("kernel32.dll", CharSet=CharSet.Ansi)] public static extern IntPtr GetProcAddress(IntPtr h, string n);
  [DllImport("dbghelp.dll")] public static extern uint SymSetOptions(uint o);
  [DllImport("dbghelp.dll", CharSet=CharSet.Ansi)] public static extern bool SymInitialize(IntPtr hProcess, string path, bool invade);
  [DllImport("dbghelp.dll")] public static extern bool StackWalk64(uint machine, IntPtr hProcess, IntPtr hThread, IntPtr frame, IntPtr ctx, IntPtr readMem, IntPtr funcTable, IntPtr getModBase, IntPtr translate);
  static IntPtr hp, ft, mb, frame, ctxRaw, ctx;
  public static bool Init(uint pid) {
    hp = OpenProcess(0x0410 | 0x0400, false, pid); if (hp == IntPtr.Zero) return false;
    SymSetOptions(0x00000004 | 0x00000010); // DEFERRED_LOADS | LOAD_LINES
    if (!SymInitialize(hp, null, true)) return false;
    IntPtr d = LoadLibraryA("dbghelp.dll");
    ft = GetProcAddress(d, "SymFunctionTableAccess64"); mb = GetProcAddress(d, "SymGetModuleBase64");
    frame = Marshal.AllocHGlobal(512); ctxRaw = Marshal.AllocHGlobal(1232 + 32);
    ctx = (IntPtr)(((long)ctxRaw + 15) & ~15L); return true;
  }
  // returns number of frames written into pcs
  public static int Sample(IntPtr hThread, long[] pcs) {
    if (SuspendThread(hThread) == 0xFFFFFFFF) return 0;
    int n = 0;
    try {
      for (int k = 0; k < 1232; k += 8) Marshal.WriteInt64(ctx, k, 0);
      Marshal.WriteInt32(ctx, 0x30, 0x10000B);
      if (!GetThreadContext(hThread, ctx)) return 0;
      for (int k = 0; k < 512; k += 8) Marshal.WriteInt64(frame, k, 0);
      long rip = Marshal.ReadInt64(ctx, 0xF8), rsp = Marshal.ReadInt64(ctx, 0x98), rbp = Marshal.ReadInt64(ctx, 0xA0);
      Marshal.WriteInt64(frame, 0, rip);  Marshal.WriteInt32(frame, 12, 3);
      Marshal.WriteInt64(frame, 32, rbp); Marshal.WriteInt32(frame, 44, 3);
      Marshal.WriteInt64(frame, 48, rsp); Marshal.WriteInt32(frame, 60, 3);
      while (n < pcs.Length) {
        if (!StackWalk64(0x8664, hp, hThread, frame, ctx, IntPtr.Zero, ft, mb, IntPtr.Zero)) break;
        long pc = Marshal.ReadInt64(frame, 0); if (pc == 0) break;
        pcs[n++] = pc;
      }
    } finally { ResumeThread(hThread); }
    return n;
  }
}
"@
$p = Get-Process SkyrimSE | Sort-Object WorkingSet64 -Descending | Select-Object -First 1
$main = ($p.Threads | Sort-Object StartTime | Select-Object -First 1).Id
if (-not [SW]::Init([uint32]$p.Id)) { "init failed" | Out-File "$Out.info" -Encoding ascii; exit 1 }
$mods = $p.Modules | ForEach-Object { [pscustomobject]@{ N = $_.ModuleName; B = [int64]$_.BaseAddress; E = [int64]$_.BaseAddress + $_.ModuleMemorySize } } | Sort-Object B
$mb = [int64[]]($mods | ForEach-Object { $_.B }); $me = [int64[]]($mods | ForEach-Object { $_.E }); $mn = [string[]]($mods | ForEach-Object { $_.N })
"main tid $main pid $($p.Id) modules $($mods.Count)" | Out-File "$Out.info" -Encoding ascii
$h = [SW]::OpenThread(0x1A, $false, [uint32]$main)
$pcs = New-Object 'long[]' $MaxFrames
$end = (Get-Date).AddSeconds($Seconds); $sb = New-Object System.Text.StringBuilder; $n = 0
$epoch = [datetime]'1970-01-01'
while ((Get-Date) -lt $end) {
  $c = [SW]::Sample($h, $pcs)
  if ($c -gt 0) {
    $ts = [int64]([datetime]::UtcNow - $epoch).TotalMilliseconds
    [void]$sb.Append($ts)
    for ($i = 0; $i -lt $c; $i++) {
      $a = $pcs[$i]; $idx = [Array]::BinarySearch($mb, $a); if ($idx -lt 0) { $idx = (-bnot $idx) - 1 }
      if ($idx -ge 0 -and $a -lt $me[$idx]) { [void]$sb.Append((',{0}+{1:X}' -f $mn[$idx], ($a - $mb[$idx]))) } else { [void]$sb.Append(',?') }
    }
    [void]$sb.AppendLine(); $n++
    if ($n % 300 -eq 0) { $sb.ToString() | Out-File $Out -Append -Encoding ascii -NoNewline; [void]$sb.Clear() }
  }
  Start-Sleep -Milliseconds $DelayMs
}
$sb.ToString() | Out-File $Out -Append -Encoding ascii -NoNewline
"done $n samples" | Out-File "$Out.info" -Append -Encoding ascii

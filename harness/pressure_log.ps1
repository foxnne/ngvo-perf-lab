# Log RAM/VRAM pressure every 10 s while SkyrimSE runs (waits up to 10 min for it to start). Output: CSV path given as arg.
param([string]$Out)
"time,avail_mb,pages_in_per_s,adapter_vram_mb,game_ws_mb,game_priv_mb" | Out-File -Encoding utf8 $Out
$t0 = Get-Date
while (-not (Get-Process SkyrimSE -ErrorAction SilentlyContinue)) { if (((Get-Date) - $t0).TotalMinutes -gt 10) { exit }; Start-Sleep 5 }
while ($p = Get-Process SkyrimSE -ErrorAction SilentlyContinue | Select-Object -First 1) {
    $s = (Get-Counter '\Memory\Available MBytes','\Memory\Pages Input/sec','\GPU Adapter Memory(*)\Dedicated Usage' -ErrorAction SilentlyContinue).CounterSamples
    $a = ($s | Where-Object Path -match 'available').CookedValue
    $pi = ($s | Where-Object Path -match 'pages input').CookedValue
    $v = (($s | Where-Object Path -match 'dedicated' | Measure-Object CookedValue -Maximum).Maximum) / 1MB
    "{0},{1},{2},{3},{4},{5}" -f (Get-Date -Format HH:mm:ss), [int]$a, [int]$pi, [int]$v, [int]($p.WorkingSet64/1MB), [int]($p.PrivateMemorySize64/1MB) | Out-File -Append -Encoding utf8 $Out
    Start-Sleep 10
}

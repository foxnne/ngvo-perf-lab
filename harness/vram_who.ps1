$s = Get-Counter '\GPU Process Memory(*)\Dedicated Usage' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CounterSamples | Where-Object { $_.CookedValue -gt 40MB } | Sort-Object CookedValue -Descending | Select-Object -First 6
$o = foreach ($x in $s) { $id = ($x.InstanceName -split '_')[1]; '{0} {1:N0}' -f (Get-Process -Id $id -ErrorAction SilentlyContinue).ProcessName, ($x.CookedValue/1MB) }
($o -join ' | ')

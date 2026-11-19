# Waits until the game is not running (between benchmark runs), then builds the PR-Tracy preset. Does not deploy.
while (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { Start-Sleep 5 }
& "$PSScriptRoot\build_tracy.ps1"

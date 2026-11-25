& "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\Launch-VsDevShell.ps1" -Arch amd64 -HostArch amd64 -SkipAutomaticLocation | Out-Null
Set-Location C:\Users\foxnn\dev\skyrim-community-shaders
$env:VCPKG_ROOT = 'C:\Users\foxnn\dev\vcpkg'
$log = 'C:\Users\foxnn\AppData\Local\Temp\claude\3faf89cbf3e7ed47\cb71cf91-a08f-4a3e-8d3b-cf0591936015\scratchpad\cs-prtracy-build.log'
"== configure $(Get-Date -f HH:mm:ss)" | Out-File $log -Encoding ascii
cmd /c "cmake --preset PR-Tracy >> ""$log"" 2>&1"
"CONFIGURE_EXIT $LASTEXITCODE $(Get-Date -f HH:mm:ss)" | Out-File $log -Append -Encoding ascii
cmd /c "cmake --build --preset PR-Tracy >> ""$log"" 2>&1"
"BUILD_EXIT $LASTEXITCODE $(Get-Date -f HH:mm:ss)" | Out-File $log -Append -Encoding ascii

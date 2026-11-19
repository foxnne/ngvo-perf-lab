& "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\Launch-VsDevShell.ps1" -Arch amd64 -HostArch amd64 -SkipAutomaticLocation | Out-Null
Set-Location C:\Users\foxnn\dev\skyrim-community-shaders
$env:VCPKG_ROOT = 'C:\Users\foxnn\dev\vcpkg'
$log = 'C:\Users\foxnn\AppData\Local\Temp\claude\3faf89cbf3e7ed47\f00ecae3-865a-43f6-bdb9-8828c99c0a95\scratchpad\cs-pr-build.log'
"== configure $(Get-Date -f HH:mm:ss)" | Out-File $log -Encoding ascii
cmd /c "cmake --preset PR >> ""$log"" 2>&1"
"CONFIGURE_EXIT $LASTEXITCODE $(Get-Date -f HH:mm:ss)" | Out-File $log -Append -Encoding ascii
cmd /c "cmake --build --preset PR >> ""$log"" 2>&1"
"BUILD_EXIT $LASTEXITCODE $(Get-Date -f HH:mm:ss)" | Out-File $log -Append -Encoding ascii

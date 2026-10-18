param([string]$Rom = "$PSScriptRoot\build\GAYBOY.gb", [ValidateSet('SameBoy','PyBoy','BGB')][string]$Emulator = 'SameBoy')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$romPath = (Resolve-Path -LiteralPath $Rom).Path
$pidFile = Join-Path $PSScriptRoot 'build\emulator.pid'
if (Test-Path -LiteralPath $pidFile) {
    $previousId = [int](Get-Content -LiteralPath $pidFile)
    $previous = Get-Process -Id $previousId -ErrorAction SilentlyContinue
    $details = Get-CimInstance Win32_Process -Filter "ProcessId = $previousId" -ErrorAction SilentlyContinue
    if ($previous -and $details.CommandLine -like "*$PSScriptRoot*" -and ($details.CommandLine -like '*pyboy*' -or $details.CommandLine -like '*run_emulator.py*' -or $details.CommandLine -like '*sameboy.exe*' -or $details.CommandLine -like '*bgb64.exe*')) {
        [void]$previous.CloseMainWindow()
        if (-not $previous.WaitForExit(2000)) { Stop-Process -Id $previousId }
    }
}
if ($Emulator -eq 'BGB') {
    $bgbPath = Join-Path $PSScriptRoot 'tools\bgb\bgb64.exe'
    if (!(Test-Path -LiteralPath $bgbPath)) { throw 'BGB is missing from tools/bgb.' }
    $bgb = Start-Process -FilePath $bgbPath -ArgumentList '-rom',('"' + $romPath + '"') -WorkingDirectory (Split-Path $bgbPath) -WindowStyle Normal -PassThru
    $bgb.Id | Set-Content -LiteralPath $pidFile
    Write-Output "BGB launched: $romPath (PID $($bgb.Id)). Arrows, S=A, A=B, Shift=Select, Enter=Start."
    return
}
if ($Emulator -eq 'SameBoy') {
    $sameboyPath = Join-Path $PSScriptRoot 'tools\sameboy\sameboy.exe'
    if (!(Test-Path -LiteralPath $sameboyPath)) { throw 'SameBoy is missing from tools/sameboy.' }
    $pythonWindow = Join-Path (Split-Path (Get-Command python).Source) 'pythonw.exe'
    $runner = Join-Path $PSScriptRoot 'tools\run_sameboy.py'
    $sameboy = Start-Process -FilePath $pythonWindow -ArgumentList ('"' + $runner + '"'),('"' + $romPath + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$PSScriptRoot\build\emulator.log" -RedirectStandardError "$PSScriptRoot\build\emulator-errors.log" -PassThru
    $sameboy.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build\emulator-guard.pid')
    Write-Output "SameBoy launched (DMG, project keybindings): $romPath"
    return
}
$pythonPath = (Get-Command python).Source
$pythonWindow = Join-Path (Split-Path $pythonPath) 'pythonw.exe'
$runner = Join-Path $PSScriptRoot 'tools\run_emulator.py'
$emulator = Start-Process -FilePath $pythonWindow -ArgumentList ('"' + $runner + '"'),('"' + $romPath + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Normal -RedirectStandardOutput "$PSScriptRoot\build\emulator.log" -RedirectStandardError "$PSScriptRoot\build\emulator-errors.log" -PassThru
$emulator.Id | Set-Content -LiteralPath $pidFile
Write-Output "PyBoy launched: $romPath (PID $($emulator.Id))"

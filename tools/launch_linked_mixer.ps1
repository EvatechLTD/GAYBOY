param([string]$LeftRom = "$PSScriptRoot\..\build\linked-test\LEFT\LEFT.gb", [string]$RightRom = "$PSScriptRoot\..\build\linked-test\RIGHT\RIGHT.gb")
$ErrorActionPreference = 'Stop'
$emulatorPath = (Resolve-Path "$PSScriptRoot\bgb\bgb64.exe").Path
$leftRomPath = (Resolve-Path $LeftRom).Path
$rightRomPath = (Resolve-Path $RightRom).Path
$portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0)
$portProbe.Start()
$linkPort = $portProbe.LocalEndpoint.Port
$portProbe.Stop()
$leftProcess = Start-Process -FilePath $emulatorPath -ArgumentList @('-rom',"`"$leftRomPath`"",'-listen',"127.0.0.1:$linkPort",'-nowriteini','-setting','Joypad0=27252628585A2010FFFF6B73716A6D1BFFFFFF09FF','-setting','WinX=80','-setting','WinY=100','-setting','Width=640','-setting','Height=576') -WindowStyle Normal -PassThru
Start-Sleep -Milliseconds 400
$rightProcess = Start-Process -FilePath $emulatorPath -ArgumentList @('-rom',"`"$rightRomPath`"",'-connect',"127.0.0.1:$linkPort",'-nowriteini','-setting','Joypad0=27252628585A2010FFFF6B73716A6D1BFFFFFF09FF','-setting','WinX=800','-setting','WinY=100','-setting','Width=640','-setting','Height=576') -WindowStyle Normal -PassThru
$launchInfo = @{left=$leftProcess.Id;right=$rightProcess.Id;port=$linkPort}
$launchInfo | ConvertTo-Json | Set-Content "$PSScriptRoot\..\build\linked-test\processes.json"
$launchInfo | ConvertTo-Json

param([string]$CopeRom = "$PSScriptRoot\..\build\linked-test\COPE\COPE.gb", [string]$DemoRom = "$PSScriptRoot\..\build\linked-test\DEMO\DEMO.gb")
$ErrorActionPreference = 'Stop'
$emulatorPath = (Resolve-Path "$PSScriptRoot\bgb\bgb64.exe").Path
$copeRomPath = (Resolve-Path $CopeRom).Path
$demoRomPath = (Resolve-Path $DemoRom).Path
$portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,0)
$portProbe.Start()
$linkPort = $portProbe.LocalEndpoint.Port
$portProbe.Stop()
$copeProcess = Start-Process -FilePath $emulatorPath -ArgumentList @('-rom',"`"$copeRomPath`"",'-listen',"127.0.0.1:$linkPort",'-nowriteini','-setting','WinX=80','-setting','WinY=100','-setting','Width=640','-setting','Height=576') -WindowStyle Normal -PassThru
Start-Sleep -Milliseconds 400
$demoProcess = Start-Process -FilePath $emulatorPath -ArgumentList @('-rom',"`"$demoRomPath`"",'-connect',"127.0.0.1:$linkPort",'-nowriteini','-setting','WinX=800','-setting','WinY=100','-setting','Width=640','-setting','Height=576') -WindowStyle Normal -PassThru
$launchInfo = @{cope=$copeProcess.Id;demo=$demoProcess.Id;port=$linkPort}
$launchInfo | ConvertTo-Json | Set-Content "$PSScriptRoot\..\build\linked-test\processes.json"
$launchInfo | ConvertTo-Json

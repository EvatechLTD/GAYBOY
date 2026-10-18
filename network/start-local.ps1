$ErrorActionPreference = 'Stop'
$networkRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $networkRoot
$env:Y2KCRISIS_DATA = Join-Path $repoRoot 'build/network-local'
& (Join-Path $repoRoot 'build/php/php.exe') -S 127.0.0.1:18982 -t $networkRoot (Join-Path $networkRoot 'router.php')

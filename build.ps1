$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
# Use the committed generated assets to reproduce the tested main baseline.
python tools/build_rom.py
if ($LASTEXITCODE) { throw 'ROM build or layout validation failed' }

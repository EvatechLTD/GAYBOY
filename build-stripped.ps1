$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/build_rom.py
if ($LASTEXITCODE) { throw "ROM build failed" }
foreach ($test in @("test_stripped_engine.py", "test_stripped_resident.py", "test_stripped_ui.py", "test_stripped_edit_latency.py")) {
    python (Join-Path "tools" $test)
    if ($LASTEXITCODE) { throw "$test failed" }
}
python tools/test_stripped_timing.py
if ($LASTEXITCODE) { throw "Mono timing failed" }
python tools/test_stripped_timing.py --arp
if ($LASTEXITCODE) { throw "Arp timing failed" }
python tools/package_stripped.py
if ($LASTEXITCODE) { throw "Packaging failed" }

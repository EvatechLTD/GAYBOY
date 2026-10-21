$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot -ErrorAction Stop
python tools/build_rom.py
if ($LASTEXITCODE) { throw "ROM build failed" }
foreach ($test in @("test_stripped_engine.py", "test_stripped_resident.py", "test_stripped_ui.py", "test_stripped_edit_latency.py")) {
    python (Join-Path "tools" $test)
    if ($LASTEXITCODE) { throw "$test failed" }
}
python tools/test_stripped_cpu.py --output build/stripped-cpu.json
if ($LASTEXITCODE) { throw "CPU regression failed" }
python tools/test_stripped_navigation.py --output build/stripped-navigation.json
if ($LASTEXITCODE) { throw "Navigation regression failed" }
python tools/test_stripped_timing.py
if ($LASTEXITCODE) { throw "Mono timing failed" }
python tools/test_stripped_timing.py --arp
if ($LASTEXITCODE) { throw "Arp timing failed" }
python tools/test_stripped_timing.py --dense
if ($LASTEXITCODE) { throw "Dense timing failed" }
python tools/test_stripped_timing.py --dense --arp
if ($LASTEXITCODE) { throw "Dense arp timing failed" }
if (Test-Path "build/stripped-baseline/cpu.json") {
    python tools/compare_stripped.py
    if ($LASTEXITCODE) { throw "Baseline comparison failed" }
}
python tools/package_stripped.py
if ($LASTEXITCODE) { throw "Packaging failed" }

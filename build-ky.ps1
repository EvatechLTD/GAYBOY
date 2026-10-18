$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& ./tools/gbdk/bin/lcc.exe -Wf--opt-code-size -Wl-m -Wl-j -Wm-ynKYSDTEST -Wm-yt0x19 -Wm-yo2 -Isrc/ky -o build/KY-SD-TEST.gb src/ky/main.c src/ky/ky_sd.c src/ky/pff.c
if ($LASTEXITCODE) { throw 'KY diagnostic compilation failed' }

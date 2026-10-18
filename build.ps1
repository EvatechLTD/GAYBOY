$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python tools/make_ui_font.py
if ($LASTEXITCODE) { throw 'Font generation failed' }
python tools/make_intro.py
if ($LASTEXITCODE) { throw 'Intro generation failed' }
python tools/make_cinema.py
if ($LASTEXITCODE) { throw 'Cinematic generation failed' }
python tools/make_zoom.py
if ($LASTEXITCODE) { throw 'Zoom generation failed' }
python tools/make_exp_waves.py
if ($LASTEXITCODE) { throw 'Experimental wave generation failed' }
python tools/make_drum_samples.py
if ($LASTEXITCODE) { throw "Drum sample generation failed" }
python tools/generate.py
if ($LASTEXITCODE) { throw 'Preset generation failed' }
python tools/build_rom.py
if ($LASTEXITCODE) { throw 'ROM compilation failed' }

python tools/check_rom.py
if ($LASTEXITCODE) { throw 'ROM layout validation failed' }

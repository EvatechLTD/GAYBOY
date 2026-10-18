# Project listening emulator

Development listening and demo sound approval use SameBoy. Launch with
`./launch-emulator.ps1 -Emulator SameBoy` (also the default).
The launcher pins the accurate DMG high-pass filter and zero added interference.
It generates a custom GAYBOY palette from the website's explicit palette in
`website/emulator/player.js`, preserving all four RGB colors on every restart.

Record the current development ROM with the website's exact SameBoy WASM binary:

```powershell
python tools/record_sameboy.py --seconds 30 --output recordings/sameboy-demo.mp4
```

Requires Chrome, `python -m pip install playwright numpy`, and FFmpeg on PATH.
Outputs MP4, unmodified 48 kHz stereo PCM WAV for listening approval, and a JSON
report with ROM/core hashes and palette colors. Optional `--timeline demo.json`
accepts timed `at`, `button`, `hold`, and `release` events, like record_demo.py.
Time starts at power-on. Captures use the website's explicit palette.
For the vertical TR-909 performance with live button edits and tutorial captions:

```powershell
python tools/record_sameboy_kit.py
```

This uses the same unmodified SameBoy core for the complete workflow, framebuffer,
and native stereo audio. It prepares disposable patterns off camera, queues the
drum entrance on the loop boundary, then plots high tom and percussion live.
Outputs `recordings/GAYBOY-30sec-909-live-drums-SameBoy.mp4`, a lossless WAV,
and a JSON report with button events, frame observations, and core/ROM hashes.

Legacy recordings from `record_demo.py` use PyBoy audio. Do not use those older
recordings to approve SameBoy sample sound.

SameBoy 1.0.4, official Windows SDL release:
https://github.com/LIJI32/SameBoy/releases/tag/v1.0.4

Downloaded archive SHA256 (matches official SHA2-256SUMS):
777a29211e17443435dd0956b7ab775e6e9f40ee859ed4f2f14b43f7587d5a38

Run `./launch-emulator.ps1` from the project root. It now launches SameBoy
with `--model dmg`. Arrows navigate, X/Z are Game Boy A/B, Space is Select,
either Shift is Start, and F5 saves battery data and restarts the ROM.
Every launch and F5 restart opens a centered 640x480 window, preserves the game
aspect ratio, and keeps the window above other windows. Startup sizing is
reapplied through SDL boot/ROM resize events. The mouse pointer stays visible.
All other keyboard shortcuts are blocked while the SameBoy window is focused,
including Escape/menu, save states, debugger, pause, mute and fullscreen.
Use the window close button to exit. Other applications retain their controls.

`tools/run_sameboy.py` enforces the project bindings in local prefs.bin before
each launch and restart, unmaps turbo/rewind/slow-motion/rapid-fire, and installs
a Windows keyboard filter scoped to the emulator's foreground process.
The filter exits when SameBoy closes. `tools/sameboy_cursor.py` disables the two
SDL cursor-hide calls in the verified 1.0.4 executable. The unmodified binary is
preserved as `sameboy.exe.original`; unexpected binary versions are rejected.

SameBoy stores battery data as build/GAYBOY.sav. Existing PyBoy battery data
was copied once from build/GAYBOY.gb.ram; that original is preserved. The two
emulators' battery files are independent after this import.

`./launch-emulator.ps1 -Emulator PyBoy` remains available for comparison.
Python automation still uses PyBoy for program-state and CPU-hook checks.
Do not infer a physical audio defect from PyBoy audio alone: the user verified
that the PCM refresh carrier heard there is absent on their actual DMG-01.
SameBoy is the replacement listening reference, pending the same listening
comparison. Hardware remains authoritative.

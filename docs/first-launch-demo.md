# First-launch demo

The normal `build/GAYBOY.gb` includes the demo beat supplied in
`DEMO SONG/GAYBOY  GB .srm`. It installs the converted song and its patterns
when initializing blank cartridge save RAM; no companion `.srm` is needed.
Existing saves are preserved, including valid empty sparse libraries.

A flash cart may retain its current save in internal RAM even after an SD-card
save is removed. Use the cart's save-management controls to start with blank
RAM when testing the first-launch demo.

`src/sparse_seed.c` contains the embedded demo, so normal builds include it
without special build flags. `tools/make_sparse_seed.py` regenerates that source
from a validated sparse save; `--demo-seed` on `tools/build_rom.py` provides a
temporary build override.

The supplied legacy save becomes `DEMO SONG`, with the original four patterns
(`!`, `!`, `!`, `!GAY`) in pads 1 through 4. All 80 notes/hits and timing are preserved. Release defaults set every
track mixer level to 127 and disable hi-hat metallic in all four patterns.
Other saved patch settings, including WAVE 000, remain as authored.
Factory defaults remain WAVE 006 and non-metallic hi-hat.
Run `python tools/update_demo_defaults.py` after reconverting the source demo.

Conversion evidence is written to `build/user-demo.conversion.json`. The
source save SHA-256 is
`1fc910817f174471ea4bb9a59b2e41cde15af212baf1ac2aa29138dc1b8dc80d`.

# Smooth Playback experiment - 2026-10-23

Branch: live-note. Settings has SMOOTH PLAYBACK (default OFF). The preference
is stored in reserved global root bytes125/126 with an S marker, outside
pattern data. With it enabled, starting transport blanks the display and skips
rendering, UI flushes, feedback drawing, and automatic OAM DMA. LCD timing and
VBlank remain enabled so clocks and input sampling continue. Editing/navigation
are ignored while blank. Select+A stops and redraws the editor; Select+Start
panics. Existing MIDI/link/audio services continue, with unchanged modulation
settings and playback engines. Live-note plotting/drag/resize remain available
when stopped. No engine or modulation setting is silently changed.

Functional tests verify actual Settings input, default OFF, persisted preference
after reboot, audible Wave playback, one-color display, no render/upload calls
or VRAM changes, ignored editing, and display/OAM restoration on stop.

Matched DMG tests use the same build and musical data with Smooth OFF/ON:
120 BPM, P1 quarter notes, synth hats every16th plus snares, sustained Wave,
and separately a P2 three-note ARP or shared square LFO on three voices (fine
and coarse pitch). Rates1/16 and1/32, three distinct start phases, 900-frame
(~15.07 s) measurement windows after warmup. Register-write probes measure
actual APU note triggers and pitch edges, rather than only logical counters.
Both modes have zero native IRQ underruns. All Smooth windows have zero
render/flush/tile/map/feedback calls. Normal playback retains frame/UI work.
No user input occurs during the measured playback window.

Worst absolute error across the three starts, milliseconds:

| Measurement | Graphics ON | Smooth |
| --- | ---: | ---: |
| Sustained ARP1/16 edges |0.352859|0.201225|
| Sustained ARP1/32 edges |0.360489|0.201225|
| LFO1/16 edges |0.567436|0.410080|
| LFO1/32 edges |0.587463|0.412941|
| Note onsets, ARP1/16 looping fixture |0.398636|0.244141|
| Note onsets, ARP1/32 looping fixture |0.393867|0.234604|
| Note onsets, LFO1/16 |3.223419|0.242233|
| Note onsets, LFO1/32 |0.392914|0.235558|

The32-step looping ARP fixture still has occasional long intervals in both
modes: maximum interval errors128.864/128.904 ms at1/16 and62.501/66.406 ms
at1/32 (graphics/Smooth). These were retained in the raw results. A separate
256-step sustained ARP control avoids its own loop boundary within the test
window and produces the ARP edge figures above, with no>1 ms edge errors.
Blanking improves steady playback precision but does not resolve that looping
ARP behavior. Not every individual start/interval improves; these are bounded
emulator observations, not hardware qualification or a universal guarantee.

Total36 measurement windows:24 looping ARP/LFO cases and12 sustained ARP
controls. Raw reports, screenshots, logs and frozen ROM are preserved in
DATA/EXPERIMENTS/live-note-20261023/smooth-playback. Regression checks cover
live plotting/painting, drag/resize audition timing, MIDI pad isolation and
sustained Wave snapshot publication.

Test ROM: build/GAYBOY-smooth-playback-test.gb. Canonical build/GAYBOY.gb
matches this image. ROM layout:270 bytes spare WRAM,512 bytes reserved stack.
SHA256: fa16d924568bd3ea213312c8305a09c249c1d775859a68dbb1c16d938414c05a

Not merged or published. Prior emulator ROMs/saves remain untouched.

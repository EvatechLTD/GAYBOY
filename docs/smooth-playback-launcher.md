# Smooth Playback static pattern launcher

Branch: live-note. Supersedes the completely blank Smooth Playback display.
Settings still enables Smooth Playback; normal playback drawing remains
suspended. Entry draws one static D-pad/A/B legend with all five pattern
numbers and names. There is no animation or active-pad redraw. Only changing
quantization writes one20-character map row. OAM DMA stays disabled.

Controls:

- Up: pattern1; Right: pattern2; Down: pattern3; Left: pattern4; B: pattern5.
- Press a mapped button to queue its pad at the current launch quantization.
  Keep it held to repeat that assigned pad. Release stops rearming; an already
  queued launch can complete, matching existing Mixer/MIDI launch behavior.
- A+Up makes quantization faster; A+Down makes it slower. Up stops at1/16.
  These combinations repeat the active pattern without selecting pads1/3.
  When another mapped button remains held, its repeat continues as well.
- A is a modifier, not a fifth-pad trigger. Left/Right keep their direct pad
  bindings even with A held; there is no previous/next-pad shortcut.
- Select+A stops; Select+Start panics. Both cancel pending launch requests.
- NOW is one-shot, consistent with existing unquantized launches.

Uses the existing mixer launch/preparation/handoff and quantize mapping.
Names are read once on entry, with the current unsaved active-pad name used
when available. Names are uppercased for the static font. Stopping invalidates
editor/menu caches and restores the prior screen; Mixer is explicitly reopened
to rebuild its cached map. No user emulator or unsaved state was overwritten.

Validation: all five pads contain distinct sustained Wave pitches and synth
hi-hats on every16th. Each mapped input switches to the correct audible pad,
repeats while held, and stops rearming on release. B is verified as launch,
not stop. Modifier quant changes do not send pad1/3 requests;1/16 is capped.
A+Left/Right direct bindings, pending-launch cancellation, actual pattern
names, unchanged legend VRAM during launches, and full Mixer canvas restoration
pass. Existing live-note plotting, resize audition, MIDI and low-Wave isolation
regressions pass. Paired-link repeat follows the existing foreground handshake;
physical linked hardware has not been requalified by these tests.

Final timing repeats cover24 looping ARP/LFO windows plus12 sustained-ARP
controls, three start phases per OFF/ON case at120BPM and1/16 or1/32.
All Smooth steady windows have zero render/flush/tile/map/feedback calls and
all windows have zero native IRQ underruns. Looping ARP gaps and occasional
modulation-related onset outliers remain; this is not a claim of universally
perfect timing. Original blank-screen results are retained in the prior audit.

ROM: build/GAYBOY-smooth-launch-test.gb; canonical build/GAYBOY.gb matches.
SHA256: f342a72bcdf273d5fe35386123dd6ef2138cccc73dd2738d92b26adb2eb8503a
ROM validation:268 bytes spare WRAM,512 bytes reserved stack.
Evidence: DATA/EXPERIMENTS/live-note-20261023/smooth-launch.
Not merged or published; physical hardware confirmation remains pending.

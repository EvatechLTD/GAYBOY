# Clicking: pulse note-off artifacts

Date: 2026-10-17

## Problem and hardware confirmation

The user hears objectionable clicks in the pulse channels during the sequencer
demo. They reproduced the artifact on actual hardware using `gayboydemo.gb`
and confirmed it is in our code, not just an emulator problem. Fix the audio
behavior before producing more demos.

Later the user requested a temporary demo workaround: set P1's envelope to rise
instead of fall. `tools/kit_demo.py` now applies that patch for new recordings;
this does not change the note-off code or prove the clicking fixed. The existing
`gayboydemo.gb` and original SameBoy recording remain the falling-envelope
baseline. Rebuilding that hardware ROM with the current fixture will pick up
the rising envelope, so explicitly restore P1 envelope direction to 0 when
rebuilding the original reproduction case.

Additional user hardware observation: a **falling envelope, gate 68%, envelope
period 7** also makes the artifact almost disappear. Treat this as a second
useful comparison patch, not a complete fix. Check interactions between gate
timing, the envelope's remaining level/phase, and the DAC transition. The user
reported "almost" gone, not eliminated.

The firmware fix is in the main source and standard build path. After trying
`gayboydemo-fixed.gb`, the user confirmed it is "much better" and requested
that these fixes remain in main code for future builds (2026-10-17).
This confirms the improvement, not a claim that every artifact is eliminated.
The root `gayboydemo.gb` remains the unchanged reproduction baseline.
The isolated test identifies DAC shutdown as a confirmed source of clicks;
do not assume that explains every possible artifact without listening.

User clarification (2026-10-17): P1 produces the objectionable click when P2
plays; muting P2 makes P1 clean. The artifact only occurs when both pulse
channels play simultaneously. Treat this overlap condition as the
primary reproduction requirement. Compare P1 alone, P2 alone, and both together
with identical patches, score, gain, and PCM load before attributing the
reported artifact to the isolated DAC-off diagnostic.
The user confirmed that it is **P1's** ENV setting: the click occurs on FALL
and disappears on RISE. Primary reproduction: P1 FALL with P2 playing. Clean
controls: change P1 to RISE, or mute P2. Include these exact comparisons.
Another confirmed clean setting: P1 remains on FALL, with envelope period 7
and gate 68%. Include this envelope/gate combination as an additional control.

## Intro comparison and candidate (2026-10-17)

The user reports that the intro's similar composition is clean. In
`src/intro.c`, `pulse()` uses a falling, period-1 envelope but there is no
per-note gate shutdown: DACs remain enabled as envelopes decay, including
rests. The intro only disables them during its final staged fade/exit.
The sequencer calls `stop()` at gate expiry and before a replacement note;
the original implementation wrote zero to NRx2 at each of these events.
The intro also has lower master gain (0x55 versus 0x77), a different P2 part,
and its own timer-driven scheduler, so it is not an otherwise identical test.

Native pulse `stop()` now writes NRx2=0x08 followed immediately by NRx4=0x80,
latching silent volume without switching the DAC off or changing routing.
The trigger is needed for DMG volume latching/zombie behavior; envelope pace
zero prevents a silent release from subsequently rising. Zero-volume falling
note-ons also keep their DAC enabled. Panic and the explicit DAC OFF parameter
still shut DACs down. Mono/experimental release behavior remains as before.
`stop()` and panic's implementation are banked to fit ROM bank 0; the PCM
interrupt is unchanged. No deferred release can cut off a replacement owner.

Candidate: `gayboydemo-fixed.gb`, fixture manifest in
`build/hardware-demo-fixed/manifest.json`. Rebuild after production objects:
`python tools/build_hardware_demo.py --output gayboydemo-fixed.gb --work-dir build/hardware-demo-fixed`.

SameBoy before/after native stereo WAVs and 10 ms event traces are in
`build/pulse-overlap/` and `build/pulse-overlap-fixed/`. These include P1 alone,
P2 alone, both, split left/right, P1 RISE, P1 FALL/period 7/gate 68, and the
full PCM demo with/without P2. Run `tools/diagnose_pulse_overlap.py` with
`--rom` and `--output-dir` to select the fixture and destination.
In the split-channel P1 gate window at 1.11–1.14 seconds, the baseline peak is
4059 with RMS 1255.25, versus candidate peak 3 and RMS 1.28 (signed 16-bit PCM).
The user subsequently confirmed the test ROM sounds much better.

Validation: ROM layout/checksum checks, 54 compiled two-pulse release/retrigger
cases across pitches/velocities/envelopes, note ownership, zero volume, explicit
DAC OFF/panic, sequencer behavior and monosynth checks passed.
The identical hardware-demo PCM stress fixtures deliver 2158/2159 blocks in
both versions, with no underruns and worst IRQ cost under 45% of its budget.
The stress test's first-step timing target fails in both baseline and candidate;
see `build/pulse-pcm-before.json` and `build/pulse-pcm-after.json`. Existing
live-Mixer timing limits also remain failing; do not claim all timing tests pass.
The pulse gate UI test currently fails in its menu-navigation helper before
gate measurement. A separate gate probe using acknowledged button input
compares 1/4/8-step notes at 68% and 100% in the preserved and candidate hardware
ROMs: all twelve measured channel durations differ by less than 0.3 ms.
At four steps/68%, P2 measures 311.1 ms before and 311.0 ms after against a
340 ms nominal duration, confirming that scheduling discrepancy predates this
change. See `build/pulse-gate-comparison.json`. The candidate is available for
hardware comparison, not full timing sign-off.

## Reproduce

- Flash the root-level `gayboydemo.gb`. It skips the intro and automatically
  plays the finished demo at 95 BPM, using TR-909 and all eight sample slots.
- P1 is the short lead, gate 88%. P2 is a 50% duty pulse bass with a 64-step
  pattern, gate 90%. The bass was moved from wave to pulse to avoid PCM stealing
  its hardware channel. The buzzier square-wave timbre is a separate issue from
  the clicks.
- Select+A stops/starts. Select+B mutes the selected channel. Use Select+Left/
  Right to select tracks, and isolate pulses versus drums.
- Build recipe: `python tools/build_hardware_demo.py`. This builds a separate
  variant from the current cached production objects without overwriting the
  normal ROM. Rebuild the production objects first if changing firmware.
- Fixture and baseline hash: `build/hardware-demo/manifest.json`.
- Original reference video/audio:
  `recordings/GAYBOY-30sec-909-live-drums-SameBoy.mp4` and adjacent `.wav`.

## Confirmed diagnostic

Run `python tools/diagnose_pulse_noteoff.py`. It uses the project's unmodified
SameBoy WASM core and a disposable idle-ROM fixture to isolate a pulse envelope
that has already decayed to silence. It then compares leaving the DAC enabled
with writing zero to NR22 at the note-off time.

Results in `build/pulse-diagnostics/report.json` and adjacent WAVs:

| Fixture | Late peak (signed 16-bit PCM) | Late RMS |
| --- | ---: | ---: |
| DAC left on | 1 | 1.00 |
| DAC off at 90% gate time | 4062 | 397.25 |
| DAC off at 100% gate time | 4062 | 397.25 |

Changing gate changes the click's timing, not its cause. The demo itself does
not use 100% pulse gates. The reference WAV also has no full-scale clipping.

## Code to investigate

- `src/main.c`, `stop()`: writes `NR12_REG=0` or `NR22_REG=0`, disabling the
  respective pulse DAC.
- `src/main.c`, `play()`: writes duty, envelope, frequency, and trigger. Check
  note-on and repeated-note transitions as well as note-off.
- `src/sequencer.c`, `seq_off()`, `seq_fire()`, and `seq_frame()`: gate expiry
  reaches `stop()` through `keyevent()`; new notes also call `seq_off()` first.
- `tools/intro_song.py` and `tools/kit_demo.py`: exact patch/score preparation.
  The pulse patches use fast descending hardware envelopes (rate 1).

Develop and test a hardware-compatible way to silence pulse notes without the
abrupt DAC transition. Do not blindly replace it with mixer routing changes:
disconnecting an enabled DAC can also pop. Account for DMG envelope quirks,
zero-volume behavior, retriggers, and note ownership. Keep panic/explicit DAC-off
semantics distinct if needed.

References: https://gbdev.io/pandocs/Audio_Registers.html and
https://gbdev.io/pandocs/Audio_details.html.

## Constraints and acceptance

- Use SameBoy as the listening/capture reference; PyBoy is useful for functional
  tests but is not the audio approval reference. Hardware listening is decisive.
- Fix firmware rather than hiding clicks with recording filters or emulator
  changes. Preserve the accurate high-pass setting and native stereo capture.
- Do not add costly work to the PCM interrupt, compromise sample playback, or
  create sequencer jitter. Rendering must not steal the audio budget.
- Compare isolated P1 and P2, multiple pitches/velocities/envelopes, short and
  sustained notes, repeated notes, gates below and at 100%, mute/unmute, transport
  stop/start, and pattern changes. Repeat with two PCM voices and UI activity.
- Produce before/after WAVs and a separate fixed hardware test ROM for user
  confirmation. Verify both clicking and timing, not just that notes play.
- ROM bank 0 is tight; check bank limits, WRAM bounds, and checksums after builds.

## Capture tooling caveat

The generic SameBoy recorder became extremely slow during the hardware-ROM
check. A batch check on a minimal same-origin page completed successfully and
verified autoplay, P2 selection, TR-909, and nonzero audio; see
`build/hardware-demo/sameboy-verified.json`. That check is not a claim that the
click was fixed. Avoid loading the full animated website when a minimal capture
page suffices.

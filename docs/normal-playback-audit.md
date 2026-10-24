# NORMAL_PLAYBACK experiment

Based on main 60804a2. DMG-mode PyBoy measurements of actual APU trigger writes, with real button gestures and graphics enabled. Hardware validation remains pending.

## Changes

- Both transports prepare the immutable note snapshot and initial ARP state before starting musical time. Normal playback keeps its screen and controls.
- Synth percussion gets two independent prepared tables in unused bank-3 SRAM. Released drum edits build the inactive table in bounded batches; the timer publishes it at a step boundary without restarting its phase. Unrelated melodic edits retain percussion ownership.
- A short fixed-ROM countdown enters the banked percussion dispatcher only for actual steps or gate endings. Foreground deadlines exclude timer-owned drum gates, avoiding redundant continuous sequencer service.
- Native melodic lookup uses byte-sized track ranges, retains explicit 256-event support, filters hash collisions, and returns immediately for a matching lowest-note head.
- An unchanged step-zero ARP chord with a rest can retain its timer-owned loop across unrelated edits. Actual published chord edits revoke automatic future looping while preserving the current chord gate.

## Matched 120 BPM comparison

P2 three-note ARP at 1/16 with a rest, 128-step Wave bassline, hat every sixteenth, snare and kick. Reported error is the worst drum interval error in milliseconds. UI values are median input acknowledgement times, not total draw completion times.

| Operation | Main drum error | Branch drum error | Main UI median | Branch UI median |
|---|---:|---:|---:|---:|
| idle | 11.168 | 0.356 | 0.0 | 0.0 |
| navigation | 9.485 | 0.387 | 33.5 | 33.5 |
| menu | 8.270 | 0.386 | 33.5 | 33.5 |
| cells | 26.712 | 0.354 | 58.6 | 50.2 |
| paint | 35.133 | 0.388 | 67.0 | 58.6 |
| multiselect | 17.310 | 0.357 | 50.2 | 50.2 |
| group_move | 37.408 | 0.341 | 167.4 | 133.9 |

At 120 BPM / 1/16 ARP, graphics-on and Smooth idle drum errors are both below 0.4 ms. The verified normal, melodic-LFO, and 240 BPM passes retain all dense hi-hat hits, stay below 1.3 ms for drums/ARP, and report no native note-buffer underruns.

## Limits and tradeoffs

- Fast 1/32 ARP plus melodic LFO can still show roughly 4?5 ms outliers with graphics running. This is not equal to main Smooth in every stress case. The successful 1/16 results must not be generalized to that case.
- Dense painting can still hold input acknowledgement for seconds. Large selection moves also retain long worst-case UI stalls; median results alone do not promise every gesture improves.
- Prepared percussion admission is conservative: internal clock, straight swing, synth-only hat/snare/kick, no P1/shared noise notes, no drum modulation, supported native engine ownership. PCM, link sync, shared voices, and modulated drums retain the existing foreground path. This experiment does not establish better timing for those fallback cases.
- Scratch table regions (bank 3): A820..A9FF and B810..BB2F; B200..B2B3 and BB30..BF7B. Presets/names, both clipboards, root metadata, resident notes, and bank-2 user kits remain separate. Tables are not song data.
- ROM layout checks pass with 49 bytes unallocated WRAM plus the existing 512-byte reserved stack.

## Validation

Passing: prepared drums (complete rhythm, first interval, stop/restart, preservation, conservative fallback), real graphical drum erase/plot and live tempo changes at 137/240/120 BPM, ARP order/transport/fallback, real ARP chord erase/restore, 256-step melodic tracks and hash collisions, Smooth controls, Wave snapshot gate, live auditions, selection scope, editbuffer state, chord resize, low-Wave/MIDI pad isolation, PCM restart, MIDI launch, and held pad launch.

Legacy drum selection/noise-release tests fail in their obsolete menu bootstrap on both main and this branch (page 11). The old resident-launch fixture also fails its Wave boundary assertion on main; no passing launch-timing claim is based on it. The old LFO combined fine/coarse test reports zero observed edges and is not counted as passing. A separate matched active-LFO benchmark passes.

Reproduce from MAIN:

```powershell
python tools/build_rom.py
python tools/benchmark_normal_playback.py --verify
python tools/benchmark_normal_playback.py --lfo --verify
python tools/benchmark_normal_playback.py --smooth --verify
python tools/benchmark_normal_playback.py --bpm 240 --verify
python tools/benchmark_normal_playback.py --arp-div 3 --lfo
python tools/test_normal_prepared_drums.py
python tools/test_arp_loop_edit_isolation.py
```

Detailed traces and the frozen main baseline live in ignored build output. Private user-session captures and saves remain outside the repository.

ROM SHA-256: `69118c5a3df0bfd7e9eb599f3898b2b9625f565814a9115c34ed42bae520f2c7`.

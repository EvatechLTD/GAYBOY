# GAYBOY — accomplishments and current capabilities

**Status date: October 17, 2026**  
**Basis:** current application source, build configuration, validation scripts, and existing ROM. This is an implementation inventory, not a claim that every feature has passed physical hardware testing.

## What we have accomplished

GAYBOY has grown into a Game Boy music workstation prototype: a MIDI instrument, editable synthesizer, piano-roll sequencer, drum machine, performance mixer, and pattern storage system in one ROM. It supports standalone composition and auditioning from the Game Boy controls, alongside external MIDI performance through Arduinoboy.

The current build targets **512 KiB ROM with MBC5, battery-backed storage, and 32 KiB cartridge RAM**. This supersedes the older 256 KiB / 8 KiB description at the top of the README.

## Instruments and sound design

| Instrument or mode | Implemented capability |
| --- | --- |
| Pulse 1 and Pulse 2 | Native pulse synthesis, duty, volume, envelopes, length, routing and pitch controls; Pulse 1 also exposes hardware sweep. |
| Wave 1 | Native wavetable synthesis, stock wave shapes, hardware output levels, and custom 32-sample wave editing through MIDI CC. |
| Noise | Native Game Boy noise synthesis with clock shift, divisor, width, envelope and routing controls. |
| Wave 2 | Separate MIDI-channel-6 software instrument with an 808-style sine-kick default; pitch, level, decay, pitch drop, waveform, and an independent eight-step pitch/wave/level table. |
| Channel 5 poly mode | Three-note allocation across tonal voices, with voice stealing, sustain, velocity, program selection and pitch bend. |
| Monosynth | Dedicated channel-5 instrument combining two native pulses and a wave oscillator, with oscillator-specific editing and shared modulation. |
| MASTURBATE | Independent experimental texture/drone page, formerly Noise Lab, with patch randomization and restoration of the previous Monosynth patch on exit. |

We have a library of **100 original game-inspired presets in ten banks**, with instant browsing and auditioning. These are approximations created for this project, not extracted game sounds. Startup uses neutral instruments rather than automatically applying a themed preset.

Sound editing includes eight-step instrument tables, arpeggios, duty sequences, vibrato, slides, gates and stereo routing. Monosynth adds held-note arpeggiation, modulation ADSR, five LFO shapes, key-reset/free-running LFO behavior, target-specific depth and phase, pulse release, and a wider 32-wave palette.

Contextual FX pages provide fine tuning in actual native period-register or software phase-increment steps. A global Experimental Mode switch allows a simpler native-hardware path or the expanded software features.

## Experimental audio engines

We have implemented multiple approaches to extending the four physical sound channels:

- Fast wave-channel arpeggiation and a two-oscillator software mixer.
- A separate Monosynth software oscillator/filter/delay engine at 2,048 samples per second through the four-bit wave output.
- Brightness/resonance wave tables, envelope/LFO filter movement, phase scanning, detune and chorus.
- Native note echoes using Pulse 2, and software PCM delay with feedback and tails.
- Experimental pulse-volume ADSR behavior and selectable native modulation control rates.
- Audio block and underrun counters to make timing problems observable.

These are implemented experimental paths with distinct quality and CPU limits. Their shared hardware resources matter: two software wave voices share one physical wave output, native echoes reserve Pulse 2, and sample playback can take priority over wave instruments.

## Composition and sequencing

The sequencer now has **seven logical tracks**: Pulse 1, Pulse 2, Wave 1, Noise, Mono 5, Wave 2 and Drums. These do not represent seven independent physical audio channels. Hardware-group playback and isolated Mono playback select different track groups.

Implemented composition tools include:

- Independent 1–64-step track lengths on a sixteenth-note grid, with 30–300 BPM tempo.
- Note entry/deletion, note audition, per-note velocity and duration, and per-track defaults and gate settings.
- Dragging note ends to resize notes, and moving notes in time or pitch while retaining their properties.
- 8/16/24/32-step zoom, scrolling piano keyboard, beat/bar guides, and a velocity lane in the 16-step view.
- Configurable meter, per-track mute and multiple-track solo.
- Playback that continues while visiting other pages, with a shared panic/stop action.
- Timer-based sequencing independent of display refresh, plus cached grid graphics and sprite overlays for cursor/playhead updates.

## Drums

A dedicated drum roll adds **ten built-in PCM sample choices and two synthesized noise rows**. Sample data is generated into ROM from the local processed break files; this is not runtime loading from SD.

The sample engine mixes up to two overlapping PCM voices. Drum editing manages overlap and replaces older hits when necessary. DRUMSYNTH exposes separate hi-hat/snare-style noise patches with level, clock shift, divisor, metallic width and fall-rate controls. These noise rows share the physical noise channel rather than providing two independent hardware voices.

Current PCM playback uses direct packed four-bit samples; its playback routine does not apply the stored per-hit velocity or duration as sample gain or an audio envelope. Noise hits do use velocity and timed duration.

## Mixer, performance and saved patterns

The MIXER page provides seven logical channel strips with mute, solo, level and routing, plus transport and **eight pattern pads**. Pattern changes can happen immediately or be queued to a beat or bar boundary.

LOAD and SAVE pages support named patterns. The storage implementation saves note pitches, velocities, durations, drum pattern data, track lengths/defaults/gates, mixer levels and pans, mute/solo, tempo, meter and playback group. Records include checksums and metadata validation, and slot 1 is restored at boot when valid.

This is a significant advance beyond the README's older statement that there are no save slots. However, **pattern storage does not serialize the complete synthesizer patches, preset edits, instrument tables or all experimental settings**. Persistence also depends on an emulator or cartridge retaining battery SRAM; unsaved live edits are not automatically guaranteed across power-off.

## MIDI and interface

Arduinoboy mGB-mode input addresses the four native instruments on channels 1–4, Mono/poly on channel 5, and Wave 2 on channel 6. Implemented handling includes running-status messages, note-on/off, velocity, sustain, full 14-bit pitch bend, program changes and instrument-specific CC mappings. Direct native voices retain a stack of up to eight held notes and recover the previous note when the newest is released.

The interface includes a contextual scrolling Start menu, direct instrument entries, on-device CC reference, waveform previews, activity meters, accelerated parameter editing, and panic/receive-overflow controls. A bundled emulator launcher supplies keyboard mappings for interactive testing.

## Supporting tools and verification

The project has a local GBDK build pipeline, generated font/wave/preset/sample assets, ROM bank and memory-layout checks, and a substantial PyBoy regression suite. Existing scripts cover MIDI, synthesis, audio spectra/timing, navigation, sequencer editing, drums, mixer behavior and battery-backed pattern reloads.

For this brief, `python tools/check_rom.py` was run successfully against the existing build. It verified the 512 KiB MBC5+battery ROM, 32 KiB RAM header, ROM checksum, bounded code banks and work-RAM layout. The full emulator regression suite was inspected as evidence of coverage but was not rerun for this documentation task.

A separate KY/original-EDGB diagnostic implements read-only SD/FAT browsing and 16-byte GBW waveform preview, with a WAV-to-GBW preparation tool. It remains a separate compatibility experiment; SD file access is not integrated into the main workstation.

## What remains unfinished or unproven

- Physical Arduinoboy timing, cartridge behavior, DMG/CGB audio quality and experimental volume behavior still require hardware verification.
- The sequencer uses internal tempo; MIDI realtime clock/start/stop messages are currently ignored.
- Eight pads provide manual and quantized pattern changes, but there is no automatic song-chain arrangement in the reviewed implementation.
- Full instrument/project serialization and integrated SD loading remain unfinished.
- Software engines trade bandwidth, quantization and CPU headroom for added capabilities; logical tracks compete for the original Game Boy audio hardware.
- Parts of the README describe older states, so this brief prioritizes the current code where they disagree.

**Milestone reached:** we have an integrated music-making prototype with playable synthesis, visual composition, sample and noise percussion, live mixing, pattern launching and battery-backed pattern storage. The next major work is hardware validation and completing project-level recall and file workflows.

## Source map

- `src/main.c`, `src/instruments.c`, `src/global.c`: MIDI, native synthesis, Wave 2 and global mode behavior.
- `src/mono.h`, `src/experimental.c`, `src/noiselab.c`: Monosynth, experimental DSP and drone performance.
- `src/sequencer.c`, `src/sequencer.h`, `src/seq_pixels.c`: transport, tracks and piano-roll editing/rendering.
- `src/drum.c`, `src/drum_samples.h`: drum sequencing, sample playback and noise patches.
- `src/mixer.c`: mixer, eight pads, quantized switching and pattern serialization.
- `src/ui.h`, `src/ui.c`: menus, page routing and instrument controls.
- `src/ky/`, `tools/prepare_ky_waves.py`: separate SD diagnostic and waveform conversion.
- `tools/build_rom.py`, `tools/check_rom.py`, `tools/test_*.py`: build configuration and validation coverage.

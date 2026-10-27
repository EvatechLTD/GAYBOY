# TWINK song SameBoy qualification

Host: `adf25cd8612d51cbc12b15e040f9c37edb5a2aaad4d5e3c819493d8a1c65f98e`.
Reference host: `5155ffde242b0b02370d2c65b7a14b819a21f24f79e3f35ad67a566d323c3e8b`.
Receiver unchanged: `MONOSIMP-LEARN-NOISE-D.gb`, `de079e296852a5cf7c2b6bb047cd6a9a46999c53f8ed372cf0c9e31f01440012`.

`tools/test_song_twink.cjs` creates isolated in-memory copies of KILLING resident data. Local lanes contain P2 chords, Wave bass, hats/snare and pulse kick. MS patterns contain rests, different held sets, low notes, a separate lane length and an eight-note option. No user save or emulator is touched. Song start, transport mode, receiver input and stop use UI buttons. Wire frames are decoded from actual SameBoy bit transfers and CRC checked.

## Accepted evidence

| Case | Actual kick/P2/Wave/Noise attacks | Worst local grid error ms | Largest onset difference from reference |
|---|---|---|---|
| 120 BPM Smooth | 20 / 80 / 4 / 80 | .447 / .182 / .131 / .448 | .067 ms |
| 240 BPM, eight MS notes, local LFO, 1/32 local ARP | 20 / 160 / 4 / 80 | .412 / .193 / .095 / .391 | .284 ms |
| 240 BPM graphics, 352 steps, MS lane length8 | 84 / 336 / 20 / 336 | .409 / .388 / .073 / .388 | .413 ms |

Local pitch/envelope sequences and attack counts match reference. The stress fixture verifies actual prepared LFO register writes and a 19-byte F5 packet. Every accepted case has zero song underruns, MS queue overflows, wire aborts and unarmed edges. Host minimum stack pointer is DEA5, inside its reserved stack. Hardware-clock versus wall-time endpoint differences remain below one tick; stress is -.166 ticks and long graphics -.022 ticks, essentially matching the respective reference measurements.

The fixed-fixture regression gate rejects local grid errors of0.6ms or more,
or relative onset divergence of0.6ms or more when a reference report is supplied.
The final120, eight-note stress240 and long graphical240 cases were rerun with
these assertions enabled against the exact qualified host image.

The long graphics test explicitly asserts that the observed viewport base becomes256, and that VRAM writes increase after crossing position256. Report: `build/song-twink-long240.json`, `pageFlip={position:256,base:256,graphicsWritesAfterCrossing:304}`.

Additional passing functional reports: `song-twink-zero240.json`, `song-twink-mute240.json`, `song-twink-solo240.json`, `song-twink-seek240.json`, `song-twink-loop240.json`. These cover scaled velocity0, MS mute/solo, seek16, natural end, looping and manual stop; D releases its held keys. All reports include decoded packets, local APU records, raw wire/APU events and clock samples.

External onset is not instantaneous. At120 BPM the unchanged receiver attacks7.72–14.43 ms after completed CRC,18.53–25.49 ms after first-byte start. The eight-note240 stress has wire time up to23.00 ms and actual onset18.80–36.51 ms after first-byte start. Long graphics ranges18.50–37.29 ms. This is separate from host local timing and includes the existing receiver foreground path. No claim of zero external jitter or identical phase is made.

## Reproduction

Run in `G:/DEVELOPMENT/GAYBOY/BRANCHES/TWINK_SONG`. Defaults use the unchanged D receiver and `G:/DEVELOPMENT/MONOSIMP-SYNTH_CORE/build/noise_link_core.cjs`, a SameBoy1.0.4 real-cable core with APU/wire diagnostics.

```powershell
node tools/test_song_twink.cjs --rom G:/DEVELOPMENT/GAYBOY/DATA/TESTS/TWINK-CHORDS-20261026/GAYBOY-TWINK-CHORDS.gb --bpm 120 --report build/song-twink-baseline120.json
node tools/test_song_twink.cjs --twink --bpm 120 --baseline build/song-twink-baseline120.json --report build/song-twink-candidate120.json
node tools/test_song_twink.cjs --lfo --arp32 --rom G:/DEVELOPMENT/GAYBOY/DATA/TESTS/TWINK-CHORDS-20261026/GAYBOY-TWINK-CHORDS.gb --bpm 240 --report build/song-twink-baseline-stress240.json
node tools/test_song_twink.cjs --twink --eight --lfo --arp32 --bpm 240 --baseline build/song-twink-baseline-stress240.json --report build/song-twink-eight-stress240.json
node tools/test_song_twink.cjs --long --graphics --ms-length 8 --rom G:/DEVELOPMENT/GAYBOY/DATA/TESTS/TWINK-CHORDS-20261026/GAYBOY-TWINK-CHORDS.gb --bpm 240 --report build/song-twink-baseline-long240.json
node tools/test_song_twink.cjs --twink --long --graphics --ms-length 8 --bpm 240 --baseline build/song-twink-baseline-long240.json --report build/song-twink-long240.json
node tools/test_song_twink.cjs --twink --level-zero --bpm 240 --report build/song-twink-zero240.json
node tools/test_song_twink.cjs --twink --mute --bpm 240 --report build/song-twink-mute240.json
node tools/test_song_twink.cjs --twink --solo-ms --bpm 240 --report build/song-twink-solo240.json
node tools/test_song_twink.cjs --twink --seek 16 --bpm 240 --report build/song-twink-seek240.json
node tools/test_song_twink.cjs --twink --loop --frames 1000 --bpm 240 --report build/song-twink-loop240.json
```

## Rejected early fixture evidence

Do not use `build/song-twink-baseline240.json` or `build/song-twink-eight240.json` as qualification: those early reports had silent drums because the fixture cleared per-engine drum level scalars. Early versions of baseline120/candidate120 were also silent; their files were replaced with corrected nonzero20/80/4/80 reports. The final test now hard-fails unless every intended local channel actually sounds, checks the expected kick/hat minimum counts and compares full local pitch/envelope sequences.

This is emulator qualification. Hardware remains authoritative.

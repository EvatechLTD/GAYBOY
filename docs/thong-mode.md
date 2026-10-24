# THONG MODE: experimental song arranger and prepared playback

Branch: `THONG_MODE`, based on main `571aa38`. This is a review build, not a main release. Git branch names cannot contain spaces. Read `briefs/JITTER BIBLE.md` before changing the ordinary playback paths.

## What is implemented

Five named pattern lanes, one sounding pattern at a time. Clips never overlap, even across lanes. New clips use the longest occupied track length of their pad. Extending a clip repeats the pad and ends at the requested offset. A gap silences the APU while the song clock continues. Adjacent same-pad plotting extends the preceding clip. LOOP defaults ON; ONCE stops at the last clip end. Editing is disabled during playback.

Timeline positions and lengths are 32-bit native sixteenths. This preserves odd-length patterns without rounding their audio length to the visible grid. The display has 32 cells per page at eighth, quarter, half, 1-bar, 2-bar, 4-bar, 8-bar, 16-bar and 32-bar zooms. Song bars are fixed four-quarter units; each pad retains its own native track lengths. Zooming never changes stored clips. There is no page-count limit; natural 32-bit coordinate bounds apply. There are 158 clip records, not 158 cells: one very long repeating clip still occupies nine bytes.

## Controls for UI review

- Open Finder with Start and choose PAGE > SONG MODE.
- D-pad moves through time and lanes. Up above the first lane reaches the header.
- B on empty time plots the lane's pattern. Tap/release B on an existing clip deletes it.
- Hold A plus Left/Right on a clip to move it horizontally.
- Hold B plus Left/Right to resize a clip. Vertical movement cannot change its pad.
- Hold A from empty time and move the D-pad to box-select clips. Selected groups move/resize horizontally with the same modifiers. Conflicting edits are rejected before changing the arrangement.
- Select+Up/Down changes zoom. Header controls also change zoom, LOOP/ONCE and BPM.
- Start+Select starts blank-screen song playback; repeat to stop.
- Select+A or header PLAY starts graphical playback. Select+A also stops.
- Set SYNC to OFF before playing this experimental backend. External clock/link playback is not supported here yet.

## The timing result and the failed approach

The first implementation compiled notes and patches but still changed scene state inside the timer interrupt. Its dispatcher could take about 11 ms; preparation alone did not prevent multi-millisecond jitter. This approach was discarded.

The working implementation compiles every referenced pad while stopped. After the blank screen is fully drawn, a foreground planner prepares timed APU register programs in a bounded ring. The interrupt only waits for the next timestamp and writes that program. Scene changes, chord scans, LFO evaluation, drum preparation and timeline lookahead happen before their deadlines. Repeating a clip does not restore the resident pad or rebuild note data in the interrupt.

Song playback temporarily owns its timer callback and foreground service loop. The normal main loop, engine timer and edit IRQ implementations are preserved. On stop the ordinary timer callback and original pad/BPM are restored, edit snapshots/indexes invalidated, waveform cache invalidated after direct Wave RAM writes, and tile ownership restored. The arrangement does not replace ordinary live-launch behavior.

The timer is fixed at 1024 Hz in this backend. Musical steps use fractional accumulation of 15360/BPM clock units. Clock timestamps wrap at 16 bits; tests run past that wrap. Queue slots contain register programs, not samples or a fixed number of musical steps. There are eight 192-byte slots, seven usable. The planner fills ahead continuously; graphical page draws only occur after committed playback position crosses the page boundary, with queue refills between tile batches. Graphical playback is available for UI review but is not yet qualified to the same timing target.

## Measured blank-screen playback

Actual APU-write hooks, not UI timestamps. Each qualified run is 5400 emulator frames (about 90 seconds), changes among three prepared pads repeatedly, and checks source SRAM is unchanged. Every run below had zero queue underruns. Values are maximum interval deviation from the expected rhythmic grid, in milliseconds; they are not a hardware measurement or an absolute latency bound.

| BPM / workload | Hats/noise | Kick | P2 | Wave |
| --- | ---: | ---: | ---: | ---: |
| 120, no modulation | 0.194 | 0.138 | 0.097 | 0.077 |
| 120, 1/32 ARP + pitch LFO | 0.208 | 0.194 | 0.327 | 0.168 |
| 137, no modulation | 0.957 | 0.780 | 0.943 | 0.794 |
| 240, 1/32 ARP + pitch LFO | 0.210 | 0.191 | 0.306 | 0.143 |

Maximum measured register-commit routine time was about 0.748 ms with modulation, below the 0.977 ms timer period. This routine time excludes interrupt entry/exit overhead; zero underruns and actual onset intervals are the relevant end-to-end checks.

Patch checks cover duty, envelope, pan, note pitch, Wave shapes and noise tuning, rather than assuming a pad-number change proves patch application. The dense hats must have no missing intervals. All five resident musical records and the entire presets/clipboard/root SRAM bank are compared before/after playback.

The frozen tuned-main reference on a related workload includes startup/transition outliers (noise/kick about 3.9 ms, P2 about 3.4 ms, Wave about 12.4 ms). It is not identical to every earlier Smooth fixture; do not turn these values into a universal percentage improvement. The new three-patch qualification meets the sub-millisecond steady playback target at 120 BPM. Hardware listening remains necessary.

## Current supported scope and explicit exclusions

Supported: native P1/P2/Wave; deterministic ARP with up to four chord notes; shared fine/coarse pitch LFO; synth hat/snare/pulse-kick; per-pad pulse duty/envelope/level/pan, Wave shape/level/pan, drum patches/tuning, master/power; independent track lengths. The global song tempo is retained across pad changes.

This backend currently refuses PCM drums, software synth engines, tables, poly modes, random ARP orders, nonstraight sequence modes/swing, certain envelope/level modulation combinations, and shared P1 notes plus pulse-kick ownership. It also refuses unsupported populated tracks, oversized compiled audio, or an active ordinary transport. The UI displays an explicit reason instead of silently falling back to an untuned path. SYNC must be OFF. These restrictions concern song playback only; normal mode capabilities retain their previous implementation and regression checks. Broadening song synthesis compatibility is future work, before claiming full feature parity.

## Memory and ownership contract

Only one new WRAM byte is allocated (`song_playing`). Link checks report 48 bytes remaining WRAM and the existing 512-byte stack reserve. Do not infer that cartridge SRAM scratch is free to use concurrently.

- Global arrangement: 1440 bytes fragmented across offsets 480..767 of all five resident 2 KiB records. Header eight bytes plus up to 158 nine-byte clips. This padding lies after metadata/tones and before notes. Copy/paste excludes this global padding deliberately.
- Bank-zero SRAM A000..A207: five 104-byte compiled scene descriptors, aliasing the inactive ordinary event index.
- A300..A3A1: 162-byte song planner runtime; A3B0..A3FF holds planning pointers, queue state, committed position, clock and register shadows.
- A4ED..A4FC: 16-byte SongView, after ordinary menu state.
- A500..AAFF: eight register-program slots. Stopped editing selection overlay at A7C0 is cleared before queue ownership begins and after it ends.
- Stopped group-edit staging uses B000 and B700, 1580 bytes each. Never live with playback's other scratch owners.
- Bank two AD00..BFFF: 4864-byte compiled note/drum/LFO cache. This exclusively replaces the ordinary edit snapshots during song playback. Resident pad five and user drum kits below AD00 remain intact.
- Cache reads MUST stage through WRAM before copying to SRAM bank zero. A pointer into SRAM zero does not continue pointing to that bank after selecting SRAM two. The initial direct-copy experiment was wrong and was removed.
- Existing user presets, root and clipboard in bank three are preserved. HOME ROM is extremely tight; keep the APU commit assembly banked, with only the short countdown/dispatch fixed.

The renderer and editor also borrow ordinary roll tiles/scratch. Exit must restore shared tiles and invalidate ordinary draw caches. A repeated exact-pixel Song-to-P1 regression covers this ownership transition. After song writes Wave RAM directly, invalidating the normal waveform cache is mandatory even when the restored pad's shape equals its previously cached shape.

## Reproduction and regression gates

Desktop SameBoy on this workstation needs `--nogl`; its OpenGL path showed a black display while emulation continued. The visible test instance uses `sameboy.exe --nogl --model dmg` with `build/GAYBOY-THONG_MODE-test.gb`. The accompanying `.sav` is a disposable three-patch demo; original user saves were not overwritten. Keyboard bindings are arrows, X=A, Z=B, Space=Select, Shift=Start.

Build with `python tools/build_rom.py`. ROM layout and memory ownership checks run as part of the build.

Song checks: `test_thong_mode.py`, `test_thong_storage.py`, `test_thong_gaps.py`, `test_thong_exit.py` and `test_thong_audio.py`. Audio options: `--song-arp --song-lfo --song-bpm 240`; optional `--write-demo PATH` writes disposable SRAM before playback. `benchmark_thong_reference.py` reads the frozen accepted main artifact. Generated evidence is under build/thong-*.json/log, not production saves.

Ordinary playback regression checks passed: Smooth Playback, prepared drums, normal prepared drums, ARP loop edit isolation, long prepared tracks, stopped plot audition, drag/resize audition, shared UI tiles, Wave pad isolation, MIDI launch, PCM gate restart, and `benchmark_normal_playback.py --verify` with and without `--lfo`. After the final Wave-cache fix, the audition test, ordinary LFO benchmark and all Song checks passed again.

Next gate: user UI review and hardware timing/listening. Then improve any handling issues, then tune graphical song playback without edits. Do not merge this experimental backend to main or publish it as the stable build before review.

## UI review correction: repeated blanking

The first review build set seqfontdirty after each Song render, then ui_render interpreted that flag as leaving the pixel roll on the next input. ui_restore_seq_tiles called ui_transition_begin, hiding the background during every edit. Settled screenshots missed this transient failure. Song now retains borrowed tile ownership while its page is active; actual page exits still restore ordinary tiles. test_thong_redraw.py checks the LCD background bit every emulated frame during navigation, plot, move, resize, zoom and header edits, and rejects any full-page restoration during those operations. The test fails on the original build and passes with this correction. Song exit, shared mixer/roll tiles and prepared ARP/LFO audio checks also pass.

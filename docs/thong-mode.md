# THONG MODE: experimental song arranger and prepared playback

Branch: `THONG_MODE`, based on main `571aa38`. This is a review build, not a main release. Git branch names cannot contain spaces. Read `briefs/JITTER BIBLE.md` before changing the ordinary playback paths.

## What is implemented

Five named pattern lanes, one sounding pattern at a time. Clips never overlap, even across lanes. New clips use the longest occupied track length of their pad. Extending a clip repeats the pad and ends at the requested offset. A gap silences the APU while the song clock continues. Adjacent same-pad plotting extends the preceding clip. LOOP defaults ON; ONCE stops at the last clip end. Editing is disabled during playback.

The editor uses one fixed four-quarter bar per cell and sixteen normal-sized cells per screen. There are no zoom or sub-bar controls. New clip lengths round up to whole bars; moving and resizing use whole bars. Time-signature-aware arrangement behavior is deferred by user request. Audio positions remain 32-bit native sixteenths internally, so the prepared playback engine does not need a new timing representation. There is no page-count limit; natural 32-bit coordinate bounds apply. There are 158 clip records, not 158 cells: one very long repeating clip still occupies nine bytes.

## Controls for UI review

- Open Finder with Start and choose PAGE > SONG MODE.
- D-pad moves through time and lanes. Up above the first lane reaches the header.
- B on empty time plots the lane's pattern. Tap/release B on an existing clip deletes it.
- Hold A plus Left/Right on a clip to move it horizontally.
- Hold B plus Left/Right to resize a clip. Vertical movement cannot change its pad.
- Hold A from empty time and move the D-pad to box-select clips. Selected groups move/resize horizontally with the same modifiers. Conflicting edits are rejected before changing the arrangement.
- Header controls are PLAY, LOOP/ONCE and BPM. Each Left/Right move or resize is one whole bar.
- Start+Select starts blank-screen song playback; repeat to stop.
- Select+A or header PLAY starts graphical playback from the navigator bar. Select+A also stops and places the navigator at the committed playback bar.
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

## Fixed-bar grid and navigation correction

User review simplified the arrangement to one bar per cell and sixteen cells per screen; all zoom/sub-bar controls were removed. The grid now uses ordinary eight-pixel outlined cells with black clip bodies. Pattern names follow the same uppercase/sanitized font mapping as the other sequencer pages. The old unsanitized lowercase glyph IDs collided with the borrowed grid tiles.

Stopped navigation retains cell signatures at bank-zero BE00..BE4F, validity at BEA0 and content/cursor metadata through BEAD. These occupy inactive roll scratch beyond both group-edit staging lists (the second list ends BD2C). No WRAM was added. Input releases and an idle header no longer request another render. Cursor moves bypass clip/name scans and update only the previous/new cell tiles. Content edits and selection changes invalidate the retained raster; page/menu exits invalidate tile ownership. Full source records and ordinary playback paths remain separate.

The final fixed-grid test measured about 6.3 ms maximum cursor-render time and 22.5 ms header navigation, compared with about 137 ms for the intermediate retained-tile renderer that still recomposed every lane. These are emulator CPU/render measurements, not end-to-end hardware input latency. test_thong_navigation.py checks a one-frame cursor-render budget, at most two uploaded tiles per move, label integrity and idle header/grid behavior. test_thong_bars.py checks a four-bar plus eight-bar arrangement occupies twelve cells, and extends an eight-bar clip to ten bars. Audio, blanking, overlap, group edits, storage, gaps and page-exit regressions pass on the simplified grid.

## Selection semantics after UI review

Newly plotting or B-resizing a clip does not select it. Inverted bodies are reserved for A selection: a held single-clip A gesture highlights that clip and release clears it; box-selected groups retain the existing inverted selection behavior. Pending B-delete anchors do not render as selections. Entering Song clears transient single-selection and gesture anchors, including values left in volatile SRAM by a previous session. test_thong_plot_selection.py verifies actual interior pixels for solid plot/resize, inverted A selection, release and deletion, rather than testing stored notes alone.

The reported overlap example was confirmed against the saved current arrangement: pad three occupied bars5..8, followed by pad two at9..10. Bars7..8 appeared hollow because the newly extended pad-three clip had been automatically highlighted; they were occupied. Collision rules were correct. The user's arrangement was retained, the requested listening-save LFO depths were disabled, and ARP was retained. Original and current pre-change saves were archived locally under build/song-visibility-save-*.

## Starting from the navigator

Select+A/header PLAY now starts at the navigator's bar instead of bar one. A pre-start seek locates the active clip or silent gap, reconstructs active pulse/Wave note groups from the compiled streams at the clip's local offset, and positions the next-clip lookahead correctly. Adjacent same-pad clips share their chain offset. Seek scans at most the cached pattern events and arrangement records; it never replays all elapsed song time. All seek work completes while stopped, before the first hardware packet. ARP/LFO oscillators begin a fresh phase on an explicit seek; this is a transport start, not phase-exact restoration of a previous oscillator state. Drums use the current step and active noise state.

Manual/automatic stop captures the committed hardware position atomically and rounds the navigator down to its bar; reaching the end returns it to the final occupied bar. Starting past the song end reports PAST SONG END. Start+Select retains the existing whole-song blank-screen start at bar one. test_thong_seek.py fails against the previous frozen ROM and passes on the change, checking a distinct second-bar P2 note, sustained Wave note, later clip, silent gap and following transition, stop position and end guard. Blank playback ARP/LFO timing and editor selection/navigation/page ownership checks pass.

## First-step kick and post-song mixer lockup

The KILLING hardware battery reproduced two independent defects. Song packets triggered the pulse kick before the empty P1 group issued its silence command. Both commands reached the APU on time, but the kick was cancelled within the same packet. Process melodic groups before drum ownership at scene entry and native track wrap. Cold seek already uses that order. The audio probe now checks the final envelope/routing of every packet containing a positive pulse trigger; merely counting trigger writes missed this defect.

Returning to ordinary playback after song compilation also exposed an existing ARP cache-validity bug. `eval_runtime_reset` clears calculated periods when restoring changed modulation settings, while retaining rate keys/BPM. The secondary key-match fast path in `arp_period` reused that invalid zero period. Foreground modulo by zero then trapped playback catch-up while timer-owned music continued and input could not run. Require a nonzero calculated period before either rate-cache fast path can reuse it. No buffer redesign, note/patch format changes, new SRAM/WRAM or extra IRQ work are needed.

`python tools/test_killing_session.py --save PATH/TO/KILLING.srm` reads the supplied battery into disposable emulation memory, checks first-step kicks at scene changes and drum loops, runs the complete arrangement through a loop, then launches/navigates/stops all five mixer pads. It verifies arrangement/note bytes and the original file remain unchanged. The battery itself is private test input and is not committed. The ordinary playback LFO timing gate and prepared Song ARP/LFO gates at 120/240 BPM pass after these corrections. User-visible test emulator copies are separate from headless probes and the original battery.

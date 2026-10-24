# JITTER BIBLE

Performance contract, engineering history, and context-recovery brief for GAYBOY.
Written 2026-10-24. Accepted code baseline: **main `57cc9c7`**, including `307a432` (NORMAL_PLAYBACK) and the shared-graphics fixes. Earlier release: `60804a2`. These are local Git identities, not a claim that GitHub or the website has been updated.

## Read this first

The user spent days chasing timing failures and nearly accepted that the hardware was too slow. It was capable of much better performance. The turnaround came from removing redundant work, preserving clocks and ownership, preparing actual hardware operations, and separating sound from editing and drawing. There was no single magic buffer or universal fix.

**Do not regress audio onset timing, continuity, or sequencer timing to add a feature.** Protect responsive navigation and bounded edit publication too. The user's priority is note timing and usable controls over perfectly precise modulation. That is not permission to degrade either without a measured comparison and an explicit discussion.

Stopped-note audition changed the product requirements: users can hear and build dense passages with transport stopped, then listen with normal graphics or Smooth Playback. Dense editing need not be effortless under the heaviest modulation for the instrument to be useful. Conversely, that workflow does not excuse avoidable playback jitter or stale edits.

For context recovery: read this file, inspect `git status`, `git branch --show-current`, and `git worktree list`, then read the relevant source and tests. A folder named MAIN is not proof that its current branch is main. During this handoff MAIN had been used for separate `song-mode` work, then was restored to clean main. That work is not part of the accepted performance baseline. Check its branch/archive before reusing or discarding anything. Do not begin song-mode implementation merely because this brief discusses it.

Paths below are repository-relative unless explicitly marked workspace-relative. Historical audits describe their own builds; their "unmerged" labels and old memory figures are not current status.

## 1. The failure and the false assumptions

A minimal reproducer was enough: synth noise hat on every sixteenth, plus a long Wave note. Copy the same pattern to two pads and switch between them. No instrument differences were needed to expose the launch problem. Later, an unchanged pattern could play acceptably between loop boundaries and hiccup every time it repeated, even with graphics suppressed.

| False premise / tempting shortcut | What we learned instead |
|---|---|
| "The Game Boy is just too slow." | Large amounts of repeated work were avoidable. Hardware listening confirmed substantial improvements; that does not establish unlimited capacity. |
| "The PPU handles graphics, so graphics cannot affect sound." | The PPU renders pixels, but the CPU still constructs tiles/maps, manages caches and uploads, and shares interrupt deadlines. Measure those costs; do not use graphics as a catch-all excuse. |
| "It must be graphics." | Smooth Playback removed ongoing graphics and still exposed loop-boundary audio work. That forced investigation of the playback path itself. |
| "Correct elapsed time means punctual sound." | A correct clock can coexist with late APU writes. Timekeeping, scheduling, register commits, and inter-channel skew are separate concerns. |
| "Nothing changed musically, so nothing expensive can happen." | Global generations, loop retrigger code, source scans, validation, patch application, and cache resets still did work on unchanged content. |
| "More preparation/buffering is automatically safer." | Unnecessary validation and poorly budgeted preparation can consume the very headroom they are intended to protect. |
| "A longer/faster pattern just needs a bigger buffer." | Buffer capacity, preparation throughput, publication ordering, and audible note opportunity are different problems. Full immutable snapshots are currently intentional. |
| "We have loads of free RAM." | Cartridge SRAM and internal WRAM are different resources. The accepted linked build has only **49 bytes unallocated WRAM**, with **512 bytes reserved stack**. Existing SRAM is heavily overlaid. |
| "A pulse-only timing improvement proves the sequencer is fixed." | It can hide whole-step problems or increase channel separation. Probe Wave, noise, kick, pulse, and PCM as applicable. |
| "Input was acknowledged, therefore the UI was responsive." | A highlight or edited note could remain invisible for seconds after acknowledgement. Measure both. |

Unused structs were worth auditing, but unused storage is not automatically processing overhead. Removing a zombie helps CPU only if it removes actual scans/copies/dispatch, and helps memory only where that storage was allocated. It was not the explanation for every jitter problem.

## 2. First turnaround: launches must preserve time and unchanged sound

External LSDj-slaved playback behaving better was an important clue about local clock/accounting and catch-up. It did not prove an instrument-specific cause. The successful launch work combined these changes:

- Five pads retain separate **2 KiB resident SRAM records**. Launch selects the destination event pool; it does not bulk-copy all notes into one shared live pool at the boundary.
- `resident.c` stages incoming name, metadata, tones and first-step melodic notes in a **private 449-byte WRAM launch buffer**, in bounded chunks (normally 16 bytes). Renderer scratch is not a safe launch buffer.
- Quantized installation waits until preparation is ready and uses an eligible boundary. Boundary code must not block on unfinished storage reads or a full first-note search.
- `tones_match_buffer()` and tone-generation validation detect identical state. `changed_copy()` and downstream dirty checks apply changed blocks only. An identical instrument must not reload Wave or reset envelopes, modulation, and global audio state just because the pad number changed.
- `seq_pattern_handoff()` replaces pattern content on the running transport. Preserve pending elapsed ticks and the appropriate link grid. Same-pad retriggers use live data directly.
- Preserve a continuing identical Wave oscillator when its actual note/instrument/velocity/pan conditions allow it. First-step voices replace their own sound; do not blanket stop and restart every channel.
- Stage cosmetic mixer work after sound/input, and defer fader uploads around launches.

The user subsequently reported exceptionally smooth hardware playback. That is a real hardware observation, not an emulator-derived universal guarantee. The cap on launch quantization is **1/16**; the earlier 1/32 launch experiments were not reliable enough. Historical fixtures at 300 BPM or 1/32 launch are stress history, not current supported UI settings.

See `briefs/patternlaunch.md`, but read its old limits/results in their historical context.

## 3. Clock and execution rules that must survive

The timer is shared with PCM and other modes. Musical elapsed-time accounting must survive timer reload changes and expensive foreground work. The native paths use DIV-based elapsed accounting with a retained fractional remainder, expressed in **1024 musical time units/second**. In the current implementation, the sampled DIV byte wraps in about **15.625 ms**: it must be sampled frequently enough. Disabling interrupts long enough to miss a wrap is not repaired by believing the clock is independent.

Do not reset the continuous DIV epoch when enabling an already-running native melodic path. Preserve elapsed time across launch/ownership changes. Do not erase a pending tail of ticks or defer it to another loop accidentally.

In `seq_frame()`, a boundary callback can hand off a pattern while more elapsed time remains. Pending time is published before that callback; if no handoff consumed it, the existing foreground pass continues with it. Accounting must not lose or double-count it.

Time advances in an interrupt; expensive source work remains bounded foreground work. Native ownership means the IRQ has already committed the audible event: foreground acknowledgement must not trigger it again. Never clear attack acknowledgements just because navigation or an unrelated setting changed.

Native/PCM/link paths have different ownership and clock rules. HRAM native-launch queue storage aliases sync FIFO space while sync is OFF. Unguarded writes/clears when sync is enabled can corrupt wire state. Preserve the guards and verify actual cable behavior separately.

## 4. Immutable editing snapshots: safety without multi-loop staleness

`storage.c` keeps two immutable playback snapshots in **bank-2 cartridge SRAM**, after user kits. Each supports 256 seven-byte prepared note records, hash heads/chains and validity bits. The editor changes resident source data; playback reads a published snapshot. This prevents half-edited chords and repeated synthesis/search work in time-critical playback.

The important distinction is:

`source edit -> snapshot prepared -> snapshot published -> next scheduled occurrence sounds`

Those are four timestamps, not one latency number. A note whose onset just passed naturally waits for its next occurrence. Publishing a snapshot must not retrigger a sustained Wave note to make an edit seem immediate.

Failures and fixes:

- One event prepared per main-loop pass starved under drawing. A captured 31-event session took about **7.27 s edit-to-ready** and **10.26 s edit-to-audible** (3.42 loops).
- A ready snapshot published after the old step-zero IRQ attack, adding a full loop. Correct ordering publishes before the eligible attack; expensive cache notifications remain foreground.
- Bounded preparation now copies up to 16 records per batch, services audio between records, yields for real input, and abandons obsolete slot/generation work. Released edits receive priority before drawing (up to four existing batches when progress is possible), with preparation opportunities between rendering quanta too.
- Intermediate 16-step/bar-spaced publication improved latency but still missed upcoming notes. **Current ready snapshots can publish before the next step**, in the guarded native or foreground path. Do not reinstate a bar-only publication rule.
- Publication refreshes changed lanes selectively and retains active gates. An unrelated bass edit must not invalidate percussion or an unchanged ARP loop.

A later one-bar Wave matrix reduced median preparation **435 -> 201 ms**, median first changed note **2143 -> 1390 ms**, max **3633 -> 2160 ms** in that fixture. These are historical causal measurements, not a universal current bound.

**The present design is not a rolling 16-step buffer.** A 16-step-window trial shortened the wait for edits but harmed audio continuity; it was not the final answer. Rolling-buffer prototypes and attempts to remove buffering/caching made things worse and were rejected. A short horizon adds refill deadlines, ownership transitions, and bookkeeping; removing preparation returns scans/synthesis to the critical path. No defensible universal numerical gain was established for those rejected trials. Do not silently resurrect them as "the obvious fix."

## 5. ARP and LFO: compile sound work, cache validation, preserve fallback

### ARP

Common deterministic chords of up to four notes compile into prepared APU packets. Cache note ranks/frequencies and rate quotients/remainders. A short countdown reaches the dispatcher only at a real deadline. Keep generic synthesis for unsupported orders, larger chords, ownership conflicts, and other unsupported modes.

A global edit generation is not proof that this chord changed. Validate actual notes, velocities, rate, instrument, level, length, retrigger and Wave data before rebuilding. Conversely, retaining packets must not hide real edits.

The final loop fix supports an eligible **single step-zero chord plus its rest entirely on the timer**. Retrigger resets ARP position, not the unchanged source data. An unrelated bass edit during the ARP's rest once caused a redundant restart about **22 ms late**. Verifying the actual chord preserved its planned next onset.

The opposite bug also occurred: automatic looping could keep the old chord after a real chord edit. Published changed-lane notifications now revoke that future automatic loop, while retaining the current chord until its natural gate/onset. `test_arp_loop_edit_isolation.py` checks real erase/restore, not just unchanged playback.

BPM is capped at **240**. ARP straight/dotted division tops out at **1/32**; triplet is capped at **1/16** so it does not exceed the intended straight-rate ceiling. FREE UI runs approximately 1..16 Hz (stored durations clamp to 63..1000 ms); larger UI rate means faster. Do not restore the old enormous ranges based on one passing emulator trace.

### LFO

The first timer LFO made 1/32 usable but slowed the whole editor. Continuous three-voice work at 256 Hz was too expensive. The retained design prepares 64 phase coefficient entries per native voice, advances phase accounting at 256 Hz, and bounds register refresh to **128 Hz**, skipping unchanged coefficients/register values.

The big win was replacing IRQ period multiplication/octave shifting with the fixed-ROM MIDI-note frequency lookup and prepared signed coarse/fine offsets, plus register-ABI/unrolled fixed-channel work. One measured worker fell **4.90 -> 0.97 ms**, and menu response returned from roughly 117-142 ms to about 50 ms. The assembled pitch kernel was checked across 518,784 combinations; lookup rounding can differ by hardware frequency ticks from the old approximation.

Another hidden cost: LFO configuration validation consumed about **12% exclusive CPU while rebuilding zero tables**. Cache completed validation by actual revision/configuration, with cheap ownership/transport/power/bypass checks. Fine detune, bend, tables and mono ownership can change without the broad pattern generation, so they still need direct guards. Avoid recursive preparation; capture the generation before yielding and recheck afterward.

A signed residual at the 128 Hz work boundary avoids alternating timer-period quantization artifacts while preserving average phase. Native note attacks reconcile LFO pitch so an old foreground pitch does not overwrite a newer IRQ phase.

Rejected: 64 Hz refresh improved UI by reducing modulation detail; generic foreground LFO note dispatch worsened note timing without solving the UI. Neither is the accepted solution. Some slower/free/dotted/triplet or combined-modulation edge precision remains quantized; the user preferred note timing/UI over perfect modulation. **Do not equate a regular note onset with perfectly timed LFO edges.**

Global MOD ENABLE is a session bypass, defaults ON, and preserves stored settings. OFF bypasses shared ADSR/LFO processing, retains direct tuning and hardware envelopes, and leaves ARP available. It is a useful editing tool and a diagnostic control.

## 6. Graphics and input: show the minimum correct change

All programmed note bodies are black. Playback alone decides which note sounds in MONO and which PCM hits are admitted. Selection inversion remains. The old grey/non-grey admission visualization forced lowest-note/overlap scans and mode-dependent recoloring; even one ARP note could lose fast editing, and switching back to MONO retained the cost. Removing that visual dependency cut one reported ARP drag's visible latency roughly **2763 -> 502 ms**. It did not change musical admission.

Selection is visual work, not a reason to rebuild musical notes. Reciprocal inverted-tile variants make masks cheaper. Preserve tile reference counts and invalidate both links when either cached tile is reused.

Source edits/collision checks still occur during drag/resize. The implementation is **not** a fully offset-only transaction. Defer/coalesce note reconstruction while D-pad is held; commit drawing/preparation after the final directional release even if A/B remains held. Releasing Right while Up remains held is not final release. Single-note changes can coalesce original/latest replacements; unsafe overlap/group cases use a bounded compositor.

Fast tap release also moved expensive replacement drawing out of the input handler, allowing queued taps to coalesce. Group membership uses a validated bitset/cache rather than repeatedly reading every event through banked selection calls. One measured group-tap series reduced event reads 3905 -> 492 and median acknowledgement about 586 -> 368 ms. Invalidate membership on count, generation, slot, track or selection changes; keep collision checks. An early release implementation forced 2-3-second full redraws and was rejected.

The compositor yields through resumable scans/tile quanta; newer edits restart staging from current data while retaining the dirty union. Obsolete viewport/meter/mode/length/track jobs must be cancelled. Preserve every real input edge. Synthetic held repeats are bounded, and accumulated repeat debt is discarded instead of replaying seconds of movement after a stall.

Top-bar stalls were often delayed visibility, not lost input: publish static header focus before an interrupted full-grid repaint. Do not scan dynamic tile reference counts for a static header change. A measured four-region stall fell from **3.5-3.7 s to 134-184 ms**.

Octave navigation must retain reusable rows rather than invalidate the whole roll on release or idle edit service. Hiding the keyboard alone saved about 9%; fixing unnecessary reconstruction was the real improvement. Keep the keyboard. Ordinary navigation, selection, move and resize stop at the visible edge; release/repress D-pad to cross. Enter the opposite edge of the destination page. Full-page drawing gates held-repeat resumption so lag cannot cause overshoot.

A chord-resize deadlock was another ordering mistake: an edge latch waited for the bottom of a renderer that the held-preview branch never reached. Decouple gesture progress from pending full note reconstruction; a page round trip must not be required to recover. Do not discard dirty work merely to make the cursor look responsive.

Keep duration 256 and 256-step lanes, odd meter grids, offscreen notes, lowest-note MONO admission, overlapping notes, and selection/velocity pixels correct. A faster incorrect compositor is not a win.

## 7. Smooth Playback was the diagnostic breakthrough, not an excuse

Stopped audition: plotting/painting plays immediately; moving to another cell previews again; resizing previews the new duration on B release. A tap/release previews an existing note or an empty cell at the last adjusted plot length. Empty-cell A must silently deselect when a selection exists. SELECT SCREEN and SELECT ALL have different scopes.

Smooth Playback starts with **Start+Select while stopped**, either order. It draws `START+SELECT TO STOP`, completes the display and note/ARP/drum preparation while musical time is stopped, then starts the clock. It keeps LCD timing, input and VBlank alive but skips ongoing render/flush/feedback/sprites and automatic OAM DMA. Normal Select+A and mixer starts remain graphical. There is no Smooth Settings toggle.

The initial jitter improved when playback waited for both startup drawing and caches. The remaining loop jitter could no longer be blamed on live drawing: repeated unchanged source preparation and foreground percussion were still audible. Turning RETRIG off helped diagnostically, but dropping retrigger was not the fix.

The Smooth launch legend/live-pad-control expansion and the "remove all buffers/caches" experiment were rolled back. Keep the accepted simple static listening mode; adding UI to it requires a new benchmark, not an assumption that "it's only a little drawing."

An early Smooth-only drum table borrowed the inactive note-buffer allocation. That was safe only under its strict stopped/read-only lifetime. **It is not the current graphical design** and must not be reused while edits can build that inactive snapshot.

## 8. Final NORMAL_PLAYBACK implementation

The same preparation discipline now applies to normal graphical playback without blanking its screen:

1. Prepare the immutable note snapshot and initial ARP state before starting musical time. Do not reset the continuous clock when native ownership starts.
2. Give eligible synth percussion **two independent prepared SRAM tables**. Each has 256 five-byte packets and a small WRAM header. Foreground prepares an inactive table in bounded two-step service batches; timer publication switches it at a musical step, without restarting its phase.
3. A small **NONBANKED countdown in fixed ROM** updates elapsed time and enters the banked drum dispatcher only for a step or gate ending. Avoid a large banked call on every timer interrupt.
4. **Exclude timer-owned percussion gates from foreground `seq_next_deadline()`.** This was the decisive second ah-ha: IRQ-owned noise flags contained values such as 1 for ownership, not foreground durations. Treating them as deadlines made the foreground sequencer run almost continuously. Prototype `seq_frame` exclusive CPU reached roughly 66% at idle. Removing redundant wakeups restored navigation while retaining tight audio.
5. Compute startup tempo divisions before the first attack. A division after triggering the first note had delayed the first interval. Gate endings subtract elapsed time from a cached step deadline; do not walk an almost-completed musical step one timer unit at a time inside the IRQ. Account elapsed time at the old BPM before retiming to a new BPM.
6. Native melodic lookup uses byte-sized ranges with explicit count-256 support. Hash collisions must match lane AND actual step. A matching head is already that melodic lane's lowest note; return directly. Do not turn byte optimization into event-255/step-255 or cross-lane corruption.
7. Global note edits do not revoke unchanged drum ownership. Actual drum packets/settings are rebuilt selectively. Slot/generation changes cancel obsolete work. Stop and unsupported ownership transitions clear the job safely.

Admission is deliberately conservative: internal clock, straight swing, synth hat/snare/kick, no shared P1/noise notes, no drum modulation, supported engine/mode and mute/solo ownership. PCM, link sync, shared voices and modulated drums retain existing fallback paths. No claim of identical improvement applies to all of them. At compatible grids the supported drum path uses 256 Hz; otherwise 1024 Hz. A 512 Hz experiment improved some fast-modulation traces but cost UI headroom and did not uniformly improve others; it was not retained. Reordering ARP ahead of LFO gave a small local gain without resolving the case and was reverted too.

### Accepted measured result

Matched DMG-mode actual APU-register probes: 120 BPM, P2 three-note 1/16 ARP with rest, 128-step Wave bassline, synth hats every sixteenth, snare and kick. Earlier main means `60804a2`, not the newly promoted main.

| Operation | Earlier main worst drum interval error | Tuned worst drum interval error | UI median, earlier -> tuned |
|---|---:|---:|---:|
| Idle | 11.168 ms | 0.356 ms | n/a |
| Navigate | 9.485 ms | 0.387 ms | 33.5 -> 33.5 ms |
| Menu | 8.270 ms | 0.386 ms | 33.5 -> 33.5 ms |
| Cell edit | 26.712 ms | 0.354 ms | 58.6 -> 50.2 ms |
| Paint | 35.133 ms | 0.388 ms | 67.0 -> 58.6 ms |
| Multiselect | 17.310 ms | 0.357 ms | 50.2 -> 50.2 ms |
| Group move | 37.408 ms | 0.341 ms | 167.4 -> 133.9 ms |

After the graphics fixes, worst regular-test drum errors remain below 0.4 ms, including the active melodic-LFO pass. Verified normal/LFO/240-BPM fixtures retain dense hat attacks and have no native note-buffer underruns. The user strongly approved the improvement; the final NORMAL_PLAYBACK change does not have separately recorded comprehensive hardware qualification.

**Limits remain:** 1/32 live ARP plus LFO can show roughly 4-5 ms outliers with graphics; some prior Smooth cases are tighter. Dense painting can stall input for seconds, and large selection moves retain long worst cases. Do not replace these facts with "perfect across the board." The regular 1/16 benchmark is not a guarantee for maximum modulation, PCM, link, or every pattern.

## 9. Memory and visual ownership are part of performance correctness

Current scratch ownership, cartridge SRAM:

| Region | Owner |
|---|---|
| Bank 2 AD00..B61F / B620..BF3F | Two 2336-byte melodic snapshots; preserve both |
| Bank 3 A000..A81F | User presets and bank names |
| Bank 3 AA00..B1FF | 2048-byte pattern clipboard |
| Bank 3 B400..B80F | Note/region clipboard |
| Bank 3 BF80..BFFF | Persistent root metadata |
| Bank 3 A820..A9FF + B810..BB2F | Drum table 0, split on whole packets |
| Bank 3 B200..B2B3 + BB30..BF7B | Drum table 1, split on whole packets |

Bank-0 B000 and neighboring regions have page-specific roll, font, preview, mixer and file scratch overlays. Read declarations and lifetimes before using them. Shared memory is not free memory. Keep RAM bank transactions bounded, restore bank zero before interrupts resume, and preserve interrupt/ROM-bank state. `volatile` alone is not atomic publication. Check ROM-bank bounds and stack reserve after every build; a successful linker exit is insufficient.

The last display bugs illustrated this concretely:

- Mixer rails occupy tiles 244..249, overlapping sequencer M/S glyphs 244..251. Claiming rail graphics must invalidate M/S cache, even if an aborted grid rebuild cleared the usual grid-font flag.
- Pad copy/paste opens overwrite confirmation, restoring font tiles over faders. Returning without `mixer_open()` left numeric knob values unchanged, so the old cache falsely skipped drawing rails. The result looked like filename garbage despite never opening a filename editor.
- Mixer now revokes M/S ownership; font restoration revokes fader ownership; font uploads use a local buffer instead of deferred staging in SRAM that pattern/file preparation can reuse.

`test_shared_ui_tiles.py` fails the old ROM on the real copy/paste/confirmation path and passes the fix, including all 42 rail tiles, copied pad bytes, eight M/S variants and repeated transitions. Do not remove these ownership checks as "redundant redraws."

Another misleading symptom was silent C1 Wave notes and spontaneous pad changes. Internal `event()` shared the external MIDI performance mapper, consuming notes 24..28 as pad commands. External parsing now enters `midi_event()`; internal playback/audition cannot launch pads. MIDI LAUNCH defaults OFF, enabled explicitly in SYNC. Do not conflate this routing bug with CPU jitter or revive it in song mode.

## 10. Experiments must compare the same music and the right metric

Generate versus live ARP was not a universal win. The meaningful comparison was **live 1/32 at 120 BPM versus generated 1/16 at 240 BPM**, with every accompanying track's positions, durations and lengths doubled to preserve wall-clock music. Merely doubling BPM changes the workload and the music.

At the same 240 BPM explicit generated notes were cheaper in that historical experiment. Against live 120 BPM, the answer depended on page/clock: doubling sequencer step frequency could outweigh saved ARP work. Prepared notes initially benefited sequencer pages more than menus; extending eligible native playback across pages addressed that asymmetry. Those earlier results include obsolete ARP failures and do not justify deleting today's live ARP. Keep meter semantics and grid resolution separate from a CPU benchmark. Current sequencer timebase remains sixteenth-note based; odd-meter display/scaling must not silently delete notes.

For every performance change:

- Freeze the baseline ROM, matching NOI/map/static symbols and disposable save. Build identity is SHA-256 plus commit, not filename or stable "1.0" label. Never mix old ROMs with current symbols.
- Use forced **DMG, 4,194,304 cycles/s**, emulated cycles and real button gestures. Host CPU time or a faster emulation setting is not Game Boy headroom.
- Probe actual APU trigger/frequency writes and PCM service, not only `play()` entry or `basepitch` after the register write. Include attack writes in LFO observations: omitting a loop-boundary Wave attack once falsely blamed LFO for a 12.7 ms error.
- Measure startup, ordinary steps, repeated loops, rested ARP return, pattern launches and inter-channel relationships separately. Run long enough for the longest track to wrap repeatedly.
- Check attack counts, exact pitch/order and dense-hat maximum gaps. A skipped hit can look perfect if interval error is reduced modulo the grid. Retrigger ON may intentionally shorten a free-running interval; compare the intended schedule, not a simplistic period.
- Check source edit time, ready time, publish time, first changed APU onset, input acknowledgement, visible completion, final pixels and retained note count. A low median does not cancel a multi-second worst case.
- Profile exclusive time: subtract tracked nested IRQ/child spans; inclusive percentages overlap. Banked trampolines and callee-cleaned stack arguments matter to entry/return hooks. An incorrect return-SP probe can invent huge function costs.
- Wait for a snapshot based on actual state, not an arbitrary fixed frame count. Stop hardware serial when injecting synthetic RX bytes; an open-cable transfer can overwrite a test with FF bytes.
- Compare exact failures on the frozen baseline. Do not relax thresholds, drop failed cases, or call an old broken menu bootstrap a new DSP regression. Conversely, a previously passing command is not proof it passes the current build.

## 11. Regression gate before future integration

Run from a clean checkout of the intended code. Preserve user emulators and saves; tests use disposable RAM and `stop(save=False)`. Use the preserved ARPTEST save via an explicit workspace path when needed. Build once after source changes, then test that exact image; do not edit production source during a build.

Core reproducible commands:

```powershell
python tools/build_rom.py
python tools/benchmark_normal_playback.py --verify
python tools/benchmark_normal_playback.py --lfo --verify
python tools/benchmark_normal_playback.py --smooth --verify
python tools/benchmark_normal_playback.py --bpm 240 --verify
python tools/benchmark_normal_playback.py --arp-div 3 --lfo
python tools/test_prepared_drums.py
python tools/test_normal_prepared_drums.py
python tools/test_prepared_long_tracks.py
python tools/test_arp_loop_edit_isolation.py
python tools/test_shared_ui_tiles.py
python tools/test_smooth_playback.py
python tools/test_live_note_plot.py
python tools/test_live_note_drag_resize.py
python tools/test_edit_snapshot_wave_gate.py
python tools/test_select_screen_all.py
python tools/test_wave_internal_pad_isolation.py
python tools/test_midi_launch.py
python tools/test_pcm_gate_restart.py
```

The `--verify` benchmark bounds drums and unaffected ARP in its named fixtures; it is not a blanket Wave/LFO/analog-audio certification. The fast 1/32+LFO command is a reported stress case, not a promised sub-1.3-ms pass. Also exercise modulation OFF, manual navigation/paint/selection/group move/resize, actual chord changes, gate continuity, new drum edits, awkward BPM such as 137, changed instruments and 256-step/hash collisions.

Song/launch changes additionally require same-pad retrigger, duplicate pads, changed pad, failed/not-ready preparation, paste onto active/inactive pads, PCM and shared-channel fallbacks, manual override, stop/restart, and actual paired-link/TWINK tests. Do not assert cable coverage from a headless single-master fixture.

Known harness caveats at this baseline: legacy drum selection/noise-release bootstraps fail on page 11 on both releases; old resident-launch fixture also has a baseline Wave-boundary failure. The strict LFO combined fine/coarse suite has recorded failures (including edge errors/zero observed edges in particular runs). Do not label all LFO tests green. Improve those harnesses independently while retaining raw failing evidence and the working matched benchmarks.

## 12. Rules for song mode and other future features

Song mode must be a small client of the prepared launch system, not a replacement sequencer clock or a second scheduler that fights it.

**Does not work:** at every arrangement boundary stop transport, load/copy the next full pattern, reset all instruments/ARP/LFO, search first notes, redraw the arrangement, then restart. This reproduces the original failure even if the code is tidy.

**Does work:** decide the next destination early, request bounded foreground preparation, validate that request against current state, and commit through the existing musical handoff. Preserve outgoing elapsed time, unchanged voices, clock phase and link-grid semantics. Define the not-ready policy explicitly; do not silently drop an arrangement entry, freeze the audio IRQ, or reset time to catch up.

Keep arrangement decisions/storage/UI outside the audio IRQ. At a boundary, consume already prepared state and perform bounded necessary work. Do not walk the song list, allocate memory, save a song, scan notes, rebuild LFO tables or draw tiles there. An unchanged loop must not increment broad generations every pass. A song cursor movement is not an instrument edit.

Give arrangement requests explicit ownership. Manual pad launches, held-pad retriggers, MIDI, link and song mode must not endlessly rearm/cancel one another. Stop/cancel must clear only the appropriate pending requests and preserve the user's expected transport behavior. Test takeover and recovery, not only unattended automatic advancement.

Do not borrow either inactive note snapshot for arrangement data, nor the drum tables/clipboards/root, and do not spend the 49-byte WRAM margin casually. Prefer a bounded prepared representation with a documented lifetime over broad new live bookkeeping. If more memory is necessary, justify a reviewed memory-map change and verify all old data owners.

Before merging, compare the exact same musical fixtures against `57cc9c7` or the later accepted baseline. Publish worst errors, counts, UI medians/maxima and audible-edit latency. New regressions are a reason to revise the implementation, not redefine "stable." Keep a separate branch until reviewed and tested. A feature working once is not a release gate.

## Evidence index and recovery order

1. This brief, then `git status`, branch/worktree list, accepted commit and current memory check.
2. `docs/normal-playback-audit.md` for final implementation, table map, measured matrix and limitations.
3. Source: `resident.c`, `tones.c`, `sequencer.c`, `storage.c`, `edit_irq.c`, `arp_irq.c`, `lfo_irq.c`, `drum_irq.c`, `engine_stream.h`, `native_feedback.c`, `seq_pixels.c`, `ui.h`, `mixer.c`, `smooth_playback.c` (all under `src/`).
4. Causal history: `docs/prep-work-audit.txt`, `lfo-prep-cache-audit.txt`, `arp-timer-audit.txt`, `arp-ui-audit.txt`, `black-notes-audit.txt`, `header-focus-audit.txt`, `paint-batch-audit.txt`, `selection-gesture-audit.txt`, `fast-taps-audit.txt`, `edit-latency-audit.txt`, `editor-navigation-promotion.md`, `generated-arp-comparison.txt`, `live-note.md`, `wave-midi-isolation-fix.md` (all under `docs/`).
5. `docs/smooth-playback.md` records the earlier Smooth-only architecture. Its inactive-note-buffer drum allocation and old free-memory numbers are superseded by NORMAL_PLAYBACK. Likewise, old clock handoffs and provisional ARP speed recommendations are evidence/history, not current implementation instructions.
6. Workspace-private `DATA/EXPERIMENTS/smooth-loop-20261023` contains captured user state and loop probes; `DATA/SAVES/stress-testing/arptest-original.sav` is preserved test input. Never overwrite originals. Ignored build JSON/logs are local evidence, not guaranteed to exist on another team's machine; the test source and this brief must remain sufficient to reproduce a comparison.

The repeated lesson: **keep unchanged sound running; prepare only real changes; publish them before their deadline; let controls draw promptly; prove the result at the APU and at the screen.**


## Songlink hardware qualification ? October 24, 2026

The user played the completed KILLING demo simultaneously on two real DMGs over a link cable and reported extremely tight sync with barely audible phasing. Preserve `GAYBOY-SONGLINK-DEMO.gb` as the hardware reference. This qualifies GAYBOY-to-GAYBOY Song Mode; it does not resolve the separate TWINK/Monosimp late-attack issue or qualify live-pattern sync.

Both machines compile their own arrangements and fill their APU queues while stopped. BUFFERING remains visible until both are ready; a shared GO serial completion establishes the playback epoch. Smooth's final stop legend is fully scanned out before GO, and Smooth ownership must remain held while waiting for the peer after local compilation finishes.

Master playback uses the unchanged song timer handler. After GO, master SIO receive interrupts are masked; optional timestamp transmission happens in foreground only with audio headroom. Two bytes carry an arbitrary hardware-clock point plus quarter-tick phase. The slave timestamps byte one, then corrects oscillator drift by altering one future TMA reload (251/253 versus normal 252). Phase math stays in foreground; the short slave IRQ wrapper resets TMA and accounts for completed corrections. Never write TIMA or DIV to correct an already-running song.

Critical discovered race: a foreground `IF_REG &= ~SIO_IFLAG` can erase a timer request that arrives between its read and write. An unsafe build lost 14 pending audio timer interrupts in a 60-second reverse-master stress run. Steady clock transmission must not clear IF. Fixed runs lost zero requests.

Failed approaches included whole-musical-tick corrections (audible jitter), direct TIMA correction (overflow/reload hazards, potentially ~62 ms gaps), averaged checkpoints (worse response), and foreground messages that assumed exact wakeup intervals (skipped checkpoints and drift). The retained protocol timestamps whenever a safe sending opportunity actually occurs.

Qualification evidence: completed demo with +1000 ppm oscillator mismatch, zero queue underruns and no Smooth VRAM writes; maximum paired-device attack separation 0.470 ms. A 240 BPM ARP/LFO stress run at -1000 ppm had zero underruns and maximum separation 1.282 ms. Reverse-master 137 BPM tests stayed within existing 1.3 ms note-timing gates. Cable-loss/start cancellation/restart tests preserve resident notes and arrangements. These emulator bounds are fixture-specific, not hardware guarantees. Ordinary playback's seven-phase editing benchmark passed with zero underruns and maximum measured drum grid error 0.343 ms.

The project stays 32 KiB: five fixed 2 KiB pad records and one arrangement per SRM. Pattern/song archive menus were removed; the 128 KiB library experiment was abandoned and archived outside the active source tree. Do not compact or relocate working pads or reduce playback preparation to add storage. The completed sanitized demo source and reproducible build command live in `assets/demo/`.

Live-pattern sync still follows the old received-clock/foreground path and disables several prepared IRQ paths. Rework it only on LIVELINKREWORK: preserve this Songlink implementation, the fixed SRAM map, PCM accounting, launch quantization, and remote control behavior. A local free-running slave clock plus bounded phase correction is the intended experiment; timing bytes must not directly execute musical steps or source scans.

# How GAYBOY achieved smooth pattern launches

The smooth launch comes from **preparing the incoming pattern ahead of time and doing only necessary work at the boundary**. Buffering and change detection work together: the buffer moves reads and first-note lookup out of the critical moment; comparing live state avoids copying, resetting and rebuilding things that already match.

## Keep pattern notes resident

Five patterns have separate 2 KiB resident SRAM records. Their note events stay in those records. Switching pads selects the destination record instead of copying its entire event pool into a shared playback buffer. Track counts and offsets describe the selected pool; the event lookup index is invalidated when its source changes.

This removes a bulk note-copy cost from every launch. It also means the launch buffer is a small staging area for launch state, not a second complete pattern.

## Prepare before the musical boundary

`sparse_request()` queues the destination and snapshots the outgoing pattern only when it is dirty. `sparse_prepare_service()` stages the incoming name, metadata and instrument settings in a private 449-byte WRAM buffer. It copies at most 16 bytes per service call and defers work when audio service is due or approaching its deadline.

Preparation also scans incoming melodic events to resolve the first-step notes, including unsorted events. The prepared notes avoid repeating that search during the handoff. Private WRAM keeps this state separate from renderer scratch memory.

The quantized launch waits until preparation is ready. It then installs at an eligible musical boundary, rather than blocking the boundary on unfinished preparation.

## Apply changes selectively

`tones_match_buffer()` compares the staged instrument state against the live state. It records `resident_tone_generation`; the fast path remains valid only if that generation still matches at installation. This prevents a live edit made after preparation from being mistaken for an unchanged instrument.

When the complete state matches, restoration skips instrument application and keeps runtime state. Otherwise, `tones.c` uses `changed_copy()` for individual parameter blocks. Wave uploads, drum invalidation and global register writes are conditional on their relevant changes. FX restoration also has its own change checks.

“Copy only what changed” therefore means selective blocks and conditional downstream work, rather than a universal byte-by-byte diff. Avoiding an unnecessary envelope/LFO reset or wave reload matters as much as saving the copy itself.

## Preserve time and sound through the handoff

`seq_pattern_handoff()` changes the pattern on the running transport. It preserves pending elapsed time; linked playback also preserves the received clock grid where required. First-step events replace their own voices without a blanket stop/start between patterns.

An identical active wave note can keep its oscillator when instrument, pitch, velocity and pan conditions match. Identical instruments avoid needless runtime resets; changed settings still take effect. Same-pad retriggers use live data directly and avoid preparing a different pattern.

Audio and input have priority over cosmetic work. Mixer rendering reuses an unchanged strip image, limits pad redraw work, and defers fader uploads after a launch. Same-pad retriggers retain the pad image and request a redraw only when the displayed playing/queued state needs it. Boundary rearming can queue its small request during input servicing, so an input action does not suppress a repeat.

## Performance controls and verification

Hold A on a pad to retrigger at the selected musical interval. A+Up selects a faster interval; A+Down selects a slower one. A+Left/Right selects the adjacent pad and launches it with the same interval, then continues retriggering without releasing A. NOW remains a one-shot launch.

The relevant regressions are `tools/test_resident_launch_delta.py`, `tools/test_resident_hold_launch.py`, and `tools/test_mixer_pad_hold.py`. They check unchanged-state preservation, changed instruments, wave continuity, musical repeat intervals, adjacent/wrapped pad switching, release behavior and PCM underruns. The adjacent-pad fixture runs at 300 BPM with two PCM hits and 1/32 retriggers. The final single-pad timing regression measured 18.9-30.4 ms between retrigger dispatches at that tempo, around the 25 ms target, within its existing 18-33 ms bounds. No bounds were relaxed. The legacy two-machine hold harness times out during boot/menu setup on both the previous release and this build; that harness does not establish linked-device coverage for this change.

“Perfect” describes the intended musical experience, not a proof of zero latency in every configuration. Emulator dispatch timestamps are not analog onset measurements. Preserve the actual timing results and hardware observations when evaluating further changes; do not attribute the result to the buffer alone.

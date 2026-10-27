# Prepared TWINK song playback

Branch: `TWINK_SONG`, based on qualified `TWINK_CHORDS` commit `50a9a4f`.

Song playback previously rejected sync mode 6 and any populated MS lane. This
branch allows TWINK song playback and compiles MS held sets before transport
starts. Monosimp continues to choose its own mono/poly/arp interpretation and
patch. There is no receiver acknowledgement, clock negotiation, patch transfer,
or remote arp calculation on the host.

## Timing contract

- Keep the existing local song register programs and 1024 Hz timer.
- Compile sorted, velocity-scaled, CRC-complete F5 packets while BUFFERING.
- Prepare each frame's optional packet in foreground before publishing qwrite.
- Commit local APU writes first. Only then copy at most 19 prepared bytes to the
  existing asynchronous TWINK wire ring; never wait for space or the receiver.
- Retain the hardware-qualified serial guard. Physical packet transmission
  takes time: successful local timing tests do not imply zero remote latency.
- Remote chords follow their own MS lane length; contiguous same-pad clips
  preserve phase. Different scenes restart the incoming lane. Gaps release it.
  Cold seek reconstructs the held set at the cursor. Stop/panic releases Monosimp.
- Count wire-queue exhaustion in `song_twink_overflows`; qualification requires
  zero. Keep local audio running rather than block its timer on a full ring.

## Memory ownership

The 32 KB battery layout, resident pads, local frame ring, and SongScene/
SongRuntime sizes are unchanged. No WRAM is allocated. Five six-byte descriptors
at bank-zero A210..A22D and six runtime bytes at A230..A235 overlay stopped-only
editing scratch. The existing unused MIDI RX ring holds eight 32-byte immutable
packet slots indexed by the corresponding local song frame. The IRQ copies the
packet into the independent transmit ring before freeing that frame slot.

Compiled MS records share the existing bounded 4864-byte bank-2 song cache.
An overfull cache fails before playback with AUDIO CACHE FULL. This branch does
not enlarge or dynamically allocate playback memory. `check_memory.py` verifies
the additional overlay boundaries. Cold `song_start` moves to bank 60 to keep
the song compiler/commit bank within its ROM limit.

## Verification

Only SameBoy qualifies audio/timing. Hardware listening remains the final check.
`tools/test_song_twink.cjs` drives two distinct ROMs over the real emulated cable
and compares actual local APU writes against an MS-free reference fixture. The
fixtures are private copies; user batteries and emulator sessions are untouched.
`tools/test_song_link.cjs` checks the bundled composition with TWINK off and
Gayboy song sync, including Smooth and graphical transport entry.

Qualified candidate SHA-256:
`adf25cd8612d51cbc12b15e040f9c37edb5a2aaad4d5e3c819493d8a1c65f98e`.
Receiver is unchanged `MONOSIMP-LEARN-NOISE-D.gb`, SHA-256
`de079e296852a5cf7c2b6bb047cd6a9a46999c53f8ed372cf0c9e31f01440012`.

Matched actual-APU comparisons against the qualified TWINK_CHORDS host:

| Fixture | Local attacks, kick/P2/Wave/noise | Worst local grid error | Largest relative onset difference from reference |
|---|---|---|---|
| 120 BPM, local ARP + bass + drums + MS chords | 20 / 80 / 4 / 80 | 0.448 ms | 0.067 ms |
| 240 BPM, 1/32 local ARP + active pitch LFO + eight-note MS chord | 20 / 160 / 4 / 80 | 0.412 ms | 0.284 ms |
| 240 BPM, graphical page crossing + eight-step MS lane | 84 / 336 / 20 / 336 | 0.409 ms | 0.413 ms |

Counts and pitch/envelope event values match each corresponding reference.
All these runs had zero register-buffer underruns, transmit-queue overflows,
wire aborts and unarmed edges. Hardware-clock/wall-clock differences stayed
below one timer tick, without accumulating lost time. Minimum stack pointer
stayed above DE00. Additional fixtures cover zero MS level, MS mute, seeking,
natural end, song looping and manual stop.

These are local timing results, not a claim of simultaneous sound from both
machines. The unchanged one-way receiver still waits for a complete F5 packet
and processes the chord through its existing synth path. Measured three-note
attacks were approximately 19–25 ms after first-byte start; larger eight-note
packets can approach 37 ms. This implementation does not compensate that
external latency or change Monosimp's attack path. The user subsequently tested
this exact host on hardware and reported that it works pretty good. The user
subsequently approved merging GAYBOY into main and publishing the web build.

The original new-fixture trials accidentally silenced drums by clearing their
engine-level defaults. They are **not** full-load performance evidence. In
particular, old `song-twink-baseline240.json` and `song-twink-eight240.json` are
invalid silent-drum fixture reports. The corrected test now explicitly requires
audible kick, noise, P2 and Wave events and compares event values as well as
counts. Use `baseline-stress240` / `eight-stress240` for the qualified stress
comparison. Reports remain under `build/`; the hardware ROM is preserved in
workspace `DATA/TESTS/TWINK-SONG-20261026/GAYBOY-TWINK-SONG.gb`.

## Current handoff after hardware testing

The user approved Monosimp promotion; its main is now 0a512be and rebuilds to
the identical accepted receiver SHA above. Prior uncommitted Monosimp-main
experiments were preserved on archive/main-before-synth-core-20261026.

No blocking song-TWINK implementation work remains after the hardware report.
The user subsequently approved GAYBOY main integration and web publication.
The merged main build must match the accepted host SHA above; release checks
cover linked live panic stop, linked Smooth and prepared TWINK song playback.
Separately, requalify cable disconnect/reconnect on the new one-way
protocol: the historical TODO describes a retired handshake and cannot prove
a current failure. Further external onset-latency tuning is optional future
work; local host timing must remain protected. Gayboy shared panic stop and
linked Smooth start/stop already exist and passed their recorded checks.

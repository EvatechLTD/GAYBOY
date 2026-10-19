# Linked mixer and native sync

## Using the mixer

GAYBOY sync defaults to AUTO. Both stopped machines listen; the first local
Play becomes master and starts its peer. Stop returns AUTO machines to listening.
MASTER and SLAVE overrides remain available. Other sync modes retain manual roles.
The native start claim runs before arming the musical clock. A detected start
collision cancels playback and shows START CLASH - RETRY; press Play again.

Select LOCAL/LINK in the mixer header to switch between this machine and its
connected peer. LINK offers pattern selection, track volume/pan/mute/solo and
individual drum mute/solo. Hold A with arrows to change volume/pan. The master
shows acknowledged remote values; COMMAND PENDING means an edit is in flight.
Edits are absolute and guarded by the remote pattern generation. A stale edit is
rejected rather than applied to a different pattern. One follow-up control or
launch can wait behind an outstanding command; repeating the same parameter
coalesces to its latest requested value. Different additional edits should wait
for the pending indication to clear. This deliberately bounds protocol work.

Four 40-pixel pattern pads are visible at once, with five characters per label.
Move horizontally to page through visible pads. The focused pad's full name is
shown above; off-page playing/queued pads have indicators. SELECT opens layout
editing for the selected machine: arrows select, A hides/shows, B restores all,
SELECT returns. Hiding affects display/navigation only. LOCAL and LINK layouts
are independent. Layout and PAIR changes apply immediately; battery writes wait
until stopped and use redundant, checked storage records.

PAIR launches matching numbered pads on both machines. Both prepare first;
the master's existing quantization boundary commits the prepared pair with the
native pattern marker. NOW becomes 1/1 for a pair, since a slave cannot invent
an independent clock epoch. PAIR off preserves independent pattern selection.

Names are sent automatically after successful pattern save/load and song load,
and after a new connection. There is no manual name request and no need to stop
playback to refresh names. Loading a pattern/song retains the existing storage
transport behavior; name publication itself never stops playback.

## Wire and timing contract

During playback optional control and metadata add ZERO serial transfers.
Native numbered clocks retain all six sequence bits. Tick values 0..47 can carry
one extra bit in bit 6: their codes are 80..AF or C0..EF. Ticks 48..63 remain
B0..BF, preserving F0..FF for transport/tempo/pattern status. The clock phase
accumulator, six-bit gap recovery, pulse rate and raw sync paths are retained.

A new peer identifies itself through the exact reverse idle signature
F4, G, B, 01 on existing transfers. Only then does the master encode data bits.
Legacy peers receive the original numbered clocks. A connected peer uses F4 as
an idle presence heartbeat, including a reserved reply between frames so
continuous slow-tempo state traffic cannot starve presence. The slave's reply bytes use the same full-duplex
clock transfers. Stopped forced MASTER can exchange foreground packets; stopped
AUTO peers do not generate polling clocks or elect a role merely to populate UI.
Consequently AUTO discovers the expanded mixer after Play, not at idle boot.

Forward control bandwidth is 48 bits per 64 clock pulses: approximately 9,
36 and 90 bits/s at 30, 120 and 300 BPM. A 12-byte control frame therefore takes
roughly 10.7, 2.7 or 1.1 seconds of available clock capacity, plus scheduling and
acknowledgement. Initial eight-name discovery can take over a minute at 30 BPM
because acknowledgements also use this bounded forward channel. Essential
transport can interrupt optional frames. Slower metadata is preferable to
borrowing a musical deadline. No claim of instant remote controls is made.

Only the fixed-ROM bit-ring lookup runs before a clock is launched. The slave rearms serial immediately from a precomputed reply byte, then
prepares the following reply without touching the active shift register.
The native master serial ISR starts a due clock before handling optional reverse data; it never
parses frames, changes ROM/SRAM banks or accesses storage. Optional receive
backpressure drops reverse metadata and relies on acknowledgements/retries;
it cannot fill the master's musical queue. Clock receive overflow remains an
error. Foreground publishing and parsing are bounded. Metadata cannot change
clock phase, BPM, instrument positions or start transport.

Native idle startup adds F5/F7 claims before musical timing begins; a passive
peer answers F6. Simultaneous claims are handled conservatively, not by running
two clocks. Existing F1 BPM, FA/FC transport and F2 phase markers remain the
only essential non-clock transmissions while playing.

## Framing and recovery

Frames are F3, body length (5..24), type, 14-bit session, 7-bit request,
payload, CRC7. Body bytes are seven-bit clean. CRC uses polynomial 09, initial
zero, seven MSB-first bits per byte over length and body excluding CRC.
Types: HELLO=1, WELCOME=2, STATE=3, NAME=4, SET=5, LAUNCH=6, PREPARE=8,
READY=9, NAME_ACK=10. HELLO/WELCOME contain G, B, 01.

A session change discards pending edits and preparation. Commands have request
IDs and bounded retries; duplicates do not repeat edits. SET includes the expected
14-bit pattern generation. STATE includes authoritative controls, slot, pending,
quantization, generation and whether the last command applied. NAME retry deadlines account for tempo and forward ACK capacity.
NAME_ACK includes
the slot and checksum of the name, preventing an old ACK from clearing a newer
save. Dirty bits clear before reading names so a concurrent successful save
remains scheduled. Invalid lengths/CRC quarantine optional data until a new
frame or essential status. A numbered-clock gap discards the partial optional
bit frame while retaining the original musical gap recovery.

PAIR uses PREPARE/READY, then the existing F2 phase marker (bit 6 of its
seven-bit clock index tags a pair commit; six-bit phase recovery is unchanged).
An ordinary later marker cannot commit an abandoned prepared pair; no second optional
commit transfer can race the boundary. Disconnect, session reset, timeout or
stop cancels pair preparation. Optional traffic never requests oscillator reset.

## Validation and limits

The real two-machine SameBoy cable tests use emulated serial edges, not injected
receive queues. They cover dense P1/P2 plus two PCM voices, eight paired launches,
independent selection, automatic live-save names and remote controls. Wire traces
assert no additional live metadata transfers, no aborted serial transfers, no
receive overflows, unchanged underrun counters and aligned settled pattern grids.
Additional tests cover CRC rejection/retry, duplicate and malformed frames,
reconnect, pinned-main compatibility in both directions, competing starts,
role reversal/overrides, all five slave clock modes,
layout power cycles/redundancy, incremental/full pixel equivalence and queued-pad
flash cancellation.

The current 300 BPM IRQ/audio fixture passes delivery, note rate, startup and
subdivision budgets with zero measured underruns; longest measured IRQ is 7680
cycles. The pinned main baseline's corresponding historical startup budget fails
with corrected native hardware-write instrumentation; its other budgets pass.
The candidate adds bounded CPU work (approximately one percentage point in this
fixture). Zero extra transfers is a wire guarantee, not zero CPU overhead or a
proof that all hardware note-latency distributions are identical. Actual console,
cable and hot-plug checks remain necessary before a release timing-parity claim.
WRAM reserve is 1045 bytes and reserved stack is 512 bytes; adding globals needs
another memory audit. Test ROM, symbols and JSON traces live under build/.

The older standalone test_mixer_live.py is not a passing acceptance gate: it
hits an input-release timeout on the candidate and a cache-ownership assertion
on pinned main. Its fixture assumptions need a separate update. The strict
one-video-frame handoff test also fails in native mode on both builds:
Native observation runs across the five launch cases measured 14.874..17.948 ms
on the candidate and 15.105..18.312 ms on pinned main; precise samples vary
with UI/IRQ phase, and individual cases are not uniformly faster.
The threshold was not relaxed. These failures must remain visible; passing
cable/IRQ tests do not imply that every historical test is green.

Reproduce the primary gates after building the ROM and tools/build_sync_link.py:

```text
node tools/test_linked_mixer_live.cjs --bpm 30
node tools/test_linked_mixer_live.cjs --bpm 120
node tools/test_linked_mixer_live.cjs --bpm 300 --storage
node tools/test_linked_mixer_faults.cjs
node tools/test_linked_pair_timeout.cjs --bpm 120
node tools/test_linked_mixer_reconnect.cjs
node tools/test_sync_auto_start.cjs
node tools/test_sync_link.cjs --bpm 300 --stress
node tools/test_linked_mixer_legacy.cjs --reference-rom <pinned-main.gb>
python tools/test_sync_irq_budget.py
python tools/test_slave_clock_cpu.py
python tools/test_mixer_pixel_cache.py
python tools/test_queued_flash.py
python tools/test_mixer_layout_persistence.py
```

Reference main is 258b713064ab6796443b6237a040718b1d5d7e9e. The locally pinned
reference ROM SHA256 is
309cb20e48437f552fc009a26cb60a135e505de51ee78d1a262832da6f2f6051.

Sparse mixer layout occupies root bytes 110..120, leaving the current main
checkout's Quick Menu assignments at 100..109 untouched on integration.

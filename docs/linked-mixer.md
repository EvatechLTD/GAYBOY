# Linked mixer and native sync

## Using the mixer

GAYBOY sync defaults to AUTO. Both stopped machines listen; the first local
Play becomes master and starts its peer. Stop returns AUTO machines to listening.
MASTER and SLAVE overrides remain available. Other sync modes retain manual roles.
The native start claim runs before arming the musical clock. A local AUTO start
first leaves time for an in-flight external claim to finish. An eight-byte
zero guard distinguishes overlapping internal claimants from an idle high wire;
it runs only at transport startup and does not change the serial ISR. A local AUTO Play
press in the six video frames following an incoming Start is coalesced with
that start, preventing near-simultaneous presses from stopping only the slave. A detected start
collision cancels playback and shows START CLASH - RETRY; press Play again.

Open Start ? PAGE ? MIXER SETTINGS. MIXER VIEW selects LOCAL or LINK;
PAIR PATTERNS, SYNC TYPE, SYNC ROLE and both layout editors live here.
B returns to the mixer. Sync configuration edits require stopped transport.
The mixer header has no configuration controls and SELECT does not open a menu.
The pad-bank heading reads LOCAL for this machine and LINKED for the peer.
Horizontal pad navigation crosses into the linked bank after the local pages
and wraps back. Without a negotiated peer only local pads are available, even
if a song saved LINK as its preferred view. LINK offers pattern selection, track volume/pan/mute/solo and
individual drum mute/solo. Hold A with arrows to change volume/pan. The master
shows acknowledged remote values; COMMAND PENDING means an edit is in flight.
Edits are absolute and guarded by the remote pattern generation. A stale edit is
rejected rather than applied to a different pattern. One follow-up control or
launch can wait behind an outstanding command; repeating the same parameter
coalesces to its latest requested value. Different additional edits should wait
for the pending indication to clear. This deliberately bounds protocol work.

Instrument strip names use two characters: local P1/P2, W1/W2, N1, M1, D1;
linked P3/P4, W3/W4, N2, M2, D2.

Four 40-pixel pattern pads are visible at once. Each contains a small slot
number above its five-character name. The focus outline is independent of
playing inversion and queued flashing. The external number row is removed;
PAN uses the reclaimed mixer row. A stopped pad press starts transport.
A linked pad press starts AUTO transport, then sends its selection after
discovery without adding live serial transfers. A remote launch preserves the
receiver's page and open menu. Drawing and ordinary UI input pause during
preparation/installation and resume after two quiet video frames with playback
caught up. Audio and serial service continue throughout; SELECT+START panic
remains available. If clocks disappear, an uncommitted request is cancelled
after two seconds so the UI cannot remain frozen behind a disconnected launch.

Opening Start on a local pad captures its highlighted slot for Edit and File
actions, independently of the active/playing slot. Inactive Load/Save and
Copy/Paste preserve the live pattern and transport. Replacements ask for
confirmation with Cancel selected first. Pattern File/Edit actions are local;
they are unavailable in LINK view to prevent edits to the wrong machine.
Move horizontally to page through visible pads. The focused pad's full name is
shown above; off-page playing/queued pads have indicators. LOCAL LAYOUT and
LINK LAYOUT in Mixer Settings open independent editors: arrows select, A hides
or shows, B restores all, SELECT returns to settings. Hiding affects display
and navigation only. Drum strips show three-character sample names, including
Amen slice names and kit-specific percussion abbreviations. The remote kit is
packed into the existing STATE pending-slot byte, adding no bytes or transfers.

Saved songs include both hidden-strip/pad masks, PAIR and the selected mixer
view. Loading a song restores these settings; autosaved working layout changes
do not rewrite another saved song. Older songs default to all visible, PAIR off
and LOCAL view. Working layout writes wait until stopped. Song storage accepts
both the original 35-byte payload and a 46-byte extension: byte 35 version 1,
36..43 hidden masks, 44 PAIR, 45 view. Original pattern references stay at 19..34.
The working copy uses root 110..121; Page-menu assignments remain global at
100..109. Archive/save-manager readers must accept both song lengths.

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
subdivision budgets with zero measured underruns; longest measured IRQ is 7772
cycles. The pinned main baseline's corresponding historical startup budget fails
with corrected native hardware-write instrumentation; its other budgets pass.
The candidate adds bounded CPU work (approximately one percentage point in this
fixture). Zero extra transfers is a wire guarantee, not zero CPU overhead or a
proof that all hardware note-latency distributions are identical. Actual console,
cable and hot-plug checks remain necessary before a release timing-parity claim.
WRAM reserve is 1035 bytes and reserved stack is 512 bytes; adding globals needs
another memory audit. Test ROM, symbols and JSON traces live under build/.

The older test_sync_link.cjs fixture also times out before its launch checks
on both the previous and current ROM: its stopped-A and overwrite-confirmation
assumptions need updating. It is not used as an acceptance gate here.

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
node tools/test_mixer_linked_paging.cjs
node tools/test_linked_frozen_ui.cjs
node tools/test_linked_frozen_ui.cjs --wave --disconnect
node tools/test_linked_mixer_legacy.cjs --reference-rom <pinned-main.gb>
python tools/test_sync_irq_budget.py
python tools/test_slave_clock_cpu.py
python tools/test_mixer_pixel_cache.py
python tools/test_queued_flash.py
python tools/test_mixer_layout_persistence.py
python tools/test_mixer_settings.py
python tools/test_mixer_pad_context.py
python tools/test_mixer_pad_outline.py
node tools/test_mixer_pad_start.cjs
```

Reference main is 258b713064ab6796443b6237a040718b1d5d7e9e. The locally pinned
reference ROM SHA256 is
309cb20e48437f552fc009a26cb60a135e505de51ee78d1a262832da6f2f6051.

Sparse mixer layout occupies root bytes 110..120, leaving the current main
checkout's Quick Menu assignments at 100..109 untouched on integration.


For distinct emulator test content, run `python tools/prepare_linked_beats.py`
then `tools/launch_linked_mixer.ps1`. LEFT uses eight wave-only patterns:
SINE, LUNAR, TIDAL, ORBIT, PLUME, GLIDE, VAPOR, COMET. RIGHT uses eight drum-only
TR-909 patterns: BRICK, DUST, PUNCH, SWING, CLAP, STOMP, FUNK, ROLL. All sixteen
names and event contents are distinct. The generated test batteries
live in build/linked-test, preserve earlier batteries as backups and never
modify saves/*.gbsong. Keys: Shift Start, Space Select, Z B, X A.

Previous hardware-test build SHA256: `e37966aeab764c97059b91f52e14c09968c7a48c7c31c29585add7971e73c0b8`.
The 300 BPM storage/paired-launch test measured zero extra metadata transfers,
zero aborted transfers, zero unarmed edges and no added audio underruns.
Both PCM and wave receiver tests recorded zero VRAM writes or page changes
during handoff on nine pages/menu contexts. Repeated AUTO competing starts,
cable loss during preparation and reconnect passed. These emulator results
do not resolve the hardware quantization observations described above.


## Host versus slave launch investigation

`node tools/profile_linked_launch_paths.cjs` compares twelve real-cable
launches at 300 BPM: host-local, host-remote and slave-local repeated four times.
The fixture is deliberately identical across slots, with P1/P2 sixteenth notes
and two PCM voices, so changed musical contents cannot explain onset gaps.
Only fixture contents/focus are written directly; launches use A button input.
The harness records actual APU trigger writes and function entry cycles on both
machines. Instrumentation is in the emulator, not the ROM or serial ISR.

On ROM e37966ae, host-local handoff to first pulse attack measured
14.993..16.455 ms, host-remote 11.927..13.670 ms and slave-local
10.144..13.297 ms. Host sync_pattern spent about 2.8..3.4 ms before entering
the first-step firing path; slave sync_pattern returns in about 0.08 ms.
The host computes and queues F2 and its three phase bytes before its own
first-step firing. That marker also calls seq_pattern_release and
seq_pattern_start on the slave even with PAIR disabled. All four host-local
launches restarted the slave sequence; neither slave launch path did.
This is a confirmed asymmetry, not proof that it explains every audible skip.

The remote launch path also suppresses drawing during preparation/install;
local pad launches do not. Its contribution has not been isolated. These
fixtures still show substantial note-spacing excursions despite unchanged
underrun counters; zero underruns and settled grid alignment are insufficient
as musical-onset acceptance criteria. The report is diagnostic and does not
mark these timing distributions as passing. Firmware and the hardware-test ROM
were left unchanged for this investigation. Raw samples are in
build/launch-path-profile.json.


## Independent host launches and LONG

With a negotiated native peer, a quantized independent host launch keeps the
running transport grid. It restarts the selected local pattern's notes without
sending the F2 marker that would restart the slave's current sequence. PAIR,
legacy peers and explicit NOW resync retain their existing marker behavior.
The music clock and serial interrupt implementations are unchanged.

Native independent host patterns containing up to 256 events now stage their
complete note data before becoming ready to launch. Each foreground quantum
reads at most 16 bytes. The 1024-byte staging area is B020..B41F, separate from
incoming metadata, tone data and both native attack packets. Playback uses that
RAM data while copying it into the normal live arrays. Larger patterns retain
the existing streamed installation path. Direct slave launches, remote slave
launches, PAIR and raw sync modes retain their previous preparation path.

Staged events use cache state 3 and the existing B020 reader; live note readers
do not gain an extra branch. Another pad cannot overwrite active staging while
installation runs. Editing/copy/save barriers finish the installation, and
opening a menu finishes an active staged installation before font or roll
scratch can reuse B000. A pending staged preparation is rebuilt after menu/font
restoration. The 256-event and 257-event tests compare every installed event,
including first and repeated launches and a Mixer/SEQ/Mixer navigation roundtrip.
WRAM and stack reservations remain 1035 and 512 bytes.

LONG follows 1/1 in the quantize selector. It waits for the last step of the
longest populated, enabled track in the outgoing pattern, then launches or
retriggers at step one. Muting and hiding do not remove a track from this
calculation. Empty tracks are ignored when populated tracks exist; an entirely
empty pattern uses the longest enabled track. This is the longest track's cycle,
not the least common multiple of every track length. If preparation is late,
the launch waits for its next complete cycle. In PAIR the host's LONG boundary
commits both prepared patterns. LONG is carried by the existing three-bit state
field and saved in songs and the working root, without enlarging wire packets.

AUTO startup now distinguishes the native F6 acknowledgement from arbitrary
queued metadata replies: zero-valued metadata after an acknowledgement is not a
clock collision. An uncertain AUTO claim with a non-idle response and no valid
acknowledgement returns to listening. This check happens before musical clocks
are armed. A prepared PAIR repeats READY on existing reverse clock slots until
commit, so one dropped optional reply does not impose a long retry delay.

Current candidate SHA256:
`057ab58d52ea0f927ad80ec340821ce9ae3d8f4747adf9510bb9a66a88b168d7`.
Hardware-test artifact: build/GAYBOYMIXER-FIX.gb. Do not treat emulator timing as
a hardware performance-parity claim: the dense diagnostic still records note
spacing excursions outside handoff, especially on the slave. Native direct
slave launch tests pass with the same settled-grid threshold as the previous
ROM; the test now captures quiescent scheduler states rather than mid-catch-up
states. The old ROM passes the same corrected fixture. All eight launch/retrigger
cases retain zero settled grid offset.

Additional reproducible checks:

```text
node tools/profile_linked_launch_paths.cjs
node tools/profile_linked_launch_paths.cjs --forced
node tools/profile_linked_launch_paths.cjs --long
node tools/profile_linked_launch_paths.cjs --slave-only
node tools/test_host_event_staging.cjs --events 256 --menu
node tools/test_host_event_staging.cjs --events 257
node tools/test_slave_launch_sync.cjs --mode 1 --bpm 300 --stress
node tools/test_linked_mixer_live.cjs --bpm 300 --long
python tools/test_long_quantization.py
```

On this candidate the twelve-case AUTO profile measured host-local handoff to
first pulse at 11.027..13.630 ms, versus 14.993..16.455 ms on the earlier ROM.
Direct slave handoffs measured 10.721..13.150 ms, within the earlier observed
10.144..13.297 ms range. These describe first attacks in the specified fixture,
not worst-case guarantees for arbitrary songs. No slave launch used the host
staging state, and independent launch traces contained no transport restart,
link reset or new election. Full normal/LONG paired-storage tests, reconnect,
legacy-peer compatibility and all five raw/native clock invariants passed on
the matching ROM. Existing one-frame standalone handoff limitations remain.

### Mixer navigation

Mixer retains its channel viewport, pad page for each device bank, and cursor
when leaving for SEQ, Mixer Settings or file menus. Renderer scratch is still
invalidated on return; the retained view lives independently in session RAM.
Header focus no longer jumps the channel viewport back to the first strip.
This is session navigation state, not a change to the saved song format.

Check: `python tools/test_mixer_view_state.py`.

The navigation update is built as `build/GAYBOYMIXER-FIX.gb`, SHA-256
`580bc44449a079ccc75db5565d3190a1b6ddc8bb5beeb295185b90451db78b75`.
It retains the host launch and LONG changes described above. On this exact ROM,
navigation, pad file context, song settings, pixel-cache, LONG, IRQ-budget,
dense direct-slave launch, legacy-peer, host staging/menu and quick launch-path
checks passed, along with the live paired LONG/control/name-publication test.
The earlier full-profile measurements above remain attributed
to their earlier SHA rather than being restated as measurements of this ROM.

### Held pad retrigger

Holding A on a quantized pattern pad repeats the pattern. Local and directly
operated slave pads sample the held button at musical boundaries and retrigger
live events without SRAM reloads or extra serial work. This avoids missed short
intervals while the UI redraws. LONG repeats at the longest populated sequence's
end. NOW and the transport Play control stay one-shot.

Release stops rearming. A launch already queued by the normal command path
retains tap semantics and may finish after release. Leaving the pads, opening
menus or holding another button suspends automatic rearming.

Linked and PAIR holds reuse the existing command/ready path with one request
in flight. These launches stay quantized, but cable preparation/acknowledgement
may span short intervals: readiness takes precedence over repeating every such
interval. No new protocol, serial transfer type, interrupt handler or clock
source is introduced.

Tests: `python tools/test_mixer_pad_hold.py` checks consecutive local boundaries
for all four quantizations and LONG, release, NOW and transport behavior;
`node tools/test_linked_mixer_hold.cjs` checks local/direct-slave/linked/PAIR
holds at 300 BPM, boundary alignment, release, stack reserve, serial aborts,
overflow and unchanged audio underruns. IRQ budgets and mixer navigation also
pass. Current `build/GAYBOYMIXER-FIX.gb` SHA-256: `929a66a85b5a132cdfe5b682abfb4a10a90811dd0e3e96f51e82c26edc1888c8`.

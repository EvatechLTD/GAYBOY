# ARP chord handoff fix

Scope: advance preparation of the next eligible native chord; no TWINK/link redesign, UI, emulator, save format or demo-song changes.

A retriggered multi-chord arp previously exhausted its prepared packets and waited for foreground note searches at each chord boundary. Prepare the next chord from the immutable editbuffer snapshot, reuse existing packet/chord-cache storage, and perform a bounded timer handoff. Carry fractional BPM timing across the handoff and acknowledge the emitted attack without replaying it in foreground. Keep handoff receipts across unrelated snapshot/generation changes and compare actual pitches/velocities before suppressing a duplicate. Existing fallback remains for unsupported orders, free-run/no-retrigger, rests, more than four notes, and spans that exceed the existing timer width.

The coordinator adds one WRAM busy byte. No SRAM/save layout change. Chord scanning moves to ROM bank47 and cancellation becomes BANKED to fit. Reset disarms the engine; each fresh preparation clears its stale future descriptor before enabling it. This avoids redundant fixed-bank reset writes.

Validation uses SameBoy 1.0.4, actual saved notes and button-driven normal playback, graphics running. Command: node tools/test_arp_handoff_sameboy.cjs --core PATH_TO_SAMEBOY_SYNC_LINK_CORE --save PATH_TO_BASIC_ARP_SRM --pad 1 --verify.

Saved 95 BPM fixture: 320 P2 attacks; worst steady interval-grid error 1.958 ms. Standard 120 BPM demo HOOK arp also passes; worst steady error 1.346 ms. Real transport stop passes. First startup interval is reported separately; this fix does not claim to change startup or solve all Wave foreground timing. User hardware listening approved the same handoff implementation in proof2.gb. Historical PyBoy measurements are not audio/timing acceptance evidence.

Keep the existing GAYBOY-KILLING-DEMO.srm seed for the release. Do not ship the diagnostic basic-arp project as the default song.

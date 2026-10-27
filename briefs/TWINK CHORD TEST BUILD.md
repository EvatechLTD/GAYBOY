# TWINK chord hardware test

Private TWINK_CHORDS experiment; not merged into main or published.

GAYBOY sends the held MS chord (up to eight distinct pitches, sorted lowest first). The receiver owns mono/poly allocation and its own arpeggiator. There is no return handshake, receiver clock or synth-settings stream. The locked host mode label is TWINK.

Wire: F5, count, (pitch, velocity) pairs, CRC7. Count zero releases the chord. Existing F3 single-note previews and transport stop remain supported. Complete CRC-valid sets publish atomically. Host prepares immutable frames in the existing 256-byte RX workspace; the musical interrupt only transmits due prepared frames. No save-layout expansion.

Requested receiver bank: 001?010 mono with three oscillators and modest chorus/vibrato; 011?020 three-note poly (lowest to Wave, next two to pulses); 021?025 two-note poly on pulses. Wave reaches C1; pulse assignments below C2 rise one octave. Poly overflow retains the lowest available pitches. Receiver-local arp can use the full held chord.

Host C1 cursor/plot/move/drag clamps now include MS. Native incremental feedback and its pending drawing service include MS, avoiding the old delayed or unserviced MS drawing path. A cold settings navigation helper moved out of ROM bank 10 to leave the musical code unchanged while fitting the bank.

## Validation

SameBoy is mandatory (AGENTS.md); user handles musical sound checks on hardware. Source fixture setup uses private battery/state; actual buttons, serial cable, parser and APU execute normally. No user emulator/save is touched.

- Saved problematic local arp: passes actual APU timing check and transport stop.
- Native linked playback plus drift and remote panic stop: passes.
- Both-machine Smooth playback with shared start/stop: passes.
- Actual MS plot, resize, move, selection drag, paint and page navigation: completes at 120 and 240 BPM without timeout, including pending drawing queue completion.
- C1 plotting, resize and move: passes.
- Scheduled four-note chord sets: 30 consecutive changes at 120 BPM and 60 at 240 BPM, expected set/order, stop/release, no serial overflow/unarmed edges/aborts. Also passes low chord data beginning at C1.

The initial OFF/MS-edit comparison was invalid: MS editing is unavailable with TWINK off. Do not quote that fixture as a matched OFF performance result. Receiver parser checks alone do not qualify sound or voice allocation. Final pair must be rerun after receiver bank is frozen.

Host ROM: build/GAYBOY-TWINK-CHORDS.gb
SHA256: 5155ffde242b0b02370d2c65b7a14b819a21f24f79e3f35ad67a566d323c3e8b

Reports: build/chord-bank-ms-ui-final.json, build/chord-bank-ms-c1-ui.json, build/chord-bank-host-playback.json, build/chord-bank-host-low-playback.json, build/chord-bank-local-arp.json; native-link and linked-smooth logs share that prefix. Earlier reports may reference the immediately preceding host compile; rerun the final matched pair before delivery.

## Final delivered candidate

Receiver SHA256: 10ab03b935d2bdf368444cff28b84b9d1595916074808f2cbcba2ae52ab18cf8
Pair folder: DATA/TESTS/TWINK-CHORDS-20261026 (ROMs and matching NOI files).

Receiver boots into CHORD25 bank, with MIDI input unchanged by default. Select LINK ? INPUT ? TWINK. LINK ? BANK switches between CHORD25 and FACTORY. LINK ? PLAY chooses receiver-local MONO / POLY / ARP, ARP HZ and ORDER. Browsing a new chord-bank preset applies its intended mono/trio/duo mode. First25 are specifically prepared and qualified; original factory full-FX compatibility is retained but its complete library is not requalified by this experiment.

Receiver checks: all25 native-ready and correct voice groups, low Wave and pulse octave allocation, held chord through browsing, bad/partial CRC atomicity, releases and F3 previews; 60 musical-rate changed chords, 126 accepted F5 frames, two intentional bad CRC rejections, no overflow/unarmed edges. Local8Hz arp APU intervals124.995?125.447ms and16Hz32attacks/2seconds. Faster-than-frame changes may coalesce on receiver; do not claim every arbitrary-rate burst produces a separate audible attack.

Final exact-pair regressions: chord-bank-final-pair-playback.json (30/60 scheduled chord changes at120/240BPM plus stop), chord-bank-final-pair-ui.json (all13 actual MS editing/navigation actions at eachtempo). Both pass. User performs soundchecks on hardware.

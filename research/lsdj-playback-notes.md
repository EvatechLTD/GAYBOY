# LSDj playback investigation

Reference checkout: `LSDisJ/`, https://github.com/rbong/LSDisJ (including its Beast submodule).

The checkout contains annotated symbols and disassembly tools, not a complete
standalone playback source tree. Its README requires an original matching
9.2.L or 8.5.1 ROM. The official 9.2.L download returned HTTP 455 during this
investigation, so no reconstructed playback assembly has been inspected.
In particular, the timer entry at bank 0:$0391 is labeled but its internals
are not explained by the available annotations.

## Verified documentation findings

- The official kit patcher recommends preparing samples at 11,468 Hz offline:
  https://www.littlesounddj.com/lsd/latest/lsd-patcher/documentation.html
- The official 9.2.6 manual describes two kit/sample selections and hard,
  soft, fold, and wrap mixing modes, plus full/half playback speed:
  https://www.littlesounddj.com/lsd/latest/documentation/LSDj_9_2_6.pdf

These establish two-voice sample playback as a useful reference, but do not
establish the exact implementation or CPU cost of LSDj's mixer.

## Implications for this ROM

The initial proof preserved the 22,050 Hz mastered source samples, with
approximately 22,075.8 Hz hardware playback. Two voices consumed approximately
83% of DMG CPU time, and the next pitched-track sixteenth in the combined
300 BPM pattern-switch test arrived after 84.8 ms (50 ms ideal).

The user subsequently authorized lower-rate preparation. The preserved masters
are now antialiased to 11,468 Hz in `BREAKS/AMEN172chop/processed-lsdj` using
`tools/prepare_drum_samples.py`. Compression and normalization are not repeated.
The matching hardware clock runs at 11,459.846995 Hz (-0.071%), with 11,712 CPU
cycles per 32-sample block. Packed sample storage fell from 32,000 to 16,656 bytes.
The same pattern-switch timing regression now passes at 57.01 ms, without
relaxing its existing 58 ms upper limit.

The longer forced-DMG stress test (`build/pcm-timing-final.json`) keeps two PCM
voices and P1/P2 active at 300 BPM for approximately six seconds. The complete
timer interrupt uses 42.8% CPU on average and 44.7% worst case; there are zero
audio drops and the sustained note rate is correct. Steady onset jitter is
3.8 ms idle and 10.4 ms during scrolling. Direct cold transport start has a late
second note at 67.4 ms versus 50 ms ideal, so that test reports its startup timing
failure explicitly. The separate quantized Mixer switch regression passes.

Our player already quantizes samples offline to packed 4-bit PCM, reads ROM
in unrolled blocks, and mixes two packed nibbles in parallel. Profiling shows
that foreground scheduling gaps, rather than just mixing arithmetic, can
starve playback. The PCM path now prepares its next block on the audio timer.
Tests verify exact prepared sample bytes across the occupied ROM data banks,
exact two-voice mixing, synchronized simultaneous hits, and zero buffer underruns.
This implementation and its measurements are independent of any unverified
claim about LSDj's internal assembly. Emulator cycle measurements still need
physical DMG verification; heavy experimental DDS timing remains a separate issue.

## Hardware buzz investigation

The user reported a constant tone over every drum sample on a DMG-01. The
player was toggling NR30 while CH3 remained routed to the mixer. The developer
who documented the anti-spike technique describes that exact symptom and the
NR51 disconnect/reconnect fix:
https://gbdev.gg8.se/forums/viewtopic.php?id=362

Each PCM upload now saves the actual NR51 value, clears CH3's two routing bits,
disables its DAC, uploads wave RAM, enables/retriggers the channel, and restores
the saved routing. CPU hooks verified 282 upload sequences, including all pan
states and preservation of pulse/noise routing. This checks executed register
order; physical DMG feedback is still needed to confirm the analog buzz result.

PCM drums are now independent of Experimental Mode, which defaults OFF. All ten
sample rows and both native noise rows work in both modes. `build/DRUMFIX.gb`
contains the anti-spike fix and the new default for the hardware retest.

### PCM ownership and refresh correction

Further hardware feedback confirmed that NR51 masking alone did not remove the
tone. The normal poly allocator could enter DDS synthesis with engine mode 3;
native audition and envelope/sustain paths could also modify the sample player.
These paths now reject PCM ownership. Only a new positive wave note after PCM
finishes can return the channel to synthesis. Sequencer drum events run first,
so simultaneous W1/W2 notes cannot replace drum playback.

Cycle measurements also exposed a separate refresh defect: the old 183-divider
wave clock emitted only 30 of each block's 32 nibbles before the next upload.
The upload now prepares its registers/pointer before disconnecting CH3 and uses
inline stores. A 176-divider wave clock fits all 32 reads within that active
window, while the block timer retains the original 11712-cycle sample cadence.
Each ROM block is rotated one nibble right to compensate for DMG's first read
at wave index 1; the listenable WAV files themselves remain unchanged. Official
LSDPatcher uses the same frame rotation convention:
https://github.com/jkotlinski/lsdpatch/blob/master/CHANGELOG.md

PyBoy can check executed register timing and ownership, but its initial wave
sample suppression differs from the real DMG's retained sample latch. Emulator
audio is therefore insufficient to certify that the physical analog tone is
gone. A DMG listening test remains necessary.

Measured after correction: 152 uploads per diagnostic fixture, zero underruns,
360 cycles from DAC-off to trigger (previously 552), and 32 reads in every
11308–11404-cycle active window. PyBoy's flat-input carrier fell about 17%,
but remained present in its audio model; this is not a claim of analog silence.

The drum grid now has horizontal row separators at every zoom. At 16-step zoom,
the bottom velocity lane follows the selected sample/noise row. Right from the
last visible cell selects that lane without changing the selected row; Up
returns to the grid. Hold B+Up/Down to edit velocity; releasing B restores
navigation. A does not latch slider editing.

Grid note entry uses B: tap empty space to plot, tap a note to erase, or hold
B and move left/right to size a new or existing note. Hold A on an existing
note and use the D-pad to move it while preserving its length. The action
stays locked until release. A also retains header and piano-audition actions.
Cell repeats start after 8 VBlanks, accelerate at 24, and reach one step per
VBlank at 48; menus and other value editors keep their previous timing.

The user subsequently verified that the remaining sample tone occurs in
PyBoy and is absent on their physical DMG-01. SameBoy is now the default
listening emulator; PyBoy remains useful for state and instruction hooks.

## Expanded sequencer storage

Patterns now use one shared pool of 512 four-byte note events. Each track's
segment preserves insertion order; event fields are step, encoded note/row,
velocity, and duration (zero encodes 256 steps). The first 1024 bytes live in
WRAM, the other 1024 at SRAM bank zero A800-ABFF. Per-track counts and offsets
replace the old dense melodic arrays and separate drum/noise/age arrays.
Pattern length and default duration are 16 bit; playback gates are 32 bit.
All eight 2560-byte saved-pattern records remain in the existing 32 KB RAM.
The B8 payload stores the 2048-byte pool plus 77 bytes of metadata. Legacy B7
records are converted on load if their events fit; oversized records are
retained and protected from automatic overwrite rather than truncated.

Copy/Paste in the sequencer Start menu copies a whole track, including notes
beyond its active length and its length/velocity/duration/gate defaults. It
does not copy tempo or instrument patches. Melodic-to-drum conversion maps
pitch classes to the twelve rows; drum-to-melodic conversion maps row offsets
above the destination's selected pitch, keeping one onset per step.

A-drag from empty grid space selects note onsets in a rectangle. Selected
notes are shaded. A-drag on a member moves the group; B-drag changes selected
lengths. Tapping A on empty space clears selection. Piano-column B auditions
while stopped, and records at the moving playhead while playing; holding B
records duration. Unmodified Down in the velocity lane scrolls lower notes,
while B+Up/Down still edits velocity. MIDI import/export is deferred; ordinary
note events retain the information needed for a future converter.

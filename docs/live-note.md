# Live note plotting prototype

Branch: live-note. Newly inserted notes audition immediately while playback is stopped, including A+B painting. Melodic notes use their plotted pitch and velocity; drum rows preview their corresponding synth/sample. Release B (or leave via Start) to stop the audition. Starting transport retires any preview before sounding sequenced notes. Deletion and playing edits do not audition. Internal preview events bypass MIDI performance mappings. No additional playback polling or persistent state was added.

Validated real B plotting, release and erase on P1/P2/Wave (including C1) and hat/snare/kick/sample rows; painted cells; transport transition and playing edits; MIDI pad isolation; deferred paint feedback; sustained Wave snapshot publication and ARP/top-bar flow. ROM layout validation passes, with 283 bytes spare WRAM and 512 bytes reserved stack. Physical hardware confirmation remains pending.

Test ROM: build/GAYBOY-live-note-test.gb. Canonical build/GAYBOY.gb contains the same prototype.
SHA256: b01b099986321e83c1f8b0e8789422aa2f78fca5a4ca075d0733908516c9f88c

Evidence: DATA/EXPERIMENTS/live-note-20261023. Not merged or published. No existing emulator session or save was modified.

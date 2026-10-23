# Live note plotting prototype

Branch: live-note. Newly inserted notes audition immediately while playback is stopped, including A+B painting. Dragging an existing note to another cell retriggers its current pitch and velocity. Resizing queues a replay: releasing B retriggers the note for its updated grid length at the current BPM, then releases it automatically. Group operations preview the edited note under the cursor. Drum rows preview their corresponding synth/sample. Natural sample/envelope decay can be shorter than the gate.

An ordinary plot/drag preview stops when its held edit button is released or on leaving via Start. Starting transport cancels a preview before sounding sequenced notes. Deletion and playing edits do not audition. Internal previews bypass MIDI performance mappings. A frame-service flag handles timed previews only when active; no sequencer note buffers or playback scheduling were changed. Nine additional bytes of temporary preview state are used.

Tests pass for P1/P2/Wave and drum plots, painting, drag pitch/position, single/group resize release, 60/120/240 BPM durations, previous-preview expiry during another resize, frame-counter wrap, transport transition, MIDI pad isolation, deferred painting, sustained Wave snapshots and pending chord selection. Four cells measured 502.28 ms at 120 BPM and 251.14 ms at 240 BPM. ROM layout: 274 bytes spare WRAM, 512 bytes reserved stack. Physical hardware confirmation remains pending.

Latest test ROM: build/GAYBOY-live-note-drag-resize-test.gb. Canonical build/GAYBOY.gb contains the same prototype; the earlier live-note-test file remains available for its running emulator.
SHA256: 1048a48f621b0b9172244d88b53949e517e179afe9f206fad29e4b01ed1191ac

Evidence: DATA/EXPERIMENTS/live-note-20261023/drag-resize. Not merged or published. Existing emulator files and unsaved sessions were not overwritten.

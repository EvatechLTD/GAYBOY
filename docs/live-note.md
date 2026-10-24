# Stopped-note audition and selection

Plotting a note while stopped auditions it immediately, including A+B painting.
Dragging an existing note to a new cell retriggers its new pitch and velocity.
Resizing queues a preview: releasing B plays the edited note for its updated
length at the current BPM, then releases it automatically. Group operations
preview the edited note under the cursor. Drum rows preview their synth/sample.
Natural hardware-envelope/sample decay can be shorter than the note gate.

An A tap on a highlighted note auditions it on release for its stored length.
An A tap on an empty cell previews that pitch using the length and velocity
that B would plot, without inserting a note. If a selection exists, the empty
A tap only deselects, silently. Dragging through empty cells still selects.
Plot/drag previews end on edit-button release or leaving through Start; starting
transport cancels outstanding previews. Playing edits and deletion do not
start previews, and internal previews bypass MIDI pad-launch mappings.

The Edit menu contains SELECT SCREEN (current visible grid scope) and SELECT
ALL (the whole current track, including other pages/octaves). Subsequent group
operations use that selection. Selection itself does not change note records.
Bounds fit selected note onsets/pitches so empty margins do not prevent moves.

The sequencer header shows current/total bars. M/S have black backgrounds
when inactive and inverted backgrounds when active, with separate focus rails.

Portable regression tests cover pulse, Wave, and drums; plot/paint; repeated
A taps; silent deselection; moved pitch; single/group resize; remembered empty
cell length; 60/120/240-BPM preview durations; pending-preview expiry; frame
counter wrap; transport; and screen versus whole-track selection edits.

See [Smooth Playback](smooth-playback.md) for the explicit Start+Select
transport and its measured performance limits.

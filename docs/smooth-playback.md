# Smooth Playback

While the sequencer is stopped, press **Start+Select** to start Smooth Playback.
Either button order works. The screen displays `START+SELECT TO STOP` once;
the display and complete note snapshot finish before musical time starts.
Press Start+Select again to stop and restore the editor. Select+A also stops.
Normal Select+A transport and mixer/pad launches remain graphical playback.
There is no Settings toggle; the former saved Smooth preference is ignored.

Smooth leaves LCD timing, VBlank, input, and audio services running. During
playback it skips rendering, flushes, feedback, sprites, and automatic OAM DMA.
Grid editing/navigation is ignored. It does not provide pad-launch controls.

## Timing changes

A retrigger resets the arpeggio position, not its unchanged source data. The
prepared timer can now repeat a supported step-zero chord including its rest,
without rescanning/rebuilding that chord at every loop. Other chord layouts
and synthesis modes retain their existing paths. Cached step-zero chord data
invalidates when its snapshot, generation, or track length changes.

Prepared melodic playback supports the full 256-step length. Hash collisions
are filtered by lane and actual step, preventing another lane's note from
being used. Wave is not automatically excluded merely because drums exist;
runtime PCM/channel ownership checks still apply.

Supported unmodulated synth drums in Smooth Playback use a prepared step table
in the inactive note-buffer allocation. It fits 256 eight-byte packets plus
spare space without allocating another full note buffer. The timer commits
drums before melodic IRQ work. The table is prepared only while stopped;
generation/tone changes invalidate the consumer before RAM can be reused.
PCM, externally synchronized playback, shared P1 notes, and modulated drum
setups retain the normal dispatcher. Existing logical-voice ownership remains
protected. At exact compatible grids (including 120/240 BPM) the timer retains
256 Hz; otherwise the supported drum path uses 1024 Hz to reduce quantization.
Starting prepared melodic playback no longer resets the continuous DIV epoch.

## Validation and limits

Actual APU-register probes on a 120-BPM pattern with a rested P2 chord,
128-step Wave bassline, hats every sixteenth, snare, and pulse kick measured:

| Drum measurement | Worst interval error |
| --- | ---: |
| Earlier foreground path, repeat boundary | 12.64 ms |
| Prepared drums, retrigger on, including startup | 0.20 ms |
| Prepared drums, retrigger off, including startup | 0.18 ms |

Each prepared run covered about 70 seconds with all expected attacks and zero
underruns. These are emulator observations, not hardware qualification or a
universal guarantee. Private captured saves and raw reports remain local in
DATA/EXPERIMENTS/smooth-loop-20261023; no user save is part of the release.

Normal playback still has editing/modulation tradeoffs. A matched dense
180-BPM drums/LFO editor workload measured worst note errors of roughly
0.5-1.0 ms before these loop changes versus 0.9-1.4 ms afterward, with some
editing input medians about one video frame slower. Both had zero underruns.
Smooth gains do not imply every normal-mode workload improves.

The linked build retains 139 bytes spare WRAM below the audio tables and
512 bytes reserved stack. Portable tests cover shortcut ordering, ignored old
preferences, complete startup preparation, no ongoing VRAM writes, recovery,
drum register/pitch order, stop/restart, unchanged notes/kits, safe fallback,
256-step cross-lane hash collisions, live audition, and editing gestures.

Run the focused checks from MAIN:

```powershell
python tools/test_smooth_playback.py
python tools/test_prepared_drums.py
python tools/test_prepared_long_tracks.py
python tools/test_live_note_drag_resize.py
python tools/test_select_screen_all.py
```

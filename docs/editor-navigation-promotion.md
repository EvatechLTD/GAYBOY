# Editor and navigation promotion - 2026-10-23

Promotes the user-tested `black-notes` prototype to main, retaining stable
version 1.0. This includes cheaper LFO preparation, black note rendering,
deferred selection/drag feedback, faster top-bar focus, bounded edit rendering,
and prompt publication of prepared edits without retriggering sustained notes.

Octave scrolling now preserves the retained grid when direction releases or
further plain navigation arrive. Idle native edit service no longer invalidates
navigation. The keyboard remains visible: hiding it alone saved about 9%, while
fixing unnecessary redraws reduced the captured MOD OFF song's median scroll
from about 887 to 151 ms stopped and 2612 to 377 ms playing.

Ordinary navigation and edit gestures stop on the first/last visible cell.
Release D-pad and press again to cross to the opposite edge of the next page.
Full page changes wait for drawing before held repeat resumes. Retained
one-row octave scrolling and header access remain available.

The final prototype passed 31 ordinary navigation cases and 79 gesture edge
cases. Rapid eight-tap octave scrolling retained its cache (703 ms stopped,
1624-1691 ms playing). Earlier checks cover pixel equivalence, source integrity,
painting, group movement/resizing, edit latency, sustained Wave gates, and
modulation-enabled playback. The user confirmed the final build in the emulator
after earlier hardware testing of this development chain.

Tested ROM SHA256:
`bdc10a1d647b3d38a4ed9aca73e1e491f4c841233f353c83bc04edb814448ac5`

Dense edits with modulation enabled can still slow the UI. The LFO preparation
changes trade some modulation-edge precision at certain rates for note timing
and responsiveness; see the historical LFO cache audit. Earlier intermediate
audit files record their own build state and are superseded by this promotion.

Local archive: `DATA/ARCHIVES/editor-navigation-20261023` preserves the working
diff, source snapshots, intermediate ROMs, saved states and test evidence.
Original song captures remain in `DATA/EXPERIMENTS/octave-scroll-20261023`.
Active emulator files are retained while their windows remain open.

The main ROM is rebuilt after merging, checked against the tested image, then
packaged for the download and browser player. Existing tutorial/shared-beat
cartridges and symbol maps are preserved. Deployment reports and public hash
verification are retained in the local archive.

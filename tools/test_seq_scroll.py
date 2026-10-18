"""Incremental pitch scrolling matches full renders at every zoom."""
exec(open('tools/test_seq_incremental.py').read().split('choose(8); settle()')[0])
from seq_storage_helpers import write_tracks

keyboard = []
a = S['_roll_keyboard']
p.hook_register(a >> 16, a & 65535, lambda _: keyboard.append(p.frame_count), None)
try:
    choose(8)
    tracks = [[] for _ in range(7)]
    tracks[0] = [[step, 54 + step % 27, 20 + step * 3, 3] for step in range(32)]
    write_tracks(p, S, tracks)
    for zoom in range(4):
        for hidden in (0, 1):
            put('seqzoom', 0, zoom); put('seqvelocityhidden', 0, hidden)
            put('seqtop', 0, 78); put('seqpitch', 0, 70)
            invalidate(True)
            for delta in (1, -1, 2, -2, 5, -5):
                before = background()
                put('seqtop', 0, v('seqtop') + delta)
                put('seqpitch', 0, v('seqtop') - 4)
                keyboard.clear()
                invalidate()
                shifted = background()
                exposed = abs(delta) * (v('seqheight') // 8)
                assert len(keyboard) == exposed, (zoom, hidden, delta, len(keyboard), exposed)
                if zoom == 1 and not hidden:
                    assert np.array_equal(before[120:], shifted[120:]), 'Pitch scroll changed velocity strip'
                invalidate(True)
                assert np.array_equal(shifted, background()), ('Scroll/full mismatch', zoom, hidden, delta)
            # An edit and scroll in the same frame must repaint moved/changed
            # notes as well as the exposed keyboard row.
            put('seqnotes', 4, 66); put('seqduration', 4, 4)
            put('seqtop', 0, v('seqtop') + 1)
            invalidate(); edited = background()
            invalidate(True)
            assert np.array_equal(edited, background()), ('Edit+scroll mismatch', zoom, hidden)
            # Real edge navigation may reuse resolved note cells as well.
            put('seqpitch', 0, v('seqtop')); put('seqhead', 0, 0)
            invalidate(True)
            press('up'); assert v('seqhead') == 1
            press('up'); settle(); fast = background()
            invalidate(True)
            assert np.array_equal(fast, background()), ('Navigation up/full mismatch', zoom, hidden)
            put('seqpitch', 0, v('seqtop') - v('seqrows') + 1)
            put('seqhead', 0, 5 if zoom == 1 and not hidden else 0)
            invalidate(True)
            press('down'); settle(); fast = background()
            invalidate(True)
            assert np.array_equal(fast, background()), ('Navigation down/full mismatch', zoom, hidden)
    print('PASS: row reuse in both directions, all zooms, partial rows, preserved velocity strip, edits during scrolling and full-render pixel equivalence')
finally:
    p.stop(save=False)

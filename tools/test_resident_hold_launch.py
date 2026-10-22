"""Held A retriggers on every eligible boundary; release and NOW stop repeats."""
from pathlib import Path

# Share disposable SRAM, symbol access and real-button acknowledgement helpers.
exec(Path('tools/test_resident_launch_delta.py').read_text().split('try:\n')[0])

try:
    enter_app(p, S)
    put('page', 18); put('dirty', 1)
    word('seqglobalbpm', 300); word('seqbpm', 300)
    put('mx', 0, 3); put('mx', 30, 4); press('a')
    assert get('seqplaying')
    boundaries = []
    launches = []
    def hook(name, callback):
        a = S['_' + name]
        p.hook_register(a >> 16, a & 65535, callback, None)
    hook('mixer_boundary', lambda _: boundaries.append(p._cycles()))
    hook('seq_pattern_handoff', lambda _: launches.append(len(boundaries)))
    for quant, interval in ((6,1), (1,2), (2,4), (3,8), (4,16), (5,1)):
        if quant == 5:
            for c in range(7): word('seqlength', 1, c*2)
        put('mx', quant, 3); put('mx', 30, 4)
        boundaries.clear(); launches.clear()
        p.button_press('a')
        for _ in range(900):
            p.tick(1)
            if len(launches) >= 4: break
        p.button_release('a'); p.tick(4)
        assert len(launches) >= 4, (quant, launches)
        gaps = [b-a for a,b in zip(launches, launches[1:])]
        assert all(gap == interval for gap in gaps), (quant, interval, launches)
        count = len(launches)
        p.tick(120)
        assert len(launches) == count, ('Repeated after release', quant)
        print('PASS held A quant', quant, 'launch boundary gaps:', gaps)
    put('mx', 0, 3); launches.clear()
    p.button_press('a'); p.tick(180); p.button_release('a'); p.tick(4)
    assert len(launches) == 1, ('NOW repeated while held', launches)
    print('PASS NOW remains one-shot')
    # Half-step launch points must not advance ordinary sixteenth-note tracks.
    halfs = []
    hook('mixer_half_boundary', lambda _: halfs.append(p._cycles()))
    for c in range(7): word('seqlength', 16, c*2)
    put('mx', 7, 3); boundaries.clear(); launches.clear(); halfs.clear()
    launch_cycles = []
    # Observe playhead resets through a separate entry point to avoid replacing hooks.
    hook('seq_native_live_commit', lambda _: launch_cycles.append(p._cycles()))
    p.button_press('a'); p.tick(120); p.button_release('a'); p.tick(4)
    assert len(launch_cycles) > 15, launch_cycles
    intervals = [(b-a)*1000/4194304 for a,b in zip(launch_cycles,launch_cycles[1:])]
    assert all(18 < t < 33 for t in intervals), intervals
    assert abs(len(halfs)-len(boundaries)) <= 1, (len(halfs),len(boundaries))
    print('PASS 1/32 held retrigger intervals ms:', min(intervals), max(intervals))
    # Keep A down throughout the shortcut: focus stays on the pad and launches continue.
    put('mx', 1, 3); put('mx', 30, 4)
    p.button_press('a'); p.tick(8)
    before = len(launches)
    p.button_press('up'); p.tick(3); p.button_release('up'); p.tick(3)
    assert get('mx',3) == 6 and get('mx',4) == 30
    p.button_press('up'); p.tick(3); p.button_release('up'); p.tick(3)
    assert get('mx',3) == 7 and get('mx',4) == 30
    p.tick(40)
    assert len(launches) > before+5
    p.button_press('down'); p.tick(3); p.button_release('down'); p.tick(3)
    assert get('mx',3) == 6 and get('mx',4) == 30
    p.button_release('a'); p.tick(6)
    print('PASS A+Up/Down changes quantization while repeating and retains pad focus')
finally:
    p.stop(save=False)

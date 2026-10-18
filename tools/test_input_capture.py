"""Short button taps survive sequencer redraws during PCM playback on DMG."""
from pathlib import Path
from seq_storage_helpers import read_tracks, write_tracks

env = {}
source = Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
exec(source.replace('sound_emulated=True,ram_file=',
                    'sound_emulated=True,cgb=False,ram_file='), env)
p, S, v, choose, press = (env[k] for k in ('p', 'S', 'v', 'choose', 'press'))

def tap(key):
    p.button_press(key)
    p.tick(1)
    p.button_release(key)
    p.tick(1)

try:
    choose(8)
    tracks = [[] for _ in range(7)]
    tracks[6] = [[s, 1, 100, 1] for s in range(16)]
    write_tracks(p, S, tracks)
    p.button_press('select')
    p.tick(5)
    press('a')
    p.button_release('select')
    p.tick(20)
    assert v('seqplaying')
    assert v('seqtrack') == 0
    for batch in range(3):
        for _ in range(4):
            tap('right')
        p.tick(45)
        assert v('seqcursor') == (batch + 1) * 4, (batch, v('seqcursor'))
    # B plots on press and resolves the gesture on release. Each pair of
    # one-frame taps must create a separate note at the intended cell.
    for batch in range(2):
        for _ in range(3):
            tap('b')
            tap('right')
        p.tick(45)
    notes = read_tracks(p, S)[0]
    expected = {12, 13, 14, 15, 0, 1}
    assert {e[0] for e in notes} == expected, notes
    assert v('seqcursor') == 2
    assert v('seqplaying')
    print('PASS: 18 one-frame navigation taps and 6 note plots during DMG PCM playback')
finally:
    p.stop(save=False)

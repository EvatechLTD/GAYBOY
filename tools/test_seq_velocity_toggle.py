"""Header V hides/restores velocity without losing notes or cursor pitch."""
from pathlib import Path
from seq_storage_helpers import write_tracks, read_tracks
env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
     .replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='), env)
p, S, v, choose, press = (env[k] for k in ('p', 'S', 'v', 'choose', 'press'))
def put(n, x, i=0): p.memory[S['_' + n] + i] = x
def settle(): p.tick(45)
def header():
    # Enter the real header and traverse M/S to V using button input.
    put('seqpitch', 127, v('seqtrack')); put('seqhead', 0)
    if v('seqtrack') == 6: put('drumrow', 0)
    press('up')
    assert v('seqhead') == 1
    for _ in range(3): press('right')
    assert v('seqhead') == 7
try:
    choose(8)
    assert not v('seqvelocityhidden') and v('seqrows') == 14
    tracks = [[] for _ in range(7)]
    tracks[0] = [[0, 61, 83, 1], [4, 58, 42, 1]]
    write_tracks(p, S, tracks)
    put('seqdrawvalid', 0); put('dirty', 1); settle()
    header(); press('a'); settle()
    assert v('seqvelocityhidden') and v('seqgridheight') == 136 and v('seqrows') == 17
    assert read_tracks(p, S) == tracks
    press('right'); assert v('seqhead') == 4
    press('left'); assert v('seqhead') == 7
    press('down'); assert not v('seqhead')
    put('seqpitch', 55); put('seqtop', 71); put('dirty', 1); settle()
    press('down')
    assert not v('seqhead') and v('seqpitch') == 54 and v('seqtop') == 70
    p.screen.image.save('build/ui-seq-velocity-hidden.png')
    header(); press('b'); settle()
    assert not v('seqvelocityhidden') and v('seqrows') == 14
    assert read_tracks(p, S) == tracks
    press('down')
    put('seqpitch', 58); put('seqtop', 71); put('dirty', 1); settle()
    press('down'); assert v('seqhead') == 5
    # The same preference applies to DRUM, including its right-edge shortcut.
    p.button_press('select'); p.tick(5); press('left')
    p.button_release('select'); settle()
    assert v('seqtrack') == 6
    header(); press('a'); press('down')
    put('seqcursor', 15, 6); put('drumrow', 11); put('dirty', 1); settle()
    press('right')
    assert not v('seqhead') and v('seqcursor', 6) == 0
    press('down'); assert not v('seqhead')
    header(); press('a'); press('down')
    put('seqcursor', 15, 6); put('dirty', 1); settle()
    press('right'); assert v('seqhead') == 5
    assert read_tracks(p, S) == tracks
    tracks[6] = [[0, 1, 100, 1], [4, 2, 100, 1]]
    write_tracks(p, S, tracks)
    p.button_press('select'); p.tick(5); press('a')
    p.button_release('select'); settle()
    assert v('seqplaying')
    header(); press('a'); settle()
    assert v('seqplaying') and v('seqvelocityhidden')
    press('b'); settle()
    assert v('seqplaying') and not v('seqvelocityhidden')
    assert read_tracks(p, S) == tracks and not env['word']('mixunderruns')
    print('PASS: header V toggle, 17/14 pitch rows, preserved notes/velocities, scrolling and DRUM lane navigation')
finally:
    p.stop(save=False)

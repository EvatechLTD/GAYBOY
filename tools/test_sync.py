"""Exercise SYNC navigation, native transport/tempo RX and slave clock gating."""
from pathlib import Path

env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0], env)
p, S, choose, press, word, v = (env[k] for k in ('p','S','choose','press','word','v'))

def inject(data):
    w = v('wr')
    for b in data:
        p.memory[S['_rx'] + w] = b
        w = (w + 1) & 255
    p.memory[S['_wr']] = w
    p.tick(4)

try:
    choose(27)
    assert v('syncmode') == 1 and v('syncslave') == 1
    press('down'); press('right'); press('right')
    assert v('syncslave') == 1
    p.screen.image.save('build/sync.png')
    inject([0xF1, 1, 9, 0xFA])
    assert word('seqglobalbpm') == word('seqbpm') == 137
    assert v('seqplaying')
    positions = bytes(p.memory[S['_seqposition']:S['_seqposition'] + 7])
    p.tick(90)
    assert bytes(p.memory[S['_seqposition']:S['_seqposition'] + 7]) == positions, 'Slave free-ran without clock'
    for _ in range(25):
        inject([0xF8])
    assert v('seqposition') == 4, '24 PPQN must advance four sixteenth steps'
    inject([0xF1, 1, 0xF8, 72])
    assert word('seqglobalbpm') == word('seqbpm') == 200
    # A phase packet carries its oscillator tick ID; clocks may interleave.
    inject([0xF2, 26, 0, 0xF8, 0])
    assert v('seqposition') == 0 and v('seqplaying')
    inject([0xFC])
    assert not v('seqplaying')
    # Numbered clocks recover a delayed/missing byte, including modulo wrap.
    inject([0xFA, 0x81, 0x82, 0x84, 0x85, 0x86])
    assert v('seqposition') == 1, 'Numbered clock gap lost musical time'
    for tick in range(7, 69):
        inject([0x80 | (tick & 63)])
    assert v('seqposition') == 11, 'Numbered clock wrap lost musical time'
    inject([0xFC])
    choose(18)
    p.memory[S['_mx'] + 4] = 64
    p.memory[S['_dirty']] = 1
    p.tick(4)
    press('b')
    assert word('seqglobalbpm') == 200, 'Slave global tempo was disabled'
    choose(27)
    press('up')
    for mode in (2,3,4,5,0):
        press('right')
        assert v('syncmode') == mode
        if mode:
            inject([0])
            assert v('seqplaying') and v('seqposition') == 0
            inject([0] * (6 if mode in (2,3) else 1))
            assert v('seqposition') == (2 if mode == 4 else 1), mode
            p.tick(160)
            assert not v('seqplaying'), 'Raw clock loss failed to stop playback'
    press('right'); press('down'); press('right'); press('right')
    assert v('syncmode') == 1 and not v('syncslave')
    p._serial()
    press('a')
    p.tick(120)
    wire = p._serial()
    assert chr(0xF1) + chr(1) + chr(72) in wire, repr(wire)
    assert chr(0xFA) in wire
    assert 150 <= sum(0x80 <= ord(b) < 0xC0 for b in wire) <= 185, sum(0x80 <= ord(b) < 0xC0 for b in wire)
    assert not v('overflow'), 'Serial transmit queue overflowed'
    press('a')
    assert chr(0xFC) in p._serial()
    print('SYNC menu, modes, native BPM, start/stop, clock gating and mixer lock passed')
finally:
    p.stop(save=False)

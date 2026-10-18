"""Per-voice drum mixer UI, playback and saved-pattern compatibility on DMG."""
from pathlib import Path
from seq_storage_helpers import write_tracks, read_word, write_word
env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
     .replace('range(60)', 'range(600)').replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='), env)
p, S, v, choose, press = (env[k] for k in ('p', 'S', 'v', 'choose', 'press'))
mx = S['_mx']
def mask(n): return read_word(p, S['_' + n])
def setmask(n, x): write_word(p, S['_' + n], x)
def focus(n): p.memory[mx + 4] = n
def toggle(row, solo=False):
    focus(38 + row * 2 + solo)
    press('a')
def start():
    p.memory[S['_drumsamplevoice']:S['_drumsamplevoice'] + 2] = [255, 255]
    focus(0)
    press('a')
    assert v('seqplaying')
def stop():
    focus(0)
    press('a')
    assert not v('seqplaying')
def noise(i): return any(p.memory[S['_noiseleft'] + i * 4 + j] for j in range(4))
def assigned(): return {v('drumsamplevoice', i) for i in range(2)} - {255}
try:
    choose(18)
    focus(26)
    press('right')
    for row in range(12):
        assert p.memory[mx + 4] == 38 + row * 2
        press('a')
        assert mask('drummutemask') == (1 << (row + 1)) - 1
        press('down')
        press('b')
        assert mask('drumsolomask') == (1 << (row + 1)) - 1
        press('up')
        if row < 11: press('right')
    press('down')
    press('down')
    assert p.memory[mx + 4] == 30
    press('up')
    assert p.memory[mx + 4] >= 38
    p.screen.image.save('build/ui-drum-mixer.png')
    setmask('drummutemask', 0)
    setmask('drumsolomask', 0)
    tracks = [[] for _ in range(7)]
    tracks[0] = [[0, 61, 100, 255]]
    tracks[6] = [[0, row + 1, 100, 255] for row in range(12)]
    write_tracks(p, S, tracks)
    for row in range(10):
        toggle(row, True)
        start()
        assert assigned() == {row}, (row, assigned())
        assert not noise(0) and not noise(1) and not v('seqowned')
        stop()
        toggle(row, True)
    toggle(10, True)
    toggle(11, True)
    start()
    assert not assigned() and noise(0) and noise(1)
    toggle(10)
    assert not noise(0) and noise(1)
    stop()
    start()
    assert not assigned() and not noise(0) and noise(1)
    stop()
    choose(20)
    press('b')
    setmask('drummutemask', 0)
    setmask('drumsolomask', 0)
    choose(19)
    press('a')
    assert mask('drummutemask') == 1024 and mask('drumsolomask') == 3072
    p.memory[0x4000] = 1
    record = bytearray(p.memory[0xA000:0xAA00])
    assert record[0] == 0xBA
    record[0] = 0xB8
    checksum = (sum(record[1:18]) + sum(record[32:2080]) + sum(record[2080:2157])) & 65535
    record[18:20] = checksum.to_bytes(2, 'little')
    p.memory[0xA000:0xAA00] = record
    p.memory[0x4000] = 0
    choose(19)
    press('a')
    assert mask('drummutemask') == mask('drumsolomask') == 0
    print('PASS: 12 vertical drum mixer strips, solos, live mute, playback filtering, BA save/load and B8 compatibility')
finally:
    p.stop(save=False)

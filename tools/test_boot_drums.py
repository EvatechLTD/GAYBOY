"""Direct DRUM boot, second-Start menu and decaying default noise patches."""
from pathlib import Path
from io import BytesIO
import numpy as np
from pyboy import PyBoy
from boot_helpers import enter_app
S = {l.split()[1]: int(l.split()[2], 16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', cgb=False, sound_emulated=True, ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def v(n): return p.memory[S['_' + n]]
def wait(predicate):
    for _ in range(180):
        p.tick(1)
        if predicate(): return
    raise AssertionError('Input/page transition stalled')
def press(key, mask):
    p.button_press(key); wait(lambda: v('lastpad') & mask)
    p.button_release(key); wait(lambda: not v('lastpad') & mask)
    p.tick(5)
try:
    enter_app(p)
    assert v('page') == 8 and v('seqtrack') == 6 and not v('navopen')
    assert v('drumkit') == v('kitchoice') == 1
    assert not v('seqplaying') and not v('intro_audio_running')
    assert list(p.memory[S['_noisepatch']:S['_noisepatch'] + 10]) == [10, 0, 1, 1, 1, 14, 4, 2, 0, 1]
    p.screen.image.save('build/boot-drum-808.png')
    p.button_press('start'); wait(lambda: v('navopen'))
    assert v('navchoice') == 8
    for _ in range(24):
        if v('navchoice') == 17: break
        press('down', 8)
    assert v('navchoice') == 17
    p.button_release('start'); wait(lambda: not v('navopen'))
    p.tick(30); assert v('page') == 17
    profiles = []
    for voice, nr43 in enumerate((0x09, 0x42)):
        assert v('drumsynthvoice') == voice
        p.button_press('b'); wait(lambda: v('lastpad') & 32)
        assert p.memory[0xFF22] == nr43
        levels = []
        for _ in range(25):
            p.tick(1)
            levels.append(float(np.sqrt(np.mean(p.sound.ndarray.astype(float) ** 2))))
        early, late = float(np.mean(levels[:3])), float(np.mean(levels[-3:]))
        assert early > 0.1 and late < early * 0.2, (voice, levels)
        profiles.append((round(early, 2), round(late, 2)))
        p.button_release('b'); wait(lambda: not v('lastpad') & 32)
        if not voice: press('select', 64)
    print('PASS: direct stopped DRUM boot, TR-808 selected, subsequent Start menu, distinct hat/snare with audible attacks and decays:', profiles)
finally:
    p.stop(save=False)

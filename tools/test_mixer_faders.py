"""Held A/B edits stay on the fader and accelerate with VBlank time."""
from pathlib import Path

env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0], env)
p, S, choose, press = (env[k] for k in ('p', 'S', 'choose', 'press'))
mx = S['_mx']

try:
    p.tick(180)  # Let the fixture's initial instrument page finish publishing.
    choose(18)
    for modifier in ('a', 'b'):
        p.memory[mx + 4] = 4  # P1 volume.
        p.memory[mx + 12] = 127
        p.memory[S['_dirty']] = 1
        p.tick(10)
        p.button_press(modifier)
        p.tick(8)
        press('down')
        assert p.memory[mx + 12] == 126, modifier
        p.button_press('down')
        samples = [126]
        for _ in range(6):
            p.tick(15)
            samples.append(p.memory[mx + 12])
        assert all(a > b for a, b in zip(samples, samples[1:])), (modifier, samples)
        early, later = samples[3], samples[6]
        assert early - later > 126 - early, (modifier, early, later)
        assert p.memory[mx + 4] == 4
        p.tick(240)
        assert p.memory[mx + 12] == 0
        p.button_release('down')
        p.tick(8)
        p.button_press('up')
        p.tick(300)
        assert p.memory[mx + 12] == 127
        p.button_release('up')
        p.button_release(modifier)
        p.tick(10)
        press('down')
        assert p.memory[mx + 4] == 5  # Releasing modifier restores navigation.
        assert p.memory[mx + 12] == 127
    print('PASS: continuous A/B fader editing, logarithmic acceleration, clamping and navigation')
finally:
    p.stop(save=False)

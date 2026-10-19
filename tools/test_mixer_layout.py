"""Exercise layout through real UI input; hiding must not change audio state."""
from pathlib import Path

env = {}
exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0], env)
p, S, choose, press, v = (env[k] for k in ('p', 'S', 'choose', 'press', 'v'))

try:
    choose(18)
    before = (v('seqmuted'), v('seqsolo'),
              bytes(p.memory[S['_mx'] + 12:S['_mx'] + 26]))
    press('select')
    assert v('layout_cursor') == 0
    press('a')  # Hide P1.
    press('select')
    press('down'); press('down')  # Header -> tempo -> first visible strip.
    assert v('mx', 4) == 6, 'Focus did not skip hidden P1'
    press('select')
    # Hide every other strip and every pad, retaining stable logical IDs.
    for _ in range(27):
        press('down'); press('a')
    press('select')
    press('down'); press('down')
    assert v('mx', 4) == 0, 'Empty layout did not return to a safe header'
    after = (v('seqmuted'), v('seqsolo'),
             bytes(p.memory[S['_mx'] + 12:S['_mx'] + 26]))
    assert before == after, 'Hiding controls modified audio state'
    choose(8); choose(18)
    press('select'); press('b'); press('select')  # Escape hatch: show all.
    assert bytes(p.memory[S['_mixer_hidden']:S['_mixer_hidden'] + 4]) == bytes(4)
    press('down'); press('down')
    assert v('mx', 4) == 2, 'Show all did not restore P1 navigation'
    print('Mixer hide/show, empty-layout navigation and audio-state isolation passed')
finally:
    p.stop(save=False)

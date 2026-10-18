"""Drive the real one-shot boot intro before application regression checks."""
from pathlib import Path

def enter_app(p, symbols=None):
    if symbols is None:
        symbols = {l.split()[1]: int(l.split()[2], 16)
                   for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
    for _ in range(2800):
        p.tick(1)
        if p.memory[symbols['_introready']]:
            break
    assert p.memory[symbols['_introready']], 'Intro never reached Press Start'
    p.button_press('start')
    # Sparse libraries validate occupied slots and install optional hardware
    # demo data before publishing the first editable screen. This is a boot
    # liveness limit; live input/launch timing has separate strict checks.
    for _ in range(1800):
        p.tick(1)
        if not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8 and p.memory[symbols['_seqtrack']]==6 and not p.memory[symbols['_navopen']]:
            break
    assert not p.memory[symbols['_introactive']] and p.memory[symbols['_page']]==8 and p.memory[symbols['_seqtrack']]==6 and not p.memory[symbols['_navopen']], 'Intro did not open the DRUM sequencer'
    p.button_release('start')
    p.tick(50)
    assert not p.memory[symbols['_navopen']]


def enable_experimental(p):
    """Explicit UI opt-in for DSP regressions; production now boots with it off."""
    symbols = {l.split()[1]: int(l.split()[2], 16)
               for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
    def value(name): return p.memory[symbols['_' + name]]
    if value('experimental_mode'):
        return
    def press(key, mask):
        p.button_press(key)
        for _ in range(120):
            p.tick(1)
            if value('lastpad') & mask: break
        assert value('lastpad') & mask
        p.button_release(key)
        for _ in range(120):
            p.tick(1)
            if not value('lastpad') & mask: break
        assert not value('lastpad') & mask
        p.tick(4)
    for target in (16, 11):
        p.button_press('start')
        for _ in range(120):
            p.tick(1)
            if value('navopen'): break
        assert value('navopen')
        for _ in range(32):
            if value('navchoice') == target: break
            press('down', 8)
        assert value('navchoice') == target
        p.button_release('start')
        for _ in range(120):
            p.tick(1)
            if not value('navopen'): break
        p.tick(20)
        if target == 16:
            press('a', 16)
            assert value('experimental_mode')

"""Power-cycle the real layout writer in sparse and legacy batteries."""
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app

S = {line.split()[1]: int(line.split()[2], 16)
     for line in Path('build/GAYBOY.noi').read_text().splitlines()
     if line.startswith('DEF ')}


def boot(data):
    p = PyBoy('build/GAYBOY.gb', window='null', cgb=False,
              sound_emulated=True, ram_file=BytesIO(data))
    p.set_emulation_speed(0)
    enter_app(p, S)
    return p


def battery(p):
    data = bytearray()
    for bank in range(4):
        p.memory[0x4000] = bank
        data.extend(p.memory[0xa000:0xc000])
    p.memory[0x4000] = 0
    return data


def store(p, masks, pair):
    p.memory[S['_mixer_hidden']:S['_mixer_hidden'] + 8] = list(masks)
    p.memory[S['_linkpair']] = pair
    p.memory[S['_mixer_layout_dirty']] = 1
    for _ in range(1200):
        p.tick(1)
        if not p.memory[S['_mixer_layout_dirty']]:
            return
    raise AssertionError('Layout commit did not finish')


def verify(data, masks, pair, sparse):
    p = boot(data)
    try:
        assert p.memory[S['_sparse_enabled']] == sparse
        assert bytes(p.memory[S['_mixer_hidden']:S['_mixer_hidden'] + 8]) == masks
        assert p.memory[S['_linkpair']] == pair
    finally:
        p.stop(save=False)


for legacy in (False, True):
    seed = bytearray(32768)
    if legacy:
        seed[8192 + 2500:8192 + 2504] = b'GBM2'
    first = bytes((3, 0, 17, 5, 128, 2, 64, 8))
    second = bytes((1, 32, 0, 8, 4, 1, 16, 2))
    p = boot(seed)
    try:
        assert p.memory[S['_sparse_enabled']] == (0 if legacy else 1)
        store(p, first, 1)
        old = battery(p)
        store(p, second, 0)
        new = battery(p)
    finally:
        p.stop(save=False)
    verify(old, first, 1, 0 if legacy else 1)
    verify(new, second, 0, 0 if legacy else 1)
    # Lose the newest legacy record, or one redundant sparse root.
    damaged = bytearray(new)
    if legacy:
        base = 3 * 8192 + 0x1c10
        a, b = damaged[base + 2], damaged[base + 18]
        newest = 16 if (b - a) % 256 < 128 else 0
        damaged[base + newest] = 0
        verify(damaged, first, 1, 0)
    else:
        damaged[8192] = 0
        verify(damaged, second, 0, 1)
print('PASS sparse/legacy layout and PAIR power cycles, redundant-record recovery')

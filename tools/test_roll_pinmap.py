"""Exercise actual-CPU tile pinning across every tile ID and count boundary."""
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app
S = {l.split()[1]: int(l.split()[2], 16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', cgb=False, sound_emulated=False, ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
try:
    enter_app(p)
    p.memory[0, 0x3FF0] = 0x18; p.memory[0, 0x3FF1] = 0xFE
    p.memory[0xFFFF] = p.memory[0xFF07] = p.memory[0xFF0F] = 0
    p.memory[0x0000] = 10; p.memory[0x4000] = 0
    a = S['_roll_pinmap']; bank = a >> 16
    p.memory[0x2000] = bank; p.memory[0xFF90] = bank
    source = list(range(256)) * 2
    for count in (0, 1, 15, 16, 17, 255, 256, 360, 512):
        expected = [0] * 128
        for tile in source[:count]:
            index = tile - 64 if 64 <= tile < 96 else tile - 128 if 160 <= tile < 244 else tile - 136 if tile >= 252 else None
            if index is not None: expected[index] = 1
        p.memory[0xB000:0xB200] = source
        p.memory[0xAD00:0xAD80] = [0] * 128
        p.memory[0xDF00:0xDF02] = [0xF0, 0x3F]
        p.register_file.SP = 0xDF00
        p.register_file.D = 0xB0; p.register_file.E = 0
        p.register_file.B = count >> 8; p.register_file.C = count & 255
        p.register_file.PC = a & 65535
        for _ in range(20):
            p.tick(1)
            if p.register_file.PC in (0x3FF0, 0x3FF1): break
        assert p.register_file.PC in (0x3FF0, 0x3FF1), count
        assert p.register_file.SP == 0xDF02, ('stack', count)
        assert p.register_file.B * 256 + p.register_file.C == count, ('BC preservation', count)
        assert list(p.memory[0xAD00:0xAD80]) == expected, count
    print('PASS: tile pinning matches every tile ID, font/control exclusions, count boundaries, stack and BC preservation')
finally:
    p.stop(save=False)

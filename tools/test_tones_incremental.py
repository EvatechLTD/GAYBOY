"""Actual DMG CPU equivalence and validation for bounded tone preparation."""
from pathlib import Path
from io import BytesIO
import json
import re
from pyboy import PyBoy
from boot_helpers import enter_app

S = {line.split()[1]: int(line.split()[2], 16)
     for line in Path('build/GAYBOY.noi').read_text().splitlines()
     if line.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', cgb=False,
          sound_emulated=False, ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
enter_app(p)
p.memory[0, 0x3ff0] = 0
p.memory[0, 0x3ff1] = 0x18
p.memory[0, 0x3ff2] = 0xfe
p.memory[0xffff] = p.memory[0xff07] = p.memory[0xff0f] = 0
p.memory[0] = 0x0a
p.memory[0x4000] = 0
p.memory[0x2000] = p.memory[0xff90] = 39
p.memory[0x3000] = 0
p.memory[S['_seqplaying']] = 0
ended = [None]
p.hook_register(0, 0x3ff0, lambda _: ended.__setitem__(0, p._cycles()), None)


def call(name):
    sp = 0xdf00
    p.memory[sp:sp + 6] = [0xf0, 0x3f, 0, 0, 0, 0]
    p.register_file.SP = sp
    p.register_file.PC = S['_' + name] & 65535
    ended[0] = None
    begin = p._cycles()
    for _ in range(120):
        p.tick(1)
        if ended[0] is not None:
            break
    assert ended[0] is not None, name
    assert p.register_file.SP == sp + 2, (name, 'stack imbalance')
    return p.register_file.A, ended[0] - begin


def finish():
    costs = []
    for _ in range(100):
        result, cycles = call('tones_step')
        costs.append(cycles)
        if result:
            return result, costs
    raise AssertionError('Preparation did not finish')


try:
    # Exercise both ends of each field range, including biased signed pitches
    # and sixteen-bit values, rather than comparing only boot defaults.
    call('tones_pack_begin')
    cursor = p.memory[0xbcfe] | p.memory[0xbcff] << 8
    index = 0
    while p.memory[cursor + 4]:
        destination = p.memory[cursor] | p.memory[cursor + 1] << 8
        maximum = p.memory[cursor + 2] | p.memory[cursor + 3] << 8
        flags = p.memory[cursor + 5]
        value = maximum if index & 1 else 1 if flags & 2 else 0
        if flags & 4:
            value = (value - 24) & 255
        p.memory[destination] = value & 255
        if flags & 1:
            p.memory[destination + 1] = value >> 8
        cursor += 6
        index += 1
    assert index == 416
    call('tones_pack')
    packed = bytes(p.memory[0xbd00:0xbe20])
    call('tones_pack_begin')
    result, pack_costs = finish()
    assert result == 1 and bytes(p.memory[0xbd00:0xbe20]) == packed

    p.memory[0xb871:0xb991] = packed
    p.memory[0xba00:0xbcfe] = bytes(766)
    result, _ = call('tones_decode')
    assert result == 1
    decoded = bytes(p.memory[0xba00:0xbcfe])
    p.memory[0xba00:0xbcfe] = bytes(766)
    call('tones_decode_begin')
    result, decode_costs = finish()
    assert result == 1 and bytes(p.memory[0xba00:0xbcfe]) == decoded

    source = Path('src/tones.c').read_text().split('tonefields[]={', 1)[1].split('};', 1)[0]
    fields = [(int(a), int(b), int(c))
              for a, b, c in re.findall(r',\s*(\d+),\s*(\d+),\s*(\d+)\s*}', source)]
    for nonzero in (False, True):
        offset = 0
        bad = bytearray(packed)
        for maximum, width, flags in fields:
            if (flags & 2) if nonzero else maximum < (1 << width) - 1:
                for bit in range(width):
                    at = offset + bit
                    if nonzero:
                        bad[at >> 3] &= ~(1 << (at & 7))
                    else:
                        bad[at >> 3] |= 1 << (at & 7)
                break
            offset += width
        else:
            raise AssertionError('Missing validation fixture')
        p.memory[0xb871:0xb991] = bad
        call('tones_decode_begin')
        result, _ = finish()
        assert result == 2, ('Invalid field accepted', nonzero)

    report = {'pack_slices': len(pack_costs), 'decode_slices': len(decode_costs),
              'max_pack_slice_ms': max(pack_costs) * 1000 / 4194304,
              'max_decode_slice_ms': max(decode_costs) * 1000 / 4194304}
    Path('build/tones-incremental.json').write_text(json.dumps(report, indent=2))
    print('PASS: exact incremental packing/decoding, invalid ranges/nonzero fields, bounded slices', json.dumps(report))
finally:
    p.stop(save=False)

"""Execute SRAM transfers on a DMG CPU and check bytes, checksums and timing."""
from pathlib import Path
from io import BytesIO
import json
from pyboy import PyBoy
from boot_helpers import enter_app

S = {l.split()[1]: int(l.split()[2], 16)
     for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', cgb=False,
          sound_emulated=False, ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
enter_app(p)
p.memory[0, 0x3ff0:0x3ff3] = [0, 0x18, 0xfe]
p.memory[0xffff] = p.memory[0xff07] = p.memory[0xff0f] = 0
p.memory[0] = 0x0a
p.memory[0x4000] = 0
p.memory[0x2000] = p.memory[0xff90] = 41
p.memory[0x3000] = 0
p.memory[S['_seqplaying']] = 0
ended = [None]
p.hook_register(0, 0x3ff0, lambda _: ended.__setitem__(0, p._cycles()), None)


def call(name, size):
    args = [0, 32, 0, 0, 0xb0, size & 255, size >> 8]
    sp = 0xdf00
    p.memory[sp:sp + 13] = [0xf0, 0x3f, 0, 0, 0, 0] + args
    p.register_file.SP = sp
    p.register_file.PC = S['_' + name] & 65535
    ended[0] = None
    begin = p._cycles()
    for _ in range(300):
        p.tick(1)
        if ended[0] is not None:
            break
    assert ended[0] is not None, name
    assert p.register_file.SP == sp + 2, (name, 'stack imbalance')
    return (ended[0] - begin) * 1000 / 4194304


results = []
try:
    for name in ('readpart', 'writepart'):
        for checking in (0, 1):
            for size in (16, 64, 2048):
                expected = bytes((i * 37 + 19) & 255 for i in range(size))
                p.memory[S['_mx'] + 45] = checking
                p.memory[S['_mx'] + 43:S['_mx'] + 45] = [0, 0]
                if name == 'readpart':
                    p.memory[0x4000] = 1
                    p.memory[0xa020:0xa020 + size] = expected
                    p.memory[0x4000] = 0
                    p.memory[0xb000:0xb000 + size] = bytes(size)
                else:
                    p.memory[0xb000:0xb000 + size] = expected
                elapsed = call(name, size)
                if name == 'readpart':
                    actual = bytes(p.memory[0xb000:0xb000 + size])
                else:
                    p.memory[0x4000] = 1
                    actual = bytes(p.memory[0xa020:0xa020 + size])
                    p.memory[0x4000] = 0
                assert actual == expected, (name, checking, size)
                checksum = p.memory[S['_mx'] + 43] | p.memory[S['_mx'] + 44] << 8
                assert checksum == (sum(expected) & 65535 if checking else 0)
                results.append(dict(operation=name, checksum=checking, bytes=size, cpu_ms=elapsed))
    Path('build/pattern-io-micro.json').write_text(json.dumps(results, indent=2))
    print('PASS: SRAM byte/checksum equivalence', json.dumps(results))
finally:
    p.stop(save=False)

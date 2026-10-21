"""Run actual banked main code on the DMG CPU, with deterministic RAM fixtures."""
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy


class Engine:
    def __init__(self, rom):
        self.S = {l.split()[1]: int(l.split()[2], 16)
                  for l in Path(rom).with_suffix('.noi').read_text().splitlines()
                  if l.startswith('DEF ')}
        self.p = PyBoy(str(rom), window='null', sound_emulated=False,
                       cgb=False, ram_file=BytesIO(bytes(32768)))
        self.p.set_emulation_speed(0)
        p = self.p
        p.memory[0] = 10
        p.memory[0x4000] = 0
        p.memory[0xffff] = p.memory[0xff0f] = p.memory[0xff40] = 0
        p.memory[0xff50] = 1
        p.memory[0xc000:0xe000] = [0] * 8192
        p.memory[0xc000:0xc004] = [0x18, 0, 0x18, 0xfe]
        self.returned = []
        p.hook_register(0, 0xc000, lambda _: self.returned.append(p._cycles()), None)
        self.put('experimental_mode', 1)
        self.put('power', 1)
        self.word('seqbpm', 120)
        self.put('frameadvance', 1)
        self.call('eval_defaults')
        self.base = bytes(p.memory[0xc000:0xe000])
        self.ram = bytes(p.memory[0xa000:0xc000])

    def reset(self):
        self.p.memory[0xc000:0xe000] = self.base
        self.p.memory[0xa000:0xc000] = self.ram

    def put(self, name, value, offset=0):
        self.p.memory[self.S['_' + name] + offset] = value & 255

    def get(self, name, offset=0):
        return self.p.memory[self.S['_' + name] + offset]

    def word(self, name, value, offset=0):
        self.put(name, value, offset)
        self.put(name, value >> 8, offset + 1)

    def call(self, name, args=()):
        p = self.p
        address = self.S['_' + name]
        bank = address >> 16
        p.memory[0x2000] = p.memory[0xff90] = bank
        frame = [0, 0xc0, 0, 0, 0, 0, *args]
        p.memory[0xdfe0:0xdfe0 + len(frame)] = frame
        p.register_file.SP = 0xdfe0
        p.register_file.PC = address & 65535
        self.returned.clear()
        start = p._cycles()
        for _ in range(100):
            p.tick(1)
            if self.returned:
                return p.register_file.A, self.returned[-1] - start
        raise AssertionError((name, hex(p.register_file.PC)))

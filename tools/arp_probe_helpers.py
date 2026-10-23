"""Observe real APU trigger writes in both generic and prepared arp paths."""
import ast
from pathlib import Path
import pyboy

def hook_attacks(p, rom, symbols, channel, callback, frequency_callback=None, include_editbuffer=False, register_hook=None):
    data = Path(rom).read_bytes()
    tree = ast.parse((Path(pyboy.__file__).parent / 'core/opcodes.py').read_text())
    lengths = next(ast.literal_eval(n.value.args[1]) for n in tree.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'OPCODE_LENGTHS' for t in n.targets))
    trigger = (0xff14, 0xff19, 0xff1e)[channel]
    frequency_low = [0]
    def write(site):
        op, extra, cycles = site
        r = p.register_file
        target = ((r.B << 8) | r.C) if op == 2 else ((r.D << 8) | r.E) if op == 0x12 else r.HL if op in (0x22, 0x32, 0x36, 0x77) else 0xff00+extra if op == 0xe0 else 0xff00+r.C if op == 0xe2 else extra
        value = extra if op == 0x36 else r.A
        if target == trigger-1:
            frequency_low[0] = value
            return
        audible = p.memory[(0xff12, 0xff17, 0xff1c)[channel]] & (0xf0 if channel < 2 else 0x60)
        if target == trigger and value & 128 and audible:
            callback(p._cycles()+cycles)
            if frequency_callback:
                frequency_callback(frequency_low[0] | ((value & 7) << 8))
    for name in ('_play', '_arp_native_sound', '_arp_irq_tick', '_arp_irq_due') + (('_editirq_commit',) if include_editbuffer else ()):
        if name not in symbols: continue
        pointer = symbols[name]
        bank, pc = pointer >> 16, pointer & 65535
        end = min(v & 65535 for k, v in symbols.items() if k.startswith('_') and not k.startswith('_rROM') and v >> 16 == bank and (v & 65535) > pc)
        while pc < end:
            at = bank*16384+pc-16384 if bank else pc
            op = data[at]
            length = 2 if op == 0xcb else lengths[op]
            if op in (2, 0x12, 0x22, 0x32, 0x36, 0x77, 0xe0, 0xe2, 0xea):
                extra = data[at+1] if length > 1 else 0
                if op == 0xea: extra |= data[at+2] << 8
                cycles = 16 if op == 0xea else 12 if op in (0x36, 0xe0) else 8
                if name == '_play' or op == 0xe0 and extra in (trigger-0xff00,trigger-1-0xff00) or op == 0xea and extra in (trigger,trigger-1):
                    (register_hook or p.hook_register)(bank, pc, write, (op, extra, cycles))
            pc += length

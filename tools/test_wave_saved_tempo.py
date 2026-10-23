"""Whole-note gates must survive SRAM tempo caches from an earlier boot."""
import argparse
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app

ap = argparse.ArgumentParser()
ap.add_argument('--rom', default='build/GAYBOY.gb')
ap.add_argument('--save', type=Path)
args = ap.parse_args()
rom = Path(args.rom)
symbols = {line.split()[1]: int(line.split()[2], 16)
           for line in rom.with_suffix('.noi').read_text().splitlines() if line.startswith('DEF ')}
p = PyBoy(str(rom), window='null', sound_emulated=True, cgb=False,
          ram_file=BytesIO(args.save.read_bytes() if args.save else bytes(32768)))
p.set_emulation_speed(0)

def get(name, i=0):
    a = symbols['_' + name] + i
    return p.memory[0, a] if 0xa000 <= a < 0xc000 else p.memory[a]

def put(name, value, i=0):
    a = symbols['_' + name] + i
    if 0xa000 <= a < 0xc000: p.memory[0, a] = value & 255
    else: p.memory[a] = value & 255

def word(name, value, i=0):
    put(name, value, i); put(name, value >> 8, i+1)

try:
    enter_app(p, symbols)
    if not args.save:
        offset = 0
        for c in range(7):
            events = [[0, 37, 127, 16], [16, 43, 127, 16]] if c == 2 else [[s, 11, 127, 1] for s in range(0, 16, 2)] if c == 6 else []
            word('seqeventoffsets', offset, c*2)
            word('seqeventcounts', len(events), c*2)
            word('seqlength', 32 if c == 2 else 16, c*2)
            for event in events:
                p.memory[1, 0xa300+offset*4:0xa304+offset*4] = event
                offset += 1
        # Recreate the persisted SRAM cache with newly initialized WRAM.
        word('seqbpm', 120); word('seqglobalbpm', 120)
        word('seqcachedbpm', 120); word('seqstepunits', 128)
        word('seqwholeunits', 0)
        for c in range(7):
            put('seqcachedgate', 100, c); word('seqgateunits', 128, c*2)
        put('pattern_dirty', 1)
    put('seqtrack', 2); put('selected', 2); put('dirty', 1)
    p.tick(60)
    p.button_press('select'); p.tick(3)
    p.button_press('a'); p.tick(4)
    p.button_release('a'); p.button_release('select')
    assert get('seqplaying')
    assert get('seqwholeunits') | get('seqwholeunits', 1) << 8, 'Persisted tempo cache skipped whole-note initialization'
    checked = 0
    for frame in range(650):
        p.tick(1)
        # Avoid onset/boundary frames; require sustained hardware output.
        if 2 <= get('seqposition', 2) % 16 <= 13 and not get('waveengine'):
            assert get('seqowned', 2) and get('active', 2) and p.memory[0xff26] & 4, (frame, get('seqposition', 2))
            checked += 1
    assert checked > 300 and get('editbuffer_valid'), checked
    print('PASS saved-tempo whole-note initialization and sustained Wave before/after playback buffering:', checked, 'frames')
finally:
    p.stop(save=False)

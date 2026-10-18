"""Pin the compiled ROM and its matching symbols for browser tutorial checks.

Run after build_rom.py and check_rom.py. The normal download is left untouched.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
rom = (ROOT/'build/GAYBOY.gb').read_bytes()
symbols = {line.split()[1][1:]:int(line.split()[2],16)
           for line in (ROOT/'build/GAYBOY.noi').read_text().splitlines()
           if line.startswith('DEF _')}
names = ('page navopen navchoice seqplaying seqtrack seqcursor seqpitch seqhead '
         'seqfocus seqedit seqapending seqposition seqevents_lo seqevents_hi '
         'seqeventcounts seqeventoffsets seqmuted seqsolo seqlength lastpad').split()
assert len(rom) == 1048576 and rom[0x147] == 0x1B and rom[0x149] == 3
assert (sum(rom)-rom[0x14e]-rom[0x14f]) & 65535 == int.from_bytes(rom[0x14e:0x150],'big')
metadata = {'rom':'downloads/GAYBOY-tutorial.gb',
            'sha256':hashlib.sha256(rom).hexdigest(),
            'symbols':{name:symbols[name] for name in names},'mixer':symbols['mx']}
(ROOT/'website/downloads/GAYBOY-tutorial.gb').write_bytes(rom)
(ROOT/'website/emulator/tutorial-rom.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Pinned tutorial cartridge:',metadata['sha256'])

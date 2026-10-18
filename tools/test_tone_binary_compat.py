"""Compare serialization and restore against a slot captured before optimization.

Requires build/alpha1-legacy-tone-slot.bin from the unchanged ROM's
test_pattern_tones fixture. Does not read or write the user's cartridge save.
"""
from pathlib import Path

legacy = Path('build/alpha1-legacy-tone-slot.bin').read_bytes()
assert len(legacy) == 2560 and legacy[0] == 0xBA
source = Path('tools/test_pattern_tones.py').read_text()
source = source.replace(
    'saved=record(0);assert',
    "saved=record(0);assert saved[2161:2449]==legacy[2161:2449], 'Packed tone format changed';record(0,legacy);saved=legacy;assert",
)
exec(source)
print('PASS: byte-identical tone serialization and loading pre-optimization slot')

"""Check protected engine memory and report storage separately from scratch.

This is deliberately based on linked addresses, not C structure estimates.
Intentional page-local overlays are listed as one owner. No unused byte of
engine bank zero or WRAM is advertised as available song storage.
"""
import argparse
import json
from pathlib import Path


def audit(rom):
    symbols = {
        line.split()[1]: int(line.split()[2], 16)
        for line in rom.with_suffix('.noi').read_text().splitlines()
        if line.startswith('DEF ')
    }
    image = rom.read_bytes()
    heap_end = symbols['s__HEAP_END']
    work_margin = 0xD800 - heap_end
    assert work_margin >= 1024, ('Engine WRAM reserve below 1024 bytes', work_margin)
    assert symbols['_wavepixels'] == 0xB000, 'Preview must use page-local SRAM scratch'
    assert symbols['_seqevents_hi'] == 0xA800
    assert symbols['_pulsekickleft'] == 0xAC59
    assert symbols['_drumnoisetail'] == 0xAC58
    assert symbols['_expdelay'] == 0xA000
    assert symbols['_mx'] == 0xAC80
    assert symbols['_prep'] == 0xACB4
    assert symbols['_ui_loading_active'] == 0xACFE
    assert symbols['_ui_loading_step'] == 0xACFF
    assert symbols['_rolltiles'] == 0xB000
    assert symbols['_rolldirty'] + 20 <= 0xC000
    stack_bottom = max(symbols[name] + size for name, size in (
        ('_softlut', 64), ('_explut', 32), ('_expwet', 256),
        ('_expalpha', 256), ('_expreslut', 256), ('_expinterp', 256),
        ('_expfeedback', 256)))
    assert stack_bottom <= 0xDE00, 'Keep at least 512 bytes for stack/interrupts'
    assert image[0x147] == 0x1B and image[0x149] == 3, '32 KiB battery RAM target changed'

    # Entire engine bank is protected, including holes and page-local overlays.
    bank_zero = [
        (0xA000, 0xA800, 'audio delay'),
        (0xA800, 0xAC00, 'upper live event pool'),
        (0xAC00, 0xAD00, 'PCM, mixer, preparation and UI control state'),
        (0xAD00, 0xB000, 'renderer, mixer preview and drum edit overlays'),
        (0xB000, 0xC000, 'roll tiles, pattern/tone preparation and UI preview overlays'),
    ]
    assert sum(end - start for start, end, _ in bank_zero) == 8192

    # Current persistence layout. Slot 8 is a virtual address used only for
    # the bank-3 tail journal span, not a ninth pattern record.
    owned = {}

    def reserve(bank, start, size, owner):
        assert 1 <= bank <= 3 and 0 <= start <= start + size <= 8192
        for offset in range(start, start + size):
            key = bank, offset
            assert key not in owned, ('SRAM ownership overlap', key, owned.get(key), owner)
            owned[key] = owner

    for slot in range(8):
        bank, base = 1 + slot // 3, slot % 3 * 2560
        reserve(bank, base, 20, 'pattern name/tag/checksum')
        reserve(bank, base + 32, 2417, 'pattern events/settings/patch')
    reserve(1, 2500, 4, 'legacy boot signature')
    reserve(3, 0x1400, 2064, 'maximum track/region clipboard')
    spans = [(2, 2560, 512), (5, 2560, 512), (8, 2560, 512),
             (0, 2449, 51), (0, 2504, 56)]
    spans += [(slot, 2449, 111) for slot in range(1, 8)]
    spans += [(slot, 20, 12) for slot in range(8)]
    for slot, offset, size in spans:
        reserve(1 + slot // 3, slot % 3 * 2560 + offset, size, 'durable journal allocation')
    unused = 3 * 8192 - len(owned)
    return {
        'rom': str(rom),
        'cartridge_ram_bytes': 32768,
        'engine_bank_reserved_bytes': 8192,
        'engine_bank_regions': [{'start': hex(a), 'end_exclusive': hex(b), 'owner': name}
                                for a, b, name in bank_zero],
        'wram_unused_below_audio_tables_bytes': work_margin,
        'wram_minimum_reserve_bytes': 1024,
        'stack_reserved_bytes': 0xE000 - stack_bottom,
        'stack_minimum_reserve_bytes': 512,
        'legacy_persistence_bank_unassigned_bytes': unused,
        'sparse_pool_physical_bytes': 304 * 64,
        'sparse_pool_root_bytes': 4 * 64,
        'sparse_pool_allocatable_payload_bytes': 300 * 62,
        'sparse_recovery_reserve_bytes': 3056,
        'clipboard_reserved_bytes': 2064,
        'sparse_pool_regions': [
            {'bank': 1, 'start': '0xa000', 'end_exclusive': '0xc000'},
            {'bank': 2, 'start': '0xa000', 'end_exclusive': '0xb800'},
            {'bank': 3, 'start': '0xa000', 'end_exclusive': '0xb400'},
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=Path('build/GAYBOY.gb'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.rom)
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + '\n')
    print(encoded)

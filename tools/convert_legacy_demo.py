"""Convert a legacy demo using native patches exported by the real ROM.

First run inspect_legacy_demo_rom.py against the original save. This deliberately
uses the legacy decoder rather than maintaining a second packed-patch decoder.
The source save is never modified. Every metadata byte, event, and native patch
is checked again after serializing the sparse image.
"""
import argparse
from binascii import crc_hqx
from hashlib import sha256
import json
from pathlib import Path

from sparse_image import SparseImage


def word(data, at=0):
    return int.from_bytes(data[at:at + 2], 'little')


def le(value):
    return value.to_bytes(2, 'little')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def convert(source, report, patches, song_name):
    require(len(source) == 32768, 'Expected a 32 KiB legacy save')
    require(report['source_sha256'] == sha256(source).hexdigest(), 'Export belongs to another save')
    require(len(patches) == 450 * len(report['slots']), 'Wrong native patch export size')
    exported = {s['slot'] - 1: (s, patches[i * 450:(i + 1) * 450])
                for i, s in enumerate(report['slots'])}
    require(len(exported) == len(report['slots']), 'Duplicate exported slots')
    records = []
    for slot in range(8):
        at = (1 + slot // 3) * 8192 + (slot % 3) * 2560
        record = source[at:at + 2560]
        if record[0] not in (0xBA, 0xB9, 0xB8):
            require(record[0] in (0, 255), f'Unsupported legacy tag in slot {slot + 1}')
            require(slot not in exported, 'Export contains an unsaved slot')
            continue
        require(slot in exported, f'Missing actual ROM export for slot {slot + 1}')
        meta = record[2080:2161]
        checked_meta = meta if record[0] != 0xB8 else meta[:77]
        checksum = sum(record[1:18]) + sum(record[32:2080]) + sum(checked_meta)
        if record[0] == 0xBA:
            checksum += sum(record[2161:2449])
        require(checksum & 65535 == word(record, 18), f'Legacy checksum failed in slot {slot + 1}')
        if record[0] == 0xB8:
            meta = meta[:77] + bytes(4)
        counts = [word(meta, i * 2) for i in range(7)]
        require(sum(counts) <= 512, 'Too many legacy events')
        events = record[32:32 + sum(counts) * 4]
        tracks, pos = [], 0
        for count in counts:
            tracks.append([list(events[i:i + 4]) for i in range(pos, pos + count * 4, 4)])
            pos += count * 4
        exported_slot, native = exported[slot]
        name = record[1:17].split(b'\0')[0].decode('ascii')
        require(exported_slot['name'] == name and exported_slot['events'] == tracks,
                f'Actual ROM event/name mismatch in slot {slot + 1}')
        require(exported_slot['metadata_hex'] == meta.hex(), f'Actual ROM metadata mismatch in slot {slot + 1}')
        require(exported_slot['native_patch_sha256'] == sha256(native).hexdigest(), 'Native export checksum failed')
        records.append((slot, record[1:17], meta, events, tracks, native))
    require(records, 'No saved demo patterns')
    battery, pages, next_page = bytearray(32768), bytearray(b'\xff' * (304 * 64)), 4

    def obj(kind, payload):
        nonlocal next_page
        header = kind.encode() + b'\x01' + le(len(payload))
        blob = header + le(crc_hqx(header + payload, 65535)) + payload
        count = (len(blob) + 61) // 62
        require(next_page + count <= 304, 'Demo exceeds sparse pool capacity')
        head = next_page
        for i in range(count):
            page = next_page + i
            pages[page * 64:page * 64 + 2] = le(page + 1 if i + 1 < count else 65535)
            part = blob[i * 62:(i + 1) * 62]
            pages[page * 64 + 2:page * 64 + 2 + len(part)] = part
        next_page += count
        return head

    active, library, natives = [65535] * 8, [], {}
    for slot, name, meta, events, tracks, native in records:
        if native not in natives:
            natives[native] = obj('T', native)
        compact = meta[:14] + bytes(word(meta, 14 + i * 2) & 255 for i in range(7))
        compact += bytes(word(meta, 28 + i * 2) & 255 for i in range(7)) + meta[42:]
        step = 15360 // word(meta, 75)
        mask = sum(1 << i for i in range(6) if any(e[0] == 0 for e in tracks[i]))
        drums = sum(e[0] == 0 for e in tracks[6])
        mask |= 64 if drums == 0 else 128 if drums == 1 else 0
        prefix = name + compact + b''.join(le(step * gate // 100) for gate in meta[49:56])
        prefix += le(step) + bytes([mask]) + le(natives[native])
        require(len(prefix) == 102, 'Internal prefix size error')
        active[slot] = obj('P', prefix + events)
        library.append(active[slot])
    mx = source[3200:3264]
    selected = mx[1] if mx[0] == 0xD3 and mx[1] < 8 else records[0][0]
    quant = mx[3] if mx[0] == 0xD3 and mx[3] < 3 else 0
    encoded_name = song_name.encode('ascii')
    require(0 < len(encoded_name) <= 16, 'Song name must be 1..16 ASCII characters')
    song = obj('S', encoded_name.ljust(17, b'\0') + bytes([quant, selected]) + b''.join(map(le, active)))
    library_head = obj('L', le(len(library)) + b''.join(map(le, library)))
    root = bytearray(b'\xff' * 128)
    root[:9] = b'GBD1' + le(1) + bytes([1, selected, quant])
    root[16:32] = b''.join(map(le, active))
    root[32:34], root[96:98] = le(song), le(library_head)
    root[126:] = le(crc_hqx(root[:126], 65535))
    pages[:128] = root
    pages[128:256] = root
    # Unallocated storage has no graph meaning. Zero it so the ROM seed writer
    # can omit the free tail without carrying hundreds of erased pages.
    pages[next_page * 64:] = bytes((304 - next_page) * 64)
    battery[8192:16384] = pages[:8192]
    battery[16384:22528] = pages[8192:14336]
    battery[24576:29696] = pages[14336:]
    image = SparseImage(battery)
    require(image.library() == library and image.songs()[0]['patterns'] == active, 'Graph roundtrip failed')
    for slot, name, meta, events, tracks, native in records:
        decoded = image.object(active[slot], 'P')
        compact = decoded[16:83]
        expanded = compact[:14]
        expanded += b''.join(le(n or 256) for n in compact[14:21])
        expanded += b''.join(le(n or (0 if i == 6 else 256)) for i, n in enumerate(compact[21:28]))
        expanded += compact[28:]
        require(expanded == meta and decoded[:16] == name and decoded[102:] == events,
                'Serialized pattern parity failed')
        require(image.object(word(decoded, 100), 'T') == native, 'Serialized native parity failed')
    return bytes(battery), {'source_sha256': sha256(source).hexdigest(),
        'output_sha256': sha256(battery).hexdigest(), 'patterns': len(records),
        'events': sum(len(r[3]) // 4 for r in records), 'native_patches': len(natives),
        'song': image.songs()[0], 'allocated_pages': next_page,
        'free_pool_bytes': (304 - next_page) * 62,
        'exact_roundtrip': ['all 81 metadata bytes', 'names', 'ordered events', 'all 450 native patch bytes'],
        'slots': [{'slot': r[0] + 1, 'name': r[1].split(b'\0')[0].decode('ascii')} for r in records]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--decoded-report', type=Path, required=True)
    parser.add_argument('--native-patches', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--song-name', default='DEMO SONG')
    args = parser.parse_args()
    require(args.source.resolve() != args.output.resolve(), 'Output cannot overwrite original save')
    original = args.source.read_bytes()
    battery, result = convert(original, json.loads(args.decoded_report.read_text()),
                              args.native_patches.read_bytes(), args.song_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(battery)
    require(args.source.read_bytes() == original, 'Original save changed')
    result['source_unchanged'] = True
    args.output.with_suffix('.conversion.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

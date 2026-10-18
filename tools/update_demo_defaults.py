"""Apply release mixer/HH defaults to an embedded sparse demo, preserving its graph."""
from pathlib import Path
from binascii import crc_hqx
import re
from sparse_image import SparseImage
from make_sparse_seed import generate


def hihat_offset():
    text = Path('src/tones.c').read_text().split('static void apply_prepared(void)', 1)[1].split('static void finalize_prepared(void)', 1)[0]
    offset = 0
    for symbol, size in re.findall(r'ld hl,#([^\n]+)\n\s*\.rept (\d+)', text):
        if symbol.strip() == '_noisepatch':
            return offset + 3
        offset += int(size)
    raise ValueError('Missing native hi-hat field')


def update(source=Path('src/sparse_seed.c')):
    text = source.read_text().split('static const uint8_t seed[]={', 1)[1].split('};', 1)[0]
    pages = bytearray(map(int, re.findall(r'\d+', text)))
    pages.extend(bytes(304 * 64 - len(pages)))
    battery = bytearray(32768)
    def pack():
        battery[8192:16384] = pages[:8192]
        battery[16384:22528] = pages[8192:14336]
        battery[24576:29696] = pages[14336:]
    pack();image = SparseImage(battery)
    def replace(head, payload):
        kind = pages[head * 64 + 2]
        header = bytes([kind, 1]) + len(payload).to_bytes(2, 'little')
        blob = header + crc_hqx(header + payload, 65535).to_bytes(2, 'little') + payload
        offset = 0
        while head != 65535:
            at = head * 64;part = blob[offset:offset + 62]
            pages[at + 2:at + 2 + len(part)] = part
            offset += len(part);head = int.from_bytes(pages[at:at + 2], 'little')
        assert offset == len(blob)
    refs = set(image.library())
    for song in image.songs():refs.update(ref for ref in song['patterns'] if ref != 65535)
    patches = set()
    for ref in refs:
        pattern = bytearray(image.object(ref, 'P'))
        pattern[58:65] = bytes([127] * 7)
        patches.add(int.from_bytes(pattern[100:102], 'little'))
        replace(ref, pattern)
    for ref in patches:
        patch = bytearray(image.object(ref, 'T'));patch[hihat_offset()] = 0;replace(ref, patch)
    pack()
    battery_path = Path('build/demo-release.sav');battery_path.write_bytes(battery)
    generate(battery_path, source)
    print('Updated demo:', len(refs), 'patterns,', len(patches), 'patches; all faders 127; HH metallic off')

if __name__ == '__main__':update()

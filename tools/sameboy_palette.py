"""Use the website's explicit four colors for SameBoy development and capture."""
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]


def website_palette():
    source = (ROOT/'website/emulator/player.js').read_text(encoding='utf-8')
    match = re.search(r'_emulator_set_bw_palette_simple\(instance, type,\s*'
                      r'(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*'
                      r'(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+)\)', source)
    if not match:
        raise RuntimeError('Website palette definition changed; update sameboy_palette.py before capture')
    return tuple(int(color, 16) for color in match.groups())


def configure_desktop_palette(data):
    colors = website_palette()
    # Website arguments are white-to-black; SameBoy's native palette and
    # .sbp files store black-to-white, followed by the LCD-off white color.
    native_colors = (*reversed(colors), colors[0])
    rgb = b''.join(bytes((c & 255, (c >> 8) & 255, (c >> 16) & 255))
                   for c in native_colors)
    (ROOT/'tools/sameboy/Palettes/GAYBOY.sbp').write_bytes(b'LPBS\0'+rgb+struct.pack('<iII', 0, 0, 0))
    data[264] = 4  # Custom palette
    data[4416:4441] = b'GAYBOY'.ljust(25, b'\0')

"""Keep SameBoy 1.0.4's cursor visible; preserve its original executable."""
from hashlib import sha256

ORIGINAL_SHA256 = 'd20b8882069e87a5613fd3a71734253709be7ffd749871e70e260a4f70718008'
# Standalone SDL_ShowCursor(SDL_DISABLE) calls in the official Windows binary.
HIDE_CALLS = {0x34769: bytes.fromhex('e8325f0000'),
              0x37826: bytes.fromhex('e8752e0000')}


def keep_cursor_visible(executable):
    data = bytearray(executable.read_bytes())
    original = bytearray(data)
    for offset, call in HIDE_CALLS.items():
        if data[offset:offset+5] not in (call, b'\x90'*5):
            raise RuntimeError('Unsupported SameBoy cursor patch location')
        original[offset:offset+5] = call
    if sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeError('Unsupported SameBoy executable version')
    if data == original:
        backup = executable.with_suffix('.exe.original')
        if not backup.exists():
            backup.write_bytes(original)
        for offset in HIDE_CALLS:
            data[offset:offset+5] = b'\x90'*5
        executable.write_bytes(data)

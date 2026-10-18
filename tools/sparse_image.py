"""Read-only inspector for disposable GBD1 sparse battery images."""
from binascii import crc_hqx


class SparseImage:
    def __init__(self, battery):
        if len(battery) != 32768:
            raise ValueError('Expected 32 KiB battery image')
        self.pages = battery[8192:16384] + battery[16384:22528] + battery[24576:29696]
        roots = [self.pages[offset:offset + 128] for offset in (0, 128)]
        roots = [r for r in roots if r[:4] == b'GBD1' and crc_hqx(r[:126], 65535) == self.word(r, 126)]
        if not roots:
            raise ValueError('No valid sparse root')
        self.root = roots[0]
        for candidate in roots[1:]:
            delta = (self.word(candidate, 4) - self.word(self.root, 4)) & 65535
            if 0 < delta < 32768:
                self.root = candidate

    @staticmethod
    def word(data, at=0):
        return int.from_bytes(data[at:at + 2], 'little')

    def object(self, head, kind=None):
        data = bytearray()
        visited = set()
        while head != 65535:
            if not 4 <= head < 304 or head in visited:
                raise ValueError('Invalid/cyclic object chain')
            visited.add(head)
            page = self.pages[head * 64:(head + 1) * 64]
            data.extend(page[2:])
            head = self.word(page)
        size = self.word(data, 2)
        if data[1] != 1 or kind is not None and data[0] != ord(kind):
            raise ValueError('Unexpected object type/version')
        if size + 6 > len(data) or len(visited) != (size + 67) // 62:
            raise ValueError('Invalid object length')
        payload = bytes(data[6:6 + size])
        if crc_hqx(bytes(data[:4]) + payload, 65535) != self.word(data, 4):
            raise ValueError('Object checksum mismatch')
        return payload

    def library(self):
        head = self.word(self.root, 96)
        if head == 65535:
            return []
        data = self.object(head, 'L')
        return [self.word(data, 2 + i * 2) for i in range(self.word(data))]

    def songs(self):
        result = []
        for i in range(32):
            head = self.word(self.root, 32 + i * 2)
            if head == 65535:
                continue
            data = self.object(head, 'S')
            result.append({'index': i, 'name': data[:16].split(b'\0')[0].decode('ascii'),
                           'quant': data[17], 'active': data[18],
                           'patterns': [self.word(data, 19 + j * 2) for j in range(8)]})
        return result

    def pattern_name(self, head):
        return self.object(head, 'P')[:16].split(b'\0')[0].decode('ascii')

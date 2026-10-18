"""Inspect a user's legacy save in isolated RAM through the actual ROM UI."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from seq_storage_helpers import read_tracks, read_word

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom', type=Path, default=Path('build/GAYBOY.gb'))
parser.add_argument('--save', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
original = args.save.read_bytes()
original_hash = sha256(original).hexdigest()
source = Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
source = source.replace('build/GAYBOY.gb', args.rom.as_posix()).replace('build/GAYBOY.noi', args.rom.with_suffix('.noi').as_posix())
source = source.replace('BytesIO(bytes(32768))', 'BytesIO(original)').replace('enter_app(p)', 'enter_app(p,S)')
source = source.replace('range(60)', 'range(1800)').replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file=')
exec(source)


def native_patch():
    assembly = Path('src/tones.c').read_text().split('static void apply_prepared(void)', 1)[1].split('static void finalize_prepared(void)', 1)[0]
    data = bytearray()
    for expression, size in re.findall(r'ld hl,#([^\n]+)\n\s*\.rept (\d+)', assembly):
        symbol, _, offset = expression.strip().partition('+')
        address = S[symbol] + (int(offset) if offset else 0)
        data.extend(p.memory[address:address + int(size)])
    data.extend(p.memory[S['_pulsekickpatch']:S['_pulsekickpatch'] + 8])
    assert len(data) == 450
    return bytes(data)


def live_metadata():
    data = bytearray()
    for symbol, size in (('_seqeventcounts', 14), ('_seqlength', 14), ('_seqdefaultdur', 14),
                         ('_seqdefaultvel', 7), ('_seqgate', 7)):
        data.extend(p.memory[S[symbol]:S[symbol] + size])
    data.extend(p.memory[S['_mx'] + 12:S['_mx'] + 26])
    for name in ('seqmuted', 'seqsolo', 'seqbeats', 'seqdenom', 'seqmode'):
        data.append(v(name))
    for symbol in ('_seqbpm', '_drummutemask', '_drumsolomask'):
        data.extend(p.memory[S[symbol]:S[symbol] + 2])
    assert len(data) == 81
    return bytes(data)


try:
    assert v('sparse_enabled') == 0, 'Source was not recognized as legacy GBM2'
    choose(18)
    slots = []
    patches = bytearray()
    for index in range(8):
        start = (1 + index // 3) * 8192 + index % 3 * 2560
        record = original[start:start + 2560]
        if record[0] not in (0xba, 0xb9, 0xb8, 0xb7):
            continue
        if index:
            p.memory[S['_mx'] + 4] = 30 + index
            press('a')
            p.tick(30)
        assert v('mx', 1) == index, (index, v('mx', 1))
        tracks = read_tracks(p, S)
        name = bytes(p.memory[S['_mx'] + 26:S['_mx'] + 43]).split(b'\0')[0].decode('ascii')
        assert name == record[1:18].split(b'\0')[0].decode('ascii')
        raw = native_patch()
        metadata = live_metadata()
        assert metadata == record[2080:2161], ('Runtime metadata differs from source', index)
        offset = 0
        for track in tracks:
            assert bytes(value for event in track for value in event) == record[32 + offset:32 + offset + len(track) * 4]
            offset += len(track) * 4
        patches.extend(raw)
        slots.append({'slot': index + 1, 'name': name, 'legacy_tag': hex(record[0]),
                      'event_counts': [len(track) for track in tracks], 'events': tracks,
                      'lengths': [read_word(p, S['_seqlength'] + track * 2) for track in range(7)],
                      'bpm': read_word(p, S['_seqbpm']), 'beats': v('seqbeats'), 'denominator': v('seqdenom'),
                      'mode': v('seqmode'), 'levels': list(p.memory[S['_mx'] + 12:S['_mx'] + 19]),
                      'pans': list(p.memory[S['_mx'] + 19:S['_mx'] + 26]),
                      'hihat': list(p.memory[S['_noisepatch']:S['_noisepatch'] + 5]),
                      'waveform': p.memory[S['_param'] + 2 * 26 + 14],
                      'native_patch_sha256': sha256(raw).hexdigest()})
        slots[-1]['metadata_hex'] = metadata.hex()
    assert args.save.read_bytes() == original
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {'source': str(args.save), 'source_sha256': original_hash,
              'source_file_unchanged': True, 'rom': str(args.rom), 'legacy_enabled': True, 'slots': slots}
    args.output.write_text(json.dumps(result, indent=2))
    args.output.with_suffix('.patches.bin').write_bytes(patches)
    print(json.dumps({'source_unchanged': True, 'slots': [dict((key, item[key]) for key in
                     ('slot', 'name', 'legacy_tag', 'event_counts', 'lengths', 'bpm', 'waveform', 'hihat', 'native_patch_sha256'))
                     for item in slots]}, indent=2))
finally:
    p.stop(save=False)

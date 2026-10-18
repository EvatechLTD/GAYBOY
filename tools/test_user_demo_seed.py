"""Verify the shipped demo preserves authored data with release mixer/HH defaults."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from pyboy import PyBoy
from boot_helpers import enter_app
from seq_storage_helpers import read_tracks
from sparse_image import SparseImage

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom', type=Path, default=Path('build/GAYBOY.gb'))
parser.add_argument('--expected', type=Path, default=Path('build/validation/user-demo-original.json'))
parser.add_argument('--output', type=Path, default=Path('build/validation/user-demo-seed.json'))
args = parser.parse_args()
expected = json.loads(args.expected.read_text())
source_hash = sha256(Path(expected['source']).read_bytes()).hexdigest()
assert source_hash == expected['source_sha256']
slots = expected['slots']
# Release defaults intentionally override only mixer levels and HH metallic.
from update_demo_defaults import hihat_offset
native_exports = args.expected.with_suffix('.patches.bin').read_bytes()
for index, item in enumerate(slots):
    meta = bytearray.fromhex(item['metadata_hex']);meta[56:63] = bytes([127] * 7)
    item['metadata_hex'] = meta.hex()
    patch = bytearray(native_exports[index * 450:(index + 1) * 450])
    patch[hihat_offset()] = 0
    item['native_patch_sha256'] = sha256(patch).hexdigest()
factory_checks = []


def factory_probe(player, symbols):
    def probe(_):
        wave = player.memory[symbols['_param'] + 2 * 26 + 14]
        metal = player.memory[symbols['_noisepatch'] + 3]
        assert wave == 6 and metal == 0, (wave, metal)
        factory_checks.append({'waveform': wave, 'hihat_metallic': metal})
    address = symbols['_ui_loading_begin']
    player.hook_register(address >> 16, address & 65535, probe, None)


source = Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
source = source.replace('build/GAYBOY.gb', args.rom.as_posix()).replace('build/GAYBOY.noi', args.rom.with_suffix('.noi').as_posix())
source = source.replace('enter_app(p)', 'enter_app(p,S)').replace('p.set_emulation_speed(0);enter_app',
                        'p.set_emulation_speed(0);factory_probe(p,S);enter_app')
source = source.replace('range(60)', 'range(1800)').replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file=')
exec(source)


def battery():
    data = bytearray()
    for bank in range(4):
        p.memory[0x4000] = bank
        data.extend(p.memory[0xa000:0xc000])
    p.memory[0x4000] = 0
    return bytes(data)


def native_patch():
    text = Path('src/tones.c').read_text().split('static void apply_prepared(void)', 1)[1].split('static void finalize_prepared(void)', 1)[0]
    data = bytearray()
    for expression, size in re.findall(r'ld hl,#([^\n]+)\n\s*\.rept (\d+)', text):
        symbol, _, offset = expression.strip().partition('+')
        address = S[symbol] + (int(offset) if offset else 0)
        data.extend(p.memory[address:address + int(size)])
    data.extend(p.memory[S['_pulsekickpatch']:S['_pulsekickpatch'] + 8])
    assert len(data) == 450
    return bytes(data)


def metadata():
    data = bytearray()
    for symbol, size in (('_seqeventcounts', 14), ('_seqlength', 14), ('_seqdefaultdur', 14),
                         ('_seqdefaultvel', 7), ('_seqgate', 7)):
        data.extend(p.memory[S[symbol]:S[symbol] + size])
    data.extend(p.memory[S['_mx'] + 12:S['_mx'] + 26])
    data.extend(v(name) for name in ('seqmuted', 'seqsolo', 'seqbeats', 'seqdenom', 'seqmode'))
    for symbol in ('_seqbpm', '_drummutemask', '_drumsolomask'):
        data.extend(p.memory[S[symbol]:S[symbol] + 2])
    assert len(data) == 81
    return data.hex()


checked = []


def check(index, stage):
    p.tick(30)
    item = slots[index]
    name = bytes(p.memory[S['_mx'] + 26:S['_mx'] + 43]).split(b'\0')[0].decode('ascii')
    assert name == item['name'], (stage, name)
    assert read_tracks(p, S) == item['events'], stage
    assert metadata() == item['metadata_hex'], stage
    digest = sha256(native_patch()).hexdigest()
    assert digest == item['native_patch_sha256'], (stage, digest, item['native_patch_sha256'])
    assert not p.memory[0xff40] & 0x20, 'Intro window remained enabled over workstation'
    checked.append({'stage': stage, 'slot': item['slot'], 'name': name, 'native_patch_sha256': digest})


try:
    assert v('sparse_enabled') == 1 and v('sparse_patterns') == len(slots)
    image = SparseImage(battery())
    names = [image.pattern_name(ref) for ref in image.library()]
    assert names == [slot['name'] for slot in slots], names
    assert not any('DUST' in name or 'CHIP' in name for name in names)
    assert len(image.songs()) == 1
    check(0, 'fresh-zero-no-companion')
    choose(24)
    press('a')
    assert v('sparse_song') == 0 and v('page') == 18
    check(0, 'load-embedded-song')
    for index in range(len(slots)):
        choose(19)
        p.memory[S['_mx'] + 6] = index
        press('a')
        check(index, 'global-pattern-' + str(index + 1))
    saved = battery()
    p.stop(save=False)
    p = PyBoy(str(args.rom), window='null', sound_emulated=True, cgb=False, ram_file=BytesIO(saved))
    p.set_emulation_speed(0)
    enter_app(p, S)
    check(len(slots) - 1, 'reboot-after-global-load')
    p.stop(save=False)
    p = PyBoy(str(args.rom), window='null', sound_emulated=True, cgb=False, ram_file=BytesIO(bytes([255]) * 32768))
    p.set_emulation_speed(0)
    factory_probe(p, S)
    enter_app(p, S)
    assert v('sparse_enabled') == 1 and v('sparse_patterns') == len(slots)
    check(0, 'fresh-ff-no-companion')
    assert sha256(Path(expected['source']).read_bytes()).hexdigest() == source_hash
    result = {'rom': str(args.rom), 'source_file_unchanged': True, 'source_sha256': source_hash,
              'patterns': names, 'songs': [song['name'] for song in image.songs()],
              'factory_preferences': factory_checks, 'checks': checked,
              'authored_patch_waveform': slots[0]['waveform'], 'authored_patch_hihat': slots[0]['hihat']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print('PASS: fresh zero/FF installs supplied demo without companion; names/events/metadata/native patch match release defaults; song/browser/reboot pass; factory006/off kept separately')
finally:
    p.stop(save=False)

"""B on the live pad opens its editor without restarting a sustaining note."""
from pathlib import Path
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');args=ap.parse_args()
rom=Path(args.rom)
source=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
source=source.replace('build/GAYBOY.gb',str(rom).replace('\\','/')).replace('build/GAYBOY.noi',str(rom.with_suffix('.noi')).replace('\\','/'))
exec(source.replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='))
from seq_storage_helpers import write_tracks, write_word

mx = S['_mx']
calls = []


def hook(name, callback):
    address = S['_' + name]
    p.hook_register(address >> 16, address & 65535, callback, None)


try:
    choose(18)
    tracks = [[] for _ in range(7)]
    tracks[0] = [[0, 61, 100, 128]]
    write_tracks(p, S, tracks)
    for channel in range(7):
        write_word(p, S['_seqlength'] + channel * 2, 256)
    write_word(p, S['_seqbpm'], 120)
    p.memory[mx + 4] = 0
    press('a')
    assert v('seqplaying') and v('seqowned') and v('active')
    p.tick(15)
    for name in ('seq_transport', 'seq_pattern_start', 'seq_pattern_release'):
        hook(name, lambda _, name=name: calls.append(name))
    hook('play', lambda _: calls.append('pulse retrigger') if p.register_file.A == 0 else None)
    hook('seq_off', lambda _: calls.append('pulse release') if p.register_file.A == 0 else None)
    for quantization in (0, 1, 2):
        p.memory[mx + 3] = quantization
        p.memory[mx + 4] = 30 + p.memory[mx + 1]
        position = v('seqposition')
        press('b')
        for _ in range(180):
            if v('page') == 8:
                break
            p.tick(1)
        assert v('page') == 8, ('Live B did not open the editor', quantization)
        assert v('seqplaying') and v('seqowned') and v('active'), 'Live B interrupted the held pulse'
        assert v('seqposition') >= position, 'Live B reset the pattern position'
        assert not calls, (quantization, calls)
        choose(18)
    print('PASS: real B opens the current pattern for all quantizations, preserving transport and held pulse without retrigger/release')
finally:
    p.stop(save=False)

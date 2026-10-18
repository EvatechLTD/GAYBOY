"""Empty grids own their sprites; cursor moves retain VRAM on DMG timing."""
from pathlib import Path
from seq_storage_helpers import write_tracks
env = {}
source = Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('range(60)', 'range(600)')
exec(source.replace('bytes(32768)', 'bytes([165])*32768')
     .replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file='), env)
p, S, v, choose, press = (env[k] for k in ('p', 'S', 'v', 'choose', 'press'))

def hook(name, fn):
    a = S['_' + name]
    p.hook_register(a >> 16, a & 65535, fn, None)

def background():
    return bytes(p.memory[0x8800:0x9800]) + bytes(p.memory[0x9800:0x9A40])

def no_intro_sprites():
    for i in list(range(17)) + list(range(37, 40)):
        assert not p.memory[0xFE00 + i * 4 + 1], ('leftover sprite', i)

try:
    choose(8)
    no_intro_sprites()
    p.screen.image.save('build/grid-hardware-piano.png')
    rebuilds, blanks, stores, unsafe = [], [], [], []
    hook('seq_pixels', lambda _: rebuilds.append('piano'))
    hook('drum_render', lambda _: rebuilds.append('drum'))
    hook('ui_transition_begin', lambda _: blanks.append(p.frame_count))
    # Trace the actual VRAM store instruction, rather than relying on an
    # emulator accepting writes that physical VRAM would discard in mode 3.
    a = S['_ui_vram_copy']
    rom = Path('build/GAYBOY.gb').read_bytes()
    offset = (a >> 16) * 0x4000 + (a & 0x3FFF)
    store = (a & 65535) + rom[offset:offset + 40].index(0x12)
    def at_store(_):
        stores.append(1)
        if p.memory[0xFF41] & 3 == 3: unsafe.append(p._cycles())
    p.hook_register(a >> 16, store, at_store, None)
    for track in (0, 6):
        if track == 6:
            p.button_press('select'); p.tick(5); press('left')
            p.button_release('select'); p.tick(30)
            if v('seqhead'): press('down')
        assert v('seqtrack') == track
        no_intro_sprites()
        before = background()
        rebuilds.clear(); blanks.clear()
        for key in ['down', 'up', 'right', 'left'] * 3:
            press(key)
            assert p.memory[0xFF40] & 1, 'Background blanked on cursor move'
        assert not rebuilds and not blanks, (track, rebuilds, blanks)
        assert background() == before, ('Cursor move changed background', track)
        if track == 0:
            for _ in range(20): press('up')
            assert v('seqtop') > 71 and not blanks, ('Pitch scroll blanked grid', blanks)
    p.screen.image.save('build/grid-hardware-drums.png')
    tracks = [[] for _ in range(7)]
    tracks[6] = [[s, 1 + (s & 1), 100, 1] for s in range(16)]
    write_tracks(p, S, tracks)
    p.button_press('select'); p.tick(5); press('a')
    p.button_release('select'); p.tick(20)
    assert v('seqplaying')
    for _ in range(4):
        press('b')
        press('right')
    assert stores and not unsafe, ('Unsafe VRAM writes', len(stores), unsafe[:5])
    assert not env['word']('mixunderruns'), 'PCM underrun during grid redraw'
    print('PASS: no intro ghosts with dirty SRAM, cursor-only navigation on both grids,', len(stores), 'VRAM writes outside mode 3 during PCM')
finally:
    p.stop(save=False)

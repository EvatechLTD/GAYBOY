"""Check the airborne white shell against the actual DMG sprite/background mask."""
from pathlib import Path
from pyboy import PyBoy

symbols = {line.split()[1]: int(line.split()[2], 16)
           for line in Path('build/GAYBOY.noi').read_text().splitlines()
           if line.startswith('DEF ')}
p = PyBoy('build/GAYBOY.gb', window='null', sound_emulated=True)
p.set_emulation_speed(0)
try:
    for _ in range(1500):
        p.tick(1)
        if p.memory[symbols['_intro_audio_scene']] == 2:
            break
    assert p.memory[symbols['_intro_audio_scene']] == 2
    # Hold the art clock on each pose, allowing banked tile uploads to settle.
    p.memory[0xff07] = 0
    p.tick(90)
    address = symbols['_intro_scene_ticks']
    for pose, (dx, dy) in enumerate(((-46, -17), (-42, -29), (-32, -38), (-20, -40)), 3):
        ticks = (400 + (pose-3)*12 + 3)*4
        p.memory[address] = ticks & 255
        p.memory[address+1] = ticks >> 8
        p.tick(90)
        p.screen.image.save(f'build/train-solid-{pose}.png')
        sx, sy = p.memory[0xff43], p.memory[0xff42]
        sx = sx if sx < 128 else sx-256
        sy = sy if sy < 128 else sy-256
        for y in range(max(84+dy, 26), min(101+dy, 72)):
            for x in range(66+dx, 74+dx):
                assert p.screen.image.getpixel((x-sx, y-sy))[:3] == (255, 255, 255), (pose, x, y)
finally:
    p.stop(save=False)
print('PASS: white shell stays opaque across four airborne window-overlap poses')

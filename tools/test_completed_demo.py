"""Completed demo installs only into a blank battery; existing music survives."""
from io import BytesIO
from pathlib import Path
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
p.stop(save=False)
source=Path('assets/demo/KILLING.srm').read_bytes()

def check(battery,expected):
    global p
    size=131072 if rom.read_bytes()[0x149]==4 else 32768
    p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(battery.ljust(size,b'\0')))
    p.set_emulation_speed(0);enter_app(p,symbols)
    for i in range(5):
        at=8192+i*2048;base=0xa000+(i%4)*2048;bank=1+i//4
        assert bytes(p.memory[bank,base+480:base+1792])==expected[at+480:at+1792],('notes/song',i)
        assert bytes(p.memory[bank,base+16:base+32])==expected[at+16:at+32],('name',i)
    p.stop(save=False)

try:
    check(bytes(32768),source)
    changed=bytearray(source);changed[8192+768]=7;changed[8192+2048+768]=11
    check(changed,changed)
    print('PASS completed five-pad/nine-clip demo on blank boot, existing battery never replaced')
finally:p.stop(save=False)

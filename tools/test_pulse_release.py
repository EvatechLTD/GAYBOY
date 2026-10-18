"""Compiled DMG release/retrigger/ownership checks; SameBoy approves audio."""
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app

s={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)

def send(*messages):
    w=p.memory[s['_wr']]
    for message in messages:
        for byte in message:
            p.memory[s['_rx']+w]=byte;w=(w+1)&255
    p.memory[s['_wr']]=w
    for _ in range(30):
        p.tick(1)
        if p.memory[s['_rd']]==w:break
    assert p.memory[s['_rd']]==w,'MIDI stalled'
    p.tick(1)

try:
    enter_app(p)
    send((0xb0,103,127))
    for c in range(2):
        for index,value in {0:2,1:10,2:0,3:1,4:0,5:0,6:0,8:0,9:0,21:3,22:0,23:0}.items():
            p.memory[s['_param']+c*26+index]=value
    cases=0
    for direction in (0,1):
        for period in (0,1,7):
            for note in (36,60,84):
                for velocity in (1,90,127):
                    for c in range(2):
                        p.memory[s['_param']+c*26+2]=direction
                        p.memory[s['_param']+c*26+3]=period
                    send((0x90,note,velocity),(0x91,note,velocity))
                    other=p.memory[0xff17]
                    send((0x80,note,0))
                    assert p.memory[0xff12]==8
                    assert p.memory[0xff17]==other,'P1 release changed P2 envelope'
                    assert not p.memory[s['_active']] and p.memory[s['_active']+1]
                    send((0x90,note+1,127),(0x81,note,0))
                    expected=(10<<4)|(direction<<3)|period
                    assert p.memory[0xff12]==expected and p.memory[0xff17]==8
                    p.tick(3)
                    assert p.memory[s['_active']],'Old release silenced retrigger'
                    send((0x80,note+1,0))
                    cases+=1
    # Releasing an older key must leave the newer owner sounding.
    send((0x90,60,127),(0x90,64,127),(0x80,60,0))
    assert p.memory[s['_held']]==64 and p.memory[s['_active']]
    send((0x80,64,0))
    assert p.memory[0xff12]==8 and not p.memory[s['_active']]
    # A falling patch at zero initial volume must not switch its DAC off.
    p.memory[s['_param']+1]=0;p.memory[s['_param']+2]=0
    send((0x90,60,127))
    assert p.memory[0xff12]==8
    # Explicit DAC OFF and panic remain real hardware shutdowns.
    send((0xb0,63,127))
    assert p.memory[0xff12]==0
    send((0xb0,103,127))
    assert p.memory[0xff12]==p.memory[0xff17]==0
    print(f'PASS: {cases} two-pulse release/retrigger cases; ownership, zero volume, DAC OFF and panic')
finally:
    p.stop(save=False)

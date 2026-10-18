from boot_helpers import enter_app
"""Execute the actual GB span routine against a pixel reference in emulation."""
from pathlib import Path
from io import BytesIO
import random
from pyboy import PyBoy
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',cgb=False,sound_emulated=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0);enter_app(p)
# A private emulator-only return loop makes one near routine independently
# callable. ROM files and the running GUI emulator are never changed.
p.memory[0,0x3ff0]=0x18;p.memory[0,0x3ff1]=0xfe
p.memory[0xffff]=0;p.memory[0xff07]=0;p.memory[0xff0f]=0
p.memory[0x0000]=0x0a;p.memory[0x2000]=13;p.memory[0x3000]=0;p.memory[0xff90]=13
rng=random.Random(13004)
for case in range(100):
 base=(0xba00,0xbb40,0xbd40)[case%3]
 original=bytearray(rng.randrange(256) for _ in range(320));expected=original.copy()
 left=rng.randrange(161);right=rng.randrange(left,161);y=rng.randrange(8);color=rng.randrange(4)
 for x in range(left,right):
  at=(x>>3)*16+y*2;mask=128>>(x&7)
  expected[at]=(expected[at]&~mask)|(mask if color&1 else 0)
  expected[at+1]=(expected[at+1]&~mask)|(mask if color&2 else 0)
 p.memory[base:base+320]=original
 sp=0xdf00;p.memory[sp:sp+5]=[0xf0,0x3f,left,right,color]
 p.register_file.SP=sp;p.register_file.D=base>>8;p.register_file.E=base&255;p.register_file.A=y
 p.register_file.PC=S['_roll_span']&65535;p.tick(1)
 assert p.register_file.PC in (0x3ff0,0x3ff1),(case,hex(p.register_file.PC))
 assert p.register_file.SP==sp+5,('callee stack cleanup',case,hex(p.register_file.SP))
 assert bytes(p.memory[base:base+320])==expected,(case,hex(base),y,left,right,color)
p.stop(save=False)
print('PASS: 100 actual-CPU span calls match pixel reference across offsets, bounds, colors and SRAM pages')

"""Execute the naked stride-four lookup and validate its ABI and CPU budget."""
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app
import random,json
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',cgb=False,sound_emulated=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0);enter_app(p)
p.memory[0,0x3ff0]=0;p.memory[0,0x3ff1]=0x18;p.memory[0,0x3ff2]=0xfe
p.memory[0xffff]=0;p.memory[0xff07]=0;p.memory[0xff0f]=0;p.memory[0]=0x0a;p.memory[0x4000]=0;p.memory[0x2000]=14;p.memory[0x3000]=0;p.memory[0xff90]=14
end=[None];p.hook_register(0,0x3ff0,lambda _:end.__setitem__(0,p._cycles()),None)
rng=random.Random(84512);results=[]
try:
 for case in range(300):
  n=256 if case<257 else rng.randrange(257);step=case if case<256 else rng.randrange(256)
  events=[[i,61,100,1] for i in range(n)] if case<256 else [[rng.randrange(256),0 if rng.randrange(3)==0 else 61,100,1] for _ in range(n)]
  if case==256:events=[[0,61,100,1] for _ in range(256)];step=255
  expected=next((n-i for i,e in enumerate(events) if e[0]==step and e[1]),0)
  p.memory[0xb000:0xb000+n*4]=sum(events,[])
  sp=0xdf00;p.memory[sp:sp+3]=[0xf0,0x3f,step];p.register_file.SP=sp;p.register_file.D=0xb0;p.register_file.E=0;p.register_file.B=n>>8;p.register_file.C=n&255
  p.register_file.PC=S['_storage_scan_step']&65535;end[0]=None;begin=p._cycles();p.tick(1)
  actual=p.register_file.B<<8|p.register_file.C
  assert actual==expected,(case,n,step,expected,actual)
  assert p.register_file.SP==sp+3,('callee cleanup',case,hex(p.register_file.SP))
  assert end[0] is not None
  if case==256:results.append({'records':n,'all_miss_cycles':end[0]-begin,'cycles_per_record':(end[0]-begin)/n})
 print('PASS:300actualCPUlookupcases,all256steps,placeholdernotes,emptyspans,remaining-countreturn,callee-stackcleanup',json.dumps(results))
finally:p.stop(save=False)


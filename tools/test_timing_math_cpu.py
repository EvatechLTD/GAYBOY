"""Execute production timing helpers on the emulated CPU against Python integers."""
from pathlib import Path
from io import BytesIO
import argparse,json,random,itertools,hashlib
from pyboy import PyBoy
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output',default='build/timing-math-cpu.json');ap.add_argument('--lookup-only',action='store_true');args=ap.parse_args()
S={l.split()[1]:int(l.split()[2],16) for l in Path(args.rom).with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(args.rom,window='null',sound_emulated=False,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
result={};cycles=[]
# This isolated math harness never enters the application or enables its IRQs.
# Each production function returns to a trap followed by an unhooked JR loop.
p.memory[0xffff]=0;p.memory[0xff0f]=0;p.memory[0xff50]=1;p.memory[0xff40]=0
p.memory[0xc000:0xc004]=[0x18,0x00,0x18,0xfe]
def returned(_):
 r=p.register_file;result.update(value32=r.C|(r.B<<8)|(r.E<<16)|(r.D<<24),value16=r.C|(r.B<<8),end=p._cycles())
p.hook_register(0,0xc000,returned,None)
def call(name,arguments=()):
 addr=S['_'+name];bank=addr>>16;p.memory[0x2000]=bank&255;p.memory[0x3000]=bank>>8
 if '__current_bank' in S:p.memory[S['__current_bank']]=bank
 stack=0xdfe0;frame=[0,0xc0,0,0,0,0]+list(arguments)
 p.memory[stack:stack+len(frame)]=frame;p.register_file.SP=stack;p.register_file.PC=addr&65535
 result.clear();start=p._cycles();p.tick(1)
 assert result,('Function did not return',name,arguments,hex(p.register_file.PC))
 cycles.append((name,result['end']-start));return result.copy()
try:
 lookups=[]
 for bpm in range(30,301):
  at=S['_seqbpm'];p.memory[at]=bpm&255;p.memory[at+1]=bpm>>8
  got=call('drum_step_samples')['value16'];expected=171900//bpm
  assert got==expected,('drum_step_samples',bpm,got,expected)
  lookups.append((bpm,got))
 gates=[]
 if not args.lookup_only:
  assert '_seq_gate_length' in S,'Requires production gate helper candidate'
  edges=list(itertools.product((0,1,2,51,85,127,128,255,256,511,512),(1,2,3,127,128,254,255,256),(0,1,2,49,50,51,99,100)))
  rng=random.Random(0x504b4742);vectors=edges+[(rng.randrange(513),rng.randrange(1,257),rng.randrange(101)) for _ in range(2048)]
  for units,duration,gate in vectors:
   got=call('seq_gate_length',(units&255,units>>8,duration&255,gate))['value32'];expected=max(1,units*duration*gate//100)
   assert got==expected,('seq_gate_length',units,duration,gate,got,expected)
   gates.append((units,duration,gate,got))
 report={'rom_sha256':hashlib.sha256(Path(args.rom).read_bytes()).hexdigest(),'model':'DMG isolated production machine-code execution','drum_tempo_lookups':len(lookups),'gate_boundary_vectors':len(edges) if not args.lookup_only else 0,'gate_random_vectors':2048 if not args.lookup_only else 0,'gate_cases':len(gates),'max_cycles':{n:max(c for name,c in cycles if name==n) for n in set(n for n,_ in cycles)},'passes':True};Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:p.stop(save=False)

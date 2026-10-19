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
p.memory[0x0000]=0x0a;p.memory[0x4000]=0;p.memory[0xffff]=0;p.memory[0xff0f]=0;p.memory[0xff50]=1;p.memory[0xff40]=0
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
 deadlines=0
 if not args.lookup_only:
  def store(name,value,size=1,index=0):
   at=S['_'+name]+index*size;p.memory[at:at+size]=list(int(value).to_bytes(size,'little'))
  def deadline_case(bpm,clock,gate_values=None,gate_lengths=None,noise=(0,0),kick=0,mono=0,stale=False):
   global deadlines
   store('seqbpm',bpm,2);store('seqcachedbpm',0 if stale else bpm,2);store('seqstepunits',15360//bpm,2);store('seqclock',clock,2);store('monomode',mono)
   gate_values=gate_values or [100]*7;gate_lengths=gate_lengths or [0]*7
   for c in range(7):store('seqgate',gate_values[c],1,c);store('seqgateleft',gate_lengths[c],4,c)
   store('drumnoiseowned',int(any(noise)))
   for c in range(2):store('noiseleft',noise[c],4,c)
   store('pulsekickleft',kick,4)
   step=(15360-clock+bpm-1)//bpm;expected=step
   for c,length in enumerate(gate_lengths):
    if length and length<expected:
     if c<2 and not mono and gate_values[c]==100 and length+1==step:continue
     expected=length
   for length in noise+(kick,):
    if length and length<expected:expected=length
   call('seq_next_deadline');at=S['_seqdeadline'];got=p.memory[at]|p.memory[at+1]<<8
   assert got==max(1,expected),('deadline',bpm,clock,gate_values,gate_lengths,noise,kick,mono,stale,got,expected)
   deadlines+=1
  for bpm in range(30,301):
   for clock in (0,1,bpm-1,bpm,bpm+1,15359):deadline_case(bpm,clock)
  for _ in range(2048):
   bpm=rng.randrange(30,301);clock=rng.randrange(15360);step=(15360-clock+bpm-1)//bpm
   lengths=[rng.choice((0,1,max(1,step-1),step,step+1,65536)) for _ in range(7)]
   values=[rng.choice((0,1,80,99,100)) for _ in range(7)]
   deadline_case(bpm,clock,values,lengths,noise=(rng.randrange(513),rng.randrange(513)),kick=rng.randrange(257),mono=rng.randrange(2),stale=bool(rng.randrange(2)))
 report={'scheduler_deadline_cases':deadlines,'rom_sha256':hashlib.sha256(Path(args.rom).read_bytes()).hexdigest(),'model':'DMG isolated production machine-code execution','drum_tempo_lookups':len(lookups),'gate_boundary_vectors':len(edges) if not args.lookup_only else 0,'gate_random_vectors':2048 if not args.lookup_only else 0,'gate_cases':len(gates),'max_cycles':{n:max(c for name,c in cycles if name==n) for n in set(n for n,_ in cycles)},'passes':True};Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:p.stop(save=False)

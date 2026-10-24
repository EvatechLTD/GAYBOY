"""Timer drums retain every hit, stop cleanly, preserve data, and fall back safely."""
from pathlib import Path
from io import BytesIO
import ast
import pyboy
exec(Path('tools/test_live_note_plot.py').read_text().split('\ntry:')[0])
S=symbols;noise_hits=[];kick_hits=[]
code=rom.read_bytes();tree=ast.parse((Path(pyboy.__file__).parent/'core/opcodes.py').read_text())
lengths=next(ast.literal_eval(n.value.args[1]) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPCODE_LENGTHS' for t in n.targets))
def percussion(kind):
 if p.register_file.A&128 and p.memory[0xff21 if kind=='noise' else 0xff12]&0xf0:
  (noise_hits if kind=='noise' else kick_hits).append({'cycle':p._cycles()+12,'pitch':p.memory[0xff22] if kind=='noise' else p.memory[0xff13]})
a=S['_drum_irq_emit'];bank=a>>16;pc=a&65535
end=min(v&65535 for k,v in S.items() if k.startswith('_') and v>>16==bank and v&65535>pc)
while pc<end:
 at=bank*16384+pc-16384;op=code[at];size=2 if op==0xcb else lengths[op]
 if op==0xe0 and code[at+1] in (0x14,0x23):p.hook_register(bank,pc,percussion,'noise' if code[at+1]==0x23 else 'kick')
 pc+=size
tracks=[[],[[0,n,127,16] for n in (61,65,68)],[[s,37+(s//16%3)*3,127,16] for s in range(0,128,16)],[],[],[],
 [[s,13,127,1] for s in (0,6,10)]+[[s,12,127,1] for s in (4,12)]+[[s,11,127,1] for s in range(16)]]
counts=[len(t) for t in tracks];total=sum(counts);event_end=0xa300+total*4

def setup_fixture():
 enter_app(p,S);offset=0
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',32 if c==1 else 128 if c==2 else 16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 for i in range(128):put('evalpatch',0,i)
 for i in range(24):put('coarsepitch',0,i)
 for i in range(3):put('evalpatch',127,64+i)
 for i,v in ((0,1),(2,4),(4,1),(13,1)):put('evalpatch',v,16+i)
 put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0;put('experimental_mode',1);put('mod_bypass',0);put('waveengine',0)
 put('mx',255,2);word('seqbpm',120);word('seqglobalbpm',120)
 put('eval_moddirty',1);put('seqirqdirty',1);word('pattern_generation',1);put('pattern_dirty',1)
 put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127);put('dirty',1);p.tick(120)

def transport():
 key('select',True);key('start',True);key('start',False);key('select',False)
def u16(n):return get(n)+256*get(n,1)
try:
 setup_fixture();fixture=BytesIO();p.save_state(fixture)
 events=bytes(p.memory[1,0xa300:event_end]);kits=bytes(p.memory[2,0xa800:0xad00])
 protected=[(0xa000,0xa820),(0xaa00,0xb200),(0xb400,0xb810),(0xbf80,0xc000)]
 # Seed unused/private storage without disturbing the loaded fixture.
 for start,end in protected:
  if start!=0xbf80:p.memory[3,start:end]=[(i*37+11)&255 for i in range(end-start)]
 saved=[bytes(p.memory[3,i] for i in range(start,end)) for start,end in protected]
 transport();p.tick(600)
 assert get('drum_irq_active') and get('smooth_playback_active')
 assert len(noise_hits)>=80 and len(kick_hits)>=15,(len(noise_hits),len(kick_hits))
 # The shared hat/snare noise pitch matches the original mixed patches.
 assert [h['pitch'] for h in noise_hits[:32]]==([1,1,1,1,34,1,1,1,1,1,1,1,34,1,1,1]*2)
 gaps=[(y['cycle']-x['cycle'])/4194.304 for x,y in zip(noise_hits,noise_hits[1:])]
 assert max(abs(g-125) for g in gaps)<1,gaps[:20]
 assert bytes(p.memory[1,0xa300:event_end])==events and bytes(p.memory[2,0xa800:0xad00])==kits
 assert all(bytes(p.memory[3,i] for i in range(start,end))==data for (start,end),data in zip(protected,saved)), 'Prepared drums overwrote persistent storage/clipboard'
 transport();assert not get('seqplaying') and not get('drum_irq_active')
 before=len(noise_hits);p.tick(120);assert len(noise_hits)==before
 transport();p.tick(120);assert get('drum_irq_active')
 print('PASS complete hat/kick rhythm, original noise mix, timing, unchanged notes/kits, stop and restart')
 # An unrelated edit must leave independent prepared percussion running.
 word('pattern_generation',u16('pattern_generation')+1);p.tick(5)
 assert get('drum_irq_active') and get('seqplaying')
 print('PASS unrelated generation keeps timer-owned drums running')
 for kind in ('pcm','shared_p1','modulated'):
  fixture.seek(0);p.load_state(fixture)
  if kind=='pcm':p.memory[1,0xa300+sum(counts[:6])*4+1]=1
  elif kind=='shared_p1':
   data=bytes(p.memory[1,0xa300:event_end]);p.memory[1,0xa304:event_end+4]=data;p.memory[1,0xa300:0xa304]=[0,49,110,4]
   word('seqeventcounts',1,0)
   for c in range(1,7):word('seqeventoffsets',sum(counts[:c])+1,c*2)
  else:put('evalpatch',128,5*16+10)
  word('pattern_generation',u16('pattern_generation')+1);put('eval_moddirty',1);put('seqirqdirty',1);put('pattern_dirty',1)
  transport();p.tick(120)
  assert get('seqplaying') and not get('drum_irq_active'),kind
  if kind=='pcm':assert get('waveengine')==3
  transport();assert not get('seqplaying')
  print('PASS unsupported setup retains normal playback:',kind)
finally:p.stop(save=False)

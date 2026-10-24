"""Actual APU onset probes across precompiled song patch changes and loop wraps."""
from pathlib import Path
import ast,json,pyboy,sys
use_arp='--song-arp' in sys.argv
use_lfo='--song-lfo' in sys.argv
bpm=120
demo_path=None
if '--write-demo' in sys.argv:
 at=sys.argv.index('--write-demo');demo_path=Path(sys.argv[at+1]);del sys.argv[at:at+2]
if '--song-bpm' in sys.argv:
 at=sys.argv.index('--song-bpm');bpm=int(sys.argv[at+1]);del sys.argv[at:at+2]
for flag in ('--song-arp','--song-lfo'):
 if flag in sys.argv:sys.argv.remove(flag)
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
code=rom.read_bytes();tree=ast.parse((Path(pyboy.__file__).parent/'core/opcodes.py').read_text())
lengths=next(ast.literal_eval(n.value.args[1]) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPCODE_LENGTHS' for t in n.targets))
hits={n:[] for n in ('noise','kick','p1','p2','wave')};graphics=[];cost=[];entry=[];returns=set();runtime=S['_song_runtime']
def attack(kind):
 reg={'noise':0xff21,'kick':0xff12,'p1':0xff12,'p2':0xff17,'wave':0xff1c}[kind]
 if p.register_file.A&128 and p.memory[reg]& (0x60 if kind=='wave' else 0xf0):
  hits[kind].append({'cycle':p._cycles()+12,'scene':p.memory[runtime+152],'position':int.from_bytes(bytes(p.memory[runtime+28:runtime+32]),'little')})
wave_shadow=[0]*16
def programmed(_):
 reg=p.register_file.C
 if 0x30<=reg<=0x3f:wave_shadow[reg-0x30]=p.register_file.A
 if reg not in (0x14,0x19,0x1e,0x23):return
 kind={0x14:'kick',0x19:'p2',0x1e:'wave',0x23:'noise'}[reg]
 volume=p.memory[{'kick':0xff12,'p2':0xff17,'wave':0xff1c,'noise':0xff21}[kind]]
 if p.register_file.A&128 and volume&(0x60 if kind=='wave' else 0xf0):
  q=0xa500+p.memory[S['_song_qread']]*192
  hits[kind].append({'cycle':p._cycles()+8,'scene':p.memory[q+3],'position':int.from_bytes(bytes(p.memory[q+4:q+8]),'little'),'freq':p.memory[0xff22] if kind=='noise' else p.memory[{'kick':0xff13,'p2':0xff18,'wave':0xff1d}[kind]]|((p.register_file.A&7)<<8),'env':p.memory[{'kick':0xff12,'p2':0xff17,'wave':0xff1c,'noise':0xff21}[kind]],'duty':p.memory[0xff16]>>6 if kind=='p2' else 0,'pan':p.memory[0xff25]&({'kick':0x11,'p2':0x22,'wave':0x44,'noise':0x88}[kind]),'wave':wave_shadow[:] if kind=='wave' else []})
a=S['_song_program'];bank=a>>16;pc=a&65535;end=min(v&65535 for k,v in S.items() if k.startswith('_') and v>>16==bank and v&65535>pc)
while pc<end:
 at=pc if not bank else bank*16384+pc-16384;op=code[at];size=2 if op==0xcb else lengths[op]
 if op==0xe2:p.hook_register(bank,pc,programmed,None)
 pc+=size
for fn in ('ui_render','ui_flush','ui_upload_tile','ui_upload_map'):
 a=S['_'+fn];p.hook_register(a>>16,a&65535,lambda n:graphics.append((n,p._cycles())),fn)
def done(_):
 if entry and p.register_file.SP==entry[-1][0]:
  _,start=entry.pop();cost.append(p._cycles()-start)
def begin(_):
 sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;b=0 if ret<0x4000 else p.memory[S['__current_bank']]
 if (b,ret) not in returns:returns.add((b,ret));p.hook_register(b,ret,done,None)
 entry.append((sp+2,p._cycles()))
a=S['_song_audio_commit'];p.hook_register(a>>16,a&65535,begin,None)

try:
 enter_app(p,S);put('sticky_start',1);put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0;put('experimental_mode',1);put('waveengine',0)
 tracks=[[],[[0,61,127,16],[16,65,127,16]],[[0,37,127,32]],[],[],[],[[s,13,127,1] for s in (0,6,10)]+[[s,12,127,1] for s in (4,12)]+[[s,11,127,1] for s in range(16)]]
 if use_arp:tracks[1]=[[s,n,127,16] for s in (0,16) for n in (61,65,68)]
 offset=0
 for c,t in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(t),c*2);word('seqlength',32 if c in (1,2) else 16,c*2)
  for e in t:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 for i in range(128):put('evalpatch',0,i)
 for i in range(24):put('coarsepitch',0,i)
 for i in range(3):put('evalpatch',127,64+i)
 if use_arp:
  for at,v in ((16,1),(18,3),(20,1)):put('evalpatch',v,at)
 if use_lfo:
  for c in (1,2):put('evalpatch',1,c*16+8);put('evalpatch',64,c*16+9);put('coarsepitch',12,c*3+1);put('coarsepitch',1,c*3+2)
  for at,v in ((4,0),(6,3),(7,1),(8,0),(9,1)):put('globalmod',v,at)
 word('seqbpm',bpm);word('seqglobalbpm',bpm);word('pattern_generation',1);put('pattern_dirty',1);put('eval_moddirty',1);put('seqirqdirty',1);p.tick(180)
 base=bytes(p.memory[1,0xa000:0xa800])
 for slot in (1,2):
  at=0xa000+slot*2048;p.memory[1,at:at+2048]=base
  p.memory[1,at+16:at+32]=list(('PATCH '+str(slot+1)).ljust(16).encode())
  p.memory[1,at+160]=slot%3;p.memory[1,at+161]=15-slot*2;p.memory[1,at+163]=slot
  p.memory[1,at+206]=slot*2;p.memory[1,at+207]=1+slot%2;p.memory[1,at+280]=slot;p.memory[1,at+297]=24+slot*3;p.memory[1,at+96]=1 if slot==1 else 2;p.memory[1,at+97]=2 if slot==1 else 1
  eventbase=at+768
  event_index=0
  for channel,events in enumerate(tracks):
   for e in events:
    if channel<3:p.memory[1,eventbase+event_index*4+1]=e[1]+slot*(2 if channel==2 else 3)
    event_index+=1
 choose_song();tap('b');tap('right');tap('right');tap('down');tap('b');tap('right');tap('right');tap('down');tap('b')
 assert clips()==[(0,32,0),(32,32,1),(64,32,2)],clips()
 if demo_path:
  demo_path.parent.mkdir(parents=True,exist_ok=True)
  demo_path.write_bytes(b''.join(bytes(p.memory[bank,0xa000:0xbfff])+bytes([p.memory[bank,0xbfff]]) for bank in range(4)))
 protected=[bytes(p.memory[1+slot//4,0xa000+(slot%4)*2048:0xa000+(slot%4)*2048+480])+bytes(p.memory[1+slot//4,0xa000+(slot%4)*2048+768:0xa000+(slot%4)*2048+1792]) for slot in range(5)]
 bank3=bytes(p.memory[3,0xa000:0xbfff])+bytes([p.memory[3,0xbfff]])
 key('select',True);key('start',True);key('start',False);key('select',False)
 assert get('song_playing') and get('smooth_playback_active'),('start failed',get('song_view',15),clips())
 graphics.clear();p.tick(5400)
 assert not graphics,graphics[:5]
 assert get('song_playing')
 for slot,before in enumerate(protected):
  base=0xa000+(slot%4)*2048;bank=1+slot//4
  assert bytes(p.memory[bank,base:base+480])+bytes(p.memory[bank,base+768:base+1792])==before,('Resident notes/tones corrupted',slot)
 assert bytes(p.memory[3,0xa000:0xbfff])+bytes([p.memory[3,0xbfff]])==bank3,'Bank3 presets/clipboards/root modified'
 assert get('song_underruns')+256*get('song_underruns',1)==0,'Prepared register queue underrun'
 out={}
 for kind,h in hits.items():
  gaps=[(b['cycle']-a['cycle'])/4194.304 for a,b in zip(h,h[1:])]
  nominal=15000/bpm if kind in ('noise','kick') else ((7500 if use_arp else 240000)/bpm) if kind=='p2' else 480000/bpm
  out[kind]={'hits':len(h),'max_grid_error_ms':max((abs(g-round(g/nominal)*nominal) for g in gaps),default=0),'min_gap':min(gaps,default=0),'max_gap':max(gaps,default=0),'scenes':sorted(set(a['scene'] for a in h))}
 print('Max song IRQ commit ms',max(cost,default=0)/4194.304);print(json.dumps(out,indent=2));Path('build/thong-audio'+('-arp' if use_arp else '')+('-lfo' if use_lfo else '')+('' if bpm==120 else '-'+str(bpm))+'.json').write_text(json.dumps({'summary':out,'hits':hits,'max_irq_commit_ms':max(cost,default=0)/4194.304,'frames':5400,'bpm':bpm,'rom':str(rom),'underruns':get('song_underruns')+256*get('song_underruns',1)},indent=2))
 assert out['noise']['hits']>450 and out['noise']['max_grid_error_ms']<1.3,out['noise']
 assert out['noise']['max_gap']<15000/bpm+1.3,out['noise']
 assert out['noise']['scenes']==[0,1,2],out['noise']
 assert out['p2']['hits']>25 and out['wave']['hits']>12
 assert max(out[k]['max_grid_error_ms'] for k in ('noise','kick','p2','wave'))<1.3,out
 for scene in (1,2):
  pulse=[h for h in hits['p2'] if h['scene']==scene]
  wave=[h for h in hits['wave'] if h['scene']==scene]
  assert pulse and all(h['duty']==scene%3 and h['env']==((15-scene*2)<<4)|scene and h['pan']==(2 if scene==1 else 32) for h in pulse),(scene,pulse[:2])
  assert wave and all(h['pan']==(64 if scene==1 else 4) for h in wave),(scene,wave[:2])
  assert any(h['scene']==scene and h['position']%32==0 and h['freq']==(scene<<4)|1 for h in hits['noise']),scene
 assert len({tuple(h['wave']) for h in hits['wave']})>=3,'Wave-shape patch changes did not reach APU'

 key('select',True);key('start',True);key('start',False);key('select',False)
 assert not get('song_playing') and not get('seqplaying') and not get('smooth_playback_active')
 assert get('wavepending')==1,'Normal waveform cache was not invalidated after direct song writes'
 print('PASS actual patch registers/pan/waves, blank song playback, three prepared states, all note timing, gap-free drums, looping and stop/restore')
finally:p.stop(save=False)

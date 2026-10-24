"""Matched audio-register and UI latency probes with the display running."""
from pathlib import Path
from io import BytesIO
import sys,json,statistics
verify='--verify' in sys.argv
if verify:sys.argv.remove('--verify')
lfo='--lfo' in sys.argv
if lfo:sys.argv.remove('--lfo')
arp_div=4
if '--arp-div' in sys.argv:
 at=sys.argv.index('--arp-div');arp_div=int(sys.argv[at+1]);del sys.argv[at:at+2]
bpm=120
if '--bpm' in sys.argv:
 at=sys.argv.index('--bpm');bpm=int(sys.argv[at+1]);del sys.argv[at:at+2]
start_offset=0
if '--start-offset' in sys.argv:
 at=sys.argv.index('--start-offset');start_offset=int(sys.argv[at+1]);del sys.argv[at:at+2]
smooth='--smooth' in sys.argv
if smooth:sys.argv.remove('--smooth')
exec(Path('tools/test_prepared_drums.py').read_text().split('\ntry:\n')[0])
from arp_probe_helpers import hook_attacks
# Frozen builds keep their matching static-symbol offsets beside the ROM.
objpath=rom.with_suffix('.drum.sym');objpath=objpath if objpath.exists() else Path('build/objects/drum.sym')
obj={l.split()[1]:(l.split()[0],int(l.split()[2],16)) for l in objpath.read_text().splitlines() if len(l.split())==4 and l.split()[0].isdigit() and l.split()[2]!='********'}
area,offset=obj['_drum_fire'];base=(S['_drum_fire']&65535)-offset;bank=S['_drum_fire']>>16
for fn,reg,kind in [('_drum_noise',0x23,'noise'),('_kick_start',0x14,'kick')]:
 pc=base+obj[fn][1];end=base+min(v for k,(a,v) in obj.items() if a==area and v>obj[fn][1])
 while pc<end:
  at=bank*16384+pc-16384;op=code[at];size=2 if op==0xcb else lengths[op]
  if op==0xe0 and code[at+1]==reg:p.hook_register(bank,pc,percussion,kind)
  pc+=size
registry={};notes=[[],[],[]];graphics={n:0 for n in ['ui_render','ui_flush','ui_upload_map','ui_upload_tile']}
def register(b,a,f,c):
 site=b,a
 if site not in registry:
  registry[site]=[];p.hook_register(b,a,lambda k:[fn(ctx) for fn,ctx in tuple(registry[k])],site)
 registry[site].append((f,c))
for c in (1,2):hook_attacks(p,rom,S,c,lambda cy,c=c:notes[c].append(cy),include_editbuffer=True,register_hook=register)
for n in graphics:
 a=S['_'+n];register(a>>16,a&65535,lambda n:graphics.__setitem__(n,graphics[n]+1),n)
profiling=False;irq_stack=[];irq_stats={};irq_returns=set()
def irq_return(_):
 sp=p.register_file.SP
 while irq_stack and irq_stack[-1][1]==sp:
  name,_,start,children=irq_stack.pop();cycles=p._cycles()-start
  row=irq_stats.setdefault(name,[0,0,0,0]);row[0]+=1;row[1]+=cycles;row[2]=max(row[2],cycles);row[3]+=cycles-children
  if irq_stack:irq_stack[-1][3]+=cycles
def irq_enter(name):
 if not profiling:return
 sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;b=0 if ret<0x4000 else p.memory[S['__current_bank']]
 if (b,ret) not in irq_returns:irq_returns.add((b,ret));register(b,ret,irq_return,None)
 irq_stack.append([name,sp+(4 if name=='editbuffer_irq_event' else 2),p._cycles(),0])
for n in ['engine_timer','drum_irq_tick','arp_irq_due','editirq_commit','editbuffer_irq_event','ui_input','ui_render','ui_flush','seq_frame','seq_irq_prepare','editbuffer_service','drum_irq_service','drum_irq_configure','service_frame']:
 if '_'+n in S:
  a=S['_'+n];register(a>>16,a&65535,irq_enter,n)
acks=[]
def key(n,down):
 mask={'a':16,'b':32,'start':128,'select':64,'right':1,'left':2,'up':4,'down':8}[n]
 start=p._cycles();(p.button_press if down else p.button_release)(n)
 for _ in range(1800):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:
   acks.append((p._cycles()-start)/4194.304);return
 raise AssertionError(('Input timeout',n,down))
def tap(n):key(n,True);key(n,False)
def transport():
 key('select',True);tap('start' if smooth else 'a');key('select',False)
def stats(hits,nominal=125):
 gaps=[(y['cycle']-x['cycle'])/4194.304 for x,y in zip(hits,hits[1:])]
 errors=[abs(g-round(g/nominal)*nominal) for g in gaps]
 return {'hits':len(hits),'max_gap_ms':max(gaps,default=0),'max_grid_error_ms':max(errors,default=0),'p95_grid_error_ms':sorted(errors)[int(.95*(len(errors)-1))] if errors else 0}
try:
 setup_fixture();word('seqbpm',bpm);word('seqglobalbpm',bpm);put('evalpatch',arp_div,18);put('seqirqdirty',1)
 if lfo:
  for c in (1,2):
   put('evalpatch',1,c*16+8);put('evalpatch',64,c*16+9);put('coarsepitch',0,c*3);put('coarsepitch',12,c*3+1);put('coarsepitch',1,c*3+2)
  for i,v in [(4,0),(6,3),(7,1),(8,0),(9,1)]:put('globalmod',v,i)
  put('eval_moddirty',1);put('seqirqdirty',1)
 put('sticky_start',1);fixture=BytesIO();p.save_state(fixture);reports={}
 for phase in (['idle'] if smooth else ['idle','navigation','menu','cells','paint','multiselect','group_move']):
  fixture.seek(0);p.load_state(fixture)
  put('page',8);put('seqtrack',2);put('selected',2);put('seqhead',0);put('seqfocus',0);put('seqcursor',4,2);put('seqpitch',72,2);put('seqtop',79,2);put('seqviewinitialized',127);put('dirty',1);p.tick(90)
  if phase=='group_move':
   put('seqcursor',0,2);put('seqpitch',36,2);put('seqtop',50,2);put('seqgrouptrack',2);put('seqgroupx0',0);put('seqgroupx1',112);put('seqgroupy0',36);put('seqgroupy1',42);put('dirty',1);p.tick(30)
  p.tick(start_offset);transport();p.tick(240)
  assert get('seqplaying') and bool(get('smooth_playback_active'))==smooth
  noise_hits.clear();kick_hits.clear();notes=[[],[],[]];acks.clear();graphics={n:0 for n in graphics}
  profiling=True;irq_stack=[];irq_stats={}
  before_generation=get('pattern_generation')+256*get('pattern_generation',1);start=p._cycles()
  if phase in ('paint','multiselect','group_move'):key('a',True)
  if phase=='paint':key('b',True)
  if phase=='menu':tap('start');assert get('navopen')
  for i in range(28):
   if phase=='idle':p.tick(10)
   elif phase=='cells':tap('b')
   elif phase=='menu':tap('down')
   elif phase=='paint':tap('right')
   elif phase=='multiselect':tap('up' if i<3 else 'right' if i%12<6 else 'left')
   elif phase=='group_move':tap('up' if i%2==0 else 'down')
   else:tap('right' if i%12<6 else 'left')
  for n in ('a','b'):p.button_release(n)
  if phase=='menu':tap('select')
  p.tick(120)
  profiling=False
  row={'exclusive_cpu_percent':{n:100*v[3]/(p._cycles()-start) for n,v in irq_stats.items()},'irq_cpu_percent':{n:100*v[1]/(p._cycles()-start) for n,v in irq_stats.items()},'irq_max_ms':{n:v[2]/4194.304 for n,v in irq_stats.items()},'tma':p.memory[0xff06],'note_hits':[len(a) for a in notes],'note_intervals_ms':[[(y-x)/4194.304 for x,y in zip(a,a[1:])] for a in notes],'note_timing':[stats([{'cycle':cy} for cy in lane],15000/bpm*16 if c==2 else 937.5*(1<<arp_div)/bpm) for c,lane in enumerate(notes)],'noise':stats(noise_hits,15000/bpm),'kick':stats(kick_hits,15000/bpm),'ui_median_ms':statistics.median(acks) if acks else 0,'ui_max_ms':max(acks,default=0),'elapsed_ms':(p._cycles()-start)/4194.304,'graphics':graphics,'drum_irq_active':get('drum_irq_active'),'underruns':get('editirq_underruns')+256*get('editirq_underruns',1),'generation_before':before_generation,'generation_after':get('pattern_generation')+256*get('pattern_generation',1)}
  assert row['noise']['hits']>8 and not row['underruns'],row
  if verify:
   assert row['noise']['max_gap_ms']<15000/bpm+1.3,row
   assert row['drum_irq_active'] and max(row['noise']['max_grid_error_ms'],row['kick']['max_grid_error_ms'],row['note_timing'][1]['max_grid_error_ms'])<1.3,row
  assert not any(graphics.values()) if smooth else graphics['ui_flush']>0
  reports[phase]=row;print(phase,json.dumps(row),flush=True)
 target=Path('build')/(rom.stem+('-smooth' if smooth else '-normal')+('-lfo' if lfo else '')+('' if arp_div==4 else '-arpdiv'+str(arp_div))+('' if bpm==120 else '-'+str(bpm))+'-benchmark.json');target.write_text(json.dumps(reports,indent=2))
finally:p.stop(save=False)

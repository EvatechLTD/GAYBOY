"""Matched DMG audio-register timing and input latency for actual editor gestures."""
import argparse, hashlib, json, statistics
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app
import test_pcm_timing as probes

ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output',default='build/editbuffer-timing.json');ap.add_argument('--bpm',type=int,default=180);ap.add_argument('--drums',action='store_true');ap.add_argument('--lfo',action='store_true');ap.add_argument('--mod-bypass',action='store_true');ap.add_argument('--rolling-probe',action='store_true',help='Record rejected prototype results without accepting timing failures');ap.add_argument('--lfo-voices',type=int,default=3,choices=(0,1,2,3));ap.add_argument('--profile-irq',action='store_true');ap.add_argument('--phases',default='idle,navigation,cells,paint,multiselect,group_move');args=ap.parse_args()
rom=Path(args.rom);S={l.split()[1]:int(l.split()[2],16) for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
def get(n,i=0):
 a=S['_'+n]+i
 return p.memory[0,a] if 0xa000<=a<0xc000 else p.memory[a]
def put(n,x,i=0):
 a=S['_'+n]+i
 if 0xa000<=a<0xc000:p.memory[0,a]=x&255
 else:p.memory[a]=x&255
def word(n,x,i=0):put(n,x,i);put(n,x>>8,i+1)
acks=[]
def press(key,hold=1):
 mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64,'start':128}[key]
 start=p._cycles();p.button_press(key)
 for _ in range(600):
  p.tick(1)
  if get('lastpad')&mask:break
 assert get('lastpad')&mask,('input timeout',key)
 acks.append((p._cycles()-start)*1000/4194304);p.tick(hold);p.button_release(key)
 for _ in range(600):
  p.tick(1)
  if not get('lastpad')&mask:break
 assert not get('lastpad')&mask
def attacks(site):
 op,extra,cost=site;r=p.register_file
 at=(r.B<<8)|r.C if op==2 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
 value=extra if op==0x36 else r.A
 if at==0xff14 and value&128 and p.memory[0xff12]&0xf0:
  hits.append(p._cycles()+cost)
def event_total():return sum(get('seqeventcounts',c*2)|(get('seqeventcounts',c*2+1)<<8) for c in range(7))
try:
 enter_app(p,S)
 tracks=[[[s,49,110,1] for s in range(0,64,4)],[[s,61,100,1] for s in range(64)],[[0,49,100,16]],[],[],[],[]]
 if args.drums:tracks[2]=[];tracks[6]=[[s,4,100,1] for s in range(0,64,4)]
 editor=6 if args.drums else 1
 offset=0
 for c,events in enumerate(tracks):
  word('seqeventcounts',len(events),c*2);word('seqeventoffsets',offset,c*2);word('seqlength',64,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 word('seqglobalbpm',args.bpm);word('seqbpm',args.bpm);put('pattern_dirty',1)
 word('seqdefaultdur',1,12)
 put('page',8);put('seqtrack',editor);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqcursor',4,editor);put('seqpitch',64,1);put('seqtop',71,1);put('drumrow',5);put('seqviewinitialized',127);put('seqdrawvalid',0);put('dirty',1)
 if args.lfo:
  for c in range(args.lfo_voices):
   put('evalpatch',1,c*16+8);put('evalpatch',64,c*16+9)
   put('coarsepitch',0,c*3);put('coarsepitch',12,c*3+1);put('coarsepitch',1,c*3+2)
  for i,v in [(4,0),(6,3),(7,1),(8,0),(9,1)]:put('globalmod',v,i)
  word('pattern_generation',1);put('seqirqdirty',1)
 if args.mod_bypass:
  put('page',2);put('eval_row',10);put('dirty',1);p.tick(30);press('a')
  assert get('mod_bypass')==1
  put('page',8);put('dirty',1)
 p.tick(30);p.button_press('select');press('a');p.button_release('select');p.tick(800)
 assert get('seqplaying')
 if args.mod_bypass:assert not get('lfo_irq_mask') and not get('eval_lfousers') and not get('eval_envusers')
 if args.lfo:
  # Long tracks publish their first snapshot on a loop boundary. Compare
  # steady playback, not different first-publication phases between builds.
  for _ in range(2400):
   if get('editbuffer_valid'):break
   p.tick(1)
  assert get('editbuffer_valid'),'Initial LFO playback snapshot never published'

 hits=[];probes.ROM=rom
 if args.lfo:
  from arp_probe_helpers import hook_attacks
  hook_attacks(p,rom,S,0,hits.append,include_editbuffer=True)
 else:
  for pc,op,extra,cost in probes.pulse_write_sites(S):
   if '_editirq_commit' in S and pc>=S['_editirq_commit'] and not (op==0xe0 and extra==0x14):continue
   p.hook_register(0,pc,attacks,(op,extra,cost))
 irq_times=[];irq_state=[None];irq_returns=set()
 def irq_return(_):
  if irq_state[0] and p.register_file.SP==irq_state[0][1]+2:
   irq_times.append(p._cycles()-irq_state[0][0]);irq_state[0]=None
 def irq_entry(_):
  sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=p.memory[0xff90] if 0x4000<=ret<0x8000 else 0
  irq_state[0]=(p._cycles(),sp)
  if (bank,ret) not in irq_returns:
   p.hook_register(bank,ret,irq_return,None);irq_returns.add((bank,ret))
 if args.profile_irq and '_editirq_attacks' in S:p.hook_register(0,S['_seq_irq_tick'],irq_entry,None)
 fixture=BytesIO();p.save_state(fixture)
 reports={}
 for phase in args.phases.split(','):
  fixture.seek(0);p.load_state(fixture)
  for key in ('a','b','left','right','up','down'):p.button_release(key)
  p.tick(12);put('seqhead',0);put('seqfocus',0);put('seqcursor',4,editor);put('seqpitch',64,1);put('drumrow',5);put('seqgrouptrack',255);put('seqapending',0);put('dirty',1);p.tick(30)
  start_count=event_total();hits.clear();acks.clear();irq_times.clear();start=p._cycles();group_seen=False
  rolling_before={n:get(n)|(get(n,1)<<8) for n in ('editbuffer_underruns','editbuffer_refills','editbuffer_scanned','editbuffer_copied','editbuffer_restarts')} if '_editbuffer_underruns' in S else {}
  if phase=='paint':p.button_press('a');p.button_press('b');p.tick(3)
  if phase=='multiselect':p.button_press('a');p.tick(3)
  if phase=='group_move':
   put('seqpitch',60,1);put('drumrow',6);put('seqgrouptrack',editor);put('seqgroupx0',4);put('seqgroupx1',7);put('seqgroupy0',6 if args.drums else 60);put('seqgroupy1',6 if args.drums else 60);p.button_press('a');p.tick(3)
  for i in range(28):
   if phase=='idle':p.tick(5)
   elif phase=='cells':press('b')
   elif phase=='paint':press('right')
   elif phase=='multiselect':press('down' if i<4 else 'right' if i%12<6 else 'left')
   elif phase=='group_move':press('up' if i%2==0 else 'down')
   else:press('right' if i%12<6 else 'left')
   group_seen|=get('seqgrouptrack')==editor
  for key in ('a','b'):p.button_release(key)
  p.tick(12)
  intervals=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])];nominal=60000/args.bpm
  if not args.rolling_probe:assert len(intervals)>=4,(phase,len(hits))
  reports[phase]={'attacks':len(hits),'max_error_ms':max((abs(t-nominal) for t in intervals),default=None),'p95_error_ms':sorted(abs(t-nominal) for t in intervals)[int(.95*(len(intervals)-1))] if intervals else None,
   'intervals_ms':intervals,'input_ack_max_ms':max(acks,default=0),'input_ack_median_ms':statistics.median(acks) if acks else 0,'elapsed_ms':(p._cycles()-start)*1000/4194304,'events_before':start_count,'events_after':event_total(),'selection_seen':group_seen}
  if rolling_before:
   reports[phase]['rolling']={n:((get(n)|(get(n,1)<<8))-v)&65535 for n,v in rolling_before.items()}
   reports[phase]['timing_pass']=len(intervals)>=4 and reports[phase]['rolling']['editbuffer_underruns']==0 and reports[phase]['max_error_ms']<2
   if not args.rolling_probe:assert reports[phase]['timing_pass'],(phase,reports[phase])
  if phase=='paint':assert event_total()!=start_count,'Paint did not mutate cells'
  if phase=='paint' and args.lfo and not args.drums:
   begin=get('seqeventoffsets',2)|(get('seqeventoffsets',3)<<8);count=get('seqeventcounts',2)|(get('seqeventcounts',3)<<8)
   painted=[]
   for i in range(count):
    e=list(p.memory[1,0xa300+(begin+i)*4:0xa304+(begin+i)*4])
    if e[1]==65:painted.append(e[0])
   assert sorted(painted)==list(range(4,33)),('Paint skipped or duplicated cells',painted)

  if phase=='multiselect':assert group_seen,'Selection gesture was not exercised'
  if '_editirq_underruns' in S:reports[phase]['irq_underruns']=get('editirq_underruns')|(get('editirq_underruns',1)<<8)
  if '_editbuffer_valid' in S:reports[phase]['snapshot_active']=get('editbuffer_valid')
  if irq_times:reports[phase].update(irq_cpu_percent=100*sum(irq_times)/(p._cycles()-start),irq_max_ms=max(irq_times)*1000/4194304)
  print(phase,{k:round(v,3) if isinstance(v,float) else v for k,v in reports[phase].items() if k!='intervals_ms'},flush=True)
  Path(args.output).write_text(json.dumps({'rom':str(rom),'bpm':args.bpm,'partial':True,'phases':reports},indent=2)+'\n')
 result={'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'bpm':args.bpm,'model':'DMG','probe':'P1 hardware trigger writes','phases':reports}
 Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
finally:p.stop(save=False)

"""Actual UI flow: plot chord,enable ARP,navigate cells,enter all header areas."""
from pathlib import Path
import json,re,hashlib
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
S=symbols
class Profile:
 def __init__(self):
  self.enabled=False;self.stack=[];self.stats={};self.hooks={}
  for n in ('engine_timer', 'lfo_irq_tick', 'lfo_irq_pitch', 'seq_irq_tick', 'arp_irq_tick', 'arp_irq_due', 'editirq_commit', 'seq_irq_prepare', 'lfo_irq_prepare', 'eval_arp_prepare', 'arp_irq_prepare', 'eval_mod_configure', 'eval_mod_frame', 'eval_audio_frame', 'editbuffer_service', 'editbuffer_boundary', 'eval_chord_refresh', 'eval_drum_prepare', 'seq_frame', 'sparse_service', 'sparse_prepare_service', 'sparse_snapshot', 'tones_capture', 'resident_move', 'ui_input', 'ui_render', 'ui_flush', 'native_edit_flush','seq_render','seq_dimensions','seq_tiles','seq_playhead','roll_selection_prepare','roll_header_range','seq_pixels','roll_render_begin','roll_navigation_abort','roll_clear_transition','seq_meterbuild'):
   if '_'+n in S:self.hook(S['_'+n]>>16,S['_'+n]&65535,lambda n=n:self.enter(n))
  # Count actual table-rebuild branch entries separately from cache polling.
  listing=Path('build/objects/lfo_irq.lst').read_text()
  tail=listing.split('__critical{lfo_irq_mask&=~bit;}',1)[1]
  offset=int(re.search(r'^\s*([0-9A-Fa-f]{8})\s+F3',tail,re.M)[1],16)
  sym=next(int(l.split()[2],16) for l in Path('build/objects/lfo_irq.sym').read_text().splitlines() if len(l.split())>3 and l.split()[1]=='_lfo_irq_prepare')
  code=S['_lfo_irq_prepare'];at=(code&65535)-sym+offset;bank=code>>16
  assert rom.read_bytes()[bank*16384+at-16384]==0xf3,'LFO object/listing does not match audited ROM'
  self.hook(bank,at,self.rebuilt)
 def rebuilt(self):
  if self.enabled:self.rebuilds+=1
 def hook(self,b,a,f):
  if (b,a) not in self.hooks:
   self.hooks[b,a]=[];p.hook_register(b,a,lambda site:[fn() for fn in tuple(self.hooks[site])],(b,a))
  self.hooks[b,a].append(f)
 def enter(self,n):
  if not self.enabled:return
  if n=='lfo_irq_prepare' and p.memory[p.register_file.SP+6]:self.force_calls+=1
  if n in ('seq_render','seq_pixels'):
   self.events.append({'fn':n,'ms':round((p._cycles()-self.start)*1000/4194304,2),'head':get('seqhead'),'valid':get('seqdrawvalid'),'top':get('seqtop',get('seqtrack')),'viewtop':get('seqviewtop'),'base':get('seqbase'),'viewbase':get('seqviewbase'),'cursor':get('seqcursor',get('seqtrack')),'cancelled':get('rollcancelled'),'queued':(get('padread'),get('padwrite'))})
  sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;b=0 if ret<0x4000 else p.memory[S['__current_bank']]
  if ('return',b,ret) not in self.hooks:
   self.hooks['return',b,ret]=[];self.hook(b,ret,self.returned)
  self.stack.append([n,sp+2,p._cycles(),0])
 def returned(self):
  sp=p.register_file.SP
  while self.stack and self.stack[-1][1]==sp:
   n,_,start,children=self.stack.pop();cost=p._cycles()-start
   row=self.stats.setdefault(n,{'calls':0,'inclusive_cycles':0,'exclusive_cycles':0,'max_cycles':0});row['calls']+=1;row['inclusive_cycles']+=cost;row['exclusive_cycles']+=cost-children;row['max_cycles']=max(row['max_cycles'],cost)
   if self.stack:self.stack[-1][3]+=cost
 def begin(self):self.stack=[];self.stats={};self.enabled=True;self.events=[];self.rebuilds=0;self.force_calls=0;self.start=p._cycles()
 def end(self):
  self.enabled=False;elapsed=p._cycles()-self.start
  for r in self.stats.values():r['exclusive_cpu_pct']=round(100*r['exclusive_cycles']/elapsed,3);r['inclusive_cpu_pct']=round(100*r['inclusive_cycles']/elapsed,3)
  return {'render_events':self.events,'lfo_table_rebuilds':self.rebuilds,'lfo_forced_prepare_calls':self.force_calls,'elapsed_cycles':elapsed,'functions':self.stats,'open_spans':[(r[0],r[1]) for r in self.stack]}
def key(n,down):
 mask={'a':16,'b':32,'select':64,'up':4,'down':8,'right':1,'left':2}[n];start=p._cycles();(p.button_press if down else p.button_release)(n)
 for _ in range(1800):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return (p._cycles()-start)*1000/4194304
 raise AssertionError(('input timeout',n,down))
def tap(n):return max(key(n,True),key(n,False))
def header_visible():
 h=get('seqhead');c=get('seqtrack');a=33 if get('evalpatch',c*16) else 45
 bar=(get('seqbeats')*(16//get('seqdenom')));length=get('seqlength',c*2)|(get('seqlength',c*2+1)<<8)
 first=35 if length%bar else int(str(length//bar)[0])+16
 wanted=(a+(0 if h==1 else 96),244+((get('seqmuted')>>c)&1)+(2 if h==2 else 0),248+((get('seqsolo')>>c)&1)+(2 if h==3 else 0),first+(0 if h==4 else 96))
 return tuple(p.memory[0x9800+x] for x in (4,9,11,13))==wanted
def visible_tap(n):
 start=p._cycles();ack=tap(n)
 for _ in range(1800):
  p.tick(1)
  if header_visible():return round((p._cycles()-start)*1000/4194304,3),ack
 raise AssertionError(('header never caught up',n,get('seqhead'),[p.memory[0x9800+x] for x in (4,9,11,13)]))
try:
 enter_app(p,S);offset=0
 tracks=[[[0,n,110,32] for n in (49,53,56)],[],[[i,n,110,8] for i,n in zip((0,8,16,24),(37,37,40,35))],[],[],[],[[i,11,100,1] for i in range(0,32,2)]+[[i,12,100,1] for i in (4,12,20,28)]+[[i,13,110,1] for i in (0,8,16,24)]]
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',32,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('evalpatch',1,0);put('evalpatch',1,13);put('evalpatch',3,2)
 word('seqbpm',120);word('seqglobalbpm',120);word('seqdefaultdur',16,2)
 put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127);put('seqcursor',0,1);put('seqpitch',60,1);put('seqtop',68,1);put('seqdrawvalid',0);put('dirty',1)
 key('select',True);tap('a');key('select',False);p.tick(180)
 # P2 note data and its ARP mode are created entirely through normal controls.
 tap('b')
 for _ in range(4):tap('up')
 tap('b')
 for _ in range(3):tap('up')
 tap('b');assert get('seqeventcounts',2)==3
 while not get('seqhead'):tap('up')
 assert get('seqhead')==1;tap('a');assert get('evalpatch',16)==1;tap('down');assert not get('seqhead')
 profiler=Profile();rows=[]
 for target in (16,22,24,28):
  while get('seqcursor',1)>0:tap('left')
  for _ in range(4):tap('down')
  while get('seqcursor',1)<target:tap('right')
  while get('seqcursor',1)>target:tap('left')
  while get('seqpitch',1)<get('seqtop',1) and not get('seqhead'):tap('up')
  assert not get('seqhead'),('left grid too early',target)
  profiler.begin();entry,entryack=visible_tap('up');assert get('seqhead')
  header=get('seqhead');right,rightack=visible_tap('right');left,leftack=visible_tap('left');profile=profiler.end()
  row={'cursor':target,'header':header,'entry_ms':round(entry,3),'entry_ack_ms':round(entryack,3),'right_ms':round(right,3),'left_ms':round(left,3),'arp_active':get('arp_active_mask'),'arp_irq':get('arpirq_enabled'),'profile':profile};rows.append(row)
  print({k:v for k,v in row.items() if k!='profile'},'hot',[(n,round(r['max_cycles']/4194.304,2)) for n,r in sorted(profile['functions'].items(),key=lambda kv:-kv[1]['max_cycles'])][:5],flush=True)
  while get('seqhead')!=1:tap('left')
  off,offack=visible_tap('a');assert not get('evalpatch',16)
  on,onack=visible_tap('a');assert get('evalpatch',16)==1
  row.update(off_visible_ms=off,on_visible_ms=on,entry_timing_pass=entry<500)
  if 'before' not in rom.stem:assert entry<500 and off<750,('header delay',row)
  p.tick(180);tap('down');assert not get('seqhead')
 Path('build/topbar-ui-'+rom.stem+'.json').write_text(json.dumps({'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'cases':rows},indent=2))
 print('PASS real plotting,ARP enable,cell navigation and repeated entry into all four header regions')
finally:p.stop(save=False)

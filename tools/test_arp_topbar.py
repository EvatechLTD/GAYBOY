"""Trace actual grid-to-header entry and recovery with two live ARP tracks."""
from pathlib import Path
import json,re,hashlib
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
S=symbols
class Profile:
 def __init__(self):
  self.enabled=False;self.stack=[];self.stats={};self.hooks={}
  for n in ('engine_timer', 'lfo_irq_tick', 'lfo_irq_pitch', 'seq_irq_tick', 'arp_irq_tick', 'arp_irq_due', 'editirq_commit', 'seq_irq_prepare', 'lfo_irq_prepare', 'eval_arp_prepare', 'arp_irq_prepare', 'eval_mod_configure', 'eval_mod_frame', 'eval_audio_frame', 'editbuffer_service', 'editbuffer_boundary', 'eval_chord_refresh', 'eval_drum_prepare', 'seq_frame', 'sparse_service', 'sparse_prepare_service', 'sparse_snapshot', 'tones_capture', 'resident_move', 'ui_input', 'ui_render', 'ui_flush', 'native_edit_flush','seq_render','seq_dimensions','seq_tiles','seq_playhead','roll_selection_prepare','roll_header_range'):
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
 def begin(self):self.stack=[];self.stats={};self.enabled=True;self.rebuilds=0;self.force_calls=0;self.start=p._cycles()
 def end(self):
  self.enabled=False;elapsed=p._cycles()-self.start
  for r in self.stats.values():r['exclusive_cpu_pct']=round(100*r['exclusive_cycles']/elapsed,3);r['inclusive_cpu_pct']=round(100*r['inclusive_cycles']/elapsed,3)
  return {'lfo_table_rebuilds':self.rebuilds,'lfo_forced_prepare_calls':self.force_calls,'elapsed_cycles':elapsed,'functions':self.stats,'open_spans':[(r[0],r[1]) for r in self.stack]}
def key(n,down):
 mask={'a':16,'select':64,'up':4,'down':8,'right':1,'left':2}[n];start=p._cycles();(p.button_press if down else p.button_release)(n)
 for _ in range(1800):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return round((p._cycles()-start)*1000/4194304,3)
 raise AssertionError(('input timeout',n,down))
reports=[]
for lanes in ((0,1),(1,2),(0,2)):
 if reports:p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
 try:
  enter_app(p,S);offset=0;target=lanes[-1]
  for c in range(7):
   events=[[0,n,110,32] for n in (61,65,68)] if c in lanes else [[i,n,110,8] for i,n in zip((0,8,16,24),(37,37,40,35))] if c==2 else [[i,11,100,1] for i in range(0,32,2)]+[[i,12,100,1] for i in (4,12,20,28)]+[[i,13,110,1] for i in (0,8,16,24)] if c==6 else []
   word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',32,c*2)
   for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
   if c in lanes:put('evalpatch',1,c*16);put('evalpatch',1,c*16+13);put('evalpatch',3,c*16+2)
  word('seqbpm',120);word('seqglobalbpm',120);word('pattern_generation',1);put('pattern_dirty',1);put('seqirqdirty',1)
  put('page',8);put('seqtrack',target);put('selected',target);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127);put('seqtop',68,target);put('seqpitch',68,target)
  key('select',True);key('a',True);key('a',False);key('select',False);p.tick(1200)
  profiler=Profile()
  for repetition in range(2):
   put('seqhead',0);put('seqcursor',0,target);put('seqpitch',get('seqtop',target),target);put('dirty',1);p.tick(90)
   top=get('seqtop',target);profiler.begin()
   press=key('up',True);release=key('up',False);right=key('right',True);key('right',False);left=key('left',True);key('left',False)
   profile=profiler.end()
   assert get('seqhead')==1,('did not reach MODE header',lanes,get('seqhead'))
   key('a',True);key('a',False);p.tick(180);assert get('evalpatch',target*16)==0
   key('a',True);key('a',False);p.tick(180);assert get('evalpatch',target*16)==1
   row={'lanes':lanes,'repetition':repetition,'entry_ms':press,'release_ms':release,'right_ms':right,'left_ms':left,'top_before':top,'top_after':get('seqtop',target),'arp_mask':get('arpirq_enabled'),'profile':profile};reports.append(row)
   print({k:v for k,v in row.items() if k!='profile'},'hot',[(n,round(r['max_cycles']/4194.304,2)) for n,r in sorted(profile['functions'].items(),key=lambda kv:-kv[1]['max_cycles'])][:6],flush=True)
   Path('build/topbar-'+rom.stem+'.json').write_text(json.dumps({'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'cases':reports},indent=2))
  # Reach the header through real held/repeating UP, rather than teleporting
  # focus or tapping from an already positioned cursor.
  put('seqhead',0);put('seqpitch',get('seqtop',target)-4,target);put('dirty',1);p.tick(90)
  top=get('seqtop',target);profiler.begin();start=p._cycles();key('up',True)
  for _ in range(600):
   p.tick(1)
   if get('seqhead'):break
  else:raise AssertionError(('held UP did not reach header',lanes))
  reached=p._cycles();p.tick(3);release=key('up',False);right=key('right',True);key('right',False);profile=profiler.end()
  assert get('seqtop',target)==top,('UP repeats spilled into header scrolling',lanes,top,get('seqtop',target))
  row={'lanes':lanes,'repetition':'held_up','entry_ms':round((reached-start)*1000/4194304,3),'release_ms':release,'right_ms':right,'top_before':top,'top_after':get('seqtop',target),'arp_mask':get('arpirq_enabled'),'profile':profile};reports.append(row)
  print({k:v for k,v in row.items() if k!='profile'},'hot',[(n,round(r['max_cycles']/4194.304,2)) for n,r in sorted(profile['functions'].items(),key=lambda kv:-kv[1]['max_cycles'])][:6],flush=True)
  Path('build/topbar-'+rom.stem+'.json').write_text(json.dumps({'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'cases':reports},indent=2))
 finally:p.stop(save=False)

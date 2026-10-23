"""Attribute main-ROM prep cost with nested IRQ time counted separately.
Uses the normal editor fixture; profiling changes no ROM code or thresholds.
Inclusive spans overlap; exclusive spans subtract tracked children.
"""
from pathlib import Path
import re
class Profile:
 def __init__(self):
  self.enabled=False;self.stack=[];self.stats={};self.hooks={}
  for n in ('engine_timer', 'lfo_irq_tick', 'lfo_irq_pitch', 'seq_irq_tick', 'arp_irq_tick', 'arp_irq_due', 'editirq_commit', 'seq_irq_prepare', 'lfo_irq_prepare', 'eval_arp_prepare', 'arp_irq_prepare', 'eval_mod_configure', 'eval_mod_frame', 'eval_audio_frame', 'editbuffer_service', 'editbuffer_boundary', 'eval_chord_refresh', 'eval_drum_prepare', 'seq_frame', 'sparse_service', 'sparse_prepare_service', 'sparse_snapshot', 'tones_capture', 'resident_move', 'ui_input', 'ui_render', 'ui_flush', 'native_edit_flush'):
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
source=Path('tools/test_editbuffer_timing.py').read_text()
source=source.replace(' fixture=BytesIO();p.save_state(fixture)',' profiler=Profile()\n fixture=BytesIO();p.save_state(fixture)',1)
source=source.replace('  start_count=event_total();','  profiler.begin()\n  start_count=event_total();',1)
source=source.replace('  intervals=[','  profile=profiler.end()\n  intervals=[',1)
source=source.replace('  if rolling_before:',"  reports[phase]['profile']=profile\n  if rolling_before:",1)
exec(compile(source,'tools/test_editbuffer_timing.py','exec'))

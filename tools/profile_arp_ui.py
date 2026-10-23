"""Matched real-playback cycle attribution and input latency; inclusive spans overlap."""
import argparse,json,hashlib,statistics
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app

ap=argparse.ArgumentParser();ap.add_argument('--internal',action='store_true');ap.add_argument('--view',choices=('instrument','menu'),default='instrument');ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--save',type=Path,required=True);ap.add_argument('--output',default='build/arp-ui-profile.json');args=ap.parse_args()
rom=Path(args.rom);S={l.split()[1]:int(l.split()[2],16) for l in rom.with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(args.save.read_bytes()));p.set_emulation_speed(0)
def get(n,i=0):
 a=S['_'+n]+i;return p.memory[0,a] if 0xa000<=a<0xc000 else p.memory[a]
def put(n,v,i=0):
 a=S['_'+n]+i
 if 0xa000<=a<0xc000:p.memory[0,a]=v&255
 else:p.memory[a]=v&255
def word(n,v,i=0):put(n,v,i);put(n,v>>8,i+1)
class Profile:
 def __init__(self):
  self.enabled=False;self.stack=[];self.stats={};self.hooks={}
  for n in ('engine_timer','editirq_elapsed','seq_irq_tick','arp_irq_tick','seq_next_deadline','seq_fire','drum_fire','mixer_boundary','editbuffer_boundary','seq_frame','eval_seq_tick','eval_arp_wait','eval_arp_prepare','arp_irq_prepare','seq_irq_prepare','arp_irq_due','eval_seq_fire','eval_seq_prepare','ui_input','ui_render','ui_flush','seq_pixels','native_mode_feedback'):
   if '_'+n in S:self.hook(S['_'+n]>>16,S['_'+n]&65535,lambda n=n:self.enter(n))
 def hook(self,b,a,f):
  if (b,a) not in self.hooks:
   self.hooks[b,a]=[];p.hook_register(b,a,lambda site:[fn() for fn in tuple(self.hooks[site])],(b,a))
  self.hooks[b,a].append(f)
 def enter(self,n):
  if not self.enabled:return
  sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;b=0 if ret<0x4000 else S['_'+n]>>16
  if ('return',b,ret) not in self.hooks:
   self.hooks['return',b,ret]=[];self.hook(b,ret,self.returned)
  self.stack.append([n,sp+2,p._cycles(),0])
 def returned(self):
  sp=p.register_file.SP
  while self.stack and self.stack[-1][1]==sp:
   n,_,start,children=self.stack.pop();cost=p._cycles()-start
   row=self.stats.setdefault(n,{'calls':0,'inclusive_cycles':0,'exclusive_cycles':0,'max_cycles':0});row['calls']+=1;row['inclusive_cycles']+=cost;row['exclusive_cycles']+=cost-children;row['max_cycles']=max(row['max_cycles'],cost)
   if self.stack:self.stack[-1][3]+=cost
 def begin(self):self.stack=[];self.stats={};self.enabled=True;self.start=p._cycles()
 def end(self):
  self.enabled=False;elapsed=p._cycles()-self.start
  for r in self.stats.values():r['exclusive_cpu_pct']=round(100*r['exclusive_cycles']/elapsed,3);r['inclusive_cpu_pct']=round(100*r['inclusive_cycles']/elapsed,3)
  return {'elapsed_cycles':elapsed,'functions':self.stats,'open_spans':[(r[0],r[1]) for r in self.stack]}
prof=Profile()
def key(k,down):
 mask={'a':16,'b':32,'select':64,'left':2,'right':1,'down':8,'up':4}[k];start=p._cycles();(p.button_press if down else p.button_release)(k)
 for _ in range(360):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return round((p._cycles()-start)*1000/4194304,3)
 return None
rows=[]
try:
 enter_app(p,S);put('seqtrack',1);put('selected',1);put('seqhead',1);put('seqfocus',0);put('seqdrawvalid',0);put('dirty',1);p.tick(250)
 if args.internal:
  put('syncmode',0);put('syncarmed',0);p.memory[0xff07]=0;p.memory[0xff06]=p.memory[0xff05]=240;p.memory[0xff0f]&=~4;p.memory[0xff07]=4
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(180)
 fixture=BytesIO();p.save_state(fixture)
 for bpm in (120,240):
  for mode in ('off','native','random','modulated'):
   fixture.seek(0);p.load_state(fixture)
   word('seqbpm',bpm);word('seqglobalbpm',bpm);word('seqcachedbpm',0)
   put('evalpatch',int(mode!='off'),16);put('evalpatch',3,18);put('evalpatch',0,19);put('evalpatch',3 if mode=='random' else 0,21)
   if mode=='modulated':put('evalpatch',1,25)
   word('pattern_generation',(get('pattern_generation')|get('pattern_generation',1)<<8)+1);word('seqdeadline',1)
   put('page',1);put('navopen',int(args.view=='menu'));put('navcategory',0);put('navchoice',1);put('eval_tab',0);put('eval_row',0);put('dirty',1);p.tick(180)
   prof.begin();p.tick(360);idle=prof.end()
   prof.begin();latencies=[]
   for k in ('down','up','down','up','down','up','down','up'):
    latencies.extend((key(k,True),key(k,False)))
   nav=prof.end()
   row={'bpm':bpm,'mode':mode,'view':args.view,'native_mask':get('arpirq_enabled'),'syncmode':get('syncmode'),'syncarmed':get('syncarmed'),'waveengine':get('waveengine'),'TMA':p.memory[0xff06],'idle':idle,'navigation':nav,'ack_ms':latencies,'median_ack_ms':statistics.median(x for x in latencies if x is not None),'max_ack_ms':max(x for x in latencies if x is not None)};rows.append(row)
   Path(args.output).write_text(json.dumps({'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'cases':rows},indent=2))
   print(bpm,mode,'ack',row['median_ack_ms'],row['max_ack_ms'],'idle',[(n,r['exclusive_cpu_pct']) for n,r in sorted(idle['functions'].items(),key=lambda x:-x[1]['exclusive_cycles'])][:8],'open',idle['open_spans'],flush=True)
finally:p.stop(save=False)

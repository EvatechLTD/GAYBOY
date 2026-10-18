"""Foreground stage costs during actual mixed-audio mixer launch/navigation."""
from pathlib import Path
import argparse,json,statistics,re
from seq_storage_helpers import write_tracks,write_word
ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/promo-candidate1/GAYBOY.gb');ap.add_argument('--output',default='build/launch-stage-profile.json');ap.add_argument('--lst',default='build/promo-candidate1/mixer.lst');args=ap.parse_args()
env={};src=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file=');src=src.replace('build/GAYBOY.gb',args.rom).replace('build/GAYBOY.noi',str(Path(args.rom).with_suffix('.noi')));exec(src,env)
p,S,choose,press=env['p'],env['S'],env['choose'],env['press'];mx=S['_mx'];CPU=4194304
records=[];return_hooks={};starts=[];attacks=[];irqstack=[];irqs=[];phase='setup'
def v(n,i=0):return p.memory[S['_'+n]+i]
def sm(i,x):p.memory[mx+i]=x
def addret(bank,pc,fn):
 k=(bank,pc)
 if k not in return_hooks:return_hooks[k]=[];p.hook_register(bank,pc,lambda key:[f() for f in list(return_hooks[key])],k)
 return_hooks[k].append(fn)
def hook(n,fn):
 a=S['_'+n];p.hook_register(a>>16,a&65535,fn,None)
def profile(name):
 def entered(_):
  sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=p.memory[0xff90] if 0x4000<=ret<0x8000 else 0
  c=p.register_file.A if name in ('seq_fire','keyevent','play') else p.memory[sp+6] if name in ('seq_note_event','drum_fire') else None
  item={'name':name,'phase':phase,'c':c,'start':p._cycles(),'end':None};records.append(item)
  if name=='seq_pattern_start':starts.append(item)
  cleanup={'keyevent':1,'play':1,'kick_start':4}.get(name,0)
  def returned():
   if item['end'] is None and p.register_file.SP==sp+2+cleanup:item['end']=p._cycles()
  addret(bank,ret,returned)
 hook(name,entered)
def settled_slot(slot):
 for _ in range(1200):
  p.tick(1)
  if p.memory[mx+1]==slot and p.memory[mx+2]==255:break
 assert p.memory[mx+1]==slot and p.memory[mx+2]==255,'Stopped fixture load did not complete'
 p.tick(60)
def pattern(duty):
 tracks=[[] for _ in range(7)];tracks[0]=[[s,61+s%5,100,4] for s in range(0,64,4)];tracks[1]=[[s,68+s%3,100,1] for s in range(64)];tracks[6]=[[s,1 if s%8==0 else 4,127,4] for s in range(0,64,4)]+[[s,13,127,1] for s in range(1,64,4)];write_tracks(p,S,tracks)
 for c in range(7):write_word(p,S['_seqlength']+c*2,64)
 write_word(p,S['_seqbpm'],220);p.memory[S['_param']]=duty
def apu_write(site):
 op,extra,cost=site;r=p.register_file
 at=(r.B<<8)|r.C if op==0x02 else (r.D<<8)|r.E if op==0x12 else r.HL if op in (0x22,0x32,0x36,0x77) else 0xff00+extra if op==0xe0 else 0xff00+r.C if op==0xe2 else extra
 value=extra if op==0x36 else r.A
 if at==0xff19 and value&128:attacks.append(p._cycles()+cost)
def irq_start(_):
 if v('waveengine')==3:irqstack.append((p._cycles()-20,p.register_file.SP))
def irq_end(_):
 if irqstack and irqstack[-1][1]==p.register_file.SP:
  begin,_=irqstack.pop();irqs.append((begin,p._cycles()+16))
try:
 choose(18);pattern(0);choose(20);press('b');sm(4,31);press('a');settled_slot(1);pattern(2);choose(20);sm(6,1);press('b');sm(4,30);press('a');settled_slot(0);sm(4,0);press('a');assert v('seqplaying');p.tick(30)
 for n in ('seq_pattern_start','drum_fire','kick_start','seq_fire','seq_note_event','seq_event_next_step','keyevent','play','fine_apply','drum_step_samples','drum_timer','mixer_velocity','mixer_pan'):
  if '_'+n in S:profile(n)
 import test_pcm_timing as pcm;pcm.ROM=Path(args.rom)
 for pc,op,extra,cost in pcm.pulse_write_sites(S):p.hook_register(0,pc,apu_write,(op,extra,cost))
 p.hook_register(0,0x50,irq_start,None);reti=0x80+Path(args.rom).read_bytes()[0x80:0xa0].index(bytes([0xd9]));p.hook_register(0,reti,irq_end,None)
 phase='same';sm(3,0);sm(4,30);press('a');p.tick(15)
 phase='new';sm(4,31);press('a');p.tick(360)
 windows=[]
 for start in starts:
  attack=next((a for a in attacks if a>=start['start']),None)
  if attack is None:continue
  children=[r for r in records if r['name']!='seq_pattern_start' and r['start']>=start['start'] and r['start']<attack]
  span_irq=sum(max(0,min(b,attack)-max(a,start['start'])) for a,b in irqs if b>start['start'] and a<attack)*1000/4194304
  windows.append({'phase':start['phase'],'start_to_actual_p2_ms':(attack-start['start'])*1000/4194304,'timer_IRQ_union_ms':span_irq,'stages':[{'name':r['name'],'c':r['c'],'at_ms':(r['start']-start['start'])*1000/4194304,'duration_ms':(r['end']-r['start'])*1000/4194304 if r['end'] is not None else None} for r in children]})
 report={'model':'DMG','bpm':220,'length':64,'windows':windows};Path(args.output).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:p.stop(save=False)

"""Emulated DMG input acknowledgment and drum repaint timings during PCM."""
from pathlib import Path
import json,statistics
ns={};src=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
exec(src.replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file='),ns)
p,S,v,choose,press=(ns[k] for k in ('p','S','v','choose','press'))
profiles={};callbacks={};CPU=4194304

def put(n,i,x):p.memory[S['_'+n]+i]=x

def hook(bank,addr,fn):
 key=(bank,addr)
 if key not in callbacks:
  callbacks[key]=[];p.hook_register(bank,addr,lambda k:[f() for f in list(callbacks[k])],key)
 callbacks[key].append(fn)

def profile(name):
 a=S['_'+name];state=[None];profiles[name]=[]
 def entered():
  sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=p.memory[0xff90] if 0x4000<=ret<0x8000 else 0
  state[0]=(p._cycles(),sp+2)
  def returned():
   if state[0] and p.register_file.SP==state[0][1]:profiles[name].append((p._cycles()-state[0][0])*1000/CPU);state[0]=None
  hook(bank,ret,returned)
 hook(a>>16 if a>=65536 else 0,a&65535,entered)
try:
 choose(18)
 for i in range(384):put('seqnotes',i,0)
 for c in range(7):put('seqlength',c,16)
 for i in range(128):put('drumhits',i,10 if i%8 in (0,1) else 0);put('noisehits',i,0);put('drumvel',i,100);put('drumdur',i,4)
 put('seqtrack',0,6);put('seqbpm',0,120);put('seqbpm',1,0)
 p.memory[S['_mx']+4]=0;press('a');choose(8);assert v('seqtrack')==6
 for name in ('drum_render','drum_velocity_render'):profile(name)
 acknowledgments=[]
 for _ in range(6):
  t=p._cycles();p.button_press('down')
  for _ in range(600):
   p.tick(1)
   if v('lastpad')&8:break
  acknowledgments.append((p._cycles()-t)*1000/CPU)
  p.button_release('down')
  for _ in range(600):
   p.tick(1)
   if not v('lastpad')&8:break
  p.tick(4)
 result={'button_ack_ms':acknowledgments,'profiles':{k:{'calls':len(a),'median_ms':statistics.median(a) if a else None,'max_ms':max(a) if a else None} for k,a in profiles.items()}}
 Path('build/seq-edit-timing.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:p.stop(save=False)

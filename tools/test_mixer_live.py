"""Forced-DMG live Mixer controls, pattern requests, CPU budget and note drift.

This drives real buttons and measures emulated CPU cycles. Pattern and save
fixtures use disposable cartridge RAM; the user's save file is never opened.
"""
from pathlib import Path
import argparse,json,statistics,re
CPU=4194304

def run(frames=180,events512=False,bpm=300):
 env={}
 source=Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0]
 source=source.replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file=')
 exec(source,env)
 p,S,v,word=(env[k] for k in ('p','S','v','word'))
 from seq_storage_helpers import write_tracks,write_word
 mx=S['_mx'];callbacks={};measuring=[False];acks=[];notes=[];irq=[];active_irq=[None];samples=[];switch_wait=[None];switch_first=[]
 def put(n,i,x):p.memory[S['_'+n]+i]=x
 def m(i):return p.memory[mx+i]
 def setm(i,x):p.memory[mx+i]=x
 def hook(bank,addr,fn):
  key=(bank,addr)
  if key not in callbacks:
   callbacks[key]=[];p.hook_register(bank,addr,lambda k:[f() for f in list(callbacks[k])],key)
  callbacks[key].append(fn)
 def press(key):
  mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64,'start':128}[key]
  start=p._cycles();p.button_press(key)
  for _ in range(600):
   p.tick(1)
   if v('lastpad')&mask:break
  assert v('lastpad')&mask,('button press stalled',key,'PC',hex(p.register_file.PC),'ROMbank',p.memory[0xff90],'seqservicing',v('seqservicing'),'ticks',word('seqticks'),'deadline',word('seqdeadline'),'slot',m(1),'pending',m(2),'cache',m(48),'counts',[p.memory[S['_seqeventcounts']+c*2]|p.memory[S['_seqeventcounts']+c*2+1]<<8 for c in range(7)])
  if measuring[0]:acks.append((key,(p._cycles()-start)*1000/CPU))
  p.button_release(key)
  for _ in range(600):
   p.tick(1)
   if not v('lastpad')&mask:break
  assert not v('lastpad')&mask,('button release stalled',key)
  p.tick(2)
 def choose(n):
  p.button_press('start')
  for _ in range(120):
   p.tick(1)
   if v('navopen'):break
  assert v('navopen')
  for _ in range(30):
   if v('navchoice')==n:break
   press('down')
  assert v('navchoice')==n
  p.button_release('start');p.tick(35);assert v('page')==(1 if n==0 else n)
 def state(key,down):
  mask={'right':1,'left':2,'up':4,'down':8,'b':32}[key]
  (p.button_press if down else p.button_release)(key)
  for _ in range(600):
   p.tick(1)
   if bool(v('lastpad')&mask)==down:break
  assert bool(v('lastpad')&mask)==down,('held button not acknowledged',key,down)
 def hold(key,n):
  state('b',True);state(key,True);p.tick(n)
  state(key,False);state('b',False);p.tick(3)
 def pattern(slot):
  length=256 if events512 else 16
  tracks=[[] for _ in range(7)]
  tracks[0]=[[s,61+s%4,100,1] for s in range(0,length,2 if events512 else 1)]
  tracks[1]=[[s,68+s%3,100,1] for s in range(length)]
  tracks[6]=[[s,sample,127,4] for s in range(0,length,4) for sample in (4,10)]
  write_tracks(p,S,tracks)
  for c in range(7):write_word(p,S['_seqlength']+c*2,length)
  put('seqbpm',0,bpm&255);put('seqbpm',1,bpm>>8);put('seqmode',0,0)
  for c in range(7):setm(12+c,100 if c<2 else 127);setm(19+c,3)
  for i,ch in enumerate(('L0'+str(slot)+'\0').encode()):setm(26+i,ch)
 def boundary():
  if not measuring[0] or m(2)==255:return
  beat=16//v('seqdenom');unit=beat if m(3)==1 else beat*v('seqbeats')
  if ((m(10)|(m(11)<<8))+1)%unit==0:switch_wait[0]=(p._cycles(),m(2))
 def played():
  if measuring[0] and p.register_file.A==1:
   notes.append((p._cycles(),v('seqposition',1),m(1)))
   if switch_wait[0] and m(1)==switch_wait[0][1]:switch_first.append((p._cycles()-switch_wait[0][0])*1000/CPU);switch_wait[0]=None
 def irq_start():
  if measuring[0] and v('waveengine')==3:active_irq[0]=(p._cycles()-20,p.register_file.SP,bool(v('drumon') and v('drumon',1)))
 def irq_end():
  state=active_irq[0]
  if state and p.register_file.SP==state[1]:irq.append((state[0],p._cycles()+16-state[0],state[2]));active_irq[0]=None
 def profile(name):
  if '_'+name in S:addr=S['_'+name]
  else:
   lines=Path('build/objects/mixer.lst').read_text().splitlines();line=next((l for l in lines if re.search('_'+name+':$',l)),None)
   if line is None:return
   addr=(18<<16)|0x4000|int(line.split()[0],16)
  state=[None]
  def entered():
   if not measuring[0]:return
   sp=p.register_file.SP;ret=p.memory[sp]|p.memory[sp+1]<<8;bank=p.memory[0xff90] if 0x4000<=ret<0x8000 else 0
   state[0]=(p._cycles(),sp+2)
   def returned():
    if state[0] and p.register_file.SP==state[0][1]:
     samples.append((name,p._cycles()-state[0][0]));state[0]=None
   hook(bank,ret,returned)
  hook(addr>>16 if addr>=65536 else 0,addr&65535,entered)
 try:
  assert p.memory[0xff4d]==255,'DMG mode required'
  choose(18);pattern(0)
  choose(20);press('b');assert v('page')==18
  setm(4,31);press('a');assert m(1)==1
  if v('page')!=18:choose(18)
  pattern(1);setm(4,30);press('a');assert m(1)==0
  setm(3,2);setm(4,0);press('a');assert v('seqplaying')
  p.tick(30)
  addr=S['_play'];hook(0,addr,played);addr=S['_mixer_boundary'];hook(addr>>16,addr&65535,boundary);hook(0,0x50,irq_start);hook(0,0x9b,irq_end)
  for name in ('mixer_render','mixer_input','mixer_velocity','snapshot','prefetch','pads','prime','tailcopy','switchslot','install_events'):profile(name)
  begin=p._cycles();blocks=word('engineblocks');drops=word('mixunderruns');measuring[0]=True
  p.tick(frames)
  # B editing stays on the selected field and never silences the reference P2.
  setm(4,4);before=m(12);hold('up',75);assert m(12)>before and m(4)==4
  hold('left',3);assert m(4)==4 and 0<m(12)<127
  setm(4,5);hold('left',3);assert m(19)==0 and m(4)==5
  hold('right',3);assert m(19)==3 and m(4)==5
  setm(4,2);press('a');assert v('seqmuted')&1;p.tick(20);press('a');assert not v('seqmuted')&1
  setm(4,7);press('a');assert v('seqsolo')&2;p.tick(20);press('a');assert not v('seqsolo')&2
  setm(4,28);hold('down',18);assert 0<m(18)<127 and m(4)==28
  setm(4,29);hold('left',3);assert m(25)==0 and m(4)==29
  hold('right',3);assert m(25)==3 and m(4)==29
  p.tick(frames)
  for target in (1,0,1):
   setm(4,30+target);press('a')
   for _ in range(300):
    p.tick(1)
    if m(1)==target and m(2)==255 and not v('seqservicing'):break
   assert m(1)==target and m(2)==255,('queued pattern did not switch',target)
   assert not v('seqeventcache'),'Cache-view ownership leaked after pattern installation'
   p.tick(35)
  elapsed=p._cycles()-begin;measuring[0]=False
  assert len(notes)>80
  residual=[t-(notes[0][0]+i*CPU*60/(bpm*4)) for i,(t,_,_) in enumerate(notes)]
  intervals=[(b[0]-a[0])*1000/CPU for a,b in zip(notes,notes[1:])]
  per={}
  for name in ('mixer_render','mixer_input','mixer_velocity','snapshot','prefetch','pads','prime','tailcopy','switchslot','install_events'):
   vals=[cost for n,cost in samples if n==name]
   if vals:per[name]={'calls':len(vals),'median_ms':statistics.median(vals)*1000/CPU,'max_ms':max(vals)*1000/CPU}
  span=notes[-1][0]-notes[0][0];expected=elapsed/(CPU*60/(bpm*4))
  result={'model':'DMG forced cgb=False','bpm':bpm,'stored_events':512 if events512 else 40,'elapsed_seconds':elapsed/CPU,'reference_p2_onsets':len(notes),'expected_onsets':expected,
   'p2_interval_ms_min':min(intervals),'p2_interval_ms_max':max(intervals),'p2_phase_jitter_ms_peak_to_peak':(max(residual)-min(residual))*1000/CPU,
   'p2_phase_drift_ms':(residual[-1]-residual[0])*1000/CPU,'audio_blocks':(word('engineblocks')-blocks)&65535,'audio_underruns':(word('mixunderruns')-drops)&65535,
   'full_irq_cpu_percent':sum(cost for _,cost,_ in irq)*100/elapsed,'full_irq_cycles_max':max(cost for _,cost,_ in irq),
   'switch_first_p2_ms':switch_first,'cache_view_after_switch':v('seqeventcache'),'button_ack_ms_max':max(t for _,t in acks),'function_profiles':per,'interactions':'held B volume/pan, mute P1, solo P2, DRUM level/pan, three bar-quantized requests'}
  result['largest_intervals']=[{'ms':intervals[i],'before':notes[i][1:],'after':notes[i+1][1:]} for i in sorted(range(len(intervals)),key=lambda i:intervals[i],reverse=True)[:12]]
  result['smallest_intervals']=[{'ms':intervals[i],'before':notes[i][1:],'after':notes[i+1][1:]} for i in sorted(range(len(intervals)),key=lambda i:intervals[i])[:6]]
  result['meets_audio_delivery']=result['audio_underruns']==0
  result['meets_note_rate']=abs(len(notes)-expected)<2
  result['meets_live_timing']=result['p2_interval_ms_max']<=60000/(bpm*4)+8 and result['p2_phase_jitter_ms_peak_to_peak']<=12
  return result
 finally:p.stop(save=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bpm',type=int,default=300);parser.add_argument('--frames',type=int,default=180);parser.add_argument('--events512',action='store_true');args=parser.parse_args()
 result=run(args.frames,args.events512,args.bpm);Path('build/mixer-live.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
 assert result['meets_audio_delivery'] and result['meets_note_rate'] and result['meets_live_timing'],'Live Mixer timing regression; see build/mixer-live.json'

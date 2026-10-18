"""Real-button ordinary-pattern launch timing, forced DMG and disposable SRAM."""
from pathlib import Path
import argparse,json,sys
from io import BytesIO
from pyboy import PyBoy
from seq_storage_helpers import write_tracks,write_word

ap=argparse.ArgumentParser();ap.add_argument('--rom',default='build/GAYBOY.gb');ap.add_argument('--output',default='build/ordinary-launch.json');ap.add_argument('--quick',action='store_true');args=ap.parse_args()
CPU=4194304
S={l.split()[1]:int(l.split()[2],16) for l in Path(args.rom).with_suffix('.noi').read_text().splitlines() if l.startswith('DEF ')}
results=[]
for length,bpm in ([(16,120),(32,180),(64,220)] if args.quick else [(n,b) for n in (16,32,64) for b in (120,180,220)]):
 p=PyBoy(args.rom,window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0)
 def v(n,i=0):return p.memory[S['_'+n]+i]
 def put(n,i,x):p.memory[S['_'+n]+i]=x
 def m(i):return v('mx',i)
 def sm(i,x):put('mx',i,x)
 def press(key):
  mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'start':128}[key];start=p._cycles();p.button_press(key)
  for _ in range(600):
   p.tick(1)
   if v('lastpad')&mask:break
  assert v('lastpad')&mask
  ack=(p._cycles()-start)*1000/CPU;p.button_release(key)
  for _ in range(600):
   p.tick(1)
   if not v('lastpad')&mask:break
  assert not v('lastpad')&mask
  p.tick(2);return start,ack
 def choose(n):
  p.button_press('start')
  for _ in range(600):
   p.tick(1)
   if v('navopen'):break
  for _ in range(32):
   if v('navchoice')==n:break
   press('down')
  assert v('navchoice')==n;p.button_release('start');p.tick(40);assert v('page')==n
 def settled_slot(slot):
  for _ in range(1200):
   p.tick(1)
   if m(1)==slot and m(2)==255:break
  assert m(1)==slot and m(2)==255,('stopped slot load did not complete',slot,m(1),m(2))
  p.tick(60) # Fixture setup only: finish retained graphics before mutating data.
 def pattern(duty):
  tracks=[[] for _ in range(7)]
  tracks[0]=[[s,61+s%5,100,1] for s in range(length)]
  tracks[1]=[[s,68+s%3,100,1] for s in range(length)]
  tracks[6]=[[s,1 if s%8==0 else 4,110,1] for s in range(0,length,4)]
  write_tracks(p,S,tracks)
  for c in range(7):write_word(p,S['_seqlength']+c*2,length)
  write_word(p,S['_seqbpm'],bpm);put('param',0,duty)
 def ready(slot):
  # Setup must not edit events or press Play while a preceding pad load is
  # still installing its metadata. Measured launches below remain real-time.
  for _ in range(1800):
   if m(1)==slot and m(2)==255 and not v('seqservicing') and ('_prep' not in S or not v('prep')):return
   p.tick(1)
  raise AssertionError(('Setup pad load did not settle',slot,m(1),m(2),v('seqservicing')))
 try:
  for _ in range(2800):
   p.tick(1)
   if v('introready'):break
  p.button_press('start')
  for _ in range(120):
   p.tick(1)
   if not v('introactive') and v('page')==8:break
  p.button_release('start');p.tick(50)
  choose(18);pattern(0);choose(20);press('b')
  sm(4,31);press('a');ready(1)
  if v('page')!=18:choose(18)
  pattern(2);choose(20);sm(6,1);press('b')
  sm(4,30);press('a');ready(0)
  if v('page')!=18:choose(18)
  sm(4,0);press('a')
  for _ in range(180):
   if v('seqplaying'):break
   p.tick(1)
  assert v('seqplaying');p.tick(30)
  notes=[];starts=[];boundaries=[];releases=[];transports=[];input_entries=[]
  def hook(name,fn):
   a=S['_'+name];p.hook_register(a>>16,a&65535,fn,None)
  hook('play',lambda _ :notes.append((p._cycles(),m(1),v('seqposition',1))) if p.register_file.A==1 else None)
  hook('seq_pattern_start',lambda _:starts.append((p._cycles(),len(boundaries))))
  hook('mixer_boundary',lambda _:boundaries.append((p._cycles(),m(10)|(m(11)<<8),m(2))))
  hook('seq_pattern_release',lambda _:releases.append(p._cycles()))
  hook('seq_transport',lambda _:transports.append(p._cycles()))
  hook('mixer_input',lambda _:input_entries.append(p._cycles()) if p.memory[p.register_file.SP+7]&16 and m(4)>=30 else None)
  for quant in (0,1,2):
   for same in (True,False):
    p.tick(30);notes.clear();starts.clear();boundaries.clear();releases.clear();transports.clear();input_entries.clear()
    target=m(1) if same else 1-m(1);sm(3,quant);sm(4,30+target)
    click,ack=press('a');_,navigation_ack=press('right')
    for _ in range(360):
     p.tick(1)
     if starts and m(2)==255 and not v('seqservicing'):break
    assert starts,(length,bpm,quant,same,'launch timeout');p.tick(45)
    assert v('param')==target*2,('Incoming pulse tone did not follow saved pattern',length,bpm,quant,same,target,v('param'))
    intervals=[(b[0]-a[0])*1000/CPU for a,b in zip(notes,notes[1:])]
    first=next((n[0] for n in notes if n[0]>=starts[0][0]),None)
    unit=4 if quant==1 else 16
    eligible=[b for b in boundaries[:starts[0][1]] if b[0]>=click and (b[1]+1)%unit==0] if quant else []
    result=dict(length=length,bpm=bpm,quant=('OFF','BEAT','BAR')[quant],same_pattern=same,button_ack_ms=round(ack,3),physical_to_action_entry_ms=round((input_entries[0]-click)*1000/CPU,3) if input_entries else None,click_to_launch_ms=round((starts[0][0]-click)*1000/CPU,3),launch_to_first_p2_ms=round((first-starts[0][0])*1000/CPU,3) if first else None,max_note_interval_ms=round(max(intervals,default=0),3),nominal_step_ms=60000/bpm/4,interval_jitter_ms=round(max(intervals,default=0)-min(intervals,default=0),3),boundaries_before_launch=starts[0][1],eligible_boundaries_passed_before_launch=max(0,len(eligible)-1),release_calls=len(releases),transport_calls=len(transports))
    result['navigation_after_request_ack_ms']=round(navigation_ack,3)
    results.append(result);Path(args.output).write_text(json.dumps(results,indent=2));print(json.dumps(result),flush=True)
    assert not transports and v('seqplaying')
 finally:p.stop(save=False)

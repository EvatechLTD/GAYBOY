"""Held pad launches follow musical quantization, never button-repeat time."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])
from seq_storage_helpers import write_word,mark_pattern_changed

def write_tracks(p,S,tracks):
 offset=0;slot=v("mx",1);bank=1+(slot>>2);base=0xa000+(slot&3)*2048+768
 for c,events in enumerate(tracks):
  write_word(p,S["_seqeventcounts"]+c*2,len(events));write_word(p,S["_seqeventoffsets"]+c*2,offset)
  for event in events:
   for j,x in enumerate(event):p.memory[bank,base+offset*4+j]=x
   offset+=1
 mark_pattern_changed(p,S)

def resident_tracks(slot):
 offset=0;result=[];bank=1+(slot>>2);base=0xa000+(slot&3)*2048
 for c in range(7):
  count=p.memory[bank,base+32+c*2]|p.memory[bank,base+33+c*2]<<8
  result.append([[p.memory[bank,base+768+(offset+i)*4+j] for j in range(4)] for i in range(count)])
  offset+=count
 return result
launches=[];boundaries=[]
def hook(name,callback):
 a=S['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def boundary(_):boundaries.append((v('seqposition'),v('seqposition',1)))
def launch(_):launches.append((len(boundaries),boundaries[-1] if boundaries else None))
def wait(fn,limit=2400):
 for _ in range(limit):
  if fn():return
  p.tick(1)
 assert fn(),(launches,v('mx',2),v('page'))
try:
 enter_app(p,S);choose(18)
 p.memory[S['_syncmode']]=0;p.memory[S['_syncslave']]=0
 write_word(p,S['_seqbpm'],300);write_word(p,S['_seqglobalbpm'],300)
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,100,1]];tracks[1]=[[0,68,100,1]];tracks[6]=[[0,1,100,1],[0,2,100,1]]
 write_tracks(p,S,tracks)
 write_word(p,S['_seqlength'],7);write_word(p,S['_seqlength']+2,24)
 hook('mixer_boundary',boundary);hook('seq_pattern_handoff',launch)
 p.memory[0,S['_mx']+4]=0
 if not v('seqplaying'):tap('a')
 assert v('seqplaying')
 for quant in [1,2,3,4,5]:
  p.memory[0,S['_mx']+3]=quant;p.memory[0,S['_mx']+4]=30
  launches.clear();boundaries.clear();p.button_press('a')
  wait(lambda:len(launches)>=5)
  held=launches[:5]
  expected=24 if quant==5 else 1<<quant
  assert all(b[0]-a[0]==expected for a,b in zip(held,held[1:])),(quant,held)
  if quant==5:assert all(x[1][1]==23 for x in held),(quant,held)
  p.button_release('a');wait(lambda:not v('lastpad')&16)
  # Like a tap, a launch already queued before release still completes.
  wait(lambda:v('mx',2)==255);count=len(launches);p.tick(240)
  assert len(launches)==count,(quant,'repeated after release')
  print('PASS held quant',quant,'consecutive boundary interval',expected)
 # Populate destination resident patterns with distinct melodies and two PCM hits.
 for slot in (1,2,4):
  base=0xa000+(slot&3)*2048;bank=1+(slot>>2)
  events=[[0,61+slot,100,1],[0,1,100,1],[0,2,100,1]]
  for c,count in enumerate((1,0,0,0,0,0,2)):
   p.memory[bank,base+32+c*2]=count;p.memory[bank,base+33+c*2]=0
  for i,event in enumerate(events):
   for j,x in enumerate(event):p.memory[bank,base+768+i*4+j]=x
 # Slide to adjacent patterns without releasing A. Leave Right held while
 # the destination prepares, installs and repeatedly retriggers at 300 BPM.
 p.memory[0,S['_mx']+3]=7
 p.memory[0,S['_mx']+4]=30
 p.button_press('a');wait(lambda:v('lastpad')&16)
 for key,target in [('right',1),('right',2),('left',1),('left',0),('left',4),('right',0)]:
  p.button_press(key)
  mask=1 if key=='right' else 2
  wait(lambda:v('lastpad')&mask)
  assert v('mx',4)==30+target,(key,target,v('mx',4))
  wait(lambda:v('mx',1)==target)
  assert v('mx',3)==7 and v('seqplaying')
  launches.clear();wait(lambda:len(launches)>=6)
  assert v('mx',1)==target and v('mx',3)==7
  if target==0:assert resident_tracks(0)[0]==tracks[0]
  p.button_release(key);wait(lambda:not v('lastpad')&mask)
 # Changing the divisor during the same A hold retains the current pad.
 for key,expected in [('down',6),('up',7)]:
  tap(key);assert v('mx',3)==expected and v('mx',1)==0
 p.button_release('a');wait(lambda:not v('lastpad')&16)
 wait(lambda:v('mx',2)==255);count=len(launches);p.tick(120)
 assert len(launches)==count
 assert v('mixunderruns')==0 and v('mixunderruns',1)==0
 print('PASS held-A adjacent/wrapped pad switches at 300 BPM, 1/32 retriggers, divisor preserved, release stops')
 # The launch header follows the same speed direction on both axes.
 p.memory[0,S['_mx']+3]=2;p.memory[0,S['_mx']+4]=1
 p.button_press('b');wait(lambda:v('lastpad')&32)
 for key,expected in [('up',1),('right',6),('down',1),('left',2)]:
  tap(key);assert v('mx',3)==expected and v('mx',4)==1,(key,v('mx',3),v('mx',4))
 p.button_release('b');wait(lambda:not v('lastpad')&32)
 p.memory[0,S['_mx']+4]=30
 # NOW has no musical repeat interval and must remain one-shot.
 p.memory[0,S['_mx']+3]=0;launches.clear();p.button_press('a');p.tick(240)
 assert len(launches)==1,launches
 p.button_release('a');p.tick(30)
 # Holding A on Play must not repeatedly toggle transport.
 p.memory[0,S['_mx']+4]=0;p.button_press('a');p.tick(90)
 assert not v('seqplaying')
 print('PASS release stops rearming; NOW and transport remain one-shot')
finally:p.stop(save=False)

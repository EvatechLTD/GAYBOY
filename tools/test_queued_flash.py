"""Exercise queued-pad flashing and the actual quantized launch in the demo."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
from collections import Counter
from pyboy import PyBoy
from quick_demo import QuickDemo

S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
p.tick(150);p.button_press('start');p.tick(15);p.button_release('start');p.tick(30)
d=QuickDemo(p,S)
for _ in d.prepare():p.tick()
d.frames=0;d.log=[];d.stage_times=[];d.sequence=d.run()
states=[];active=set();solid=set();flash_uploads=[]
def value(name):return p.memory[S['_'+name]]
def uploads(_):
 if d.v('page')==18 and p.memory[S['_mx']+2]==1 and p.memory[S['_mx']+9] and value('padflash_slot')==1:
  flash_uploads.append(d.frames)
a=S['_set_bkg_data'];p.hook_register(a>>16,a&65535,uploads,None)
if '_ui_upload_tile' in S:
 a=S['_ui_upload_tile'];p.hook_register(a>>16,a&65535,uploads,None)
def digest(x0,x1):return hashlib.sha256(p.screen.ndarray[112:128,x0:x1,:3].tobytes()).hexdigest()
neighbor_stable=False;cancelled=False
try:
 while not d.done and d.frames<2200:
  d.step();p.tick()
  if d.v('page')!=18 or not p.memory[S['_mx']+9] or value('ui_transition_hidden'):continue
  pending=p.memory[S['_mx']+2]
  if pending==1 and value('padflash_slot')==1:
   phase=value('padflash_off')
   states.append((d.frames,phase,digest(21,39)))
   active.add(digest(1,19))
  elif p.memory[S['_mx']+1]==1 and pending==255 and value('padflash_slot')==255:
   solid.add(digest(21,39))
 assert d.done
 # Replace a queued pad with its adjacent neighbor. Their shared edge tile
 # must not make the cancelled pad flash, and picking the active pad cancels.
 def drive(sequence):
  for _ in sequence:p.tick();d.frames+=1
 drive(d.choose(18))
 p.memory[S['_seqbpm']]=30;p.memory[S['_seqbpm']+1]=0
 for _ in range(650):
  if p.memory[S['_mx']+10]==0 and p.memory[S['_mx']+11]==0:break
  p.tick()
 drive(d.tap('up'));drive(d.tap('right'));drive(d.tap('right'));drive(d.tap('a'))
 p.tick(50)
 assert p.memory[S['_mx']+2]==2
 drive(d.tap('right'));drive(d.tap('a'));p.tick(45)
 assert p.memory[S['_mx']+2]==3
 neighbor=set();phases_replaced=set()
 for _ in range(50):
  p.tick();neighbor.add(digest(41,59));phases_replaced.add(value('padflash_off'))
 assert len(neighbor)==1 and phases_replaced=={0,1}, 'Cancelled neighbor inherited the queued flash'
 neighbor_stable=True
 drive(d.tap('left'));drive(d.tap('left'));drive(d.tap('a'));p.tick(50)
 assert p.memory[S['_mx']+1]==1 and p.memory[S['_mx']+2]==255 and value('padflash_off')==0
 cancelled=True
finally:p.stop(save=False)
phases={phase for _,phase,_ in states}
changes=sum(a[1]!=b[1] for a,b in zip(states,states[1:]))
assert phases=={0,1} and changes>=2, 'Queued pad did not visibly flash'
assert len({h for _,_,h in states})>=2, 'Flash flag changed without changing the picture'
assert len(active)==1, 'The currently playing pad flashed'
assert len(solid)==1, 'Launched pad did not settle into a solid display'
on=Counter(h for _,phase,h in states if phase==0).most_common(1)[0][0]
off=Counter(h for _,phase,h in states if phase==1).most_common(1)[0][0]
assert on!=off and solid=={on}, 'Playing appearance differs from the illuminated queued pad'
assert not flash_uploads, 'Blink animation regenerated graphics'
assert d.transition_snapshot[:3]==[15,63,31], 'Launch missed the arrangement loop boundary'
result={'flash_transitions':changes,'queued_samples':len(states),'active_pad_stable':True,
        'launched_pad_solid':True,'tile_uploads_during_blink':len(flash_uploads),
        'replaced_neighbor_stable':neighbor_stable,'active_pad_cancels_queue':cancelled,'stages':d.stage_times}
Path('build/queued-flash.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

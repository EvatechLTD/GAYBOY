"""Repeated real keyboard saves preserve live/resident names, data and pad graphics."""
from pathlib import Path
from collections import deque
from io import BytesIO
import numpy as np
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
def keyboard(target):
 todo=deque([(get('mx',4),[])]);seen=set()
 while todo:
  at,path=todo.popleft()
  if at in seen:continue
  seen.add(at)
  if at==target:
   for k in path:tap(k)
   tap('a');return
  row,col=divmod(at,6) if at<36 else (6,at-36)
  for key in ('left','right','up','down'):
   r,c=row,col
   if key=='left':c=(c-1)%(4 if r==6 else 6)
   if key=='right':c=(c+1)%(4 if r==6 else 6)
   if key=='up':r=(r-1)%7;c=min(c,3) if r==6 else c
   if key=='down':r=(r+1)%7;c=min(c,3) if r==6 else c
   todo.append((36+c if r==6 else r*6+c,path+[key]))
 raise AssertionError(('No keyboard route',target))
def name(slot):
 bank=1+slot//4;base=0xa000+(slot%4)*2048
 return bytes(p.memory[bank,base+16:base+32]).split(b'\0')[0]
def live_name():return bytes(get('mx',26+i) for i in range(17)).split(b'\0')[0]
def rename(slot,label,cancel=False):
 choose(18);put('mx',30+slot,4);put('dirty',1);p.tick(30);choose(20);tap('a');assert get('mx',7)
 keyboard(38)
 for c in label:keyboard(ord(c)-ord('A'))
 if cancel:
  tap('select');assert get('page')==20 and not get('mx',7);choose(18);return
 keyboard(39);assert get('page')==26,'Expected overwrite confirmation';tap('up');tap('a');p.tick(90)
 assert get('page')==18 and not get('mx',10)
 assert name(slot)==label.encode(),('Resident name was replaced while saving',name(slot),label)
 if slot==get('mx',1):assert live_name()==label.encode(),('Live name stayed stale',live_name(),label)
 assert bytes(p.memory[0,0xae40+slot*5:0xae45+slot*5]).split(b'\0')[0]==label[:5].encode(),'Mixer pad name cache stayed stale'
 choose(19)
 row=2+slot
 actual=bytes((get('canvas',row*20+4+i)%96)+32 for i in range(len(label)))
 assert actual==label.encode(),('Browser name stayed stale',actual,label)
 tap('select');assert get('page')==18
try:
 enter_app(p,symbols);put('sticky_start',1)
 original=name(0)
 # The first rename of an inactive pad succeeds even on the old bug.
 rename(1,'FIRST');assert live_name()==original
 choose(18);put('mx',31,4);put('dirty',1);p.tick(30);tap('b');p.tick(90);assert get('mx',1)==1
 screenshots=[]
 for i,label in enumerate(('SECOND','ABCDEFGHIJKLMNOP','LAST')):
  choose(30);put('seqcursor',i,2);put('seqpitch',36+i,2);put('seqtop',60,2);put('dirty',1);p.tick(30);tap('b')
  assert get('seqeventcounts',4)==i+1
  put('param',i+1);put('pattern_dirty',1)
  rename(1,label)
  assert p.memory[1,0xa880]==i+1,'Changed patch data was not saved'
  p.tick(120);assert name(1)==label.encode() and live_name()==label.encode(),'Idle snapshot reverted name'
  screenshots.append(np.asarray(p.screen.image).copy()[120:136,32:64])
 assert all(not np.array_equal(a,b) for a,b in zip(screenshots,screenshots[1:])),'Pad text pixels did not update'
 rename(1,'CANCEL',True);assert name(1)==b'LAST' and live_name()==b'LAST'
 assert name(0)==original,'Renaming another pad changed the active source pad'
 p.screen.image.save('build/repeated-pattern-save.png')
 battery=BytesIO();p.save_state(battery)
 ram=b''.join(bytes(p.memory[bank,0xa000:0xbfff])+bytes([p.memory[bank,0xbfff]]) for bank in range(4))
 p.stop(save=False)
 p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(ram));p.set_emulation_speed(0)
 enter_app(p,symbols);put('sticky_start',1);choose(18);put('mx',31,4);put('dirty',1);p.tick(30);tap('b');p.tick(90)
 assert get('mx',1)==1 and name(1)==b'LAST' and live_name()==b'LAST','Battery reboot lost the name'
 assert get('seqeventcounts',4)==3 and p.memory[1,0xa880]==3,'Battery reboot lost saved notes or patch'
 print('PASS inactive/active repeated renames,16-char/short names, browser/pad pixels, notes/patches, cancel and battery reboot')
finally:p.stop(save=False)

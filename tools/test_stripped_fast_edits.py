"""Real DMG input: single-cell publication, continued navigation and A+B paint."""
from pathlib import Path
import json,sys
reports=[]
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
rom=Path(sys.argv[sys.argv.index('--rom')+1]) if '--rom' in sys.argv else Path('build/GAYBOY.gb')
prefix=prefix.replace("Path('build/GAYBOY.noi')","rom.with_suffix('.noi')").replace("'build/GAYBOY.gb',",'str(rom),')
if '--baseline' in sys.argv:prefix=prefix.replace("v('sticky_start')",'1')
def tilepixel(x,y):
 tile=p.memory[0x9800+(1+y//8)*32+x//8]
 address=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16
 off=address+(y%8)*2;mask=128>>(x%8)
 return bool(p.memory[off]&mask)+2*bool(p.memory[off+1]&mask)
def grid():return bytes(tilepixel(x,y) for y in range(v('seqgridheight')) for x in range(24,160))
def count():return v('seqeventcounts',12)|v('seqeventcounts',13)<<8
def notes():
 p.memory[0x4000]=1
 data=[list(p.memory[0xa300+i*4:0xa304+i*4]) for i in range(count())]
 p.memory[0x4000]=0
 return data
def tapquick(key):p.button_press(key);p.tick(1);p.button_release(key);p.tick(1)
for rownum,velocity in ((0,False),(5,False),(0,True),(5,True)):
 exec(prefix)
 try:
  enter_app(p,S);put('drumrow',rownum);put('seqvelocityhidden',not velocity);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  # Explicit one-step hats, including sampled hats. Long paint is checked separately.
  put('seqdefaultdur',1,12);put('seqdefaultdur',0,13)
  x=28;y=(rownum+(1 if rownum>=3 and '--baseline' not in sys.argv else 0))*8+3;assert tilepixel(x,y)==0
  before=grid();latencies={};events=[]
  if '_roll_note_feedback' in S:
   ptr=S['_seq_event_put'];p.hook_register(ptr>>16,ptr&65535,lambda _:events.append((p._cycles(),tilepixel(x,y))),None)
  for action,color in (('plot',3),('delete',0)):
   started=p._cycles();p.button_press('b');p.tick(1);p.button_release('b')
   for _ in range(240):
    if tilepixel(x,y)==color:break
    p.tick(1)
   visible_ms=(p._cycles()-started)*1000/4194304;latencies[action+'_visible_ms']=visible_ms
   for _ in range(240):
    if count()==(1 if action=='plot' else 0) and not v('seqapending'):break
    p.tick(1)
   ms=(p._cycles()-started)*1000/4194304;latencies[action+'_ready_ms']=ms
   assert tilepixel(x,y)==color and count()==(1 if action=='plot' else 0),(rownum,velocity,action,ms,count())
   if '--baseline' not in sys.argv:assert visible_ms<85 and ms<100,(rownum,velocity,action,visible_ms,ms)
   if action=='plot':
    started=p._cycles();p.button_press('right');p.tick(1);p.button_release('right')
    for _ in range(120):
     if v('seqcursor',6)==1:break
     p.tick(1)
    assert v('seqcursor',6)==1
    latencies['navigate_ms']=(p._cycles()-started)*1000/4194304
    tapquick('left');p.tick(4)
  assert grid()==before,'Deleting must restore the original grid exactly'
  if events:assert events[0][1]==3,'Publish changed cell before writing its note record'
  if '--baseline' in sys.argv:
   reports.append({'row':rownum,'velocity_visible':velocity,**latencies});continue
  # Multiple handles survive middle deletion and compacted event records.
  for step in (0,4,8):put('seqcursor',step,6);put('dirty',1);p.tick(8);press('b')
  put('seqcursor',4,6);put('dirty',1);p.tick(8);press('b')
  assert sorted(e[0] for e in notes())==[0,8],notes()
  put('seqcursor',8,6);put('dirty',1);p.tick(8);press('b');assert [e[0] for e in notes()]==[0]
  # The incremental image must agree with a forced complete render.
  p.tick(30);image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert '--baseline' in sys.argv or grid()==image,'Fast edit differs from full redraw'
  reports.append({'row':rownum,'velocity_visible':velocity,**latencies})
 finally:p.stop(save=False)
# Fresh hihat patterns: paint identical default lengths, never resize or erase.
if '--baseline' not in sys.argv:
 for length in (1,4):
  exec(prefix)
  try:
   enter_app(p,S);put('drumrow',0);put('seqdefaultdur',length,12);put('seqdefaultdur',0,13);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
   p.button_press('a');p.tick(2);p.button_press('b');p.tick(4)
   for _ in range(7):tapquick('right')
   p.button_release('a');p.button_release('b');p.tick(6)
   if count()!=8:print('paint backlog',length,count(),v('seqcursor',6),v('padread'),v('padwrite'));p.tick(12)
   assert count()==8 and v('seqcursor',6)==7,notes()
   assert sorted((e[0],e[3]) for e in notes())==[(i,length) for i in range(8)],notes()
   p.tick(100);image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(240);assert grid()==image,'Paint differs from complete render'
   p.screen.image.save('build/stripped-paint-'+str(length)+'.png')
  finally:p.stop(save=False)
 output=Path('build/stripped-fast-edits.json');output.write_text(json.dumps(reports,indent=2)+'\n')
if '--baseline' in sys.argv:Path('build/stripped-pre-cellfix/fast-edits.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))

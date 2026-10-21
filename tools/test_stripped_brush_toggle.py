"""A+B movement toggles occupied cells, including sustained note bodies."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
for track,rownum in ((6,3),(6,0),(0,0)):
 exec(prefix);exec(helpers)
 try:
  enter_app(p,S);put('seqtrack',track);put('drumrow',rownum);put('seqhead',0);put('seqfocus',0);put('seqdefaultdur',1,track*2);put('seqdefaultdur',0,track*2+1);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  def records():
   n=v('seqeventcounts',track*2)|v('seqeventcounts',track*2+1)<<8;p.memory[0x4000]=1
   result=[list(p.memory[0xa300+i*4:0xa304+i*4]) for i in range(n)];p.memory[0x4000]=0;return result
  def border():
   if track==6 and rownum==3:assert all(tilepixel(x,32)==1 for x in range(24,160)),'missing sample top edge'
  border()
  for step in (1,3):put('seqcursor',step,track);put('dirty',1);p.tick(20);press('b');p.tick(80)
  put('seqcursor',0,track);put('dirty',1);p.tick(20)
  p.button_press('a');p.tick(4);p.button_press('b');p.tick(80)
  for key,expected in (('right',[0,3]),('right',[0,2,3]),('right',[0,2]),('left',[0])):
   press(key);p.tick(80);assert sorted(e[0] for e in records())==expected,(track,rownum,key,records());border()
  p.button_release('a');p.button_release('b');p.tick(80);assert len(records())==1
  # Start the chord on the existing note; entering its body erases it.
  put('seqdefaultdur',4,track*2);put('seqcursor',4,track);put('dirty',1);p.tick(30);press('b');p.tick(80)
  put('seqcursor',4,track);put('dirty',1);p.tick(30);p.button_press('a');p.tick(4);p.button_press('b');p.tick(50)
  assert sorted(e[0] for e in records())==[0,4]
  press('right');p.tick(80);assert sorted(e[0] for e in records())==[0,4,5],('body paint creates a separate onset',records())
  p.button_release('a');p.button_release('b');p.tick(80);border()
  image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid(),'toggle differs from full rendering'
 finally:p.stop(save=False)
print('PASS: sample top border, A+B mixed paint/erase, onset hit, chord entry and release on drum and pulse grids')

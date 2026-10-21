"""Chord edits retain local drawing; one onset shares one velocity slider."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
for track in (0,1,2):
 exec(prefix);exec(helpers)
 try:
  enter_app(p,S);put('seqtrack',track);put('seqviewinitialized',127);put('evalpatch',1,track*16);put('evalpatch',1,track*16+13);put('seqtop',60,track);put('seqhead',0);put('seqfocus',0);put('seqvelocityhidden',0);put('seqdefaultdur',2,track*2);put('seqdefaultdur',0,track*2+1);put('rollcache',0);put('seqdrawvalid',0);put('dirty',1);p.tick(160)
  def records():
   n=v('seqeventcounts',track*2)|v('seqeventcounts',track*2+1)<<8
   return [list(p.memory[1,0xa300+i*4:0xa304+i*4]) for i in range(n)]
  def image():return bytes(tilepixel(x,y) for y in range(136) for x in range(16,160))
  def compare(label):
   p.tick(50);before=image();put('rollcache',0);put('seqdrawvalid',0);put('dirty',1);p.tick(160);after=image();assert before==after,(track,label,[(i%144+16,i//144,a,b) for i,(a,b) in enumerate(zip(before,after)) if a!=b][:12])
  for step in (2,6):
   for pitch in (48,52,55):
    put('seqcursor',step,track);put('seqpitch',pitch,track);put('eval_plotvel',42 if pitch==48 else 99,track);put('dirty',1);p.tick(20);press('b');p.tick(100);compare('insert')
  assert all(e[2]==42 for e in records()),records()
  rebuild=[];ptr=S['_seq_pixels'];p.hook_register(ptr>>16,ptr&65535,lambda _:rebuild.append(p._cycles()),None)
  put('seqhead',5);put('seqcursor',2,track);put('seqpitch',59,track);put('dirty',1);p.tick(20);p.button_press('b');p.tick(4);press('up');p.button_release('b');p.tick(50)
  assert [e[2] for e in records() if e[0]==2]==[43]*3,records();assert not rebuild,(track,'slider full redraw');compare('chord velocity');rebuild.clear()
  put('seqhead',0);put('seqcursor',2,track);put('seqpitch',52,track);put('dirty',1);p.tick(20);p.button_press('b');p.tick(4);press('right');p.button_release('b');p.tick(50)
  assert [e[3] for e in records() if e[0]==2 and e[1]==53]==[3],records();assert not rebuild,(track,'resize full redraw');compare('chord resize');rebuild.clear()
  put('seqcursor',2,track);put('seqpitch',52,track);put('dirty',1);p.tick(20);p.button_press('a');p.tick(4);press('right');p.button_release('a');p.tick(60)
  assert any(e[0]==3 and e[1]==53 for e in records()),('chord note drag blocked',records());assert not rebuild,(track,'chord drag full redraw');compare('chord drag');rebuild.clear()
  # Select the whole chord phrase, then drag and resize it as a group.
  put('seqcursor',0,track);put('seqpitch',47,track);put('dirty',1);p.tick(20);p.button_press('a');p.tick(4)
  for _ in range(7):press('right');p.tick(20)
  for _ in range(9):press('up');p.tick(20)
  p.button_release('a');p.tick(50);assert v('seqgrouptrack')==track;assert not rebuild,(track,'chord selection full redraw');compare('chord selection');rebuild.clear()
  put('seqcursor',2,track);put('seqpitch',48,track);put('dirty',1);p.tick(20);before=records();p.button_press('a');p.tick(4);press('right');p.button_release('a');p.tick(100)
  assert sorted(e[0] for e in records())==sorted(e[0]+1 for e in before),('chord group drag',records());assert not rebuild,(track,'chord group drag full redraw');compare('chord group drag');rebuild.clear()
  put('seqcursor',3,track);put('seqpitch',48,track);put('dirty',1);p.tick(20);before=records();p.button_press('b');p.tick(4);press('right');p.button_release('b');p.tick(100)
  assert [e[3] for e in records()]==[e[3]+1 for e in before],('chord group resize',records());assert not rebuild,(track,'chord group resize full redraw');compare('chord group resize');rebuild.clear()
  put('seqgrouptrack',255);put('seqdrawvalid',2);put('dirty',1);p.tick(60)
  # Preserve ghost colors when returning to mono with plotted chords.
  put('evalpatch',0,track*16);put('rollcache',0);put('seqdrawvalid',0);put('dirty',1);p.tick(160);rebuild.clear()
  put('seqcursor',7,track);put('seqpitch',48,track);put('dirty',1);p.tick(20);press('b');p.tick(80);assert not rebuild,(track,'ghost delete full redraw');compare('ghost admission')
 finally:p.stop(save=False)
print('PASS: P1/P2/Wave chord velocity, inherited velocity, local slider, chord resize and ghost admission pixels')

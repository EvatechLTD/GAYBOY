"""Edit/Generate is sequencer-only, targets origin and applies back to the grid."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
exec(prefix)
try:
 enter_app(p,S)
 def records(c):
  n=v('seqeventcounts',c*2)|v('seqeventcounts',c*2+1)<<8;o=v('seqeventoffsets',c*2)|v('seqeventoffsets',c*2+1)<<8
  return [list(p.memory[1,0xa300+(o+i)*4:0xa304+(o+i)*4]) for i in range(n)]
 # A separate track must survive both preview and Keep.
 put('seqtrack',0);put('seqhead',0);put('seqfocus',0);put('dirty',1);p.tick(100);press('b');p.tick(60);other=records(0)
 put('seqtrack',2);put('seqdrawvalid',0);put('dirty',1);p.tick(100)
 p.button_press('start');p.tick(30);press('right');assert v('navcategory')==1
 for _ in range(20):
  if v('navchoice')==47:break
  press('down')
 assert v('navchoice')==47 and v('theorytrack')==2
 p.button_release('start');p.tick(160);assert v('genopen') and v('seqtrack')==2 and 'LIVE PREVIEW' in line(0)
 assert records(0)==other and records(2),('wrong track generated',records(0),other)
 assert all(v('canvas',2*20+i)<96 for i in range(1,5)),'label highlighted'
 assert all(v('canvas',2*20+i)>=96 for i in range(11,17)),'value not highlighted'
 press('down');p.button_press('b');p.tick(4);press('up');p.button_release('b');p.tick(80);assert v('genroot')==10
 put('genrow',12);put('dirty',1);p.tick(30);press('a');p.tick(120)
 assert v('page')==8 and not v('genopen') and v('seqtrack')==2 and not v('seqhead') and not v('seqfocus')
 assert records(0)==other and records(2)
 for screen in (1,16,18,10):
  put('page',screen);put('dirty',1);p.tick(80);p.button_press('start');p.tick(30);press('right');seen=[]
  for _ in range(20):seen.append(v('navchoice'));press('down')
  assert 47 not in seen,(screen,'Generate outside grid',seen)
  press('select');p.button_release('start');p.tick(50)
 put('page',10);put('seqfocus',1);put('dirty',1);p.tick(60);assert 'GEN' not in line(17)
finally:p.stop(save=False)
print('PASS: Edit/Generate context, originating track isolation, value highlight/edit and Apply returns to grid')

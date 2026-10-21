from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,S)
 for track in (0,1,2,3,6):
  put('seqtrack',track);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  assert all(v('canvas',i)==96 for i in (8,10,12)),('pattern label',track)
  if track==6:
   assert all(v('canvas',i)==96 for i in range(4,8)),'Drum mode label'
   put('drumrow',0);put('seqhead',0);put('dirty',1);p.tick(10);press('up');assert v('seqhead')==2
   for key,head in (('right',3),('right',4),('right',2),('left',4)):
    press(key);assert v('seqhead')==head,(key,v('seqhead'))
  menu(18);p.tick(120)
  assert all(v('canvas',i) in list(range(64,96))+list(range(160,168)) for i in range(300,340)),'Pad rows contain stale sequencer tiles'
  assert all(p.memory[0x9800+16*32+i]==v('canvas',320+i) for i in range(20)),'Pad row was not published'
  p.screen.image.save('build/stripped-mixer-transition.png')
  menu(8);p.tick(180)
 # Direct vertical entry follows the cursor's horizontal position.
 for track in (0,6):
  put('seqtrack',track);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  for col,head in ((0,2 if track==6 else 1),(6,2),(8,3),(12,4)):
   put('seqhead',0);put('seqcursor',col,track);put('seqpitch',v('seqtop',track),track);put('drumrow',0);put('dirty',1);p.tick(12);press('up');assert v('seqhead')==head,(track,col,v('seqhead'))
 # Header tracks the first visible step, including three-digit values.
 put('seqhead',0);put('seqlength',0,12);put('seqlength',1,13)
 for cursor,expected in ((0,'1/256'),(16,'17/256'),(96,'97/256'),(240,'241/256')):
  put('seqcursor',cursor,6);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  actual=''.join(chr(v('canvas',i)%96+32) for i in range(13,20)).strip();assert actual==expected,(actual,expected)
 menu(10);put('seqfocus',9);put('dirty',1);p.tick(40)
 for _ in range(2):
  value=''.join(chr(v('canvas',12*20+i)%96+32) for i in range(16,19));assert value in ('ON ','OFF'),value
  label=''.join(chr(v('canvas',12*20+i)%96+32) for i in range(1,14));assert label.strip()=='VELOCITY VIEW',label
  press('a');p.tick(30)
 print('PASS: no sequencer pattern label, no drum mode entry, clean mixer row below pads')
finally:p.stop(save=False)

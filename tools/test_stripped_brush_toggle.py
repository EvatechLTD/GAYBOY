"""Real DMG input: deferred A+B brush, direction lock and both button orders."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
for track,rownum in ((6,2),(6,3),(0,0)):
 for order in ('ab','ba','same'):
  exec(prefix)
  try:
   enter_app(p,S);put('seqtrack',track);put('drumrow',rownum);put('seqhead',0);put('seqfocus',0);put('seqdefaultdur',1,track*2);put('seqdefaultdur',0,track*2+1);put('seqdrawvalid',0);put('dirty',1);p.tick(100)
   def steps():
    n=v('seqeventcounts',track*2)|v('seqeventcounts',track*2+1)<<8
    return sorted(p.memory[1,0xa300+i*4] for i in range(n))
   def chord():
    if order=='same':p.button_press('a');p.button_press('b')
    else:p.button_press(order[0]);p.tick(4);p.button_press(order[1])
    p.tick(30)
   def release():p.button_release('a');p.button_release('b');p.tick(40)
   def move(key):press(key);p.tick(20)
   # Empty start: forming and releasing chord alone never leaves a note.
   chord();assert steps()==[],(track,order,'eager plot',steps());release();assert steps()==[]
   chord();move('right');assert steps()==[0,1],(track,order,steps())
   move('right');assert steps()==[0,1,2]
   move('left');assert steps()==[0,1,2],('paint lock reversed',steps())
   release()
   # Start on existing note: no change until movement; erase includes start.
   put('seqcursor',2,track);put('dirty',1);p.tick(30);chord();assert steps()==[0,1,2]
   move('left');assert steps()==[0],('erase start',track,order,steps())
   move('right');assert steps()==[0],('erase lock reversed',steps())
   move('left');move('left');assert steps()==[]
   move('left');assert v('seqcursor',track)==0 and steps()==[],('edge clamp',steps())
   release()
   # Fresh hold resets direction. Painting preserves occupied cells.
   chord();move('right');release();chord();move('right');assert steps()==[0,1,2];release()
   # Erasing from an empty cell does not create a provisional B-first note.
   put('seqcursor',3,track);put('dirty',1);p.tick(30);chord();assert steps()==[0,1,2]
   move('left');assert steps()==[0,1];release()
  finally:p.stop(save=False)
print('PASS: deferred first cell, left erase, right paint, direction lock, release reset, button orders, edge clamp on pulse and drum/sample grids')

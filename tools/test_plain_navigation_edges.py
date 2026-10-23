"""Plain navigation uses edge release latches without selection or edit buttons."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_gesture_page_edges.py').read_text().split('\ntry:')[0])
def plain(c,direction,zoom=1,beats=4,playing=False):
 setup(c,'nav',direction,playing,zoom,beats)
 assert get('seqgrouptrack')==255 and not get('seqapending')
 oldbase=get('seqbase');oldtop=get('seqtop',c);cols=get('seqcols');rows=get('seqrows')
 target=oldbase if direction=='left' else oldbase+cols-1 if direction=='right' else oldtop if direction=='up' else oldtop-rows+1
 key(direction,True);p.tick(480)
 actual=get('seqpitch',c) if direction in ('up','down') else get('seqcursor',c)
 assert actual==target and not get('seqhead'),('plain navigation escaped edge',c,direction,target,actual,get('seqhead'))
 assert get('seqbase')==oldbase and get('seqtop',c)==oldtop
 key(direction,False);key(direction,True)
 if direction in ('left','right'):
  base=oldbase+(-cols if direction=='left' else cols);wait_page(c,base)
  assert get('seqcursor',c)==target+(-1 if direction=='left' else 1),'wrong opposite-side entry'
  assert get('seqcursor',c)-base==(cols-1 if direction=='left' else 0)
 elif direction=='up':assert get('seqhead') and get('seqtop',c)==oldtop,'header access was lost'
 else:
  wait_page(c,oldbase,oldtop-1);assert get('seqpitch',c)==target-1
  p.tick(120);assert get('seqtop',c)<oldtop-1,'retained one-row scrolling latched every row'
 key(direction,False)
 assert get('seqgrouptrack')==255,'navigation created a selection'
 print('PASS plain',c,direction,'zoom',zoom,'meter',beats,'playing',playing,flush=True)
try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot)
 for c in (0,1,2,6):
  for direction in ('left','right'):plain(c,direction)
 for c in (0,1,2):
  for direction in ('up','down'):plain(c,direction)
 for zoom in (0,2):
  for direction in ('left','right','up','down'):plain(1,direction,zoom=zoom)
 for direction in ('left','right','up','down'):plain(1,direction,beats=3)
 for direction in ('left','right','up','down'):plain(1,direction,playing=True)
 setup(1,'nav','left');put('seqcursor',16,1);put('seqhead',6);put('seqdrawvalid',0);put('dirty',1);p.tick(360)
 key('left',True);wait_page(1,0);assert get('seqcursor',1)==15 and not get('seqhead'),'piano page shortcut wrong entry'
 p.tick(480);assert get('seqcursor',1)==0 and not get('seqhead'),'held shortcut escaped first cell'
 key('left',False);key('left',True);assert get('seqhead')==6,'first-page piano access lost';key('left',False)
 print('PASS piano-page shortcut and first-cell release latch',flush=True)
finally:p.stop(save=False)

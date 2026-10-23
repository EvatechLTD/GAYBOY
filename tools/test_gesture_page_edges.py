"""Real held gestures stop on all four edges; repress enters the opposite edge."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'b':32,'left':2,'right':1,'up':4,'down':8,'select':64}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(1800):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def tap(n):key(n,True);key(n,False)
def setup(c,kind,direction,playing=False,zoom=1,beats=4):
 boot.seek(0);p.load_state(boot);offset=0
 group=kind.startswith('group');resize='resize' in kind;left=direction=='left'
 width=(beats*4+1)//2 if zoom==0 else min(32,beats*4*(2 if zoom==2 else 1))
 step=0 if resize else width+4 if left else 4
 duration=width+5 if resize and left else 5 if resize else 1
 cursor=duration-1 if resize else step
 voices=[2,3,4] if c==6 and group else [3] if c==6 else [61,65,68] if group else [61]
 tracks=[[] for _ in range(7)];tracks[c]=[[step,n,100,duration] for n in voices]
 if playing:
  if c!=2:tracks[2]=[[s,n,100,8] for s,n in zip((0,8,16,24),(37,37,40,35))]
  tracks[6]=[[i,11,100,1] for i in range(32)]+[[i,12,100,1] for i in (4,12,20,28)]+[[i,13,100,1] for i in (0,8,16,24)]
 for t,events in enumerate(tracks):
  word('seqeventoffsets',offset,t*2);word('seqeventcounts',len(events),t*2);word('seqlength',64,t*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('page',8);put('seqtrack',c);put('selected',c if c<3 else 2);put('seqzoom',zoom);put('seqbeats',beats);put('seqdenom',4);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127);put('seqcursor',cursor,c);put('seqpitch',60,c);put('seqtop',64 if zoom==0 else 71,c);put('drumrow',5);put('seqdrawvalid',0);put('dirty',1);put('pattern_dirty',1);word('seqglobalbpm',120);word('seqbpm',120)
 if c<3:put('evalpatch',1,c*16+13)
 if playing and c==1:put('evalpatch',1,16);put('evalpatch',3,18)
 if group:
  put('seqgrouptrack',c);put('seqgroupx0',step);put('seqgroupx1',step);put('seqgroupy0',4 if c==6 else 60);put('seqgroupy1',6 if c==6 else 67)
 if playing:key('select',True);tap('a');key('select',False)
 p.tick(360)
 return cursor
def wait_page(c,base,top=None):
 for _ in range(1800):
  p.tick(1)
  if get('seqviewbase')==base and (top is None or get('seqviewtop')==top) and get('seqdrawvalid') and get('seqfontdirty'):return
 raise AssertionError(('page did not publish',c,base,top,get('seqcursor',c),get('seqbase'),get('seqviewbase'),get('seqtop',c),get('seqviewtop')))
def gesture(c,kind,direction,playing=False,zoom=1,beats=4):
 setup(c,kind,direction,playing,zoom,beats);button='b' if 'resize' in kind else 'a'
 if kind=='box':put('seqpitch',69,c);put('dirty',1);p.tick(120)
 oldtop=get('seqtop',c);oldbase=get('seqbase');rows=get('seqrows');cols=get('seqcols')
 endpoint=oldbase if direction=='left' else oldbase+cols-1 if direction=='right' else oldtop if direction=='up' else oldtop-rows+1
 key(button,True);key(direction,True);p.tick(480)
 actual=get('seqpitch',c) if direction in ('up','down') else get('seqcursor',c)
 assert actual==endpoint,(c,kind,direction,'overshot/stopped early',actual,endpoint,get('seqgestureblocked'))
 assert get('seqbase')==oldbase and get('seqtop',c)==oldtop
 p.tick(120);assert (get('seqpitch',c) if direction in ('up','down') else get('seqcursor',c))==endpoint,'held edge escaped'
 key(direction,False);key(direction,True)
 # Stop at the first published destination, before its fresh repeat delay.
 newbase=oldbase-cols if direction=='left' else oldbase+cols if direction=='right' else oldbase
 newtop=oldtop+rows if direction=='up' else oldtop-rows if direction=='down' else oldtop
 wait_page(c,newbase,newtop if c!=6 else None)
 expected=endpoint-1 if direction in ('left','down') else endpoint+1
 actual=get('seqpitch',c) if direction in ('up','down') else get('seqcursor',c)
 assert actual==expected,(c,kind,direction,'wrong entry',actual,expected,get('seqviewbase'),get('seqviewtop'))
 if direction=='left':assert actual-newbase==cols-1
 if direction=='right':assert actual-newbase==0
 if direction=='up':assert newtop-actual==rows-1
 if direction=='down':assert newtop-actual==0
 key(direction,False);key(button,False)
 print('PASS',c,kind,direction,'ARP beat' if playing else '',flush=True)
try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot)
 for c in (0,1,2,6):
  for kind in ('move','resize','group_move','group_resize'):
   for direction in ('right','left'):gesture(c,kind,direction)
 for c in (0,1,2):
  for kind in ('move','group_move'):
   for direction in ('up','down'):gesture(c,kind,direction)
 for direction in ('right','left','up','down'):gesture(1,'group_move',direction,True)
 for direction in ('right','left','up','down'):gesture(1,'box',direction)
 for zoom in (0,2):
  for direction in ('right','left','up','down'):gesture(1,'group_move',direction,zoom=zoom)
  for direction in ('right','left'):gesture(1,'group_resize',direction,zoom=zoom)
 for direction in ('right','left','up','down'):gesture(1,'group_move',direction,beats=3)
 for direction in ('right','left'):gesture(1,'group_resize',direction,beats=3)
 for c in (1,2,6):
  setup(c,'group_resize','right')
  for i in range(3):p.memory[1,0xa303+i*4]=16
  put('seqcursor',0,c);put('seqdrawvalid',0);put('dirty',1);p.tick(360)
  key('b',True);key('right',True);p.tick(480)
  assert get('seqcursor',c)==15 and all(p.memory[1,0xa303+i*4]==16 for i in range(3)),('body resize skipped screen edge',c)
  key('right',False);key('right',True);wait_page(c,16)
  assert get('seqcursor',c)==16 and all(p.memory[1,0xa303+i*4]==17 for i in range(3))
  key('right',False);key('b',False);print('PASS resize from note body',c,flush=True)
 for direction,bound in (('up',0),('down',12)):
  setup(6,'move',direction);key('a',True);key(direction,True);p.tick(480)
  assert get('drumrow')==bound and not get('seqhead')
  key(direction,False);key(direction,True);p.tick(60);assert get('drumrow')==bound and not get('seqhead')
  key(direction,False);key('a',False);print('PASS drum voice boundary',direction,flush=True)
 for c in (0,1,2,6):
  setup(c,'move','left');put('seqcursor',16,c);put('seqdrawvalid',0);put('dirty',1);p.tick(360)
  tap('left');wait_page(c,0);assert get('seqcursor',c)==15 and not get('seqhead')
  tap('right');wait_page(c,16);assert get('seqcursor',c)==16
  print('PASS plain page entry',c,flush=True)
finally:p.stop(save=False)

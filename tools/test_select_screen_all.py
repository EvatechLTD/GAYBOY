"""Menu selections keep screen scope separate from whole-track group edits."""
from pathlib import Path
exec(Path('tools/test_live_note_plot.py').read_text().split('\ntry:')[0])

def menu(item):
 put('navopen',1);put('navcategory',1);put('navchoice',item);put('dirty',1)
 p.tick(10);tap('a');assert not get('navopen')

def records(c):
 return [bytes(p.memory[1,0xa300+i*4:0xa304+i*4]) for i in range(get('seqeventcounts',c*2))]

try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot);calls=[]
 for c in (0,2,6):
  setup(c,24 if c==2 else 60 if c==0 else 0)
  events=([[2,61,110,2],[6,63,110,2],[20,61,110,2],[4,85,110,2]] if c==0 else
          [[2,25,110,2],[6,27,110,2],[20,25,110,2],[4,49,110,2]] if c==2 else
          [[2,11,110,2],[6,12,110,2],[20,11,110,2],[4,13,110,2]])
  for t in range(7):
   word('seqeventoffsets',0 if t<=c else len(events),t*2)
   word('seqeventcounts',len(events) if t==c else 0,t*2);word('seqlength',32,t*2)
  for i,e in enumerate(events):p.memory[1,0xa300+i*4:0xa304+i*4]=e
  put('seqcursor',2,c);put('dirty',1);p.tick(30)
  before=records(c);menu(53)
  assert records(c)==before,'Selection changed note data'
  assert get('seqgrouptrack')==c and get('seqgroupx0')==2 and get('seqgroupx1')==6
  key('b',True);tap('right');key('b',False)
  after=records(c)
  assert [e[3] for e in after]==([3,3,2,3] if c==6 else [3,3,2,2]),after
  menu(38)
  assert get('seqgrouptrack')==c and get('seqgroupx0')==2 and get('seqgroupx1')==20
  key('b',True);tap('right');key('b',False)
  after=records(c)
  assert [e[3] for e in after]==([4,4,3,4] if c==6 else [4,4,3,3]),after
  print('PASS screen selection vs all-track resize including hidden page/octave',c,flush=True)
finally:p.stop(save=False)

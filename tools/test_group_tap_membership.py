"""Cached group membership respects selection changes, edits and index255."""
from pathlib import Path
exec(Path('tools/test_black_note_overlap.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'b':32,'up':4,'down':8,'right':1,'left':2}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def tap(n):key(n,True);key(n,False);p.tick(120)
def events():
 n=get('seqeventcounts',2)|(get('seqeventcounts',3)<<8)
 return [list(p.memory[1,0xa300+i*4:0xa304+i*4]) for i in range(n)]
def box(x0,x1,pitch):
 put('seqhead',0);put('seqapending',0);put('seqcursor',x0,1);put('seqpitch',pitch,1)
 put('seqgrouptrack',1);put('seqgroupx0',x0);put('seqgroupx1',x1);put('seqgroupy0',pitch);put('seqgroupy1',pitch);put('seqdrawvalid',0);put('dirty',1);p.tick(240)
try:
 enter_app(p,symbols);put('evalpatch',1,29)
 initial=[[s,61,100,2] for s in (0,2,4,6,8)]
 install([[],initial,[],[],[],[],[]],1);box(0,2,60)
 key('a',True)
 for _ in range(3):tap('up')
 key('a',False)
 assert [e[1] for e in events()]==[64,64,61,61,61]
 box(4,6,60);key('a',True);tap('up');key('a',False)
 assert [e[1] for e in events()]==[64,64,62,62,61],'selection cache reused old box'
 # A normal erase compacts the records and changes the count/generation.
 put('seqcursor',4,1);put('seqpitch',61,1);tap('b');assert len(events())==4
 box(6,6,61);key('a',True);tap('up');key('a',False)
 assert events()==[[0,64,100,2],[2,64,100,2],[6,63,100,2],[8,61,100,2]]
 install([[],[[0,61,100,2],[2,61,100,2]],[],[],[],[],[]],1);box(0,2,60)
 key('a',True);tap('up');key('a',False);assert [e[1] for e in events()]==[62,62]
 # Simulate an external same-count data edit, with its required generation bump.
 p.memory[1,0xa305]=61;word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1)
 key('a',True);tap('up');key('a',False)
 assert [e[1] for e in events()]==[63,61],'same-count mutation reused stale membership'
 install([[],[[0,61,100,4],[5,61,100,4]],[],[],[],[],[]],1);box(0,0,60)
 key('a',True);tap('right');assert events()[0][0]==1
 tap('right');assert events()[0][0]==1,'collision was admitted'
 tap('left');key('a',False);assert events()[0][0]==0
 install([[],[[0,128,100,0]],[],[],[],[],[]],1);word('seqlength',256,2);box(0,0,127)
 key('a',True);tap('up');assert events()[0]==[0,128,100,0]
 tap('down');tap('up');key('a',False);assert events()[0]==[0,128,100,0]
 install([[],[[i,61,100,1] for i in range(256)],[],[],[],[],[]],1);word('seqlength',256,2);box(255,255,60)
 key('a',True);tap('up');key('a',False)
 # The initial 256-record scan may allow a held UP repeat before its release
 # is handled; every accepted movement must still affect only event255.
 assert len(events())==256 and events()[-1]==[255,get('seqgroupy0')+1,100,1] and events()[-1][1]>61 and all(e[1]==61 for e in events()[:-1])
 print('PASS membership invalidation,compaction,collision checks,note127,duration256,and event255')
finally:p.stop(save=False)

"""Header font/focus changes must preserve dynamic tile counts and selection."""
from pathlib import Path
exec(Path('tools/test_black_note_overlap.py').read_text().split('\ntry:')[0])
def refs():
 expected=[0]*120
 for i in range(360):
  tile=get('canvas',i)
  index=tile-64 if 64<=tile<96 else tile-128 if 160<=tile<244 else tile-136 if tile>=252 else -1
  if index>=0:expected[index]+=1
 actual=[get('rollonsets',i*2)|(get('rollonsets',i*2+1)<<8) for i in range(120)]
 assert actual==expected,[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
try:
 enter_app(p,symbols);put('evalpatch',1,29)
 install([[],[[0,61,100,16],[0,63,90,16],[0,65,80,16]],[],[],[],[],[]],1);refs()
 for i in range(6):
  mode(1 if i%2==0 else 0);refs()
  put('seqpitch',get('seqtop',1),1);put('dirty',1);p.tick(30);tap('up');assert get('seqhead')==1;refs()
  put('seqhead',2+i%3);put('dirty',1);p.tick(60);refs()
  put('seqhead',0);put('seqgrouptrack',1);put('seqgroupx0',0);put('seqgroupx1',4);put('seqgroupy0',60);put('seqgroupy1',64);put('seqdrawvalid',2);put('dirty',1);p.tick(120);refs()
  actual=grid();put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(240);assert grid()==actual,'Header transition corrupted selection pixels';refs()
  put('seqgrouptrack',255);put('seqdrawvalid',2);put('dirty',1);p.tick(120);refs()
 print('PASS repeated grid/header/mode changes preserve dynamic tile references and selection pixels')
finally:p.stop(save=False)

"""Edit > Duplicate: same rows, adjacent selection, atomic capacity/bounds checks."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
for track in (6,0):
 exec(prefix)
 try:
  enter_app(p,S)
  # Empty resident pool for each instrument case.
  for i in range(14):put('seqeventcounts',0,i);put('seqeventoffsets',0,i)
  put('seqtrack',track);put('seqcursor',0,track);put('seqhead',0);put('seqfocus',0);put('drumrow',5);put('seqgrouptrack',255);put('seqdefaultdur',1,track*2);put('seqdefaultdur',0,track*2+1);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  for step in (0,2):put('seqcursor',step,track);put('dirty',1);p.tick(10);press('b');p.tick(90)
  put('seqgrouptrack',track);put('seqgroupx0',0);put('seqgroupx1',3);put('seqgroupy0',5 if track==6 else v('seqpitch',track));put('seqgroupy1',v('seqgroupy0'));put('seqdrawvalid',2);put('dirty',1);p.tick(30)
  def records():
   count=v('seqeventcounts',track*2)|v('seqeventcounts',track*2+1)<<8
   p.memory[0x4000]=1;data=[list(p.memory[0xa300+i*4:0xa304+i*4]) for i in range(count)];p.memory[0x4000]=0;return data
  original=records();menu(46);p.tick(180);result=records()
  assert result==original+[[e[0]+4,*e[1:]] for e in original],(track,result)
  assert v('seqgroupx0')==4 and v('seqgroupx1')==7
  menu(46);p.tick(180);assert len(records())==6 and sorted(e[0] for e in records())==[0,2,4,6,8,10]
  # Next duplicate fits the pattern, the following one must fail atomically.
  menu(46);p.tick(180);before=records();assert len(before)==8
  p.button_press('start');p.tick(20);put('navchoice',46);p.button_release('start');p.tick(100)
  assert v('navopen') and records()==before,'Out-of-bounds duplicate must make no changes'
  press('select');p.tick(30)
  # The complete duplicate must fit the shared 256-note budget.
  put('seqgroupx0',0);put('seqgroupx1',3);put('seqlength',0,track*2);put('seqlength',1,track*2+1);put('seqeventcounts',255,track*2);put('seqeventcounts',0,track*2+1)
  for c in range(7):put('seqeventoffsets',0 if c<=track else 255,c*2);put('seqeventoffsets',0,c*2+1)
  p.memory[0x4000]=1
  for i in range(8,255):p.memory[0xa300+i*4:0xa304+i*4]=[16+(i-8)%240,original[0][1]+(i>=248),127,1]
  before=bytes(p.memory[0xa300:0xa300+1024]);p.memory[0x4000]=0
  put('seqdrawvalid',0);put('dirty',1);p.tick(240);assert v('page')==8,('capacity render crash',track,hex(p.register_file.PC),hex(p.register_file.SP))
  p.button_press('start');p.tick(20);assert v('navopen'),('menu failed',track);put('navchoice',46);p.button_release('start');p.tick(100)
  assert v('navopen') and v('seqeventfull'),(track,v('navopen'),v('seqeventfull'),v('seqgrouptrack'),v('seqgroupx0'),v('seqgroupx1'),v('seqeventcounts',track*2),v('seqeventcounts',track*2+1),v('page'),v('navchoice'),hex(p.register_file.PC),hex(p.register_file.SP))
  p.memory[0x4000]=1;after=bytes(p.memory[0xa300:0xa300+1024]);p.memory[0x4000]=0;assert before==after,'Capacity failure changed notes'
  press('select');p.tick(30)
 finally:p.stop(save=False)
print('PASS: adjacent same-row duplicate, repeated duplication, atomic boundary/capacity failure')

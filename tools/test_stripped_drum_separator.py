"""Drum synth/sample separator stays empty with selection and velocity bars."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
exec(helpers)
try:
 enter_app(p,S)
 for velocity in (False,True):
  put('seqvelocityhidden',not velocity);put('drumrow',2);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  assert v('seqgridheight')==(112 if velocity else 128)
  press('down');assert v('drumrow')==3
  press('up');assert v('drumrow')==2
  put('seqgrouptrack',6);put('seqgroupx0',0);put('seqgroupx1',7);put('seqgroupy0',0);put('seqgroupy1',5);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  assert not any(tilepixel(x,y) for y in range(24,32) for x in range(160))
  put('seqgroupx1',8);put('seqdrawvalid',2);put('dirty',1);p.tick(120)
  image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid()
  put('seqgrouptrack',255);put('drumrow',12);put('seqcursor',int(velocity),6);put('seqdefaultdur',1,12);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  press('b');p.tick(100)
  x=28+int(velocity)*8
  assert tilepixel(x,107)==3,(velocity,'last sample row missing')
  p.screen.image.save('build/stripped-drum-separator'+('-velocity' if velocity else '')+'.png')
 print('PASS: one blank separator row, selection across gap, navigation and all ten samples with velocity on/off')
finally:p.stop(save=False)

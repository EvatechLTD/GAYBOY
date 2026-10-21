"""Back-to-back painted kicks delete individually and retain tiny tails."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
for rownum in (2,3):
 exec(prefix);exec(helpers)
 try:
  enter_app(p,S);put('drumrow',rownum);put('seqdefaultdur',0,12);put('seqdefaultdur',0,13);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  p.button_press('a');p.tick(3);p.button_press('b');p.tick(60)
  for _ in range(7):press('right');p.tick(70)
  p.button_release('a');p.button_release('b');p.tick(180)
  assert count()==8,notes()
  for step in range(1,8):
   end=24+(step*136)//16
   assert tilepixel(end-1,(rownum+(1 if rownum>=3 else 0))*8+3)==0,('missing hit separator',rownum,step)
  for step in (4,0,7,2,1,3,5,6):
   put('seqcursor',step,6);put('dirty',1);p.tick(30);before=count();press('b');p.tick(180);assert count()==before-1,('B did not erase painted hit',rownum,step,notes())
  assert count()==0
 finally:p.stop(save=False)
print('PASS: painted pulse/sample kicks have onset gaps and each deletes with a B tap')

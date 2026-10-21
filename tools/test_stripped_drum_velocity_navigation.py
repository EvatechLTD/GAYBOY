"""Every drum lane keeps its velocity display after row navigation."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
exec('def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0])
def bars():return bytes(tilepixel(x,y) for y in range(112,136) for x in range(24,160))
try:
 enter_app(p,S);put('seqdefaultdur',1,12);put('seqdefaultdur',0,13)
 for rownum in range(13):
  put('drumrow',rownum);put('seqcursor',2,6);put('eval_plotvel',20+rownum*8,6);put('seqdrawvalid',0);put('dirty',1);p.tick(180);press('b');p.tick(100)
 put('seqvelocityhidden',0);put('drumrow',0);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 for rownum in range(13):
  if rownum:press('down');p.tick(120)
  assert v('drumrow')==rownum,(rownum,v('drumrow'))
  image=bars();assert 3 in image,('missing bars',rownum)
  put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==bars(),('navigation/full mismatch',rownum)
 menu(18);p.tick(180);p.screen.image.save('build/stripped-mixer-after-velocity.png')
 print('PASS: velocity bars on all thirteen populated drum rows survive downward navigation')
finally:p.stop(save=False)

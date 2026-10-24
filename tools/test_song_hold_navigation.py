"""Song left/right holds repeat across pages and stop exactly on release."""
from pathlib import Path
exec(Path('tools/test_thong_mode.py').read_text().split('\ntry:\n')[0])
try:
 enter_app(p,S);put('sticky_start',1);choose_song()
 key('right',True);p.tick(150);key('right',False)
 end=cursor();assert end>=256,('Held right did not cross a page',end)
 p.tick(60);assert cursor()==end,'Release left repeat debt'
 key('select',True);tap('right');key('select',False)
 assert cursor()==end+256,'Select+Right did not advance exactly one page'
 key('select',True);tap('left');key('select',False)
 assert cursor()==0,'Select+Left did not return to song beginning'
 key('right',True);p.tick(150);key('right',False)
 key('left',True);p.tick(220);key('left',False)
 assert cursor()==0,('Held left did not stop at song origin',cursor())
 tap('b');assert clips()==[(0,16,0)]
 key('b',True);key('right',True);p.tick(75);key('right',False);key('b',False)
 assert len(clips())==1 and clips()[0][1]>32,('Held resize failed',clips())
 length=clips()[0][1];p.tick(60);assert clips()==[(0,length,0)]
 print('PASS held L/R page crossing, release, origin clamp and repeated B-resize')
finally:p.stop(save=False)

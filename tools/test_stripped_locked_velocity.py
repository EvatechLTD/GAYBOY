"""Locked drum velocity source, channel-name access and localized slider edits."""
from pathlib import Path
import json
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
exec('def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0])
def count():return v('seqeventcounts',12)|v('seqeventcounts',13)<<8
def records():
 return [list(p.memory[1,0xa300+i*4:0xa304+i*4]) for i in range(count())]
try:
 enter_app(p,S);put('seqdefaultdur',1,12);put('seqdefaultdur',0,13)
 for rownum,velocity in ((0,90),(3,110),(12,70)):
  put('drumrow',rownum);put('seqcursor',0,6);put('eval_plotvel',velocity,6);put('seqdrawvalid',0);put('dirty',1);p.tick(180);press('b');p.tick(100)
 put('drumrow',3);put('seqcursor',0,6);put('seqhead',0);put('dirty',1);p.tick(30);press('left');assert v('seqhead')==6
 press('a');p.tick(180);assert v('seqhead')==5 and v('drumvelrow')==3 and v('seqcursor',6)==0
 rebuild=[];ptr=S['_drum_render'];p.hook_register(ptr>>16,ptr&65535,lambda _:rebuild.append(p._cycles()),None)
 before=grid();p.button_press('b');p.tick(3);start=p._cycles();press('up',1)
 for _ in range(120):
  if any(e[1]==1 and e[2]==111 for e in records()) and v('padread')==v('padwrite'):break
  p.tick(1)
 latency=(p._cycles()-start)*1000/4194304;p.button_release('b');p.tick(30)
 assert any(e[1]==1 and e[2]==111 for e in records()),records();assert not rebuild,'Velocity edit rebuilt the grid'
 assert before[:112*136]==grid()[:112*136],'Velocity edit altered note-grid pixels'
 # Held editing publishes while the edit button remains down.
 p.button_press('b');p.tick(3);p.button_press('up');p.tick(120);p.button_release('up');p.tick(8)
 assert any(e[1]==1 and e[2]==127 for e in records()) and tilepixel(28,115)==3,'Held slider update waited for button release'
 p.button_release('b');p.tick(20)
 # Leaving the sliders and moving onto other rows leaves this source pinned.
 press('up');assert v('seqhead')==6;press('right');assert v('seqhead')==0
 image=bytes(tilepixel(x,y) for y in range(112,136) for x in range(160))
 for _ in range(9):press('down')
 p.tick(100);assert v('drumrow')==12 and v('drumvelrow')==3
 assert image==bytes(tilepixel(x,y) for y in range(112,136) for x in range(160)),'Navigation changed the locked panel'
 press('left');press('b');p.tick(180);assert v('drumvelrow')==12 and v('seqhead')==5
 # All zoom sizes can show the panel; changing row names does not change zoom.
 for zoom in (0,1,2,3):
  put('seqzoom',zoom);put('seqhead',6);put('drumrow',0);put('seqdrawvalid',0);put('dirty',1);p.tick(180);press('a');p.tick(180)
  assert v('seqzoom')==zoom and v('seqgridheight')==112 and v('drumvelrow')==0
  image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid(),('bar render mismatch',zoom,[(24+i%136,i//136,a,b) for i,(a,b) in enumerate(zip(image,grid())) if a!=b][:24])
 # Grid endpoints constrain, while longer patterns page via their channel label.
 put('seqzoom',1);put('seqhead',0);put('seqlength',32,12);put('seqcursor',16,6);put('dirty',1);p.tick(180)
 press('left');assert v('seqhead')==6 and v('seqcursor',6)==16
 press('left');p.tick(180);assert v('seqhead')==0 and v('seqcursor',6)==15
 put('seqcursor',31,6);put('dirty',1);p.tick(180);press('right');assert v('seqhead')==0 and v('seqcursor',6)==31
 Path('build/stripped-locked-velocity.json').write_text(json.dumps({'slider_edit_ready_ms':latency,'grid_rebuilds_for_edit':0},indent=2)+'\n')
 p.screen.image.save('build/stripped-locked-velocity.png')
 print('PASS: locked source, names, all zoom sizes, pattern bounds, backwards paging, local velocity edit',latency)
finally:p.stop(save=False)

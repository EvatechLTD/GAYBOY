"""Local native chord edits match full pixels at every grid zoom."""
from pathlib import Path
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
for track in range(4):
 for zoom in range(4):
  exec(prefix);exec(helpers)
  try:
   enter_app(p,S);put('seqtrack',track);put('seqviewinitialized',127);put('seqzoom',zoom);put('seqtop',57,track);put('seqpitch',52,track);put('seqhead',0);put('seqfocus',0);put('evalpatch',int(track<3),track*16);put('evalpatch',1,track*16+13);put('seqdefaultdur',2,track*2);put('seqdefaultdur',0,track*2+1);put('rollcache',0);put('seqdrawvalid',0);put('dirty',1);p.tick(120)
   for pitch in (52,54):put('seqpitch',pitch,track);put('seqcursor',2,track);put('dirty',1);p.tick(20);press('b');p.tick(70)
   rebuild=[];addr=S['_seq_pixels'];p.hook_register(addr>>16,addr&65535,lambda _:rebuild.append(1),None)
   def compare():
    p.tick(60);before=bytes(tilepixel(x,y) for y in range(v('seqgridheight')) for x in range(16,160));assert not rebuild,(track,zoom,'full redraw');put('rollcache',0);put('seqdrawvalid',0);put('dirty',1);p.tick(150);after=bytes(tilepixel(x,y) for y in range(v('seqgridheight')) for x in range(16,160));assert before==after,(track,zoom,'pixels');rebuild.clear()
   put('seqpitch',52,track);put('dirty',1);p.tick(20);p.button_press('b');p.tick(4);press('right');p.button_release('b');compare()
   put('seqcursor',2,track);put('dirty',1);p.tick(20);p.button_press('a');p.tick(4);press('right');p.button_release('a');compare()
  finally:p.stop(save=False)
print('PASS: all four instruments, all four zooms, local drag/resize and chord pixels')

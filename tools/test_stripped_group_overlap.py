"""Conservative overlap fallback preserves ghost colors after group edits."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
exec('def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0])
try:
 enter_app(p,S);put('seqdefaultdur',1,12);put('seqdefaultdur',0,13)
 for rownum in (3,4,5):
  put('drumrow',rownum);put('seqcursor',2,6);put('seqdrawvalid',0);put('dirty',1);p.tick(180);press('b');p.tick(100)
 put('seqgrouptrack',6);put('seqgroupx0',1);put('seqgroupx1',3);put('seqgroupy0',0);put('seqgroupy1',5);put('drumrow',3);put('seqcursor',2,6);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 rebuild=[];ptr=S['_drum_render'];p.hook_register(ptr>>16,ptr&65535,lambda _:rebuild.append(p._cycles()),None)
 p.button_press('a');p.tick(8);press('right');p.tick(180);p.button_release('a');p.tick(30)
 assert rebuild,'PCM admission overlap must use the safe renderer'
 image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid(),'ghost pixels changed after full render'
 assert any(tilepixel(x,y)==2 for y in range(33,56) for x in range(24,64)),'ghost note missing'
 print('PASS: mixed synth/sample selection and three PCM voices preserve ghost fallback')
finally:p.stop(save=False)

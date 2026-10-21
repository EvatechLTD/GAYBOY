"""A velocity edit stays local with all256 resident note slots occupied."""
from pathlib import Path
import json
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
exec('def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0])
try:
 enter_app(p,S)
 for c in range(7):
  put('seqeventcounts',0,c*2);put('seqeventcounts',1 if c==6 else 0,c*2+1);put('seqeventoffsets',0,c*2);put('seqeventoffsets',0,c*2+1)
 put('seqlength',0,12);put('seqlength',1,13)
 p.memory[0x4000]=1
 for i in range(255):p.memory[0xa300+i*4:0xa304+i*4]=[16+i%240,11,90,1]
 p.memory[0xa6fc:0xa700]=[0,1,110,1];p.memory[0x4000]=0
 put('drumrow',3);put('seqcursor',0,6);put('seqhead',0);put('seqdrawvalid',0);put('dirty',1);p.tick(240);press('left');press('a');p.tick(240)
 assert v('drumvelrow')==3 and v('seqhead')==5
 calls={name:0 for name in ('seq_event_get','seq_event_next_step','drum_render','seq_pixels')}
 for name in calls:
  ptr=S['_'+name]
  def record(name):calls[name]+=1
  p.hook_register(ptr>>16,ptr&65535,record,name)
 p.button_press('b');p.tick(4);start=p._cycles();p.button_press('right');p.tick(1);p.button_release('right')
 for _ in range(120):
  if tilepixel(28,117)==3 and v('padread')==v('padwrite'):break
  p.tick(1)
 elapsed=(p._cycles()-start)*1000/4194304;p.button_release('b');p.tick(30)
 p.memory[0x4000]=1;record=list(p.memory[0xa6fc:0xa700]);p.memory[0x4000]=0
 assert record==[0,1,120,1],record
 assert elapsed<100 and calls['seq_event_get']<=3 and calls['seq_event_next_step']==0 and not calls['drum_render'] and not calls['seq_pixels'],(elapsed,calls)
 Path('build/stripped-velocity-dense.json').write_text(json.dumps({'visible_and_ready_ms':elapsed,'calls':calls},indent=2)+'\n')
 print('PASS:256 notes, direct hit handle, immediate velocity pixel change, no note scan or grid rebuild',elapsed,calls)
finally:p.stop(save=False)

"""Header controls keep the grid cache; mode recoloring matches a full render."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def press(key):
 p.button_press(key);p.tick(8);p.button_release(key);p.tick(100)
try:
 enter_app(p,symbols)
 offset=0
 for c in range(7):
  events=[[4,49,127,4],[4,53,100,4]] if c<3 else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('pattern_dirty',1)
 calls=[]
 for name in ('seq_pixels','drum_render'):
  ptr=symbols['_'+name];p.hook_register(ptr>>16,ptr&65535,lambda _,n=name:calls.append(n),None)
 for c in range(3):
  put('seqtrack',c);put('selected',c);put('seqhead',1);put('seqfocus',0);put('seqtop',60,c);put('seqpitch',48,c);put('seqdrawvalid',0);put('dirty',1);p.tick(200)
  for head in (1,2,3):
   put('seqhead',head);put('dirty',1);p.tick(60);calls.clear()
   press('a')
   assert not calls,(c,head,calls)
   if head==1:
    incremental=p.screen.image.copy().crop((16,8,160,112))
    put('seqdrawvalid',0);put('dirty',1);p.tick(200)
    assert incremental.tobytes()==p.screen.image.crop((16,8,160,112)).tobytes(),(c,'mode render mismatch')
   print('PASS header',c,head,flush=True)
  put('seqhead',4);put('dirty',1);p.tick(60);calls.clear()
  p.button_press('b');p.tick(3);press('up');p.button_release('b');p.tick(80)
  assert get('seqlength',c*2)==32,(c,'length did not double')
  assert not calls,(c,'offscreen length rebuilt grid',calls)
  print('PASS header length beyond viewport',c,flush=True)
finally:p.stop(save=False)

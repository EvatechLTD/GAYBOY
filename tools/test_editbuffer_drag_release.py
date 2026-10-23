"""Real drag gestures publish after D-pad release with A/B still held."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def waitkey(key,down):
 mask={'a':16,'b':32,'right':1,'up':4,'select':64}[key]
 (p.button_press if down else p.button_release)(key)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError((key,down))
def swaps():return get('editbuffer_swaps')|get('editbuffer_swaps',1)<<8
def event(c):return list(p.memory[1,0xa300+c*4:0xa304+c*4])
try:
 enter_app(p,symbols)
 offset=0
 for c in range(7):
  events=[[4,49 if c!=6 else 11,127,4]] if c in (0,1,2,6) else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('pattern_dirty',1);word('seqglobalbpm',120);word('seqbpm',120)
 waitkey('select',True);waitkey('a',True);waitkey('a',False);waitkey('select',False);p.tick(350)
 assert get('editbuffer_valid')
 fixture=BytesIO();p.save_state(fixture)
 for c in (0,1,2,6):
  for kind in ('move','resize','group_move','group_resize'):
   fixture.seek(0);p.load_state(fixture)
   put('seqdrawvalid',0);put('seqtrack',c);put('selected',c if c<3 else 2);put('seqhead',0);put('seqfocus',0);put('seqcursor',4,c);put('seqpitch',48,c);put('seqtop',60,c);put('drumrow',0);put('seqapending',0);put('seqgrouptrack',255);put('dirty',1);p.tick(60)
   if kind.startswith('group'):
    put('seqgrouptrack',c);put('seqgroupx0',4);put('seqgroupx1',4);put('seqgroupy0',0 if c==6 else 48);put('seqgroupy1',0 if c==6 else 48)
   button='b' if 'resize' in kind else 'a'
   before=swaps();generation=get('pattern_generation')|get('pattern_generation',1)<<8
   waitkey(button,True);waitkey('right',True);p.tick(2)
   assert (get('pattern_generation')|get('pattern_generation',1)<<8)!=generation,(c,kind,'no edit')
   assert swaps()==before,(c,kind,'published during movement')
   waitkey('right',False)
   for _ in range(250):
    p.tick(1)
    if swaps()>before:break
   assert swaps()>before,(c,kind,'D-pad release did not publish',get('seqapending'),get('seqamoved'))
   assert get('lastpad') & (32 if button=='b' else 16)
   waitkey(button,False)
   print('PASS',c,kind,flush=True)
finally:p.stop(save=False)

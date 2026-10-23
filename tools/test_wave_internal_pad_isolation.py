"""Actual B plotting/resizing and low Wave playback must never launch pads."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

def key(n,down):
 mask={'a':16,'b':32,'right':1,'select':64}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(600):
  p.tick(1)
  assert get('mx',1)==0 and get('mx',2)==255,'Internal edit launched/queued a pad'
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))

def tap(n):key(n,True);key(n,False)

try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot);requests=[]
 a=symbols['_mixer_launch_request'];p.hook_register(a>>16,a&65535,lambda _:requests.append(p.register_file.A),None)
 for enabled in (0,1):
  boot.seek(0);p.load_state(boot);requests.clear()
  for c in range(7):
   word('seqeventoffsets',0,c*2);word('seqeventcounts',16 if c==6 else 0,c*2);word('seqlength',16,c*2)
  for s in range(16):p.memory[1,0xa300+s*4:0xa304+s*4]=[s,11,100,1]
  put('syncmode',0);put('syncslave',0);put('syncarmed',0);p.memory[0xff02]=0
  put('midi_launch_enabled',enabled);put('seqtrack',2);put('selected',2);put('page',8)
  put('seqhead',0);put('seqfocus',0);put('seqtop',31,2);put('pattern_dirty',1);word('seqbpm',120);word('seqglobalbpm',120)
  for i,note in enumerate(range(24,29)):
   put('seqcursor',i*3,2);put('seqpitch',note,2);put('seqdrawvalid',0);put('dirty',1);p.tick(120);tap('b')
  assert get('seqeventcounts',4)==5,'B plotting failed to retain all low Wave notes'
  key('select',True);tap('a');key('select',False);p.tick(120)
  put('seqcursor',0,2);put('seqpitch',24,2);put('seqdrawvalid',0);put('dirty',1);p.tick(120)
  key('b',True);tap('right');tap('right');key('b',False)
  for _ in range(600):
   p.tick(1)
   assert get('seqplaying') and get('mx',1)==0 and get('mx',2)==255,'Low note playback stopped or switched pads'
  assert not requests,('Internal notes reached pad launcher',requests)
  print('PASS low Wave B plotting/resizing, hats and repeated loop playback; MIDI launch',enabled,flush=True)
finally:p.stop(save=False)

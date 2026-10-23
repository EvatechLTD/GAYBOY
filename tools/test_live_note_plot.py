"""Stopped plotting/painting auditions sound; erasure and playing edits do not."""
from pathlib import Path
from io import BytesIO
import numpy as np
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

def key(n,down):
 mask={'a':16,'b':32,'right':1,'select':64,'start':128}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  assert get('mx',1)==0 and get('mx',2)==255,'Audition reached MIDI pad launcher'
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))

def tap(n):key(n,True);key(n,False)

def setup(c,note):
 boot.seek(0);p.load_state(boot);calls.clear()
 for t in range(7):
  word('seqeventoffsets',0,t*2);word('seqeventcounts',0,t*2);word('seqlength',16,t*2)
 put('syncmode',0);put('syncarmed',0);p.memory[0xff02]=0
 put('midi_launch_enabled',1);put('page',8);put('seqtrack',c);put('selected',c if c<3 else 2)
 put('seqhead',0);put('seqfocus',0);put('seqzoom',1);put('seqvelocityhidden',1);put('seqviewinitialized',127)
 put('seqcursor',0,c);put('seqpitch',note if c<3 else 60,c);put('seqtop',note+7 if c<3 else 67,c)
 put('drumrow',note if c==6 else 0);put('seqdrawvalid',0);put('dirty',1);put('pattern_dirty',1)
 word('seqbpm',120);word('seqglobalbpm',120);p.tick(120)

def silent_owner(c):
 assert not get('seqauditionnote'),'Audition ownership stuck after release'
 if c<3:assert not get('active',c) and not get('keycount',c)
 else:
  assert not any(get('noiseleft',i) for i in range(8))
  assert not any(get('pulsekickleft',i) for i in range(4))
  assert not get('drumon',0) and not get('drumon',1)

try:
 enter_app(p,symbols);boot=BytesIO();p.save_state(boot);calls=[]
 a=symbols['_seq_plot_audition'];p.hook_register(a>>16,a&65535,lambda _:calls.append(p._cycles()),None)
 for c,note in ((0,60),(1,60),(2,24),(6,0),(6,1),(6,2),(6,3),(6,12)):
  setup(c,note);key('b',True)
  assert not get('seqplaying') and get('seqauditionnote')==note+1,(c,note,get('seqauditionnote'),get('seqplaying'),len(calls),get('eval_plotvel',c),get('mx',12+c),get('seqhead'),get('seqapending'))
  assert len(calls)==1 and get('seqeventcounts',c*2)==1
  audio=[p.sound.ndarray.copy()]
  for _ in range(3):p.tick(1);audio.append(p.sound.ndarray.copy())
  assert np.max(np.abs(np.concatenate(audio).astype(float)))>0,('No immediate audio',c,note)
  key('b',False);silent_owner(c)
  tap('b');assert get('seqeventcounts',c*2)==0 and len(calls)==1,'Erasure auditioned a note'
  silent_owner(c);print('PASS stopped plot, audible preview, release and erase',c,note,flush=True)
 for c,note in ((0,60),(2,24),(6,0)):
  setup(c,note);key('a',True);key('b',True);tap('right');tap('right')
  assert get('seqeventcounts',c*2)==3 and len(calls)==3,('Paint did not audition each inserted note',c,get('seqeventcounts',c*2),len(calls),get('seqcursor',c),get('seqapending'))
  key('b',False);key('a',False);silent_owner(c)
  print('PASS stopped paint auditions new cells',c,flush=True)
 setup(2,24);key('b',True);assert get('seqauditionnote')
 key('select',True);tap('a');key('select',False)
 assert get('seqplaying') and not get('seqauditionnote'),'Preview not retired before playback'
 key('b',False);p.tick(180);assert get('seqplaying'),'Release stopped playback'
 put('seqcursor',4,2);put('seqpitch',28,2);put('dirty',1);p.tick(60);before=len(calls)
 tap('b');assert len(calls)==before,'Playing plot took audition path'
 print('PASS transport retires preview; playing edits bypass audition',flush=True)
finally:p.stop(save=False)

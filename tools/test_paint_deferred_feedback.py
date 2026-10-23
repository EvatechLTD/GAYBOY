"""Deferred native velocity feedback catches up and matches a full redraw."""
from pathlib import Path
import numpy as np
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

def key(n,down):
 mask={'a':16,'b':32,'right':1,'left':2,'select':64}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError((n,down))
def tap(n):key(n,True);key(n,False)
def pending():return get('feedbackpending')|get('feedbackpending',1)<<8
try:
 enter_app(p,symbols)
 events=[[4,61,30,1],[4,65,100,1]]
 for c in range(7):
  word('seqeventoffsets',0 if c<2 else len(events),c*2);word('seqeventcounts',len(events) if c==1 else 0,c*2);word('seqlength',16,c*2)
 for i,e in enumerate(events):p.memory[1,0xa300+4*i:0xa304+4*i]=e
 put('seqzoom',1);put('seqvelocityhidden',0);put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqpitch',64,1);put('seqtop',71,1);put('seqcursor',4,1);put('seqviewinitialized',127);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 # Remove the upper overlapping onset through the ordinary cell editor.
 tap('b');p.tick(180)
 assert get('seqeventcounts',2)==1
 assert list(p.memory[1,0xa300:0xa304])==[4,61,30,1],'Wrong overlapping note removed'
 # A+B paints while bars remain queued; note data must already be present.
 key('a',True);key('b',True)
 for _ in range(7):tap('right')
 assert pending(),'Paint did not queue velocity feedback'
 count=get('seqeventcounts',2);assert count>=7,count
 key('b',False);key('a',False)
 for frames in range(600):
  p.tick(1)
  if not pending():break
 assert not pending(),'Velocity feedback did not drain'
 p.tick(5);before=p.screen.ndarray.copy()
 put('seqdrawvalid',0);put('dirty',1);p.tick(180);after=p.screen.ndarray.copy()
 assert np.array_equal(before[8:144,16:160],after[8:144,16:160]),'Deferred grid or bars differ from full rendering'
 assert get('seqeventcounts',2)==count,'Redrawing mutated notes'
 # Changing the viewport while an edit is staged discards obsolete geometry.
 tap('b');put('seqzoom',0);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 assert get('seqcols')==8
 before=p.screen.ndarray.copy();put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 assert np.array_equal(before[8:144,16:160],p.screen.ndarray[8:144,16:160]),'Viewport change retained stale edit pixels'
 print('PASS overlap,paint data,idle pixel catch-up and viewport cancellation',frames,'frames',flush=True)
finally:p.stop(save=False)

"""B draws/erases/resizes; A moves notes in melodic and drum rolls."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):fixture_put(p,S,n,i,x)
def hold(key='b'):p.button_press(key);p.tick(5)
def release(key='b'):p.button_release(key);p.tick(8)
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
try:
 choose(8)
 # A never plots on empty space; B immediately plots and extends a note.
 press('a');assert not v('seqnotes')
 pitch=v('seqpitch');hold();assert v('seqnotes')==pitch+1,'New note must plot when B is pressed'
 press('up');assert v('seqpitch')==pitch
 press('right');assert v('seqnotes')==pitch+1 and v('seqduration')==2,'Length drag must resize the plotted note before release'
 press('right');release()
 assert v('seqnotes')==pitch+1 and v('seqduration')==3
 assert v('seqdefaultdur')==3 and v('seqcursor')==2
 # B resizes an existing body without moving onset or pitch.
 hold();press('right');press('up')
 assert v('seqnotes')==pitch+1 and v('seqduration')==4 and v('seqpitch')==pitch
 press('left');release();assert v('seqduration')==3
 # Body grab moves the original onset, preserving body offset and duration.
 hold('a');press('right');press('up');release('a')
 assert not v('seqnotes') and v('seqnotes',1)==pitch+2
 assert v('seqduration',1)==3 and v('seqcursor')==3
 press('b');assert not v('seqnotes',1),'Move release must not erase; subsequent tap must erase'
 press('b');assert v('seqnotes',3)==pitch+2 and v('seqduration',3)==3
 press('b');assert not v('seqnotes',3)
 # Native noise drum rows have exact freely editable lengths, independent of PCM auto-length.
 chord('select','left');assert v('seqtrack')==6
 put('drumrow',0,10);put('seqcursor',6,0);put('seqhead',0,0);put('seqdefaultdur',6,1);put('dirty',0,1);p.tick(12)
 press('a');assert not v('noisehits')
 hold();assert v('noisehits')==1,'New drum note must plot when B is pressed'
 press('up');assert v('drumrow')==10
 press('right');press('right');release()
 assert v('noisehits')==1 and v('noisedur')==3 and v('seqdefaultdur',6)==3
 hold();press('right');press('down')
 assert v('noisehits')==1 and v('noisedur')==4 and v('drumrow')==10
 press('left');release();assert v('noisedur')==3
 hold('a');press('right');press('down');release('a')
 assert not v('noisehits') and v('noisehits',3)==1 and v('noisedur',3)==3
 assert v('drumrow')==11 and v('seqcursor',6)==1
 press('b');assert not v('noisehits',3)
 press('b');assert v('noisehits',3)==1 and v('noisedur',3)==3
 press('b');assert not v('noisehits',3)
 print('PASS: melodic/drum B drawing, erasing and resizing; A moving; anchored onsets, release safety and remembered lengths')
finally:p.stop(save=False)

exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):p.memory[S['_'+n]+i]=x
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
def drag(keys):
 p.button_press('a')
 for _ in range(60):
  p.tick(1)
  if v('lastpad')&16:break
 for k in keys:press(k)
 p.button_release('a');p.tick(60)
choose(8);p.tick(60)
press('a');assert v('seqnotes')==61
put('seqvelocity',0,63);put('seqduration',0,3)
# Holding A must leave the original note intact until movement is requested.
p.button_press('a');p.tick(50);assert v('seqnotes')==61
press('right');press('up');p.button_release('a');p.tick(60)
assert not v('seqnotes') and v('seqnotes',1)==62
assert v('seqduration',1)==3 and v('seqvelocity',1)==63
assert v('seqcursor')==1 and v('seqpitch')==61
# Pick up the body and preserve its grab offset.
press('right');drag(['right','down'])
assert not v('seqnotes',1) and v('seqnotes',2)==61
assert v('seqcursor')==3 and v('seqduration',2)==3 and v('seqvelocity',2)==63
# Reject collisions, and do not delete the grabbed note on release.
put('seqnotes',5,68);put('seqduration',5,1);put('seqvelocity',5,111)
drag(['right']);assert v('seqnotes',2)==61 and v('seqnotes',5)==68
assert v('seqcursor')==3
# Bounds prevent wrapping or clipping the dragged note.
put('seqcursor',0,2);drag(['left','left','left']);assert v('seqnotes')==61
assert v('seqcursor')==0 and v('seqduration')==3
put('seqpitch',0,0);put('seqnotes',0,1);drag(['down']);assert v('seqnotes')==1
# Velocity bars occupy y120..143 and track edits on the selected note.
put('seqpitch',0,60);put('seqnotes',0,61);put('seqvelocity',0,63)
put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(90)
assert v('seqgridheight')==112
before=int(p.screen.ndarray[133,20,0]);chord('b','up');p.tick(90)
after=int(p.screen.ndarray[133,20,0]);assert v('seqvelocity')==64 and after<before
p.screen.image.save('build/ui-sequencer-velocity.png')
# Quick A taps still erase and insert on release; empty-cell dragging also works.
press('a');assert not v('seqnotes')
drag(['right']);assert v('seqnotes',1)==61
press('a');assert not v('seqnotes',1)
# Drag across a page edge while retaining the original payload.
put('seqlength',0,32);put('seqcursor',0,15);put('seqnotes',15,61)
put('seqvelocity',15,90);put('seqduration',15,2)
drag(['right']);assert not v('seqnotes',15) and v('seqnotes',16)==61
assert v('seqvelocity',16)==90 and v('seqduration',16)==2 and v('seqbase')==16
p.stop(save=False)
print('PASS: A-drag time/pitch, body grab offset, duration/velocity preservation, collision/bounds safety, tap behavior, page crossing and velocity sliders')

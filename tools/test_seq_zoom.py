exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
import random

def put(n,i,x):p.memory[S['_'+n]+i]=x
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
def stable():p.tick(90)

choose(8);stable()
assert (v('seqzoom'),v('seqcols'),v('seqrows'))==(1,16,14)
assert [v('visible',i) for i in (18,19)]==[113,118]
# Verify actual rendered tones and one-pixel beat/bar lines.
px=p.screen.ndarray[:,:,0].astype(int)
assert px[10,16]<px[10,52]<px[10,25]<px[10,17]
assert px[10,53]==px[10,17]
# Actual pixel width covers all 16 cells and keeps the piano 16 pixels.
assert list(p.memory[0xBC80:0xBC80+17])==[16+i*144//16 for i in range(17)]
# Select+Up/Down zoom directly, preserving the current note.
chord('select','up');assert v('seqzoom')==0 and v('seqcols')==8
chord('select','down');assert v('seqzoom')==1 and v('seqcols')==16
# Header length editing uses the same per-track parameter as settings.
put('seqpitch',0,v('seqtop'));press('up');assert v('seqhead')==1
press('left');assert v('seqhead')==4
chord('b','right');assert v('seqlength')==26
press('a');press('up');press('a');assert v('seqlength')==27
press('down');assert not v('seqhead')
# Zoom is field 10; changing it preserves notes and cursor, and changes both axes.
press('a');note=v('seqnotes');cursor=v('seqcursor');pitch=v('seqpitch')
press('select');press('left');assert v('seqfocus')==10
for zoom,delta,cols,rows in ((3,'up',32,17),(0,'down',8,9),(2,'up',24,17),(1,'down',16,14)):
 while v('seqzoom')!=zoom:chord('b',delta)
 press('select');stable()
 assert (v('seqcols'),v('seqrows'))==(cols,rows)
 assert v('seqnotes')==note and v('seqcursor')==cursor and v('seqpitch')==pitch
 assert not v('seqtileoverflow')
 assert p.memory[0xBC80]==16 and p.memory[0xBC80+cols]==160
 p.screen.image.save('build/ui-seq-zoom'+str(cols)+'.png')
 press('select');press('left');assert v('seqfocus')==10
press('select')
# Stress all zooms with dense, changing pitches; final view ends at the last step.
rng=random.Random(8008)
put('seqlength',0,64)
for i in range(64):put('seqnotes',i,40+rng.randrange(48));put('seqduration',i,1)
for zoom in (0,1,2,3):
 put('seqzoom',0,zoom);put('seqcursor',0,63);put('seqpitch',0,60);put('seqtop',0,87)
 put('seqdrawvalid',0,0);put('dirty',0,1);stable()
 assert v('seqbase')+v('seqcols')==64
 assert not v('seqtileoverflow'),(zoom,v('seqtilecount'))
 print('Zoom',v('seqcols'),'tiles',v('seqtilecount'))
# Cursor movement within a viewport must not regenerate the pixel grid.
put('seqcursor',0,0);put('seqdrawvalid',0,0);put('dirty',0,1);stable()
rebuilds=[];a=S['_seq_pixels'];p.hook_register(a>>16,a&65535,lambda _:rebuilds.append(p.frame_count),None)
press('right');press('left');assert not rebuilds
assert any(p.memory[0xc000+17*4+q*4] for q in range(20))
# Stationary playback moves sprites without re-uploading the static grid.
put('seqcursor',0,0);put('seqdrawvalid',0,0);put('dirty',0,1);stable()
chord('select','a');stable();before=word('seqclock');assert any(p.memory[0xc000+17*4+q*4] for q in range(20))
assert not v('seqtileoverflow');chord('select','a');stable();assert p.memory[0xfe01]==0
choose(7);stable();assert v('previewshape')!=255 and not v('seqfontdirty')
choose(8);stable();assert not v('seqtileoverflow')
p.stop(save=False)
print('PASS: two-axis zoom, fixed-width keyboard, editable header length, dense patterns, end-aligned pages, playhead and graphics restoration')

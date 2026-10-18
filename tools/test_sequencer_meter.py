exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):p.memory[S['_'+n]+i]=x
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
def tile(x,y):return v('seqgrid',x-1)
choose(8);p.tick(60)
assert v('seqbeats')==4 and v('seqdenom')==4
assert tile(1,3)==160 and tile(5,3)==76 and tile(2,3)==64
# Empty-cell B-drag creates and extends, anchors pitch, remembers length.
chord('b','right');assert v('seqnotes')==61 and v('seqduration')==2 and v('seqcursor')==1
chord('b','right');assert v('seqduration')==3 and v('seqcursor')==2 and v('seqdefaultdur')==3
chord('b','left');assert v('seqduration')==2 and v('seqcursor')==1 and v('seqdefaultdur')==2
press('right');press('right');press('a');assert v('seqduration',3)==2
# B-drag retains the same onset across a held sequence of direction presses.
p.button_press('b');p.tick(5);press('right');press('right');press('left');p.button_release('b');p.tick(8)
assert v('seqduration',3)==3 and v('seqcursor')==5 and v('seqdefaultdur')==3
# Set 3/4 in the header; a bar occurs every twelve steps.
press('select')
for _ in range(6):press('right')
assert v('seqfocus')==7
chord('b','down');assert v('seqbeats')==3
press('select');p.tick(10)
assert tile(13,3)==160 and tile(9,3)==76
p.screen.image.save('build/ui-sequencer-3-4.png')
# 6/8: beat every two cells; bar every twelve; settings survive track changes.
press('select')
for _ in range(6):press('right')
for _ in range(3):chord('b','up')
press('right');assert v('seqfocus')==8
chord('b','up');assert v('seqbeats')==6 and v('seqdenom')==8
press('select');p.tick(12)
assert tile(3,3)==76 and tile(5,3)==76 and tile(13,3)==160
p.screen.image.save('build/ui-sequencer-6-8.png')
chord('select','right');assert v('seqbeats')==6 and v('seqdenom')==8 and v('seqdefaultdur',1)==1
chord('b','left');assert v('seqnotes',64)==61 and v('seqduration',64)==1
# End-of-pattern dragging is bounded; no wrap or overwrite of next track.
put('seqcursor',1,15);press('a');chord('b','right');assert v('seqduration',79)==1 and v('seqcursor',1)==15
assert not v('seqnotes',128)
# Preview tile reuse must not damage Monosynth wave graphics on return.
choose(7);assert v('previewshape')!=255
choose(8);p.tick(20);assert tile(3,3)==76
p.stop(save=False);print('PASS: beat/bar grid, 3/4 and 6/8 meter, empty-cell B drag, anchored resizing, remembered per-track lengths and bounds')

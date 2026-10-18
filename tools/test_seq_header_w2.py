exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

def put(n,i,x):p.memory[S['_'+n]+i]=x
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)

choose(8);press('a');assert v('seqvelocity')==100
for _ in range(12):press('up')
assert v('seqhead')==1
chord('b','up');assert v('seqdefaultvel')==101 and v('seqvelocity')==100
chord('b','right');assert v('seqdefaultvel')==111 and v('seqhead')==1
press('right');assert v('seqhead')==2
press('a');assert v('seqmuted')==1
press('b');assert not v('seqmuted') and v('seqnotes')==61
press('right');assert v('seqhead')==3
press('b');assert v('seqsolo')==1
press('a');assert not v('seqsolo')
press('down');assert not v('seqhead')
press('right');press('a');assert v('seqvelocity',1)==111
# Fifth individual instrument, exposed on MIDI channel 6, mixes with W1.
choose(0)
while v('selected')!=4:press('select')
assert list(p.memory[S['_w2settings']:S['_w2settings']+5])==[24,15,45,24,0]
p.screen.image.save('build/ui-wave2.png')
send([0x92,60,127]);assert v('active',2)
send([0x95,60,127]);assert v('w2enabled') and v('waveengine')==2
assert v('softon') and v('softon',1) and v('softowned',1)==2
step=word('softstep')
start=p.frame_count;drops=word('mixunderruns');blocks=word('engineblocks')
while p.frame_count<start+20:p.tick(1)
assert v('softon') and v('softon',1) and word('softstep')==step
assert word('engineblocks')>blocks and word('mixunderruns')==drops
assert np.max(np.abs(p.sound.ndarray.astype(float)))>0
p.tick(60);assert not v('softon',1) and v('softon')
send([0x82,60,0]);assert not v('softon')
# W2 track and other hardware tracks run together; solo suppresses other tracks.
choose(8);assert v('seqtrack')==5
for c in (0,1,2,3,5):
 for step in (0,4,8,12):
  put('seqnotes',c*64+step,61+c);put('seqvelocity',c*64+step,100);put('seqduration',c*64+step,4)
chord('select','a');assert v('seqplaying')
overlap=[]
for _ in range(40):
 overlap.append(bool(v('softon') and v('softon',1)));p.tick(1)
assert any(overlap)
# Reach the compact header from the top pitch.
put('seqpitch',5,v('seqtop',5));press('up');assert v('seqhead')==1
press('right');press('right');press('a');assert v('seqsolo')==32
assert not any(v('seqowned',c) for c in range(4))
p.tick(90);assert not any(v('seqowned',c) for c in range(4))
p.screen.image.save('build/ui-sequencer-header.png')
press('b');assert not v('seqsolo')
press('left');press('a');assert v('seqmuted')==32 and not v('softon',1)
press('b');assert not v('seqmuted')
chord('select','a');assert not v('seqplaying')
# Panic clears W2 as well.
send([0x95,60,127]);assert v('softon',1)
p.button_press('select');p.button_press('start');p.tick(20)
p.button_release('start');p.button_release('select');p.tick(10)
assert not v('softon',1)
p.stop(save=False)
print('PASS: next-note velocity, A/B mute/solo boxes, W2 defaults, independent wave mixing, kick decay, sequencer W2 and panic')

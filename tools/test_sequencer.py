exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

# This fixture exercises populated-track navigation with experimental mode enabled.
if not v('experimental_mode'):
 choose(16);press('a');choose(0)
assert v('experimental_mode')
def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
choose(8)
assert v('page')==8 and not v('seqplaying')
assert not any(v('seqnotes',i) for i in range(320))
p.button_press('b');p.tick(5);press('right');p.button_release('b');p.tick(8)
assert v('seqnotes')==61 and v('seqduration')==2 and v('seqcursor')==1
press('b');assert not v('seqnotes') # body tap erases whole note
press('b');assert v('seqnotes',1)==61
press('b');assert not v('seqnotes',1)
put('seqnotes',66,70) # Forward paging now requires a populated destination.
chord('select','right');assert v('seqtrack')==1
press('up');press('b');assert v('seqnotes',64)==62
chord('select','left');assert v('seqtrack')==0
press('select');assert v('seqfocus')==1
press('a');press('up');assert word('seqbpm')==121
press('a');press('right');assert v('seqfocus')==2
chord('b','right');assert v('seqlength')==26
press('select');assert not v('seqfocus')
# Independent 3- and 5-step loops, durations, rest, mute and stop.
for i in range(320):put('seqnotes',i,0)
for c,length in enumerate((3,5,7,9,4)):
 put('seqlength',c,length)
 for s in range(length):
  put('seqnotes',c*64+s,61+c*2+s)
  put('seqvelocity',c*64+s,100)
  put('seqduration',c*64+s,1)
put('seqbpm',0,120);put('seqbpm',1,0)
events=[]
def note(ctx):events.append((p.frame_count,v('seqposition'),v('seqposition',1)))
a=S['_seq_fire'];p.hook_register(a>>16,a&65535,note,None)
chord('select','a');assert v('seqplaying') and not v('monomode')
for c in (1,2,3,0):
 chord('select','right');assert v('seqtrack')==c and v('seqplaying') and not v('seqmode')
p.tick(120)
assert len(events)>45,len(events)
positions=[]
for _ in range(45):
 positions.append((v('seqposition'),v('seqposition',1)));p.tick(1)
assert any(a!=b for a,b in positions)
chord('select','b');assert v('seqmuted')&1 and not v('seqowned')
p.tick(20);assert not v('seqowned')
chord('select','b');p.tick(20);assert not v('seqmuted')&1
p.screen.image.save('build/ui-sequencer.png')
choose(0);assert v('seqplaying');old=len(events);p.tick(40);assert len(events)>old
choose(8);chord('select','a');assert not v('seqplaying') and not any(v('seqowned',c) for c in range(5))
# Channel 5 exclusively drives Monosynth, preserving the other patterns.
press('select');press('left');press('left');assert v('seqfocus')==9
chord('b','up');press('select');assert v('seqtrack')==4
chord('select','a');assert v('seqplaying') and v('monomode') and v('seqmode')
p.tick(40);assert not any(v('seqowned',c) for c in range(4))
assert v('seqposition',4)>0 or word('seqclock')
chord('select','a');assert not v('seqplaying')
press('select');press('left');press('left');chord('b','down');press('select');chord('select','a');assert not v('monomode') and not v('seqmode')
chord('select','a')
# Menu exposes ninth entry on legacy screens too.
p.button_press('start');p.tick(40);assert v('navopen');p.screen.image.save('build/ui-sequencer-menu.png');p.button_release('start');p.tick(12)
p.button_press('select');p.button_press('start');p.tick(12);p.button_release('start');p.button_release('select');p.tick(12)
assert not v('seqplaying') and not any(v('active',c) for c in range(4))
# Scroll across the complete 64-step pattern and clamp pitches at MIDI bounds.
put('seqlength',0,64);put('seqcursor',0,63);put('seqpitch',0,127)
press('up');assert v('seqpitch')==127
if v('seqhead'):press('down')
assert not v('seqhead')
press('b');assert v('seqnotes',63)==128
p.tick(12);p.screen.image.save('build/ui-sequencer-scroll.png')
press('right');assert v('seqcursor')==0
put('seqpitch',0,0);press('down');assert v('seqpitch')==0
# Sixteenth timing: 120 frames produce 16 steps at 120 BPM, within one step.
put('seqposition',0,0);put('seqclock',0,0);put('seqclock',1,0)
chord('select','a');start=p.frame_count;positions=[]
for _ in range(120):
 p.tick(1);positions.append(v('seqposition'))
transitions=sum(a!=b for a,b in zip(positions,positions[1:]));assert 15<=transitions<=17,transitions
chord('select','a')
p.stop(save=False)
print('PASS: sequencer menu, roll insert/erase, duration/velocity, header editing, independent loops, mute, transport, background playback, CH5 isolation')

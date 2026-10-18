exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
choose(7)
def coarse(direction):
 p.button_press('b');press(direction);p.button_release('b');p.tick(8)
def pos():return (v('monoosc'),v('cursor',7),v('monocol'))
goto(0,1);p.memory[S['_monoset']+1]=12
start=pos();coarse('left');assert v('monoset',1)==2 and pos()==start
coarse('right');assert v('monoset',1)==12 and pos()==start
coarse('right');assert v('monoset',1)==15
coarse('left');assert v('monoset',1)==5
coarse('left');assert v('monoset',1)==0
goto(2,2);p.memory[S['_monoset']+2*7+4]=5
coarse('left');assert v('monoset',18)==1
coarse('right');assert v('monoset',18)==11
goto(0,1,1);coarse('right');assert v('monodepth',1)==10
coarse('right');assert v('monodepth',1)==16
goto(0,1,2);address=S['_monophase']+2
p.memory[address]=99;p.memory[address+1]=1
coarse('right');assert p.memory[address]+256*p.memory[address+1]==5
coarse('left');assert p.memory[address]+256*p.memory[address+1]==355
press('a');start=pos();coarse('right');assert pos()==start
press('right');assert pos()==(0,2,0)
goto(3,0);p.memory[S['_monosource']]=250
coarse('right');assert v('monosource')==255
coarse('left');assert v('monosource')==245
p.button_press('b');press('down');p.button_release('b');p.tick(8)
assert v('monosource')==244
p.stop(save=False);print('PASS: B horizontal steps of 10, cursor lock, bounds, phase wrap, latched editing and single steps')

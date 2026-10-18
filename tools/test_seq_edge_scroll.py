"""Piano pitch scrolling and velocity-lane navigation use real D-pad inputs."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

def put(n,i,x):fixture_put(p,S,n,i,x)
try:
 choose(8);put('seqzoom',0,1);put('seqpitch',0,71);put('seqtop',0,71);put('seqhead',0,0);put('dirty',0,1);p.tick(30)
 press('up');assert v('seqpitch')==71 and v('seqtop')==71 and v('seqhead')==1
 press('up');assert v('seqpitch')==72 and v('seqtop')==72 and v('seqhead')==1
 press('down');assert v('seqhead')==0
 put('seqpitch',0,127);put('seqtop',0,127);put('seqhead',0,0);put('dirty',0,1);p.tick(20)
 press('up');assert v('seqpitch')==127 and v('seqhead')==1
 # Bottom grid row enters velocity; another Down scrolls pitch while retaining lane.
 put('seqhead',0,0);put('seqpitch',0,60);put('seqtop',0,60+v('seqrows')-1);put('dirty',0,1);p.tick(20)
 press('down');assert v('seqhead')==5 and v('seqpitch')==60
 top=v('seqtop');press('down');assert v('seqhead')==5 and v('seqpitch')==59 and v('seqtop')==top-1
 before=v('seqdefaultvel');pitch=v('seqpitch');top=v('seqtop')
 p.button_press('b');p.tick(5);press('down');p.button_release('b');p.tick(8)
 assert v('seqhead')==5 and v('seqdefaultvel')<before and v('seqpitch')==pitch and v('seqtop')==top
 press('up');assert v('seqhead')==0 and v('seqpitch')==pitch
 print('PASS: upperedgepitchscroll,MIDI127headerlimit,loweredgevelocitylane,unmodifiedDownscroll,BDownvelocity,Upreturn')
finally:p.stop(save=False)

"""Rectangle selection, group movement and group resizing through real inputs."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])

def put(n,i,x):fixture_put(p,S,n,i,x)
def cursor(step,pitch):
 put('seqcursor',0,step);put('seqpitch',0,pitch);put('seqhead',0,0);put('dirty',0,1);p.tick(12)
def drag(key,directions):
 p.button_press(key);p.tick(5)
 for direction in directions:press(direction)
 p.button_release(key);p.tick(8)
try:
 choose(8)
 for step,pitch in ((1,60),(3,62)):
  put('seqnotes',step,pitch+1);put('seqvelocity',step,99);put('seqduration',step,2)
 cursor(0,59);drag('a',['right']*4+['up']*4)
 assert v('seqgrouptrack')==0
 cursor(1,60);drag('a',['right'])
 assert not v('seqnotes',1) and not v('seqnotes',3)
 assert v('seqnotes',2)==61 and v('seqnotes',4)==63
 cursor(2,60);drag('b',['right'])
 assert v('seqduration',2)==3 and v('seqduration',4)==3
 cursor(0,59);press('a');assert v('seqgrouptrack')==255
 cursor(2,60);drag('b',['right'])
 assert v('seqduration',2)==4 and v('seqduration',4)==3
 print('PASS: melodic rectangle selection, group movement/length, empty A deselection')
finally:p.stop(save=False)

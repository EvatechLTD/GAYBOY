exec(open('tools/test_experimental.py').read().split("assert not v('expactive')")[0])
from seq_storage_helpers import fixture_put
def put(n,i,x):fixture_put(p,S,n,i,x)
cfg({0:1,21:5,22:5,23:12,24:8,25:10});choose(8);p.tick(60)
assert not v('seqmode') and v('seqtrack')<4
press('select');press('left');press('left');p.button_press('b');press('up');p.button_release('b');p.tick(8);press('select')
for i in range(16):
 put('seqnotes',256+i,49+i%8);put('seqvelocity',256+i,100);put('seqduration',256+i,1)
p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(20)
assert v('seqtrack')==4 and v('seqplaying') and v('expactive')
b=word('expblocks');u=word('expdrops');p.tick(120)
print('Sequencer + DSP blocks/drops',word('expblocks')-b,word('expdrops')-u)
assert word('expblocks')-b>=120 and word('expdrops')==u
# Stop does not leave sequencer notes owned.
p.button_press('select');p.tick(5);press('a');p.button_release('select');p.tick(12)
assert not v('seqplaying') and not v('seqowned',4)
p.stop(save=False)

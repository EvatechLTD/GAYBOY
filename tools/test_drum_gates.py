"""Overlapping PCM hits keep their attack and honor the shortened gate."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import read_tracks,write_tracks,read_word

def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
def seed(events):
 tracks=read_tracks(p,S);tracks[6]=events;write_tracks(p,S,tracks)
 put('seqgrouptrack',0,255);put('seqdrawvalid',0,0)
def plot(step,row,duration):
 put('seqcursor',6,step);put('drumrow',0,row);put('seqhead',0,0)
 put('seqdefaultdur',6,duration);put('dirty',0,1);p.tick(12);press('b')
 return read_tracks(p,S)[6]
try:
 choose(8);chord('select','left');assert v('seqtrack')==6
 put('seqlength',6,64)
 # Gate the most recently plotted hit; retain both attacks and the new hit.
 seed([[0,1,99,8],[0,2,99,8]])
 assert plot(4,2,2)==[[0,1,99,8],[0,2,99,4],[4,3,100,2]]
 # Insertion order, rather than onset, chooses which existing hit is gated.
 seed([[1,1,99,8],[0,2,99,8]])
 assert plot(4,2,2)==[[1,1,99,8],[0,2,99,4],[4,3,100,2]]
 # A later pair of attacks gates the incoming note instead of deleting either.
 seed([[4,1,99,8],[4,2,99,8]])
 assert plot(0,2,8)==[[4,1,99,8],[4,2,99,8],[0,3,100,4]]
 # A simultaneous third attack still replaces the newest existing hit.
 seed([[0,1,99,8],[0,2,99,8]])
 assert plot(0,2,2)==[[0,1,99,8],[0,3,100,2]]
 # The 808 kick's PCM source is actually capped to a one-step gate.
 put('drumkit',0,1);seed([[0,1,100,1]])
 chord('select','a');assert v('seqplaying')
 assert read_word(p,S['_drumend'])==716,read_word(p,S['_drumend'])
 p.tick(16);assert not any(v('drumon',i) for i in range(2))
 chord('select','a')
 print('PASS: gate newest overlap, preserve attacks, gate before future hits, same-onset fallback and audible PCM length')
finally:p.stop(save=False)


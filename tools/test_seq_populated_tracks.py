"""Forward sequencer track paging skips empty rolls; reverse paging visits all."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import write_tracks,read_tracks

def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(key):
 p.button_press('select');p.tick(4);press(key);p.button_release('select');p.tick(8)
 assert v('page')==8 and not v('seqpopup')
def seed(used):
 tracks=[[] for _ in range(7)]
 for c in used:tracks[c]=[[0,1 if c==6 else 61,100,1]]
 write_tracks(p,S,tracks)
def track(c):
 put('seqtrack',0,c);put('seqhead',0,0);put('seqfocus',0,0);put('dirty',0,1);p.tick(12)
try:
 choose(8);put('experimental_mode',0,0)
 seed((0,2,6));track(0);before=read_tracks(p,S)
 for expected in (2,6,0):chord('right');assert v('seqtrack')==expected
 for expected in (6,3,2,1,0):chord('left');assert v('seqtrack')==expected
 # Muted and solo-filtered tracks still contain plotted notes.
 put('seqmuted',0,4);put('seqsolo',0,1);chord('right');assert v('seqtrack')==2
 assert read_tracks(p,S)==before
 # Starting on an empty roll finds the next populated one; a sole populated
 # roll wraps to itself, and a completely empty pattern stays put.
 track(1);chord('right');assert v('seqtrack')==2
 seed((2,));track(2);chord('right');assert v('seqtrack')==2
 seed(());track(0);chord('right');assert v('seqtrack')==0
 chord('left');assert v('seqtrack')==6
 # Hardware mode cannot visit experimental-only tracks even if they have notes.
 seed((4,5));track(0);chord('right');assert v('seqtrack')==0
 # Experimental H mode includes W2 but excludes the isolated Monosynth track.
 put('experimental_mode',0,1);seed((0,4,5,6));track(0)
 for expected in (5,6,0):chord('right');assert v('seqtrack')==expected
 for expected in (6,5,3,2,1,0):chord('left');assert v('seqtrack')==expected
 # The isolated M mode retains its one-track navigation.
 put('seqmode',0,1);track(4)
 for key in ('right','left'):chord(key);assert v('seqtrack')==4
 print('PASS: populated forward track paging, all-track reverse paging, wrap, empty patterns, muted notes and hardware/experimental/Mono track eligibility')
finally:p.stop(save=False)

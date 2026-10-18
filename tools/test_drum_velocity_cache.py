"""DRUM velocity cache preserves oldest-covering-event semantics for every row."""
exec(open('tools/test_seq_incremental.py').read().split('choose(8); settle()')[0])
from seq_storage_helpers import write_tracks,write_word
import random
rng=random.Random(2049)
def wait():
 for _ in range(2400):
  p.tick(1)
  if v('seqdrawvalid')==1 and not v('rollbuilding') and v('seqviewtrack')==6 and bytes(p.memory[S['_canvas']:S['_canvas']+360])==bytes(p.memory[S['_visible']:S['_visible']+360]):p.tick(2);return
 raise AssertionError('DRUM renderer did not settle')
def heights(events,row,base):
 out=[]
 for step in range(base,base+16):
  event=next((e for e in events if e[1]==row+1 and e[0]<=step<e[0]+(e[3] or 256)),None)
  vel=event[2] if event is not None and event[0]==step else 0
  out.append(1+(vel*20)//127 if vel else 0)
 return out
try:
 choose(8);put('seqtrack',0,6);put('seqzoom',0,1);put('seqvelocityhidden',0,0);put('seqcursor',6,0);write_word(p,S['_seqlength']+12,64)
 tracks=[[] for _ in range(7)]
 events=[[rng.randrange(64),1+rng.randrange(13),rng.randrange(128),rng.choice((1,2,4,16,0))] for _ in range(160)]
 # Force all thirteen voices to have visible onsets and overlapping bodies.
 events=[e for row in range(13) for e in ([0,row+1,10+row*9,3],[2,row+1,127,4])]+events
 tracks[6]=events;write_tracks(p,S,tracks);put('seqdrawvalid',0,0);put('dirty',0,1);wait()
 checks=0
 for base in (0,16,48):
  put('seqcursor',6,base);put('seqdrawvalid',0,0);put('dirty',0,1);wait()
  for row in range(13):
   put('drumrow',0,row);put('dirty',0,1);wait()
   actual=list(p.memory[S['_rolloldvel']:S['_rolloldvel']+16]);expected=heights(events,row,base)
   assert actual==expected,('Velocity cache mismatch',base,row,actual,expected)
   incremental=background();put('seqdrawvalid',0,0);put('dirty',0,1);wait()
   assert np.array_equal(incremental,background()),('Partial/full velocity pixels differ',base,row)
   checks+=1
 print('PASS:',checks,'row/viewport velocity comparisons, overlapping event age, zero velocities and duration256; exact partial/full pixels')
finally:p.stop(save=False)

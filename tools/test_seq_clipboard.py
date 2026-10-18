"""Track clipboard uses real Start-menu actions and disposable cartridge RAM."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):p.memory[S['_'+n]+i]=x
def action(n):
 p.button_press('start')
 for _ in range(120):
  p.tick(1)
  if v('navopen'):break
 assert v('navopen')
 for _ in range(32):
  if v('navchoice')==n:break
  press('down')
 assert v('navchoice')==n
 p.button_release('start');p.tick(180);assert v('page')==8 and not v('navopen')
from seq_storage_helpers import fixture_put,read_tracks,write_tracks

def put(n,i,x):fixture_put(p,S,n,i,x)
try:
 choose(8);p.tick(20)
 tracks=[[] for _ in range(7)]
 tracks[0]=[[i,61+i%12,30+i,1+i%4] for i in range(64) if i%3==0]
 write_tracks(p,S,tracks)
 put('seqlength',0,8);put('seqgate',0,73);put('seqdefaultvel',0,91);put('seqdefaultdur',0,3)
 expected=read_tracks(p,S)[0]
 action(21);put('seqtrack',0,1);action(22)
 assert read_tracks(p,S)[1]==expected
 assert v('seqlength',1)==8 and v('seqgate',1)==73 and v('seqdefaultvel',1)==91 and v('seqdefaultdur',1)==3
 # Sparse drum copy includes both noise rows and the pulse kick row.
 tracks=read_tracks(p,S);tracks[6]=[[step,row,90,1] for step in (0,7,31,63) for row in (1,2,11,12,13)]
 write_tracks(p,S,tracks);put('seqtrack',0,6);action(21);original=read_tracks(p,S)[6]
 tracks=read_tracks(p,S);tracks[6]=[];write_tracks(p,S,tracks);action(22)
 assert read_tracks(p,S)[6]==original
 # Cross conversion chooses the first stored voice at each step.
 put('seqtrack',0,2);put('seqpitch',2,60);action(22)
 assert read_tracks(p,S)[2]==[[step,61,90,1] for step in (0,7,31,63)]
 # Melodic indices10/11/12 map to NHH/NSN/PK, including inactive cells.
 tracks=read_tracks(p,S);tracks[3]=[[0,11,100,1],[31,12,100,1],[63,13,100,1]];write_tracks(p,S,tracks)
 put('seqtrack',0,3);action(21);put('seqtrack',0,6);action(22)
 assert read_tracks(p,S)[6]==[[0,11,100,1],[31,12,100,1],[63,13,100,1]]
 print('PASS: real track Copy/Paste, sparse events, metadata, NHH/NSN/PK, inactive cells and cross-track conversion')
finally:p.stop(save=False)

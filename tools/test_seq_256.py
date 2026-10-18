"""256-step UI endpoints and retained rendering agree with a complete rebuild."""
exec(open('tools/test_seq_incremental.py').read().split('choose(8); settle()')[0])
from seq_storage_helpers import write_tracks,read_tracks
try:
 choose(8);put('seqlength',0,256);put('seqcursor',0,255);put('seqzoom',0,1);put('seqpitch',0,60)
 tracks=[[] for _ in range(7)];tracks[0]=[[step,61,100,1] for step in range(256)]
 write_tracks(p,S,tracks);invalidate(True)
 assert v('seqlength')==256 and v('seqbase')==240 and v('seqcursor')==255
 assert len(read_tracks(p,S)[0])==256
 row=(v('seqtop')-60)*8+11;x=16+15*9+2
 assert background()[row,x]==3,'Step255 disappeared or was mistaken for a sentinel'
 # Editing the final event must preserve keyboard pixels and match a full render.
 before=background();tracks[0][-1][1]=63;write_tracks(p,S,tracks);invalidate();retained=background()
 assert np.array_equal(before[:,0:16],retained[:,0:16]),'Retained edit changed keyboard'
 invalidate(True);assert np.array_equal(retained,background()),'256 endpoint retained/full mismatch'
 # Right wraps the256th step to0; Left focuses its visible piano rather than underflowing.
 press('right');assert v('seqcursor')==0
 press('left');assert v('seqhead')==6 and v('seqcursor')==0
 print('PASS:256onsets ononechannel,length256,laststep255,retainedendpointpixels,keyboardreuse,256wrap')
finally:p.stop(save=False)

"""DRUM step255, length256, >256 shared events and native PCM coexistence."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(240)'))
from seq_storage_helpers import read_tracks,write_tracks
try:
 choose(8);p.button_press('select');press('left');p.button_release('select');p.tick(30)
 tracks=[[] for _ in range(7)];tracks[6]=[[step,11+(step&1),100,1] for step in range(256)]+[[0,8,127,1],[0,10,127,1],[255,1,127,1]]
 write_tracks(p,S,tracks);put('seqlength',6,256);put('seqcursor',6,255);put('drumrow',0,0);put('seqzoom',0,3);put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(180)
 assert v('seqbase')==224 and not v('seqtileoverflow')
 press('b');assert not any(e[0]==255 and e[1]==1 for e in read_tracks(p,S)[6])
 press('b');assert any(e[0]==255 and e[1]==1 for e in read_tracks(p,S)[6])
 assert len(read_tracks(p,S)[6])==259
 press('right');assert v('seqcursor',6)==0
 p.button_press('select');press('a');p.button_release('select');p.tick(60)
 assert v('waveengine')==3 and word('engineblocks')>100 and word('mixunderruns')==0
 assert len(read_tracks(p,S)[6])==259 and v('seqlength',6)==256
 print('PASS: DRUM259events,step255erase/reinsert,256length/wrap,last32viewport,2PCM+256noiseevents,zeroaudiooverruns')
finally:p.stop(save=False)

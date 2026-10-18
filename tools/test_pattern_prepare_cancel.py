"""Cancelled background launches preserve the outgoing saved pattern."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file='))
from seq_storage_helpers import write_tracks
mx=S['_mx']
def sm(i,x):p.memory[mx+i]=x
def tag(slot):
 p.memory[0x4000]=1+slot//3
 try:return p.memory[0xa000+slot%3*2560]
 finally:p.memory[0x4000]=0
try:
 choose(18)
 tracks=[[] for _ in range(7)];tracks[0]=[[s,61,100,1] for s in range(16)];write_tracks(p,S,tracks)
 choose(20);press('b');sm(4,31);press('a');write_tracks(p,S,tracks);choose(20);sm(6,1);press('b');sm(4,30);press('a')
 sm(4,0);press('a');assert v('seqplaying')
 # Request while playing, then cancel by requesting the active pad again.
 sm(3,2);sm(4,31);press('a');sm(4,30);press('a')
 p.tick(240)
 assert tag(0)==0xba,('Active saved pattern was invalidated by cancellation',tag(0))
 # Request again, then leave Mixer. Any unfinished outgoing save must settle.
 sm(4,31);press('a');choose(8);p.tick(240)
 assert tag(0)==0xba,('Leaving Mixer left the active saved pattern invalid',tag(0))
 assert not v('prep'),('Preparation stalled off Mixer',v('prep'))
 print('PASS: active-pad cancellation and navigation preserve saved pattern and settle preparation')
finally:p.stop(save=False)

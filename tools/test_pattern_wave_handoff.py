"""A live PCM pattern can hand channel 3 back to an incoming native wave."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file='))
from seq_storage_helpers import write_tracks
mx=S['_mx']
def setm(i,x):p.memory[mx+i]=x
def record(slot,data=None):
 p.memory[0x4000]=1+slot//3;at=0xa000+(slot%3)*2560
 try:
  if data is not None:p.memory[at:at+2560]=data
  return bytes(p.memory[at:at+2560])
 finally:p.memory[0x4000]=0
try:
 choose(18)
 tracks=[[] for _ in range(7)];tracks[6]=[[i,1,127,1] for i in range(16)]
 write_tracks(p,S,tracks)
 choose(20);press('b');saved=record(0)
 tracks=[[] for _ in range(7)];tracks[2]=[[0,61,127,16]]
 write_tracks(p,S,tracks)
 choose(20);setm(6,1);press('b');record(0,saved)
 choose(19);setm(6,0);press('a')
 choose(18);setm(4,0);press('a');assert v('seqplaying')
 assert v('waveengine')==3
 setm(3,1);setm(4,31);press('a')
 for _ in range(360):
  p.tick(1)
  if p.memory[mx+1]==1 and v('waveengine')==0 and v('active',2) and not v('seqservicing'):break
 assert p.memory[mx+1]==1 and v('seqplaying')
 assert v('waveengine')==0, 'Idle PCM must return channel 3 to native WAVE'
 assert v('active',2) and v('basepitch',2)==60
 assert p.memory[0xff26]&4, 'Incoming WAVE note must actually sound'
 assert p.memory[0xff07]&7==4, 'Native timer rate must be restored'
 p.tick(60)
 assert v('seqplaying') and v('seqposition',2)>0
 print('PASS: PCM-to-native WAVE handoff restores audio and clock without stopping transport')
finally:p.stop(save=False)

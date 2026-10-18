"""Prepared pattern launches install the new tone before their first note."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('range(60)','range(600)').replace('sound_emulated=True,ram_file=','sound_emulated=True,cgb=False,ram_file='))
from seq_storage_helpers import write_tracks
mx=S['_mx'];launches=[]
def setm(i,x):p.memory[mx+i]=x
def record(slot,data=None):
 p.memory[0x4000]=1+slot//3;at=0xa000+(slot%3)*2560
 try:
  if data is not None:p.memory[at:at+2560]=data
  return bytes(p.memory[at:at+2560])
 finally:p.memory[0x4000]=0
try:
 choose(18);tracks=[[] for _ in range(7)];tracks[0]=[[0,61,100,1],[4,65,100,1]];write_tracks(p,S,tracks)
 p.memory[S['_param']]=2;p.memory[S['_param']+1]=4
 choose(20);press('b');tone_a=record(0)
 p.memory[S['_param']]=1;p.memory[S['_param']+1]=11
 choose(20);setm(6,1);press('b');record(0,tone_a)
 choose(19);setm(6,0);press('a');assert v('param',1)==4
 a=S['_seq_pattern_start'];p.hook_register(a>>16,a&65535,lambda _:launches.append((p.memory[mx+1],v('param'),v('param',1))),None)
 setm(3,1);setm(4,0);press('a');assert v('seqplaying')
 setm(4,31);press('a')
 for _ in range(240):
  p.tick(1)
  if p.memory[mx+1]==1 and launches:break
 assert launches[0]==(1,1,11),launches
 assert v('seqplaying') and v('param',1)==11
 # Stop and switch back without quantization; prefetch must survive the
 # autosnapshot of the outgoing pattern's different tone.
 setm(4,0);press('a');assert not v('seqplaying')
 setm(3,0);setm(4,30);press('a')
 assert p.memory[mx+1]==0 and v('param')==2 and v('param',1)==4
 print('PASS: quantized first-note tone handoff, continuing transport and independent prepared/outgoing tone caches')
finally:p.stop(save=False)

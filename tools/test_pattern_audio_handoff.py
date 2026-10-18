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
release=[];attacks=[];transports=[];results=[];pulseoffs=[]
def hook(name,callback):
 a=S['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def played(_):
 if release and p.register_file.A==0:attacks.append(p._cycles())
try:
 choose(18)
 tracks=[[] for _ in range(7)]
 tracks[0]=[[0,61,100,16]];tracks[6]=[[i,1,127,1] for i in range(16)]
 write_tracks(p,S,tracks)
 p.memory[S['_param']+1]=12;p.memory[S['_param']+3]=0
 choose(20);press('b');saved=record(0)
 p.memory[S['_param']]=1
 choose(20);setm(6,1);press('b');record(0,saved)
 choose(19);setm(6,0);press('a')
 choose(18);setm(4,0);press('a');assert v('seqplaying')
 hook('seq_pattern_release',lambda _:release.append(p._cycles()))
 hook('play',played)
 hook('seq_off',lambda _:pulseoffs.append(p._cycles()) if release and not attacks and p.register_file.A==0 else None)
 hook('seq_transport',lambda _:transports.append(p._cycles()))
 for quant,target in ((1,1),(2,0),(0,1),(0,0)):
  release.clear();attacks.clear();transports.clear();pulseoffs.clear()
  setm(3,quant);setm(4,30+target);press('a')
  for _ in range(360):
   p.tick(1)
   if p.memory[mx+1]==target and attacks and not v('seqservicing'):break
  assert attacks and release,(quant,target,release,attacks)
  assert v('seqplaying') and not transports,('transport restarted',quant,transports)
  assert not pulseoffs,('native onset was silenced before replacement',quant,pulseoffs)
  gap=(attacks[0]-release[0])*1000/4194304
  assert gap<1000/59.7275,('audible handoff gap',quant,gap)
  assert p.memory[0xff26]&1,'Incoming pulse must sound'
  results.append((quant,round(gap,3)))
 print('PASS: OFF/BEAT/BAR launches retain transport; release-to-P1 attack milliseconds:',results)
finally:p.stop(save=False)


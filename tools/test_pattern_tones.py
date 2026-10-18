"""Pattern tones round-trip across slots, legacy formats and battery reboot."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0].replace('sound_emulated=True,ram_file=', 'sound_emulated=True,cgb=False,ram_file=').replace('range(60)','range(600)'))
from seq_storage_helpers import read_tracks,write_tracks,write_word
from io import BytesIO
mx=S['_mx']
lengths={'param':104,'program':4,'edited':4,'mods':24,'tablemode':4,'tablelen':4,'tables':96,'custom':1,'customwave':16,'finepitch':10,'w2settings':5,'w2program':1,'w2tablemode':1,'w2tablelen':1,'w2tablespeed':1,'w2tables':24,'monoset':21,'monodepth':21,'monophase':42,'monosource':11,'expconfig':27,'exprelease':3,'noisepatch':10,'drumkit':1,'master':1,'vin':1,'arprate':1,'softshape':2}
def read():return {n:bytes(p.memory[S['_'+n]:S['_'+n]+size]) for n,size in lengths.items()}
def setbytes(n,data):p.memory[S['_'+n]:S['_'+n]+len(data)]=data
def save(slot):
 choose(20);p.memory[mx+6]=slot;press('b')
def load(slot):
 choose(19);p.memory[mx+6]=slot;press('a')
def record(slot,data=None):
 p.memory[0x4000]=1+slot//3;at=0xa000+(slot%3)*2560
 try:
  if data is not None:p.memory[at:at+2560]=data
  return bytes(p.memory[at:at+2560])
 finally:p.memory[0x4000]=0
try:
 choose(18)
 # Distinct edited settings, including negative table pitches and tuning.
 setbytes('program',[13,27,48,99]);setbytes('edited',[1]*4)
 for c in range(4):
  a=S['_param']+c*26;p.memory[a]=c;p.memory[a+1]=4+c;p.memory[a+2]=c&1;p.memory[a+3]=1+c
  setbytes('customwave',[(i*17)^85 for i in range(16)])
  for i in range(8):
   at=S['_tables']+c*24+i*3;p.memory[at:at+3]=[(i-4)&255,(c+i)%16,i%4]
  write_word(p,S['_finepitch']+c*2,(c*7-14)&65535)
 setbytes('custom',[1]);setbytes('drumkit',[4]);setbytes('w2settings',[31,7,84,18,3]);setbytes('w2program',[81])
 setbytes('w2tablemode',[1]);setbytes('w2tablelen',[5]);setbytes('w2tablespeed',[11])
 for c in range(3):
  for i in range(7):write_word(p,S['_monophase']+(c*7+i)*2,(c*127+i*23)%360)
 setbytes('monosource',[93,105,37,71,4,27,12,1,1,23,1]);setbytes('exprelease',[3,11,5])
 setbytes('expconfig',[0,1,8,13,37,5,9,2,7,2,23,17,52,19,24,32,12,7,1,0,1,5,3,17,11,7,5])
 setbytes('noisepatch',[9,12,6,1,4,13,8,3,0,5]);setbytes('master',[0x53]);setbytes('vin',[0x88])
 expected=read();save(0);saved=record(0);assert saved[0]==0xBA and len(saved)==2560 and saved[2500:2504]==b'GBM2'
 # Fill another slot with different settings, then explicitly load slot zero.
 setbytes('param',[0]*104);setbytes('customwave',[0]*16);setbytes('drumkit',[0]);save(1);record(0,saved)
 load(0);actual=read();assert actual==expected,{k:(expected[k],actual[k]) for k in expected if actual[k]!=expected[k]}
 # A B9 note-only record remains loadable without replacing current tones.
 legacy=bytearray(saved);legacy[0]=0xB9
 legacy[18:20]=((sum(legacy[1:18])+sum(legacy[32:2161]))&65535).to_bytes(2,'little');record(2,legacy)
 setbytes('param',[0]*104);before=read();load(2);assert read()==before
 # Reload and reboot from a disposable complete battery image.
 record(0,saved);load(0);battery=bytearray()
 for bank in range(4):p.memory[0x4000]=bank;battery.extend(p.memory[0xa000:0xc000])
 p.memory[0x4000]=0;p.stop(save=False)
 p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,cgb=False,ram_file=BytesIO(battery));p.set_emulation_speed(0);enter_app(p)
 actual=read();assert actual==expected,{k:(expected[k],actual[k]) for k in expected if actual[k]!=expected[k]}
 print('PASS: edited per-channel tones, tables, custom wave, tuning, W2, Monosynth/FX, drums, unchanged slot size, B9 compatibility and battery reboot')
finally:p.stop(save=False)

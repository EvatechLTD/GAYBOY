"""256-step patterns: versioned eight-slot SRAM, lossless legacy import, clipboard."""
from pathlib import Path
import struct,json,tempfile,shutil
ns={};exec(Path('tools/test_monosynth.py').read_text().split('# Native oscillator baseline')[0],ns)
p,S,v,choose=(ns[k] for k in ('p','S','v','choose'))

def put(n,i,x):p.memory[S['_'+n]+i]=x

def setw(n,i,x):put(n,i*2,x&255);put(n,i*2+1,x>>8)

def w(n,i=0):
 a=S['_'+n]+i*2;return p.memory[a]|p.memory[a+1]<<8

def press(k):
 mask={'up':4,'down':8,'left':2,'right':1,'a':16,'b':32,'select':64}[k];p.button_press(k)
 for _ in range(1200):
  p.tick(1)
  if v('lastpad')&mask:break
 assert v('lastpad')&mask,('press stalled',k)
 p.button_release(k)
 for _ in range(1200):
  p.tick(1)
  if not v('lastpad')&mask:break
 assert not v('lastpad')&mask,('release stalled',k)
 p.tick(8)
ns['press']=press

def menu(n):
 p.button_press('start')
 for _ in range(120):
  p.tick(1)
  if v('navopen'):break
 for _ in range(40):
  if v('navchoice')==n:break
  press('down')
 assert v('navchoice')==n
 p.button_release('start');p.tick(180)

def event_addr(i):return S['_seqevents_lo']+i*4 if i<256 else 0xA800+(i-256)*4

def setpool(tracks):
 at=0
 for c,events in enumerate(tracks):
  setw('seqeventoffsets',c,at);setw('seqeventcounts',c,len(events));setw('seqlength',c,256);setw('seqdefaultdur',c,256 if c!=6 else 0)
  for e in events:
   addr=event_addr(at)
   for j,x in enumerate(e):p.memory[addr+j]=x
   at+=1
 assert at<=512

def pool():
 return [[tuple(p.memory[event_addr(w('seqeventoffsets',c)+i):event_addr(w('seqeventoffsets',c)+i)+4]) for i in range(w('seqeventcounts',c))] for c in range(7)]

def record(slot,data=None):
 bank=1+slot//3;addr=0xA000+(slot%3)*2560
 p.memory[0x4000]=bank
 try:
  if data is not None:
   for i,x in enumerate(data):p.memory[addr+i]=x
  return bytes(p.memory[addr:addr+2560])
 finally:p.memory[0x4000]=0

def legacy(events,full=False):
 r=bytearray(2560);r[0]=0xB7;r[1:7]=b'OLDSEQ';meta=bytearray(49)
 for c in range(7):meta[c]=64;meta[7+c]=100;meta[14+c]=1;meta[21+c]=80;meta[28+c]=127;meta[35+c]=3
 meta[44]=meta[45]=4;meta[47:49]=struct.pack('<H',120)
 for c,track in enumerate(events[:6]):
  for step,note,vel,dur in track:r[32+c*64+step]=note;r[32+384+c*64+step]=vel;r[32+768+c*64+step]=dur
 for j,(step,note,vel,dur) in enumerate(events[6]):
  if note<=10:
   n=step*2+(j&1);r[1184+n]=note;r[1184+128+n]=vel;r[1184+256+n]=dur;r[1184+384+n*2:1184+386+n*2]=struct.pack('<H',1000-j)
  else:
   n=step*2+note-11;r[1184+640+n]=1;r[1184+768+n]=vel;r[1184+896+n]=dur
 r[2208:2257]=meta
 checksum=(sum(r[1:18])+sum(r[32:1184])+sum(r[1184:2208])+sum(meta))&65535;r[18:20]=struct.pack('<H',checksum)
 return r
try:
 menu(18);mx=S['_mx']
 def setm(i,x):p.memory[mx+i]=x
 setm(4,2);press('a');assert v('seqmuted')&1
 press('a');assert not v('seqmuted')&1
 setm(4,3);press('a');assert v('seqsolo')&1
 press('a');assert not v('seqsolo')&1
 setm(4,4);p.button_press('b');p.tick(4);press('down');p.button_release('b');p.tick(8)
 assert p.memory[mx+12]==126 and p.memory[mx+4]==4
 setm(4,5);p.button_press('b');p.tick(4);press('left');p.button_release('b');p.tick(8)
 assert p.memory[mx+19]==0 and p.memory[mx+4]==5
 for i,ch in enumerate(b'LONG SESSION256\0'):setm(26+i,ch)
 dense=[[(i,1+(i+c)%100,1+(i*13)%127,0 if i==0 else 255) for i in range(n)] for c,n in enumerate((100,100,80,70,50,50,62))]
 dense[6]=[(i,i%12+1,100,0 if not i else 255) for i in range(62)]
 setpool(dense);expected=pool();menu(20);press('b');assert record(0)[0]==0xBA
 for slot in range(1,8):
  setm(4,30+slot);press('a');assert p.memory[mx+1]==slot
  if v('page')!=18:menu(18)
  tracks=[[] for _ in range(7)];tracks[slot%7]=[(255,12 if slot%7==6 else 100,97,0)];setpool(tracks)
  menu(20);press('b');assert record(slot)[0]==0xBA
 setm(4,30);press('a');assert pool()==expected
 assert bytes(p.memory[mx+26:mx+41])==b'LONG SESSION256'
 assert all(w('seqlength',c)==256 and w('seqdefaultdur',c)==(0 if c==6 else 256) for c in range(7))
 # Clipboard spans both pool halves and carries all512 insertion-ordered events.
 single=[[(i&255,1+i%127,100,0 if not i else 1) for i in range(512)]]+[[] for _ in range(6)]
 setpool(single);put('seqtrack',0,0);put('selected',0,0);menu(8);menu(21)
 setpool([[] for _ in range(7)]);put('seqtrack',0,1);menu(22)
 assert w('seqeventcounts',1)==512 and pool()[1]==single[0]
 # B7 migration preserves visible notes, defaults and oldest PCM ordering.
 menu(18);old=[[(63,61,91,4)],[],[],[],[],[],[(0,2,99,2),(1,4,88,3),(2,11,70,1)]]
 original=legacy(old);record(7,original);menu(19);setm(6,7);press('a');assert record(7)==bytes(original)
 restored=pool();assert restored[0]==old[0] and restored[6]==[old[6][1],old[6][0],old[6][2]]
 # More than512 old events must fail without truncating the record or live music.
 too_many=[[(i,60,100,1) for i in range(64)] for _ in range(6)]+[[(i//2,1+i%10,100,1) for i in range(128)]+[(i//2,11+i%2,100,1) for i in range(128)]]
 rejected=legacy(too_many);record(6,rejected);before=pool();menu(19);setm(6,6);press('a')
 assert pool()==before and record(6)==bytes(rejected) and p.memory[mx+50]==1
 # Real battery file round-trip; the user's cartridge save is never opened.
 p.stop(save=False)
 with tempfile.TemporaryDirectory(prefix='gayboy-pattern256-') as tmp:
  rom=Path(tmp)/'battery.gb';shutil.copyfile('build/GAYBOY.gb',rom)
  PyBoy=ns['PyBoy'];enter_app=ns['enter_app']
  def reboot():
   global p
   p=PyBoy(str(rom),window='null',sound_emulated=True,cgb=False);p.set_emulation_speed(0);ns['p']=p;enter_app(p)
  reboot();battery=[[(255,100,87,0)]]+[[] for _ in range(6)];setpool(battery)
  menu(20);press('b');p.stop(save=True);assert rom.with_suffix('.gb.ram').exists()
  reboot();assert pool()==battery and w('seqlength')==256 and w('seqdefaultdur')==256
  p.stop(save=False)
  ram=rom.with_suffix('.gb.ram');raw=bytearray(ram.read_bytes());raw[8192+32]^=1;ram.write_bytes(raw)
  reboot();assert sum(w('seqeventcounts',c) for c in range(7))==0 and w('seqlength')==16
  # An oversized boot record survives a subsequent automatic pad switch.
  boot_old=bytearray(rejected);boot_old[2500:2504]=b'GBM2';record(0,boot_old);p.stop(save=True)
  reboot();assert p.memory[mx+50]==1
  menu(18);setm(4,31);press('a');assert record(0)==bytes(boot_old)
  p.stop(save=False)
 print('PASS: eight BA slots,256steps/durations,512event clipboard,B7migration/rejection,battery reboot/checksum and protected legacy boot record')
finally:p.stop(save=False)

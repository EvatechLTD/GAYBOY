"""Actual DMG CPU tests for the512-event,256-step shared storage pool."""
from pathlib import Path
from io import BytesIO
import random
from pyboy import PyBoy
from boot_helpers import enter_app
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',cgb=False,sound_emulated=False,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0);enter_app(p)
p.memory[0,0x3ff0]=0x18;p.memory[0,0x3ff1]=0xfe
p.memory[0xffff]=0;p.memory[0xff07]=0;p.memory[0xff0f]=0
p.memory[0x0000]=0x0a;p.memory[0x4000]=0;p.memory[0x2000]=14;p.memory[0x3000]=0;p.memory[0xff90]=14
p.memory[S['_seqplaying']]=0
BUF=0xde00;CURSOR=0xde10

def u16(x):return [x&255,x>>8]
def call(n,args=()):
 # BANKED SDCC ABI: return address, four-byte bank frame, then stack args.
 sp=0xdf00;p.memory[sp:sp+6+len(args)]=[0xf0,0x3f,0,0,0,0]+list(args)
 p.register_file.SP=sp;p.register_file.PC=S['_'+n]&65535
 for _ in range(120):
  p.tick(1)
  if p.register_file.PC in (0x3ff0,0x3ff1):break
 assert p.register_file.PC in (0x3ff0,0x3ff1),(n,hex(p.register_file.PC))
 assert p.register_file.SP==sp+2,(n,'stack imbalance',hex(p.register_file.SP))
 return p.register_file.A,p.register_file.B<<8|p.register_file.C

def put(c,e,index=65535):
 p.memory[BUF:BUF+4]=e;return call('seq_event_put',[c]+u16(index)+u16(BUF))[0]
def get(c,i):
 ok,_=call('seq_event_get',[c]+u16(i)+u16(BUF));assert ok
 return list(p.memory[BUF:BUF+4])
def count(c):return call('seq_event_count',[c])[1]
try:
 call('seq_storage_clear');model=[[] for _ in range(7)]
 # A single track can occupy every one of the256 steps, including step255.
 for step in range(256):
  e=[step,1+step%128,1+step%127,0 if step==255 else 1+step%255]
  assert put(4,e);model[4].append(e)
 assert count(4)==256 and get(4,255)==model[4][255]
 assert call('seq_duration_get',[4,255])[1]==256
 # Insert earlier tracks, shifting data across the WRAM/SRAM split.
 rng=random.Random(256512)
 for i in range(256):
  c=(0,1,2,3,5,6)[i%6];e=[rng.randrange(256),rng.randrange(1,13 if c==6 else 129),rng.randrange(128),rng.randrange(256)]
  assert put(c,e);model[c].append(e)
 assert call('seq_event_total')[1]==512
 # Track4 now straddles the physical WRAM/SRAM boundary.
 assert call('seq_note_get',[4,255])[0]==128
 assert call('seq_duration_get',[4,255])[1]==256
 # A quantized handoff may read all512 events from the prefetched pool.
 # Poison both live halves so successful reads prove the cache is authoritative.
 lo=S['_seqevents_lo'];saved=bytes(p.memory[lo:lo+1024])+bytes(p.memory[0xa800:0xac00])
 p.memory[0xb020:0xb820]=saved;p.memory[S['_seqeventcache']]=1
 p.memory[lo:lo+1024]=[0]*1024;p.memory[0xa800:0xac00]=[0]*1024
 for c in range(7):
  for i,e in enumerate(model[c]):assert get(c,i)==e,('cached pool',c,i)
 assert call('seq_note_get',[4,255])[0]==128
 assert call('seq_velocity_get',[4,255])[0]==model[4][255][2]
 assert call('seq_duration_get',[4,255])[1]==256
 p.memory[CURSOR:CURSOR+2]=[0,0]
 assert call('seq_event_next_step',[4,255]+u16(CURSOR)+u16(BUF))[0]
 assert list(p.memory[BUF:BUF+4])==model[4][255]
 p.memory[S['_seqeventcache']]=0;p.memory[lo:lo+1024]=saved[:1024];p.memory[0xa800:0xac00]=saved[1024:]
 assert not put(0,[0,61,100,1]) and p.memory[S['_seqeventfull']]
 for c in range(7):
  assert count(c)==len(model[c])
  for i,e in enumerate(model[c]):assert get(c,i)==e,(c,i)
 # Replacing a full-pool event succeeds without changing insertion order.
 e=[255,12,127,0];assert put(6,e,0);model[6][0]=e
 # Erasure compacts both physical halves without corrupting neighboring tracks.
 for c in (0,4,6,3):
  i=len(model[c])//2;call('seq_event_erase',[c]+u16(i));model[c].pop(i)
 for c in range(7):
  for i,e in enumerate(model[c]):assert get(c,i)==e,(c,i,'after erase')
 # Step iteration preserves plot order and returns all coincident drum voices.
 call('seq_storage_clear')
 for e in ([255,2,80,1],[3,4,90,2],[255,1,100,0]):assert put(6,e)
 p.memory[CURSOR:CURSOR+2]=[0,0];found=[]
 while call('seq_event_next_step',[6,255]+u16(CURSOR)+u16(BUF))[0]:found.append(list(p.memory[BUF:BUF+4]))
 assert found==[[255,2,80,1],[255,1,100,0]],found
 # A partially primed Mixer pattern reserves slots with note zero.
 p.memory[S['_seqevents_lo']+1]=0;p.memory[CURSOR:CURSOR+2]=[0,0]
 assert call('seq_event_next_step',[6,255]+u16(CURSOR)+u16(BUF))[0]
 assert list(p.memory[BUF:BUF+4])==[255,1,100,0]
 # Note helpers update in place, accept256 duration, and erase cleanly.
 assert call('seq_note_set',[0,255,128,127]+u16(256))[0]
 assert call('seq_note_get',[0,255])[0]==128
 assert call('seq_velocity_get',[0,255])[0]==127
 assert call('seq_duration_get',[0,255])[1]==256
 assert call('seq_note_set',[0,255,0,0]+u16(0))[0] and count(0)==0
 print('PASS:512shared events,256steps ononechannel,fullpool rejection,WRAM/SRAM shifts,exact insertionorder,256duration,stepiterator,notehelpers')
finally:p.stop(save=False)

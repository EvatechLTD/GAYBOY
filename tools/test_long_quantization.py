"""LONG follows the longest populated track, including 256 steps, and persists."""
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def v(n,o=0):
 a=S['_'+n]+o
 return p.memory[0,a] if 0xa000<=a<0xc000 else p.memory[a]
def tap(k):
 mask={'start':128,'select':64,'a':16,'b':32,'left':2,'right':1,'up':4,'down':8}[k]
 p.button_press(k)
 for _ in range(1800):
  p.tick(1)
  if v('lastpad')&mask:break
 assert v('lastpad')&mask,(k,'press')
 p.button_release(k)
 for _ in range(1800):
  p.tick(1)
  if not v('lastpad')&mask:break
 assert not v('lastpad')&mask,(k,'release')
 p.tick(12)
def choose(n):
 tap('start');category=4 if n in (19,20,24,25) else 0
 for _ in range(5):
  if v('navcategory')==category:break
  tap('right')
 for _ in range(30):
  if v('navchoice')==n:break
  tap('down')
 assert v('navchoice')==n,n
 tap('a');p.tick(30)
 assert v('page')==(28 if n==45 else n)
def masks():return bytes(p.memory[S['_mixer_hidden']:S['_mixer_hidden']+8])
def save(slot):
 choose(25);p.memory[S['_mx']+6]=slot;tap('b');p.tick(100)
 assert v('sparse_song')==slot
 assert not v('mx',52)
def load(slot):
 choose(24);p.memory[S['_mx']+6]=slot;tap('a');p.tick(100)
 assert v('page')==18 and v('sparse_song')==slot

from seq_storage_helpers import write_tracks,write_word
calls=[];boundaries=[]
def hook(name,callback):
 a=S['_'+name];p.hook_register(a>>16,a&65535,callback,None)
def boundary(_):boundaries.append((v('seqposition'),v('seqposition',1)))
def handoff(_):calls.append(boundaries[-1])
try:
 enter_app(p,S);choose(18)
 tracks=[[] for _ in range(7)];tracks[0]=[[0,61,100,1]];tracks[1]=[[0,68,100,1]]
 write_tracks(p,S,tracks)
 for c in range(7):write_word(p,S['_seqlength']+c*2,256 if c==2 else 7 if c==0 else 24 if c==1 else 16)
 write_word(p,S['_seqbpm'],300);write_word(p,S['_seqglobalbpm'],300)
 p.memory[S['_mx']+3]=5;p.memory[S['_mx']+4]=30
 # Save and load through the song UI, preserving LONG and track lengths.
 save(0);p.memory[S['_mx']+3]=2;load(0);assert v('mx',3)==5
 hook('mixer_boundary',boundary);hook('seq_pattern_handoff',handoff)
 p.memory[S['_mx']+4]=0;tap('a');assert v('seqplaying')
 results=[]
 for length in (24,40,256,7):
  write_word(p,S['_seqlength']+2,length)
  # Request away from the outgoing cycle end; current pad retriggers live data.
  for _ in range(5000):
   p.tick(1)
   if 1<=v('seqposition',1)<min(length-1,5):break
  calls.clear();boundaries.clear();p.memory[S['_mx']+4]=30;tap('a')
  for _ in range(6000):
   if calls:break
   p.tick(1)
  assert len(calls)==1,(length,calls)
  # At equal lengths the first populated track is selected; their phases
  # originate together for this final seven-step case only after retrigger.
  if length>7:assert calls[0][1]==length-1,(length,calls)
  else:assert calls[0][0]==6,(length,calls)
  assert v('seqplaying') and v('mx',3)==5
  results.append({'longest':length,'outgoing_positions':calls[0]})
 # Selector cycles through LONG and NOW on master, skipping NOW on slave.
 p.memory[S['_mx']+4]=0;tap('a');assert not v('seqplaying')
 choose(18);p.memory[S['_mx']+3]=4;p.memory[S['_mx']+4]=1;tap('a');assert v('mx',3)==5
 tap('a');assert v('mx',3)==(1 if v('syncslave') else 0)
 battery=bytearray()
 p.memory[S['_mx']+3]=5;save(0)
 for bank in range(4):p.memory[0x4000]=bank;battery.extend(p.memory[0xa000:0xc000])
 p.memory[0x4000]=0;p.stop(save=False)
 p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(battery));p.set_emulation_speed(0)
 enter_app(p,S);assert v('mx',3)==5;load(0);assert v('mx',3)==5
 print('PASS LONG longest populated track, 7/24/40/256 steps, song load and power cycle:',results)
finally:p.stop(save=False)

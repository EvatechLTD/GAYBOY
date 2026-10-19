"""Real Finder/settings navigation and song-scoped mixer persistence."""
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
try:
 enter_app(p,S);p.tick(30)
 choose(45);tap('down');tap('a');assert v('linkpair')==1
 for _ in range(3):tap('down')
 assert v('mx',4)==4
 tap('a');tap('a');assert masks()[0]==1
 tap('select');tap('down');tap('a');tap('down');tap('a')
 assert masks()[4]==2
 tap('select');p.screen.image.save('build/mixer-settings.png');tap('b')
 assert v('page')==18
 tap('select');assert v('page')==18 and not v('mx',5)
 tap('left');assert v('mx',4)==1
 tap('right');assert v('mx',4)==0
 first=masks();save(0)
 choose(45);tap('a');assert v('mixer_device')==1
 tap('down');tap('a');assert not v('linkpair')
 for _ in range(3):tap('down')
 tap('a');tap('b');tap('down');tap('a');tap('select');tap('b')
 second=masks();assert first!=second;save(1)
 load(0);assert masks()==first and v('linkpair')==1 and v('mixer_device')==0
 load(1);assert masks()==second and v('linkpair')==0 and v('mixer_device')==1
 # A second load must recover the original even after later root autosaves.
 load(0);assert masks()==first and v('linkpair')==1
 choose(45);p.screen.image.save('build/mixer-settings-saved-song.png')
 # Reboot the battery and load the other song through the real UI.
 battery=bytearray()
 for bank in range(4):
  p.memory[0x4000]=bank;battery.extend(p.memory[0xa000:0xc000])
 p.memory[0x4000]=0;p.stop(save=False)
 p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(battery));p.set_emulation_speed(0)
 enter_app(p,S);load(1);assert masks()==second and not v('linkpair') and v('mixer_device')==1
 choose(45);tap('a');tap('b');assert not v('mixer_device')
 p.memory[S['_mixer_hidden']:S['_mixer_hidden']+8]=[0]*8
 p.memory[S['_mx']+4]=38
 for kit,label in [(0,'KK1'),(1,'KIK')]:
  p.memory[S['_drumkit']]=kit;p.memory[S['_dirty']]=1;p.tick(60)
  shown=bytes(p.memory[S['_canvas']+96:S['_canvas']+99])
  assert shown==bytes(ord(c)-32 for c in label),(kit,shown,label)
 p.screen.image.save('build/mixer-drum-labels.png')
 print('PASS: Finder Mixer Settings, simple mixer navigation, independent layouts, song save/load, power-cycle and drum sample labels')
finally:p.stop(save=False)

from boot_helpers import enter_app
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
import numpy as np
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(bytes(32768)));p.set_emulation_speed(0);enter_app(p)
from seq_storage_helpers import fixture_value,fixture_put

def v(n,i=0):
 if "_seqeventcounts" in S:return fixture_value(p,S,n,i)
 return p.memory[S['_'+n]+i]

def put(n,i,x):fixture_put(p,S,n,i,x)
def word(n):
 if n=='seqgateleft' and '_seqeventcounts' in S:return fixture_value(p,S,n,0)
 a=S['_'+n];return p.memory[a]|p.memory[a+1]<<8
def press(k):
 mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64,'start':128}[k]
 p.button_press(k)
 for _ in range(60):
  p.tick(1)
  if v('lastpad')&mask:break
 assert v('lastpad')&mask
 p.button_release(k)
 for _ in range(60):
  p.tick(1)
  if not v('lastpad')&mask:break
 assert not v('lastpad')&mask
 p.tick(4)
def send(data):
 for b in data:
  w=v('wr');p.memory[S['_rx']+w]=b;p.memory[S['_wr']]=(w+1)&255;p.tick(8)
def choose(n):
 if n in (2,5,6,7,9,14) and not v('experimental_mode'):
  choose(16);press('a');assert v('experimental_mode');choose(0)
 if 1<=n<=6 and v('page')>=7:choose(0)
 target=([11,12,13,15,14][v('selected')] if n==0 else n)
 if '_navcategory' in S:
  press('start')
  category=4 if target in (19,20,24,25) else 3 if target in (1,2,3,4,5,6,7,9,11,12,13,14,15,17,23) else 0
  for _ in range(5):
   if v('navcategory')==category:break
   press('right')
  for _ in range(40):
   if v('navchoice')==target:break
   press('down')
  assert v('navchoice')==target,target
  press('a');p.tick(40);assert v('page')==(1 if n==0 else n)
  return
 p.button_press('start')
 for _ in range(100):
  p.tick(1)
  if v('navopen'):break
 assert v('navopen')
 for _ in range(32):
  if v('navchoice')==target:break
  press('down')
 assert v('navchoice')==target
 p.screen.image.save('build/ui-menu.png')
 p.button_release('start');p.tick(40);assert v('page')==(1 if n==0 else n)

def edit(delta):
 p.button_press('b');press('up' if delta>0 else 'down');p.button_release('b');p.tick(4)
def goto(osc,row=0,col=0):
 if v('monoedit'):press('a')
 p.button_press('select')
 while v('monoosc')!=osc:press('right')
 p.button_release('select');p.tick(4)
 while v('cursor',7)!=row:press('down')
 while v('monocol')>col:press('left')
 while v('monocol')<col:press('right')
# Instrument fixtures explicitly select P1; production boots into DRUM.
choose(0)
# These fixtures exercise editing from their explicit C4 cursor baseline.
put('seqviewinitialized',0,3)
# Native oscillator baseline, corrected octave mapping and MIDI isolation.
choose(7);assert v('monomode') and v('waveengine')==0
triggers=[]
for name in ('polyevent','polynote','enginenote','mixrender','play'):
 addr=S['_'+name];p.hook_register((addr>>16 if addr>=65536 else addr>>14),addr&65535,lambda ctx:ctx.append(True),triggers)
send([0x94,60,127]);assert [v('basepitch',i) for i in range(3)]==[60]*3
send([0x94,64,127,0x84,64,0]);assert [v('basepitch',i) for i in range(3)]==[60]*3
send([0x90,72,127,0x93,40,127,0xb4,122,127,0xc4,99]);assert not triggers
assert not p.memory[0xff07]&4 and not v('mixrunning') and not v('active',3)
goto(2);edit(-1);assert v('monoset',14)==0 and v('basepitch',2)==48
edit(-1);assert v('monoset',14)==0
assert (p.memory[S['_notes']+72]|p.memory[S['_notes']+73]<<8)>0
# Wave PW has 32 base values and depth maximum 32; waveform bank has 32 choices.
goto(2,2,1)
for _ in range(36):edit(1)
assert v('monodepth',18)==32
goto(2,2);edit(1);assert v('monoset',18)==17
goto(2,3);edit(1);assert v('monoset',19)==1
p.memory[0xff1a]=0
assert bytes(p.memory[0xff30:0xff40])==bytes(p.memory[S['_monowaves']+16:S['_monowaves']+32])
goto(2,4);edit(1);assert v('monoset',20)==2 and p.memory[0xff25]&0x44==4
goto(2,4,1)
for _ in range(5):edit(1)
assert v('monodepth',20)==3
p.screen.image.save('build/ui-mono-wave-mod.png')
# MOD screen owns ADSR, LFO type/rate, and shared bend range.
goto(3,6);edit(1);assert v('monosource',6)==3
assert all(v('param',26*c+25)==3 for c in range(3))
send([0xe4,127,127]);assert all((v('bend',2*c)|(v('bend',2*c+1)<<8))>300 for c in range(3))
send([0xe4,0,64]);p.screen.image.save('build/ui-mono-mod.png')
# Envelope modulation can raise pulse level from zero and return it on release.
for c in range(3):
 for i in range(7):p.memory[S['_monodepth']+7*c+i]=0
 p.memory[S['_monoset']+7*c+1]=0
p.memory[S['_monodepth']+1]=16
for i,x in enumerate([8,8,32,8,0,0]):p.memory[S['_monosource']+i]=x
send([0x94,67,127]);p.tick(24);assert v('envstage')==3 and v('monovol')==8
send([0x84,60,0,67,0]);p.tick(24);assert not v('monodown') and not p.memory[0xff26]&7
# LFO modulates native duty independently of ADSR.
p.memory[S['_monosource']+8]=0
p.memory[S['_monoset']+1]=12;p.memory[S['_monodepth']+1]=0
p.memory[S['_monodepth']+4]=4
for i,x in enumerate([0,0,64,0,2,4]):p.memory[S['_monosource']+i]=x
send([0x94,60,127]);duties=set()
for _ in range(100):p.tick(1);duties.add(p.memory[0xff11]>>6)
assert len(duties)>=2 and v('monoset',4)==2
for c in range(3):
 for i in range(7):p.memory[S['_monodepth']+7*c+i]=0
 p.memory[S['_monoset']+7*c+1]=0
send([0x94,72,127]);p.tick(30)
assert not np.any(p.sound.ndarray) and not p.memory[0xff25] and not p.memory[0xff07]&4
assert not triggers
p.stop(save=False)
print('PASS: native isolation, octave mapping, D-pad/B controls, per-setting depths, 32 waves/PW, pan, ADSR, LFO, bend range, mute')

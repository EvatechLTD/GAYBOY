from boot_helpers import enter_app, enable_experimental
from pathlib import Path
from pyboy import PyBoy
import json
symbols={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True);p.set_emulation_speed(0);enter_app(p);enable_experimental(p)
def val(n,i=0):return p.memory[symbols['_'+n]+i]
def serial(data):
 for b in data:
  w=val('wr');p.memory[symbols['_rx']+w]=b;p.memory[symbols['_wr']]=(w+1)&255;p.tick(8)
assert p.memory[0xff02]&128
serial([0x90,60,127]);assert val('active')==1 and p.memory[0xff26]&1
serial([0xb0,41,127]);assert val('param')==3
serial([0x80,60,0]);assert val('active')==0
serial([0xc0,99]);assert val('program')==99
serial([0xb0,117,0])
for c in range(4):
 serial([0x90+c,60,100]);assert val('active',c)==1
 serial([0x80+c,60,0]);assert val('active',c)==0
serial([0xb2,70,127,71,0]);assert val('custom')==1 and val('customwave')==0xf0
serial([0x92,60,127]);assert p.memory[0xff26]&4
serial([0xb2,103,127]);assert all(val('active',c)==0 for c in range(4))
p.button_press('down');p.tick(10);p.button_release('down');p.tick(10);assert val('program')==0
p.button_press('a');p.tick(10);p.button_release('a');p.tick(10);assert val('program')==0
p.button_press('b');p.tick(10);assert val('active')==1
p.screen.image.save('build/ui-audition.png');p.button_release('b')
for _ in range(60):
 p.tick(1)
 if not val('lastpad')&32:break
assert not val('lastpad')&32 and val('active')==0
rom=Path('build/GAYBOY.gb').read_bytes();h=0
for b in rom[0x134:0x14d]:h=(h-b-1)&255
assert h==rom[0x14d];assert ((sum(rom)-rom[0x14e]-rom[0x14f])&65535)==int.from_bytes(rom[0x14e:0x150],'big')
assert len(json.loads(Path('src/presets.json').read_text()))==100
# Macro motion without envelope retriggers: major arp, duty sequencer, gate.
serial([0xc0,3,0xb0,117,0,0x90,60,127])
p.tick(3);before=val('phase');p.tick(8);assert val('phase')!=before
serial([0xb0,112,0,113,127,114,127]);p.tick(3);assert val('mods',1)==4 and val('mods',2)==3
serial([0xb0,117,20]);p.tick(20);assert val('active')==0
# UI pages, editing and table playback; capture every screen on the real ROM.
def press(key):
 p.button_press(key);p.tick(12);p.button_release(key);p.tick(12)
def page(n):
 if 1<=n<=6 and val('page')>=7:page(0)
 n=([11,12,13,15,14][val('selected')] if n==0 else n)
 p.button_press('start');p.tick(12)
 while val('navchoice')!=n:press('down')
 p.button_release('start');p.tick(12)
 p.tick(24)
page(0);serial([0xc0,3,0xb0,117,0,0x90,60,127]);p.tick(30)
p.screen.image.save('build/ui-live.png')
page(1);before=val('param');press('right');assert val('param')==(before+1)%4
p.screen.image.save('build/ui-tone.png')
page(2);before=val('mods');press('right');assert val('mods')==(before+1)%16
p.screen.image.save('build/ui-mod.png')
page(3);before=val('program');press('down');assert val('program')==(before+1)%100
p.screen.image.save('build/ui-bank.png')
page(4);press('right');assert val('cursor',4)==7
p.screen.image.save('build/ui-cc.png')
page(5);before=val('tables');press('right');assert val('tables')==before+1
press('a');assert val('tablefield')==1
p.screen.image.save('build/ui-table.png')
serial([0xb0,118,32,119,127,117,0,112,32,0x90,60,127]);p.tick(2)
before=val('tablepos');p.tick(5);assert val('tablepos')!=before
serial([0xb0,118,96]);before=val('notestep');serial([0x90,62,127]);assert val('notestep')==before+1
p.button_press('select');p.button_press('start');p.tick(12);assert not any(val('active',c) for c in range(4))
p.button_release('select');p.button_release('start');p.tick(12)
# Synthetic MIDI burst must drain while graphical updates continue.
packet=[0xb0]+[v for i in range(60) for v in [115,i%128]]
w=val('wr')
for b in packet:p.memory[symbols['_rx']+w]=b;w=(w+1)&255
p.memory[symbols['_wr']]=w;p.tick(24);assert val('rd')==w
# Regression: knobs/wheel must never enter note trigger or rewrite wave RAM.
plays=[];waves=[]
p.hook_register(0,symbols['_play'],lambda ctx:ctx.append(True),plays)
p.hook_register(symbols['_wave']>>16,symbols['_wave']&65535,lambda ctx:ctx.append(True),waves)
def word(name,c=0):
 a=symbols['_'+name]+c*2;return p.memory[a]|(p.memory[a+1]<<8)
for c in range(4):
 serial([0xc0+c,0,0xb0+c,118,0,117,0,0x90+c,60,127]);p.tick(10)
 start=len(plays);startwave=len(waves);before=val('age',c)
 for control,value in [(41,100),(42,64),(43,100),(44,32),(45,32),(47,0),(55,96),(56,64),(59,64),(60,100),(61,64),(66,64)]:
  serial([0xb0+c,control,value])
 serial([0xe0+c,127,127]);assert word('wheellast',c)==16383
 assert len(plays)==start and len(waves)==startwave
 assert val('age',c)>=before and val('active',c)==1
 # Sustained, released keys also bend without becoming held again.
 serial([0xb0+c,64,127,0x80+c,60,0,0xe0+c,0,0]);assert val('held',c)==255 and val('active',c)==1
 assert len(plays)==start
 serial([0xb0+c,64,0]);assert val('active',c)==0
# Wave edits stay queued until a new note; no DAC interruption or play call.
serial([0xc2,0,0xb2,118,0,117,0,0x92,60,127]);start=len(plays);startwave=len(waves)
serial([0xb2,70,127,71,0]);assert val('wavepending')==1 and val('customwave')==0xf0
assert len(plays)==start and len(waves)==startwave and p.memory[0xff26]&4
serial([0x92,62,127]);assert val('wavepending')==0
# Three-note poly mode on logical MIDI channel five, including oldest steal.
serial([0xc4,0,0xb4,117,0,118,0,0x94,60,100,64,100,67,100])
assert val('polymode')==1 and all(val('active',c) for c in range(3))
assert [val('basepitch',c) for c in range(3)]==[60,64,67]
serial([0x94,72,100]);assert [val('basepitch',c) for c in range(3)]==[72,64,67]
serial([0x84,60,0]);assert val('active')==1 # Old stolen note-off is harmless.
serial([0xb4,64,127,0x84,72,0]);assert val('active')==1 and val('held')==255
start=len(plays);serial([0xe4,127,127,0xb4,41,64]);assert len(plays)==start
assert all(word('wheellast',c)==16383 for c in range(3))
serial([0xb4,64,0]);assert val('active')==0 and val('active',1)==1
serial([0xb4,123,0]);assert not any(val('active',c) for c in range(3))
# Poly browser audition produces a chord and releases it cleanly.
page(3);p.button_press('b');p.tick(12);assert all(val('active',c) for c in range(3))
p.screen.image.save('build/ui-poly.png');p.button_release('b');p.tick(12);assert not any(val('active',c) for c in range(3))
p.stop(save=False);print('PASS: boot, MIDI receive queue, four voices, CC, program 100, custom wave, panic, buttons, ROM checksums, macros, six UI pages, instant loading, local edits, tables, MIDI burst, no-retrigger CC/wheel, queued wave edits, 3-note poly/sustain/stealing')





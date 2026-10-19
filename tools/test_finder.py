"""Finder navigation and contextual actions on the compiled ROM."""
from pathlib import Path
from io import BytesIO
from pyboy import PyBoy
from boot_helpers import enter_app
S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def v(n):return p.memory[S['_'+n]]
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
def category(n):
 for _ in range(5):
  if v('navcategory')==n:return
  tap('right')
 assert v('navcategory')==n
def item(n):
 for _ in range(20):
  if v('navchoice')==n:return
  tap('down')
 assert v('navchoice')==n,n
try:
 enter_app(p);p.tick(30)
 assert v('page')==8
 tap('start');assert v('navopen')
 p.tick(120);assert v('navopen'),'release must keep menu open'
 category(1);item(35);p.screen.image.save('build/finder-edit.png')
 tap('start');assert v('page')==26 and not v('navopen')
 tap('select');assert v('page')==8
 from seq_storage_helpers import write_tracks
 tracks=[[] for _ in range(7)];tracks[6]=[[0,1,100,1]];write_tracks(p,S,tracks)
 tap('start');category(1);item(38);tap('start')
 tap('start');category(1);item(21)
 tap('start');assert v('page')==8 and not v('navopen')
 for target,track in [(28,0),(29,1),(30,2),(31,3),(34,6)]:
  tap('start');category(2);item(target);tap('start')
  assert v('page')==8 and v('seqtrack')==track,(target,v('seqtrack'))
 tap('start');category(0);item(18);tap('start');assert v('page')==18
 tap('start');category(1);item(26);tap('start');assert v('page')==26
 tap('select');assert v('page')==18
 tap('start');category(1);assert v('navchoice')==26
 tap('b');assert v('navopen');tap('select');assert not v('navopen')
 tap('start');category(3);p.screen.image.save('build/finder-instruments.png')
 tap('select');assert v('page')==18
 p.memory[S['_experimental_mode']]=1
 for target,track in [(32,4),(33,5),(34,6)]:
  tap('start');category(2);item(target);tap('start')
  assert v('page')==8 and v('seqtrack')==track,(target,v('seqtrack'))
 tap('start');category(3);item(11);tap('start');assert v('page')==1
 tap('start');category(3);item(6);p.screen.image.save('build/finder-scroll.png')
 tap('select')
 p.button_press('select');tap('start');p.button_release('select');p.tick(30)
 assert not v('navopen'),'panic shortcut must stay out of menu'
 print('PASS: latched Start menu, categories, direct tracks, contextual clear/copy, Edit context, cancel, scroll, panic')
finally:p.stop(save=False)

"""Shared M/S, fader and filename-font tiles survive real page transitions."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def tap(k):
 mask={'start':128,'select':64,'a':16,'b':32,'left':2,'right':1,'up':4,'down':8}[k]
 for down in (True,False):
  (p.button_press if down else p.button_release)(k)
  for _ in range(600):
   p.tick(1)
   if bool(get('lastpad')&mask)==down:break
  else:raise AssertionError(('input timeout',k,down))
 p.tick(12)
def choose(n):
 tap('start');category=2 if 28<=n<=34 else 4 if n in (19,20) else 1 if n in (40,41) else 0
 for _ in range(5):
  if get('navcategory')==category:break
  tap('right')
 for _ in range(32):
  if get('navchoice')==n:break
  tap('down')
 assert get('navchoice')==n,(n,get('navchoice'))
 tap('a');p.tick(180);assert get('page')==(8 if 28<=n<=34 else 18 if n==40 else 26 if n==41 else n)
def tile(n):
 at=0x8000+n*16 if p.memory[0xff40]&16 else 0x9000+(n if n<128 else n-256)*16
 return bytes(p.memory[at:at+16])
def rails():return [tile(192+i if i<12 else 220+i-12) for i in range(42)]
try:
 enter_app(p,symbols);put('sticky_start',1)
 choose(28);switches=[tile(i) for i in range(244,252)]
 # An aborted roll rebuild can clear the grid-font flag while M/S stays cached.
 put('seqfontdirty',0)
 choose(18);reference=rails();assert not get('seqtilesready'),'Mixer must revoke the overwritten M/S cache'
 # Copy/paste returns through the overwrite dialog, without mixer_open.
 put('mx',30,4);put('dirty',1);p.tick(30);choose(40)
 put('mx',31,4);put('dirty',1);p.tick(30);choose(41);tap('up');tap('a');p.tick(180)
 assert get('page')==18 and not get('mx',7)
 assert bytes(p.memory[1,0xa800:0xb000])==bytes(p.memory[3,0xaa00:0xb200]),'Pad paste changed copied data'
 assert rails()==reference,'Pad-copy confirmation left font glyphs in cached mixer rails'
 for _ in range(3):
  choose(19);tap('select');p.tick(180)
  assert get('page')==18 and not get('mx',7)
  assert rails()==reference,'Filename/font page left cached text in mixer rails'
  assert bytes(get('canvas',i) for i in range(5))==bytes(ord(c)-32+96 for c in 'MIXER')
  choose(28);assert [tile(i) for i in range(244,252)]==switches,'M/S tiles were not rebuilt after mixer'
  choose(18);assert rails()==reference,'M/S header leaked into mixer rails'
 p.screen.image.save('build/shared-ui-mixer.png')
 print('PASS M/S ownership, complete fader restoration, load-screen cancellation, three repeated round trips')
finally:p.stop(save=False)

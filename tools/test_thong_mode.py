"""Fixed-bar arrangement editing, exact clip lengths and sparse storage."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
S=symbols

def key(k,down):
 mask={'start':128,'select':64,'a':16,'b':32,'left':2,'right':1,'up':4,'down':8}[k]
 (p.button_press if down else p.button_release)(k)
 for _ in range(1800):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:break
 else:raise AssertionError(('input timeout',k,down))
 p.tick(3)
def tap(k):key(k,True);key(k,False)
def choose_song():
 tap('start')
 for _ in range(24):
  if get('navchoice')==54:break
  tap('down')
 assert get('navchoice')==54,get('navchoice')
 tap('a');p.tick(60);assert get('page')==29

def read_storage(at,n):
 out=[]
 for i in range(at,at+n):
  slot,off=divmod(i,288);out.append(p.memory[1+slot//4,0xa000+(slot%4)*2048+480+off])
 return bytes(out)
def clips():
 n=read_storage(4,1)[0];out=[]
 for i in range(n):
  b=read_storage(8+i*9,9);out.append((int.from_bytes(b[:4],'little'),int.from_bytes(b[4:8],'little'),b[8]))
 return out

def cursor():return int.from_bytes(bytes(get('song_view',i) for i in range(4)),'little')

try:
 enter_app(p,S);put('sticky_start',1);choose_song()
 assert read_storage(0,8)==b'THG1\0\0\1\0'
 tap('b');assert clips()==[(0,16,0)],clips()
 tap('right');tap('b');assert clips()==[(0,32,0)],clips()
 tap('down');tap('b');assert clips()==[(0,32,0)],'Overlapping different lane was admitted'
 tap('right');tap('b');assert clips()==[(0,32,0),(32,16,1)],clips()
 key('b',True);tap('right');key('b',False)
 assert clips()==[(0,32,0),(32,32,1)],clips()
 assert cursor()==48,cursor()
 key('a',True);tap('right');key('a',False)
 assert clips()==[(0,32,0),(48,32,1)],clips()
 # Select+arrows no longer changes the fixed bar resolution.
 before=clips();position=cursor()
 key('select',True);tap('up');tap('down');key('select',False)
 assert cursor()==position and clips()==before
 # The timeline still extends beyond a16-bit native-step coordinate.
 for i,v in enumerate((65536).to_bytes(4,'little')):put('song_view',v,i)
 put('dirty',1);p.tick(60);tap('right');assert cursor()==65552,cursor()
 # Select the two clips by drawing a box from empty time before them.
 for i,v in enumerate((0).to_bytes(4,'little')):put('song_view',v,i)
 put('song_view',2,10);put('song_view',0,11);put('song_view',0,12);put('dirty',1);p.tick(60)
 key('a',True)
 for _ in range(5):tap('right')
 tap('up');tap('up');key('a',False)
 # Move both clips horizontally without changing their lanes or lengths.
 for i,v in enumerate((0).to_bytes(4,'little')):put('song_view',v,i)
 put('song_view',0,10);put('dirty',1);p.tick(60)
 key('a',True);tap('right');key('a',False)
 assert clips()==[(16,32,0),(64,32,1)],clips()
 key('b',True);tap('left');key('b',False)
 assert clips()==[(16,16,0),(64,16,1)],clips()
 p.screen.image.save('build/thong-editor.png')
 print('PASS plot, adjacent repetition, cross-lane collision, resize, horizontal drag, fixed one-bar cells and long timeline')
finally:p.stop(save=False)

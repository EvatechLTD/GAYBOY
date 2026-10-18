"""Length dragging pauses on a fully drawn viewport before paging."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import read_tracks,write_tracks

def put(n,i,x):fixture_put(p,S,n,i,x)
def setup(track,zoom):
 put('seqtrack',0,track);put('seqzoom',0,zoom);put('seqlength',track,256)
 cols=(zoom+1)*8
 tracks=[[] for _ in range(7)];tracks[track]=[[0,1 if track==6 else 61,100,cols-2]];write_tracks(p,S,tracks)
 put('seqcursor',track,cols-3);put('seqpitch',track,60);put('drumrow',0,0)
 put('seqhead',0,0);put('seqfocus',0,0);put('seqgrouptrack',0,255)
 put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(20)
 return cols
try:
 choose(8)
 for track in (0,6):
  for zoom in (0,1,3):
   cols=setup(track,zoom)
   p.button_press('b');p.tick(3);p.button_press('right')
   for _ in range(240):
    p.tick(1)
    if v('seqcursor',track)==cols-1 and v('seqdrawvalid') and v('seqviewbase')==0:break
   else:raise AssertionError(('never drew full page',track,zoom))
   assert read_tracks(p,S)[track][0][3]==cols
   p.tick(8)
   assert v('seqcursor',track)==cols-1 and v('seqbase')==0,('overshot pause',track,zoom)
   if track==6 and zoom==1:p.screen.image.save('build/ui-length-page-pause.png')
   for _ in range(120):
    p.tick(1)
    if v('seqbase')>0:break
   else:raise AssertionError(('held resize never paged',track,zoom))
   p.button_release('right');p.button_release('b');p.tick(15)
 # Letting go at the edge keeps the completed page and exact note length.
 cols=setup(0,1);p.button_press('b');p.tick(3);p.button_press('right')
 for _ in range(120):
  p.tick(1)
  if v('seqcursor')==cols-1:break
 p.button_release('right');p.button_release('b');p.tick(25)
 assert v('seqbase')==0 and read_tracks(p,S)[0][0][3]==cols
 # Ordinary navigation crosses the boundary on the first press.
 press('right');assert v('seqcursor')==cols and v('seqbase')>0
 print('PASS: melodic/drum length edge pause at 8/16/32 columns, completed redraw, continued hold, release and immediate normal navigation')
finally:p.stop(save=False)

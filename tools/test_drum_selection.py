"""Rectangle selection and group placement/length edits on the drum roll."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
def put(n,i,x):fixture_put(p,S,n,i,x)
def chord(mod,key):
 p.button_press(mod);p.tick(5);press(key);p.button_release(mod);p.tick(8)
def holda():
 p.button_press('a')
 for _ in range(180):
  p.tick(1)
  if v('lastpad')&16:break
 assert v('lastpad')&16
def releasea():
 p.button_release('a')
 for _ in range(180):
  p.tick(1)
  if not v('lastpad')&16:break
 assert not v('lastpad')&16
 p.tick(8)
def cursor(step,row):
 put('seqcursor',6,step);put('drumrow',0,row);put('seqhead',0,0);put('dirty',0,1);p.tick(12)
try:
 choose(8);chord('select','left');assert v('seqtrack')==6
 for i in range(128):put('drumhits',i,0);put('noisehits',i,0)
 for i in (2,7):put('noisehits',i,1);put('noisevel',i,99);put('noisedur',i,2)
 cursor(0,9);holda()
 for _ in range(4):press('right')
 press('down');press('down');releasea()
 # Drag one member; both selected notes move by one column.
 cursor(1,10);holda();press('right');releasea()
 assert not v('noisehits',2) and not v('noisehits',7)
 assert v('noisehits',4) and v('noisehits',9)
 assert v('noisedur',4)==2 and v('noisedur',9)==2
 cursor(2,10);chord('b','right')
 assert v('noisedur',4)==3 and v('noisedur',9)==3
 # Empty A tap clears the selection; subsequent length edit affects one note.
 cursor(0,9);press('a');cursor(2,10);chord('b','right')
 assert v('noisedur',4)==4 and v('noisedur',9)==3
 # Editing an older PCM hit preserves its plot order for later voice eviction.
 from seq_storage_helpers import read_tracks,write_tracks
 tracks=read_tracks(p,S);tracks[6]=[[0,1,99,1],[0,2,99,1]];write_tracks(p,S,tracks)
 cursor(0,0);chord('b','right')
 assert [e[1] for e in read_tracks(p,S)[6]]==[1,2],'Resizing renewed the oldest plot age'
 cursor(0,2);press('b')
 assert [e[1] for e in read_tracks(p,S)[6]]==[1,3],'Third overlapping sample must evict the most recently plotted hit'
 print('PASS: drum rectangle selection, group move, group length edits and empty-cell clear')
finally:p.stop(save=False)

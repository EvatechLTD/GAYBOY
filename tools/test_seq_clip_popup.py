"""Selection popup, nondestructive region paste, and captured destination."""
exec(open('tools/test_monosynth.py').read().split('# Native oscillator baseline')[0])
from seq_storage_helpers import read_tracks,write_tracks

def put(n,i,x):fixture_put(p,S,n,i,x)
def cursor(x,y,track=0):
 put('seqcursor',track,x);put('drumrow' if track==6 else 'seqpitch',0 if track==6 else track,y)
 put('seqhead',0,0);put('dirty',0,1);p.tick(12)
def selectbox(track,x0,x1,y0,y1):
 for name,value in (('seqgrouptrack',track),('seqgroupx0',x0),('seqgroupx1',x1),('seqgroupy0',y0),('seqgroupy1',y1)):put(name,0,value)
 put('seqdrawvalid',0,0);put('dirty',0,1);p.tick(12)
def popup(action):
 press('select');assert v('seqpopup') and v('page')==8
 for _ in range(action):press('down')
 press('a')
try:
 choose(8);put('seqtrack',0,0);put('seqlength',0,64)
 tracks=[[] for _ in range(7)];tracks[0]=[[1,61,77,2],[3,63,99,3],[12,49,88,1]];write_tracks(p,S,tracks)
 selectbox(0,1,4,60,63);cursor(4,63)
 press('select');assert v('seqpopup') and v('page')==8
 p.tick(12);p.screen.image.save('build/ui-selection-popup.png');press('a')
 assert read_tracks(p,S)[0]==tracks[0] and not v('seqpopup')
 cursor(20,72);popup(2)
 events=read_tracks(p,S)[0]
 assert [20,70,77,2] in events and [22,72,99,3] in events,events
 assert [12,49,88,1] in events and len(events)==5
 # Cut copies exactly the highlighted range; paste keeps the new cell anchor.
 selectbox(0,1,4,60,63);cursor(4,63);popup(1)
 assert read_tracks(p,S)[0]==[[12,49,88,1],[20,70,77,2],[22,72,99,3]]
 cursor(30,75);popup(2)
 assert [30,73,77,2] in read_tracks(p,S)[0] and [32,75,99,3] in read_tracks(p,S)[0]
 # Invalid destinations leave every event unchanged and keep an error popup.
 before=read_tracks(p,S);cursor(63,75);popup(2)
 assert v('seqpopup') and read_tracks(p,S)==before
 press('b');assert not v('seqpopup') and v('page')==8
 # Drum row offsets follow the grid downwards.
 put('seqtrack',0,6);put('seqlength',6,64)
 tracks=read_tracks(p,S);tracks[6]=[[1,11,64,2],[3,12,92,1],[8,1,100,1]];write_tracks(p,S,tracks)
 selectbox(6,1,3,10,11);cursor(3,11,6);popup(0)
 cursor(20,10,6);popup(2)
 assert [20,11,64,2] in read_tracks(p,S)[6] and [22,12,92,1] in read_tracks(p,S)[6]
 # Without a highlighted range, Select retains the settings shortcut.
 put('seqgrouptrack',0,255);press('select');assert v('page')==10
 print('PASS: selection Copy/Cut/Paste popup, captured cell, note spacing/pitch/velocity/duration, unrelated notes, bounds, drums, cancel and settings')
finally:p.stop(save=False)

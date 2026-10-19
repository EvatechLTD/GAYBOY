"""Exercise Finder editing against real event storage and committed pad roots."""
exec(open('tools/test_finder.py').read().split('try:\n')[0])
from seq_storage_helpers import write_tracks,read_tracks,read_word,write_word,mark_pattern_changed
from sparse_image import SparseImage

def put(n,x,i=0):p.memory[S['_'+n]+i]=x
def w(n,i=0):return read_word(p,S['_'+n]+i*2)
def setw(n,x,i=0):write_word(p,S['_'+n]+i*2,x)
def action(n,cat=1):
 tap('start');assert v('navopen');category(cat);item(n);tap('start')
def cancel():tap('select');assert v('page')!=26
def confirm():tap('up');tap('start');assert v('page')!=26

def fixture(tracks,length=32):
 write_tracks(p,S,tracks)
 for c in range(7):setw('seqlength',length,c)
 put('seqdrawvalid',0);put('seqhead',0);put('seqfocus',0);put('seqgrouptrack',255);p.tick(30)

def image():
 data=bytearray()
 for bank in range(4):
  p.memory[0x4000]=bank;data.extend(p.memory[0xa000:0xc000])
 p.memory[0x4000]=0
 return SparseImage(bytes(data))

def pad(n):p.memory[0,S['_mx']+4]=30+n
try:
 enter_app(p);p.tick(30)
 # Select visible 16 steps, then duplicate a drum beat into steps 17..32.
 tracks=[[] for _ in range(7)];tracks[6]=[[0,1,100,1],[4,2,90,1],[8,3,110,1],[15,13,80,1],[20,1,70,1]]
 fixture(tracks);put('seqcursor',0,6);put('seqzoom',1);put('seqdrawvalid',0);p.tick(25)
 action(38);assert [v(n) for n in ('seqgrouptrack','seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1')]==[6,0,15,0,12]
 p.screen.image.save('build/finder-select-all.png')
 # A already deselects. The new action must keep that gesture.
 put('seqcursor',1,6);put('seqdrawvalid',0);p.tick(20);tap('a');assert v('seqgrouptrack')==255
 action(38);action(21)
 put('seqcursor',16,6);put('seqdrawvalid',0);p.tick(20);action(22)
 expected=tracks[6]+[[e[0]+16,*e[1:]] for e in tracks[6][:4]]
 assert sorted(read_tracks(p,S)[6])==sorted(expected),read_tracks(p,S)[6]
 assert v('seqgroupx0')==16 and v('seqgroupx1')==31
 # Delete/cut only selected notes; the first half and other tracks survive.
 action(42);assert read_tracks(p,S)[6]==tracks[6][:4]
 action(22);assert len(read_tracks(p,S)[6])==8
 action(43);assert len(read_tracks(p,S)[6])==4
 action(22);assert len(read_tracks(p,S)[6])==8
 # Whole track copying ignores the current visible selection and copies settings.
 original=read_tracks(p,S)[6];action(36)
 action(28,2);action(37);assert w('seqlength')==32
 assert len(read_tracks(p,S)[0])==8 and read_tracks(p,S)[6]==original
 # Clear Track defaults to Cancel; Select cancels and B does nothing.
 action(35);before=read_tracks(p,S);tap('b');assert v('page')==26;cancel();assert read_tracks(p,S)==before
 action(35);confirm();assert not read_tracks(p,S)[0] and read_tracks(p,S)[6]==original
 # Sequencer entry returns to last track even after instrument visits.
 action(30,2);assert v('seqtrack')==2
 action(18,0);assert v('page')==18
 action(11,3);assert v('page')==1
 action(8,0);assert v('page')==8 and v('seqtrack')==2
 # Zoom-dependent visible rectangles on melodic tracks.
 tracks=[[] for _ in range(7)];tracks[2]=[[0,49,100,1],[7,50,100,1],[16,51,100,1],[24,52,100,1]]
 fixture(tracks,64);put('seqtop',60,2);put('seqpitch',55,2)
 for zoom,base,width in [(0,0,8),(1,16,16),(2,24,24)]:
  put('seqzoom',zoom);put('seqcursor',base,2);put('seqdrawvalid',0);p.tick(30);action(38)
  assert v('seqgroupx0')==base and v('seqgroupx1')==base+width-1,(zoom,v('seqgroupx0'),v('seqgroupx1'))
  assert v('seqgroupy1')-v('seqgroupy0')+1==v('seqrows')
 # Operations are unavailable outside grid context; Page starts the bar.
 action(10,2);tap('start');assert v('navcategory')==0;category(1);assert v('navchoice')==255;tap('select')
 action(8,0);action(18,0);assert v('page')==18
 # Save a library item and a song via the existing File workflow.
 action(20,4);tap('b');assert v('page')==18
 action(25,4);tap('b');assert v('page')==18
 saved=image();library=saved.word(saved.root,96);song=saved.word(saved.root,32)
 assert library!=65535 and song!=65535
 # Pattern copy captures all tracks/settings/patches, independently of later edits.
 pad(0);action(40);copied=image();clip=copied.word(copied.root,98);assert clip!=65535
 source_bytes=copied.object(clip,'P');tone=copied.word(source_bytes,100);tone_bytes=copied.object(tone,'T')
 live=read_tracks(p,S)
 action(26);confirm();assert all(not t for t in read_tracks(p,S))
 pad(1);action(41)
 if v('page')==26:confirm()
 pasted=image();assert pasted.word(pasted.root,18)==clip
 assert all(not t for t in read_tracks(p,S)),'inactive paste must preserve the live pattern'
 tap('a');p.tick(60);assert p.memory[0,S['_mx']+1]==1
 assert read_tracks(p,S)==live
 assert image().object(tone,'T')==tone_bytes
 # Overwrite acknowledgement and cancellation preserve the destination.
 pad(1);action(41);assert v('page')==26;cancel();assert read_tracks(p,S)==live
 # Clear Song wipes the working pads only, without erasing saved archives or clipboard.
 action(39);assert v('page')==26;p.screen.image.save('build/finder-clear-song.png');cancel();assert read_tracks(p,S)==live
 p.memory[0,S['_mx']+4]=0
 if not v('seqplaying'):tap('a')
 assert v('seqplaying')
 action(39);confirm();cleared=image()
 assert all(cleared.word(cleared.root,16+i*2)==65535 for i in range(8))
 assert cleared.word(cleared.root,96)==library and cleared.word(cleared.root,32)==song
 assert cleared.word(cleared.root,98)==clip and cleared.object(clip,'P')==source_bytes
 assert all(not t for t in read_tracks(p,S)) and not v('seqplaying')
 # Pasting after Clear Song proves the clipboard remains alive across collection.
 pad(0);action(41);assert v('page')==18 and read_tracks(p,S)==live
 print('PASS: visible selection/zoom, 16-to-32 duplication, A deselect, cut/delete, entire tracks, scoped clears, last Seq channel, pad clipboard and saved archive preservation')
finally:p.stop(save=False)

"""Focused pads drive files and editing independently of the playing pattern."""
exec(open('tools/test_mixer_settings.py').read().split('try:\n')[0])
from sparse_image import SparseImage
from seq_storage_helpers import read_tracks,write_tracks

def image():
 data=bytearray()
 for bank in range(4):
  p.memory[0x4000]=bank;data.extend(p.memory[0xa000:0xc000])
 p.memory[0x4000]=0
 return SparseImage(bytes(data))
def ref(i):
 im=image();return im.word(im.root,16+i*2)
def pad(i):p.memory[0,S['_mx']+4]=30+i;p.memory[S['_dirty']]=1;p.tick(20)
def action(n):
 tap('start')
 for _ in range(5):
  if v('navcategory')==1:break
  tap('right')
 for _ in range(30):
  if v('navchoice')==n:break
  tap('down')
 assert v('navchoice')==n
 tap('a')
def confirm():assert v('page')==26;tap('up');tap('a');assert v('page')==18
try:
 enter_app(p,S);choose(18);assert v('mx',1)==0 and not v('seqplaying')
 tracks=[[] for _ in range(7)];tracks[6]=[[0,1,120,1],[7,2,95,1],[12,3,80,1]];write_tracks(p,S,tracks)
 live=read_tracks(p,S);active=ref(0);pad(1)
 choose(19);choose(20);assert p.memory[0xaea9]==1
 name=b'FOCUS PAD TWO'.ljust(17,b'\0');p.memory[0xae98:0xae98+17]=list(name)
 p.memory[0,S['_mx']+6]=v('sparse_patterns');tap('b');assert v('page')==18
 assert image().pattern_name(ref(1))=='FOCUS PAD TWO'
 assert ref(0)==active and v('mx',1)==0 and not v('seqplaying') and read_tracks(p,S)==live
 pad(1);source=ref(1);action(40);pad(2);action(41);assert v('page')==26
 tap('a');assert v('page')==18 and ref(2)!=source,'Cancel is the default'
 pad(2);action(41);confirm();assert ref(2)==source and read_tracks(p,S)==live
 pad(1);before=ref(1);choose(19);p.memory[0,S['_mx']+6]=0;tap('a');assert v('page')==26
 tap('select');assert v('page')==19 and ref(1)==before
 tap('a');confirm();assert ref(1)!=before and ref(0)==active and v('mx',1)==0
 assert read_tracks(p,S)==live and not v('seqplaying')
 pad(1);choose(20);p.memory[0,S['_mx']+6]=0;tap('b');assert v('page')==26;confirm()
 assert ref(0)==active and v('mx',1)==0 and read_tracks(p,S)==live
 pad(1);tap('a');assert v('seqplaying') and v('mx',1)==1 and v('page')==18
 running=read_tracks(p,S);pad(2);choose(19);p.memory[0,S['_mx']+6]=0;tap('a');confirm()
 assert v('seqplaying') and v('mx',1)==1 and read_tracks(p,S)==running
 p.memory[0,S['_mx']+4]=0;tap('a');assert not v('seqplaying')
 print('PASS: highlighted-pad copy/paste/load/save, overwrite/cancel, preserved live pattern and A starts playback')
finally:p.stop(save=False)

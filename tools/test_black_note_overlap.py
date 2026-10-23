"""Black visuals stay independent of native/PCM admission and safe overlap edits."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'b':32,'select':64,'up':4}[n];(p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def tap(n):key(n,True);key(n,False);p.tick(120)
def transport():key('select',True);tap('a');key('select',False);p.tick(180)
def pixel(x,y):
 tile=p.memory[0x9800+(1+y//8)*32+x//8];base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16;mask=128>>(x&7);off=base+(y&7)*2
 return bool(p.memory[off]&mask)+2*bool(p.memory[off+1]&mask)
def note_pixel(pitch,step=2):return pixel(get('rollx',step)+2,(get('seqtop',1)-pitch)*get('seqheight')+3)
def grid(left=16):return bytes(pixel(x,y) for y in range(get('seqgridheight')) for x in range(left,160))
def install(tracks,track):
 offset=0
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1);put('pattern_dirty',1);put('seqirqdirty',1)
 put('page',8);put('seqtrack',track);put('selected',track if track<3 else 2);put('seqhead',0);put('seqfocus',0);put('seqgrouptrack',255);put('seqviewinitialized',127);put('seqzoom',1);put('seqcursor',0,track);put('seqtop',65,1);put('seqpitch',62,1);put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(240)
def mode(on):
 put('seqhead',1);put('dirty',1);p.tick(30);tap('a');assert get('evalpatch',16)==on
 put('seqhead',0);put('dirty',1);p.tick(120)
try:
 enter_app(p,symbols)
 put('evalpatch',1,29)
 install([[],[[0,61,100,16],[0,63,90,16],[0,65,80,16],[4,63,90,8]],[],[],[],[],[]],1)
 assert all(note_pixel(n)==3 for n in (60,62,64)),[note_pixel(n) for n in (60,62,64)]
 before=grid();mode(1);assert grid()==before,'ARP changes note colors';mode(0);assert grid()==before,'MONO changes note colors'
 # Remove a later same-pitch note: its earlier sustaining neighbor must remain.
 put('seqcursor',4,1);put('seqpitch',62,1);put('dirty',1);p.tick(30);tap('b');p.tick(240)
 assert get('seqeventcounts',2)==3
 assert note_pixel(62,6)==3,'Overlap erase wiped the surviving note'
 # Move another pitch through the normal A+Up drag.
 put('seqcursor',0,1);put('seqpitch',64,1);put('dirty',1);p.tick(30)
 key('a',True);tap('up');key('a',False);p.tick(240)
 assert list(p.memory[1,0xa308:0xa30c])==[0,66,80,16]
 assert all(note_pixel(n)==3 for n in (60,62,65))
 image=grid();put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(240);assert image==grid(),'Native edits differ from complete rebuild'
 transport();p.tick(240);assert get('basepitch',1)==60,'MONO did not play lowest active note'
 mode(1);p.tick(240);heard=set()
 for _ in range(180):p.tick(1);heard.add(get('basepitch',1))
 assert heard=={60,62,65},heard
 mode(0);p.tick(240);assert get('basepitch',1)==60 and not get('arpirq_enabled')&2
 transport();assert not get('seqplaying')
 print('PASS black native notes,mode-independent pixels,overlap preservation,drag pixels,lowest MONO and ARP pitches')
 install([[],[],[],[],[],[],[[0,1,100,8],[0,2,100,8],[0,3,100,8]]],6)
 assert all(pixel(get('rollx',2)+2,(row+1)*8+3)==3 for row in (3,4,5)),'Rejected PCM hit was dimmed'
 transport();chosen=set()
 for _ in range(240):
  p.tick(1);chosen.update((get('drumsamplevoice'),get('drumsamplevoice',1)))
 assert chosen=={0,1},('PCM admission changed',chosen)
 transport();put('drumrow',3);put('seqcursor',0,6);put('seqdrawvalid',0);put('dirty',1);p.tick(120);tap('b');p.tick(180)
 assert get('seqeventcounts',12)==2
 assert all(pixel(get('rollx',2)+2,(row+1)*8+3)==3 for row in (4,5)),'Deleting one hit altered another row'
 image=grid(24);put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(240);assert image==grid(24),'Drum edits differ from complete rebuild'
 print('PASS all PCM hits black,two-voice playback admission unchanged,and cross-row erase preserves other hits')
finally:p.stop(save=False)

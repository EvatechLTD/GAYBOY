"""Exercise the NEWGEN menu and resident storage through the real ROM UI."""
from io import BytesIO
from pathlib import Path
from pyboy import PyBoy
from boot_helpers import enter_app

S={l.split()[1]:int(l.split()[2],16) for l in Path('build/GAYBOY.noi').read_text().splitlines() if l.startswith('DEF ')}
p=PyBoy('build/GAYBOY.gb',window='null',sound_emulated=True,ram_file=BytesIO(bytes(32768)))
p.set_emulation_speed(0)
def v(name):return p.memory[S['_'+name]]
def put(name,value):p.memory[S['_'+name]]=value
def word(name,index=0):
 a=S['_'+name]+index*2
 return p.memory[a]|p.memory[a+1]<<8
def setword(name,value,index=0):
 a=S['_'+name]+index*2;p.memory[a]=value&255;p.memory[a+1]=value>>8

def press(key):
 mask={'right':1,'left':2,'up':4,'down':8,'a':16,'b':32,'select':64,'start':128}[key]
 p.button_press(key)
 for _ in range(180):
  p.tick(1)
  if v('lastpad')&mask:break
 assert v('lastpad')&mask,('unhandled press',key)
 p.button_release(key)
 for _ in range(180):
  p.tick(1)
  if not v('lastpad')&mask:break
 assert not v('lastpad')&mask
 p.tick(8)

def resident():
 slot=p.memory[S['_mx']+1]
 return 1+(slot>>2),0xa000+(slot&3)*2048+768

def read_tracks():
 bank,base=resident();tracks=[]
 for c in range(7):
  start=word('seqeventoffsets',c);count=word('seqeventcounts',c)
  tracks.append([list(p.memory[bank,base+i*4:base+i*4+4]) for i in range(start,start+count)])
 return tracks

def write_tracks(tracks):
 assert sum(map(len,tracks))<=256
 bank,base=resident();offset=0
 for c,events in enumerate(tracks):
  setword('seqeventoffsets',offset,c);setword('seqeventcounts',len(events),c)
  for event in events:
   p.memory[bank,base+offset*4:base+offset*4+4]=event;offset+=1
 put('seqeventfull',0)
 put('seqirqready',0);put('seqirqdirty',1)

def open_gen():
 assert not v('genopen')
 put('page',8);put('seqhead',0);put('seqfocus',0)
 press('start');assert v('navopen')
 press('right');assert v('navcategory')==1
 # THEORY is contextual to the sequencer the menu was opened from.
 for _ in range(80):
  if v('navchoice')==47:break
  press('down')
 assert v('navchoice')==47,('no contextual theory item',v('navchoice'))
 press('a');assert v('genopen')
 assert not p.memory[0xff40]&2,'Piano-roll sprites overlay the generator'

def edit(row,direction='up'):
 put('genrow',row);p.button_press('a');p.tick(3);press(direction);p.button_release('a');p.tick(8)

def trigger():
 row=4 if v('seqtrack')==6 else 11
 edit(row);edit(row,'down')

def canon(tracks):return [sorted(t) for t in tracks]

try:
 enter_app(p);put('sticky_start',1)
 tracks=[[[0,49,100,1],[100,53,90,1]],[[2,61,99,1]],[],[],[],[],[[0,1,110,1],[4,2,90,2],[20,1,70,1]]]
 write_tracks(tracks);put('seqtrack',0);setword('seqlength',64,0)
 open_gen();assert v('genpreview') and not v('generror')
 # HITS is a count for EUCLID, not a second rhythm selector. Fixed rhythms
 # show a disabled value; selecting EUCLID enables numeric edits.
 assert bytes(p.memory[S['_canvas']+12*20+11:S['_canvas']+12*20+13])==bytes((13,13))
 oldhits=v('genhits');edit(10,'right');assert v('genhits')==oldhits
 for _ in range(5):edit(5,'right')
 assert v('genrhythm')==6
 edit(10,'right');assert v('genhits')==oldhits+1
 edit(10,'left')
 for _ in range(5):edit(5,'left')
 assert v('genrhythm')==1
 result=read_tracks();assert result[1:]==tracks[1:] and [100,53,90,1] in result[0]
 active=[e for e in result[0] if e[0]<64]
 assert [e[0] for e in active]==list(range(0,64,2))
 assert all(e[3]==1 and (e[1]-1-9)%12 in (0,2,3,5,7,8,10) for e in active)
 assert [e[1] for e in active[:16]]==[e[1] for e in active[16:32]]
 # Explicit length changes sustain but do not move attacks or pitches.
 edit(6);longer=read_tracks();active2=[e for e in longer[0] if e[0]<64]
 assert [e[:3] for e in active2]==[e[:3] for e in active]
 assert all(e[3]==2 for e in active2)
 # Seed edits are reproducible and leave onset positions fixed.
 before=read_tracks();edit(11);after=read_tracks()
 assert [e[0] for e in after[0]]==[e[0] for e in before[0]]
 edit(11,'down');assert read_tracks()==before
 for scale,allowed in enumerate(((0,2,4,5,7,9,11),(0,2,3,5,7,8,10),(0,2,3,5,7,9,10),(0,3,5,7,10))):
  put('genscale',scale);trigger()
  assert all((e[1]-1-9)%12 in allowed for e in read_tracks()[0] if e[0]<64)
 put('genscale',1);trigger()
 p.screen.image.save('build/newgen-instrument.png')
 press('select');assert not v('genopen') and read_tracks()==tracks
 assert p.memory[0xff40]&2,'Piano-roll cursor did not return after leaving GEN'
 # Bass progression: one root per bar, hold the same contour over changes.
 open_gen();put('gentype',1);put('genprogression',2);trigger()
 bass=[e for e in read_tracks()[0] if e[0]<64]
 for bar,pc in enumerate((9,4,5,2)):
  assert all((e[1]-1)%12==pc for e in bass if bar*16<=e[0]<(bar+1)*16 and e[0]%4==0)
 # The same four roots can fit inside a sixteen-step loop at quarter-note changes.
 put('genchange',0);trigger()
 for step,pc in zip((0,4,8,12),(9,4,5,2)):
  assert next(e for e in read_tracks()[0] if e[0]==step)[1]%12==(pc+1)%12
 put('genchange',2);trigger()
 put('genrow',12);press('a');assert not v('genopen')
 kept=read_tracks();assert kept!=tracks
 # Every displayed drum name maps to its stored voice ID, regardless of slider visibility.
 for hidden in (0,1):
  for row in range(13):
   put('seqtrack',6);put('drumrow',row);put('drumvelrow',(row+1)%13)
   put('seqvelocityhidden',hidden);setword('seqlength',16,6)
   original=read_tracks();open_gen();voice=(row+10 if row<3 else row-3)+1
   assert v('genvoice')==voice
   result=read_tracks();assert result[:6]==original[:6]
   retained=[e for e in original[6] if e[1]!=voice or e[0]>=16]
   assert [e for e in result[6] if e[1]!=voice or e[0]>=16]==retained
   generated=[e for e in result[6] if e[1]==voice and e[0]<16]
   assert [e[0] for e in generated]==list(range(0,16,2))
   if row==3 and hidden:p.screen.image.save('build/newgen-drum.png')
   press('select');assert read_tracks()==original
 # Exercise actual LEFT/RIGHT edits, not direct writes to the setting values.
 # Small enums used to jump by ten, wrap to zero, and get stuck there.
 put('drumrow',3);open_gen()
 masks={0:[0,4,8,12],1:list(range(0,16,2)),2:list(range(16)),
        3:[2,6,10,14],4:[0,6,12],5:[4,12],6:[0,4,7,10,13]}
 for expected in (2,3,4,5,6,0,1):
  edit(0,'right');assert v('genrhythm')==expected
  assert [e[0] for e in read_tracks()[6] if e[1]==1 and e[0]<16]==masks[expected]
 edit(0,'left');assert v('genrhythm')==0
 edit(0,'left');assert v('genrhythm')==6
 for expected in (6,7,8):
  edit(2,'right');assert v('genhits')==expected
  assert len([e for e in read_tracks()[6] if e[1]==1 and e[0]<16])==expected
 # One right-arrow rotation must change an eighth-note pattern to offbeats.
 edit(0,'right');edit(0,'right');assert v('genrhythm')==1
 edit(3,'right');assert v('genrotation')==1
 assert [e[0] for e in read_tracks()[6] if e[1]==1 and e[0]<16]==list(range(1,16,2))
 edit(3,'left');assert v('genrotation')==0
 # Dependencies are visible, and disabled controls cannot edit hidden values.
 oldhits=v('genhits');edit(2,'right');assert v('genhits')==oldhits
 assert bytes(p.memory[S['_canvas']+4*20+11:S['_canvas']+4*20+13])==bytes((109,109))
 oldseed=word('genseed');edit(6,'right');assert word('genseed')==oldseed
 assert ''.join(chr(p.memory[S['_canvas']+16*20+i]+32) for i in range(20))=='SEED NEEDS VARIATION'
 # Variation and seed now affect the first sixteen steps, with fixed onsets.
 before=read_tracks();edit(5,'right');assert v('genvariation')==1
 varied=read_tracks();assert varied!=before
 assert [e[0] for e in varied[6]]==[e[0] for e in before[6]]
 edit(6,'right');assert word('genseed')==oldseed+1
 assert read_tracks()!=varied
 edit(6,'left');assert read_tracks()==varied
 press('select');assert not v('genopen')
 # Drum masks, rotation, empty Euclidean rhythm, KEEP and menu-triggered rollback.
 put('drumrow',3);open_gen();put('genrhythm',6);put('genhits',5);trigger()
 events=[e for e in read_tracks()[6] if e[1]==1 and e[0]<16];assert len(events)==5
 before=[e[0] for e in events];edit(3)
 after=[e[0] for e in read_tracks()[6] if e[1]==1 and e[0]<16]
 assert sorted((s+1)%16 for s in before)==after
 # Gate-to-next follows this voice's attacks; accents leave the mask intact.
 put('genlength',5);put('genaccent',3);trigger()
 accented=[e for e in read_tracks()[6] if e[1]==1 and e[0]<16]
 assert [e[0] for e in accented]==after
 assert [e[3] for e in accented]==[b-a for a,b in zip(after,after[1:]+[16])]
 assert all(e[2]==p.memory[S['_seqdefaultvel']+6]*3//4 for e in accented)
 # Seed has no effect on a flat, unvaried drum mask.
 stable=read_tracks();edit(6);assert read_tracks()==stable
 # EUCLID counts and rotation use the current 3/8 bar (six steps).
 put('seqbeats',3);put('seqdenom',8);put('genrotation',0);put('genhits',3);trigger()
 assert [e[0] for e in read_tracks()[6] if e[1]==1 and e[0]<16]==list(range(0,16,2))
 put('seqbeats',4);put('seqdenom',4)
 put('genhits',0);trigger();assert not any(e[1]==1 and e[0]<16 for e in read_tracks()[6])
 put('genrow',7);press('a');assert not v('genopen');drumkept=read_tracks()
 open_gen();press('start');assert not v('genopen') and canon(read_tracks())==canon(drumkept)
 press('select') # close the global menu
 # Capacity rejection must be atomic; an unsuccessful preview cannot be kept.
 full=[[],[[i,61,99,1] for i in range(255)],[],[],[],[],[[0,2,90,1]]]
 write_tracks(full);put('seqtrack',0);setword('seqlength',16,0);open_gen()
 assert v('generror') and not v('genpreview') and read_tracks()==full
 put('genrow',12);press('a');assert v('genopen') and read_tracks()==full
 press('select');assert not v('genopen') and read_tracks()==full
 # A failed edit after a successful preview preserves that preview, but KEEP is
 # blocked until settings fit again; CANCEL restores the entry snapshot.
 nearfull=[[[0,49,100,1]],[[i,61,99,1] for i in range(247)],[],[],[],[],[]]
 write_tracks(nearfull);open_gen();assert v('genpreview') and not v('generror')
 good=read_tracks();edit(5);assert v('generror') and read_tracks()==good
 put('genrow',12);press('a');assert v('genopen')
 press('select');assert read_tracks()==nearfull
 put('seqtrack',6);put('drumrow',3);write_tracks(full);open_gen()
 assert v('generror') and read_tracks()==full
 press('select');assert read_tracks()==full
 # Live edits must not stop or reset transport.
 write_tracks(tracks);put('seqtrack',0);put('page',8)
 p.button_press('select');p.tick(3);press('a');p.button_release('select');p.tick(8)
 assert v('seqplaying')
 stops=[];a=S['_seq_stop'];p.hook_register(a>>16,a&65535,lambda _:stops.append(True),None)
 open_gen();edit(5);assert v('seqplaying') and not stops
 press('select');assert v('seqplaying') and not stops and read_tracks()==tracks
 print('PASS: contextual menu, instrument rhythm/length/harmony/motif/seed, all 13 drum voices with sliders visible/hidden, isolation, rotation, silence, KEEP, rollback, full capacity and live playback')
finally:p.stop(save=False)

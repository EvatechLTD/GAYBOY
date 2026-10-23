"""Real-ROM meter-aligned grids and selected-note time stretch menu actions."""
from pathlib import Path
exec(Path('tools/test_seq_meter.py').read_text().split('\ntry:')[0])

def put(name,value,index=0):p.memory[S['_'+name]+index]=value

def group(c,x0,x1,y0=0,y1=127):
 put('seqtrack',c);put('selected',c if c<3 else 2);put('seqgrouptrack',c);put('seqgroupx0',x0);put('seqgroupx1',x1);put('seqgroupy0',y0);put('seqgroupy1',y1)

def action(item,success=True):
 put('page',8);put('seqfocus',0);put('seqhead',0);put('navopen',1);put('navcategory',1);put('navchoice',item);put('dirty',1);p.tick(30);press('a')
 assert bool(v('navopen')) != success,('menu result',item,success,v('navopen'))

try:
 enter_app(p);put('sticky_start',1);write_tracks([[],[],[],[],[],[],[]])
 for c in (0,1,2,6):
  for beats,denom,cols in [(4,4,16),(3,4,12),(5,8,10),(7,8,14),(11,8,22),(32,2,32),(1,16,1)]:
   put('seqbeats',beats);put('seqdenom',denom);put('seqzoom',1);put('seqtrack',c);put('selected',c if c<3 else 2);setword('seqlength',32,c);put('seqcursor',0,c);put('page',8);put('seqfocus',0);put('seqhead',0);put('seqdrawvalid',0);put('dirty',1);p.tick(100)
   assert v('seqcols')==cols,(c,beats,denom,v('seqcols'))
  print('PASS meter-aligned grid track',c,flush=True)
 put('seqtrack',0);put('seqbeats',3);put('seqdenom',4);put('seqzoom',1);put('seqcursor',24,0);put('seqdrawvalid',0);put('dirty',1);p.tick(100)
 assert v('seqbase')==24 and v('seqcols')==12,'last page must remain bar aligned'
 put('seqcursor',0,0);put('seqdrawvalid',0);put('dirty',1);p.tick(100);p.screen.image.save('build/meter-grid-3-4-fixed.png')
 put('seqbeats',4);put('seqdenom',4);put('seqzoom',1)
 setting(10,'up');assert v('seqzoom')==2 and v('seqcols')==32
 setting(10,'up');assert v('seqzoom')==2
 setting(10,'down');assert v('seqcols')==16
 setting(10,'down');assert v('seqcols')==8
 print('PASS half/one/two-bar zoom;24-step zoom removed;last page stays bar aligned',flush=True)
 # Reproduce a real meter edit after choosing the two-bar zoom. Do not
 # force one-bar zoom in the fixture: the edit itself must select it.
 put('seqbeats',4);put('seqdenom',4);put('seqzoom',2);setword('seqlength',16);put('seqtrack',0)
 setting(7,'down');assert v('seqbeats')==3 and v('seqzoom')==1
 put('page',8);put('seqfocus',0);put('seqhead',0);put('seqcursor',0,0);put('dirty',1);p.tick(100)
 assert v('seqcols')==12 and word('seqlength')==16
 p.screen.image.save('build/meter-real-edit-3-4.png')
 print('PASS real4/4 ->3/4 control resets prior2-bar zoom;three beats visible,16steps preserved',flush=True)
 put('seqbeats',4);put('seqdenom',4);put('seqzoom',1)
 for c in (0,1,2,6):
  tracks=[[] for _ in range(7)];note=1 if c==6 else 49
  tracks[c]=[[0,note,90,2],[4,note+1,100,2],[8,note+2,110,2],[12,note,127,2]]
  write_tracks(tracks);setword('seqlength',16,c);group(c,0,15,0,12 if c==6 else 127)
  action(51);assert word('seqlength',c)==32
  assert read_tracks()[c]==[[0,note,90,4],[8,note+1,100,4],[16,note+2,110,4],[24,note,127,4]]
  write_tracks(tracks);setword('seqlength',16,c);group(c,0,15,0,12 if c==6 else 127)
  action(52);assert word('seqlength',c)==16
  first=[[e[0]//2,e[1],e[2],1] for e in tracks[c]]
  repeat=[[e[0]+8,e[1],e[2],e[3]] for e in first]
  assert sorted(read_tracks()[c])==sorted(first+repeat)
  print('PASS X2 doubles loop; /2 compresses and repeats within original bar;track',c,flush=True)
 # Whole-sequence mode without selecting anything:three quarter beats ->six.
 put('navopen',0);put('seqbeats',3);put('seqdenom',4);put('seqtrack',2);put('selected',2);put('seqgrouptrack',255)
 tracks=[[],[],[[0,37,127,12]],[],[],[],[]];write_tracks(tracks);setword('seqlength',12,2)
 action(51);assert word('seqlength',2)==24 and read_tracks()[2]==[[0,37,127,24]]
 assert v('seqgrouptrack')==255
 action(52);assert word('seqlength',2)==24 and sorted(read_tracks()[2])==[[0,37,127,12],[12,37,127,12]]
 print('PASS NO SELECTION:three-beat note becomes six beats; /2 repeats inside same loop',flush=True)
 # Reproduce the actual save:one note is just outside the old12-step loop.
 # It must scale too,otherwise it cuts across the newly stretched active notes.
 original=[[0,37,127,3],[4,40,127,4],[8,43,127,4],[12,44,127,4]]
 for select_all in (False,True):
  put('navopen',0);write_tracks([[],[],original,[],[],[],[]]);setword('seqlength',12,2);put('seqgrouptrack',255)
  if select_all:
   action(38);assert v('seqgroupx0')==0 and v('seqgroupx1')>=12 and v('seqgroupy0')==0 and v('seqgroupy1')==127
  action(51);assert word('seqlength',2)==24
  assert read_tracks()[2]==[[0,37,127,6],[8,40,127,8],[16,43,127,8],[24,44,127,8]],read_tracks()[2]
 print('PASS actual bassline reproducer:NO SELECTION and SELECT ALL scale every note including old-boundary note',flush=True)
 put('seqbeats',4);put('seqdenom',4)
 # Partial selection: anchor at4; leave notes outside the group untouched.
 tracks=[[[0,40,100,1],[4,49,90,2],[6,53,110,2],[16,60,127,1]],[],[],[],[],[],[]]
 write_tracks(tracks);setword('seqlength',32);group(0,4,7,49-1,53-1)
 action(51);assert word('seqlength')==64 and read_tracks()[0]==[[0,40,100,1],[4,49,90,4],[8,53,110,4],[16,60,127,1]]
 write_tracks(tracks);setword('seqlength',32);group(0,4,6,49-1,53-1)
 action(52);assert word('seqlength')==32
 assert sorted(read_tracks()[0])==sorted([[0,40,100,1],[4,49,90,1],[5,53,110,1],[6,49,90,1],[7,53,110,1],[16,60,127,1]])
 print('PASS partial group preserves anchor and other notes;odd onset-box width accepted',flush=True)
 # Reject lossy compression and out-of-range expansion atomically.
 tracks=[[[0,49,100,1],[1,53,100,1]],[],[],[],[],[],[]]
 write_tracks(tracks);setword('seqlength',16);group(0,0,15)
 action(52,False);assert read_tracks()==tracks and word('seqlength')==16
 assert '/2 NEEDS EVEN STEPS' in line(16),line(16)
 put('navopen',0);write_tracks([[[0,49,100,1]],[],[],[],[],[],[]]);setword('seqlength',256);group(0,0,255)
 action(51,False);assert word('seqlength')==256 and read_tracks()[0]==[[0,49,100,1]]
 print('PASS rejects sub-grid onsets and capacity overflow without modifying data',flush=True)
 # Capacity and collision failures explain the reason and leave all tracks intact.
 put('navopen',0);tracks=[[[0,49,100,2]],[[i,61,100,1] for i in range(255)],[],[],[],[],[]]
 write_tracks(tracks);setword('seqlength',16);group(0,0,15)
 action(52,False);assert read_tracks()==tracks and 'PATTERN EVENT LIMIT' in line(16),line(16)
 put('navopen',0);tracks=[[[0,49,100,2],[2,49,100,2]],[],[],[],[],[],[]]
 write_tracks(tracks);setword('seqlength',16);group(0,0,1)
 action(51,False);assert read_tracks()==tracks and 'NOTES WOULD OVERLAP' in line(16),line(16)
 print('PASS event-limit and overlap messages;failures preserve every track',flush=True)
 # Full256-step gate encoding survives expansion and reverse compression.
 put('navopen',0);write_tracks([[[0,49,100,128]],[],[],[],[],[],[]]);setword('seqlength',128);group(0,0,127)
 action(51);assert word('seqlength')==256 and read_tracks()[0]==[[0,49,100,0]]
 action(52);assert word('seqlength')==256 and sorted(read_tracks()[0])==[[0,49,100,128],[128,49,100,128]]
 print('PASS256-step gate expansion and two128-step compressed copies',flush=True)
 # Live complete-pattern stretch scales attack rate and loop with transport running.
 from arp_probe_helpers import hook_attacks
 hits=[];hook_attacks(p,Path('build/GAYBOY.gb'),S,1,hits.append,include_editbuffer=True)
 put('syncmode',0);put('syncarmed',0);p.memory[0xff07]=0;p.memory[0xff06]=p.memory[0xff05]=240;p.memory[0xff0f]&=~4;p.memory[0xff07]=4
 tracks=[[],[[i,61,127,2] for i in (0,4,8,12)],[],[],[],[],[]];write_tracks(tracks)
 for c in range(7):setword('seqlength',16,c)
 for c in range(3):p.memory[S['_evalpatch']+c*16]=0;p.memory[S['_evalpatch']+c*16+13]=0
 setword('seqbpm',120);setword('seqglobalbpm',120);setword('seqcachedbpm',0);put('seqbeats',4);put('seqdenom',4);put('page',8);put('navopen',0);put('seqfocus',0);put('seqhead',0);group(1,0,15)
 p.button_press('select');p.tick(8);press('a');p.button_release('select');p.tick(240)
 for item,gap in [(52,250),(51,500)]:
  action(item);assert v('seqplaying');p.tick(240);hits.clear();p.tick(240)
  gaps=[(b-a)*1000/4194304 for a,b in zip(hits,hits[1:])]
  assert len(gaps)>=5 and max(abs(g-gap) for g in gaps)<2,(item,gaps)
 print('PASS live /2 doubles attack rate;X2 restores it without transport restart',flush=True)
 # Selection popup offers the same actions, including wrap to /2.
 put('navopen',0);put('page',8);put('seqhead',0);put('seqfocus',0)
 press('select');assert v('seqpopup')
 press('up');assert v('seqpopupchoice')==5
 press('a');assert not v('seqpopup') and word('seqlength',1)==32
 press('select');assert v('seqpopup')
 for _ in range(4):press('down')
 assert v('seqpopupchoice')==4
 press('a');assert not v('seqpopup') and word('seqlength',1)==64
 print('PASS selection context popup X2 and /2 actions and navigation',flush=True)
finally:p.stop(save=False)

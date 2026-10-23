"""Hardware report: synth beat, Wave bass, plotted P2 chord, real box + length drag."""
from pathlib import Path
from io import BytesIO
import json
source=Path('tools/test_arp_topbar_user_flow.py').read_text().split('\ntry:')[0]
source=source.replace("'seq_meterbuild')", "'seq_meterbuild','eval_seq_group_resize','roll_selection_update','roll_preview_service','roll_commit','native_edit_mark')")
exec(source)
def u16(n,i=0):return get(n,i)|(get(n,i+1)<<8)
def state():
 return {'valid':get('seqdrawvalid'),'font':get('seqfontdirty'),'cache':get('rollcache'),'overflow':get('seqtileoverflow'),'tiles':get('seqtilecount'),'base':get('seqbase'),'viewbase':get('seqviewbase'),'cursor':get('seqcursor',1),'pending':p.memory[0,0xa469],'span':list(p.memory[0,0xa46f:0xa471]),'rows':p.memory[0,0xa473]|p.memory[0,0xa474]<<8,'preview':get('seqeditpreview'),'previewdirty':get('seqpreviewdirty')}
def chord():return [list(p.memory[1,0xa300+i*4:0xa304+i*4]) for i in range(3)]
def box():
 # Start in empty space above the chord; select all onsets via A+D-pad.
 while get('seqcursor',1)<1:tap('right')
 while get('seqpitch',1)<68:tap('up')
 assert not get('seqhead')
 key('a',True);assert get('seqapending')==4
 tap('left')
 for _ in range(8):tap('down')
 key('a',False);p.tick(120)
 assert [get(n) for n in ('seqgrouptrack','seqgroupx0','seqgroupx1','seqgroupy0','seqgroupy1')]==[1,0,1,60,68]
try:
 enter_app(p,S);offset=0
 tracks=[[],[],[[i,n,110,8] for i,n in zip((0,8,16,24),(37,37,40,35))],[],[],[],[[i,11,100,1] for i in range(32)]+[[i,12,100,1] for i in (4,12,20,28)]+[[i,13,110,1] for i in (0,8,16,24)]]
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',32,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 word('seqbpm',120);word('seqglobalbpm',120);word('seqdefaultdur',4,2)
 put('page',8);put('seqtrack',1);put('selected',1);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127);put('seqcursor',0,1);put('seqpitch',60,1);put('seqtop',71,1);put('seqdrawvalid',0);put('dirty',1)
 key('select',True);tap('a');key('select',False);p.tick(180)
 tap('b')
 for _ in range(4):tap('up')
 tap('b')
 for _ in range(3):tap('up')
 tap('b');assert get('seqeventcounts',2)==3
 while not get('seqhead'):tap('up')
 tap('a');assert get('evalpatch',16)==1;tap('down');p.tick(120)
 fixture=BytesIO();p.save_state(fixture);profiler=Profile();reports=[]
 for mode in (1,0):
  fixture.seek(0);p.load_state(fixture)
  if not mode:
   put('seqhead',1);put('dirty',1);p.tick(60);tap('a');assert not get('evalpatch',16);tap('down')
  # Return from header entry pitch to the intended empty selection anchor.
  while get('seqpitch',1)>68:tap('down')
  box();print('selected',mode,state(),chord(),flush=True)
  key('b',True);assert get('seqapending')==2
  profiler.begin();rows=[]
  for i in range(24):
   direction='right' if i<17 else 'left';start=p._cycles();ack=tap(direction)
   row={'i':i,'direction':direction,'ack_ms':ack,'elapsed_ms':(p._cycles()-start)/4194.304,'state':state(),'durations':[e[3] for e in chord()]};rows.append(row)
   print(mode,i,direction,round(row['elapsed_ms'],1),row['state'],row['durations'],flush=True)
   if i in (3,11,16):p.tick(15)
  key('b',False);p.tick(600);final=state();profile=profiler.end()
  # Compare ordinary cell input after the drag, then after a page round trip.
  navbefore=[tap('up') for _ in range(4)];p.tick(180)
  key('select',True);tap('right');tap('left');key('select',False);p.tick(600)
  navafter=[tap('down') for _ in range(4)]
  reports.append({'mode':mode,'rows':rows,'final':final,'navigation_before_ms':navbefore,'navigation_after_ms':navafter,'profile':profile})
 Path('build/chord-resize-'+rom.stem+'.json').write_text(json.dumps(reports,indent=2))
 print('DONE',[(r['mode'],r['navigation_before_ms'],r['navigation_after_ms'],r['final']) for r in reports],flush=True)
finally:p.stop(save=False)

"""Measure Dpad release -> ready -> publication -> first changed Wave attack."""
from pathlib import Path
from io import BytesIO
import sys,json
with_drums='--drums' in sys.argv
if with_drums:sys.argv.remove('--drums')
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'up':4,'select':64}[n];(p.button_press if down else p.button_release)(n)
 for _ in range(1200):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
def u16(n,i=0):return get(n,i)|(get(n,i+1)<<8)
try:
 enter_app(p,symbols);offset=0
 tracks=[[],[],[[s,n,110,4] for s,n in zip((0,4,8,12),(37,41,44,41))],[],[],[],([[i,11,100,1] for i in range(16)]+[[i,12,100,1] for i in (4,12)]+[[i,13,110,1] for i in (0,8)]) if with_drums else []]
 for c,events in enumerate(tracks):
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(events),c*2);word('seqlength',16,c*2)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 word('seqbpm',120);word('seqglobalbpm',120);put('pattern_dirty',1)
 put('page',8);put('seqtrack',2);put('selected',2);put('seqhead',0);put('seqfocus',0);put('seqviewinitialized',127);put('seqcursor',0,2);put('seqpitch',36,2);put('seqtop',48,2);put('seqdrawvalid',0);put('dirty',1)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(600);assert get('editbuffer_valid')
 fixture=BytesIO();p.save_state(fixture);rows=[]
 for phase in (2,6,10,14):
  fixture.seek(0);p.load_state(fixture)
  for _ in range(600):
   if get('seqposition',2)==phase:break
   p.tick(1)
  before=u16('editbuffer_swaps');key('a',True);key('up',True)
  assert p.memory[1,0xa301]==38,'note edit failed'
  start=p._cycles();p.button_release('up');times={}
  for frame in range(1800):
   p.tick(1);ms=(p._cycles()-start)/4194.304
   if not get('lastpad')&4:times.setdefault('release_ack_ms',ms)
   if get('editbuffer_ready'):times.setdefault('ready_ms',ms)
   if u16('editbuffer_swaps')!=before:times.setdefault('published_ms',ms)
   if get('active',2) and get('basepitch',2)==37 and get('seqsource',2)==0:
    times['changed_attack_ms']=ms;break
  assert 'changed_attack_ms' in times,(phase,times)
  row={'phase':phase,**{k:round(v,3) for k,v in times.items()},'loops_to_changed_attack':round(times['changed_attack_ms']/2000,3)};rows.append(row);print(row,flush=True)
  key('a',False)
 Path('build/wave-edit-latency-'+rom.stem+('-drums' if with_drums else '')+'.json').write_text(json.dumps(rows,indent=2))
finally:p.stop(save=False)

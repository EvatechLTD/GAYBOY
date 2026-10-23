"""Matched LFO navigation comparison; identical notes, settings and input."""
from pathlib import Path
import statistics,json
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

def key(name,down):
 mask={'a':16,'select':64,'up':4,'down':8}[name];start=p._cycles()
 (p.button_press if down else p.button_release)(name)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return (p._cycles()-start)*1000/4194304
 raise AssertionError(('input timeout',name,down))
def tap(n):return max(key(n,True),key(n,False))
def changed():
 word('pattern_generation',(get('pattern_generation')|(get('pattern_generation',1)<<8))+1)
 put('seqirqdirty',1);word('seqdeadline',1)
try:
 enter_app(p,symbols);offset=0
 for c in range(7):
  ev=[[0,61,127,64]] if c<3 else [[i,11,100,1] for i in range(0,16,2)] if c==6 else []
  word('seqeventoffsets',offset,c*2);word('seqeventcounts',len(ev),c*2);word('seqlength',64 if c<3 else 16,c*2)
  for e in ev:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
 put('syncmode',0);put('syncarmed',0);p.memory[0xff07]=0;p.memory[0xff06]=p.memory[0xff05]=240;p.memory[0xff0f]&=~4;p.memory[0xff07]=4
 put('seqtrack',2);put('selected',2);put('page',8);put('seqfocus',0);word('seqbpm',120);word('seqglobalbpm',120);changed()
 key('select',True);tap('a');key('select',False);p.tick(600)
 rows=[]
 for count,shape in [(0,0),(1,0),(3,0),(1,4),(3,4),(3,2)]:
  for c in range(3):
   put('evalpatch',0,c*16);put('evalpatch',0,c*16+13);put('evalpatch',1,c*16+8);put('evalpatch',64 if c<count else 0,c*16+9)
   put('coarsepitch',0,c*3);put('coarsepitch',12 if c<count else 0,c*3+1);put('coarsepitch',1,c*3+2)
  for i,v in [(4,shape),(6,3),(7,1),(8,0),(9,1)]:put('globalmod',v,i)
  changed();p.tick(180)
  put('navopen',1);put('navcategory',0);put('navchoice',1);put('dirty',1);p.tick(90)
  a=[]
  for _ in range(6):a.extend([tap('up'),tap('down')])
  row={'voices':count,'shape':shape,'median_ms':round(statistics.median(a),2),'max_ms':round(max(a),2)};rows.append(row);print(row,flush=True)
 Path('build/'+rom.stem+'-lfo-nav.json').write_text(json.dumps(rows,indent=2))
finally:p.stop(save=False)

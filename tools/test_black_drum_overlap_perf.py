"""Plot/delete a third overlapping PCM hit: visual latency and retained data."""
from pathlib import Path
import json,statistics,hashlib
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def pixel(x,y):
 tile=p.memory[0x9800+(1+y//8)*32+x//8];base=0x8000+tile*16 if p.memory[0xff40]&16 else 0x9000+(tile if tile<128 else tile-256)*16;off=base+(y&7)*2;mask=128>>(x&7)
 return bool(p.memory[off]&mask)+2*bool(p.memory[off+1]&mask)
try:
 enter_app(p,symbols)
 for c in range(7):word('seqeventoffsets',0,c*2);word('seqeventcounts',2 if c==6 else 0,c*2);word('seqlength',16,c*2)
 for i,e in enumerate([[0,1,100,8],[0,2,100,8]]):p.memory[1,0xa300+i*4:0xa304+i*4]=e
 word('seqdefaultdur',8,12);put('page',8);put('seqtrack',6);put('drumrow',5);put('seqcursor',0,6);put('seqhead',0);put('seqfocus',0);put('seqgrouptrack',255);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
 rows=[]
 for i in range(8):
  target=3 if i%2==0 else 2;start=p._cycles();p.button_press('b');p.tick(1);p.button_release('b')
  for _ in range(1200):
   p.tick(1)
   x=get('rollx',2)+2;color=pixel(x,51)
   if get('seqeventcounts',12)==target and ((color in (2,3)) if target==3 else color==0) and get('seqdrawvalid'):break
  else:raise AssertionError(('edit did not appear',i,get('seqeventcounts',12),color))
  rows.append({'action':'plot' if target==3 else 'erase','visible_ms':(p._cycles()-start)*1000/4194304,'color':color});p.tick(30)
 assert list(p.memory[1,0xa300:0xa308])==[0,1,100,8,0,2,100,8]
 result={'rom':str(rom),'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'median_ms':statistics.median(r['visible_ms'] for r in rows),'max_ms':max(r['visible_ms'] for r in rows),'edits':rows}
 Path('build/black-drum-overlap-'+rom.stem+'.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
 print('PASS third-hit plot/delete really changes data and preserves the two existing PCM hits')
finally:p.stop(save=False)

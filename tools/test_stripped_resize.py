"""Real input resize/move regressions, with retained-grid/full-render comparison."""
from pathlib import Path
import json
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
helpers=Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
reports=[]
for track,rownum in ((6,5),(6,0),(0,0)):
 exec(prefix)
 exec('def tilepixel'+helpers)
 try:
  enter_app(p,S);put('seqtrack',track);put('seqhead',0);put('seqfocus',0);put('drumrow',rownum);put('seqdefaultdur',1,track*2);put('seqdefaultdur',0,track*2+1);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  press('b');p.tick(100)
  def records():
   p.memory[0x4000]=1;e=list(p.memory[0xa300:0xa304]);p.memory[0x4000]=0;return e
  rebuild=[];ptr=S['_drum_render' if track==6 else '_seq_pixels'];p.hook_register(ptr>>16,ptr&65535,lambda _:rebuild.append(p._cycles()),None)
  def compare():
   p.tick(90);image=grid();put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid(),(track,rownum,'pixel mismatch',records());rebuild.clear()
  p.button_press('b');p.tick(5)
  for key,duration in (('right',2),('right',3),('left',2)):
   started=p._cycles();p.button_press(key);p.tick(1);p.button_release(key)
   for _ in range(120):
    if records()[3]==duration:break
    p.tick(1)
   latency=(p._cycles()-started)*1000/4194304
   p.tick(12);assert records()[3]==duration,(track,rownum,key,records());assert not rebuild,(track,rownum,'full resize redraw')
   reports.append({'track':track,'row':rownum,'operation':'resize '+key,'ready_ms':latency});compare()
  p.button_release('b');p.tick(20)
  p.button_press('a');p.tick(5)
  for key,step in (('right',1),('right',2),('left',1)):
   started=p._cycles();p.button_press(key);p.tick(1);p.button_release(key)
   for _ in range(120):
    if records()[0]==step:break
    p.tick(1)
   latency=(p._cycles()-started)*1000/4194304
   p.tick(12);assert records()[0]==step,(track,rownum,key,records());assert not rebuild,(track,rownum,'full move redraw')
   reports.append({'track':track,'row':rownum,'operation':'move '+key,'ready_ms':latency});compare()
  p.button_release('a');p.tick(20)
 finally:p.stop(save=False)
Path('build/stripped-resize.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))


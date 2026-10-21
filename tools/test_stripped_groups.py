"""Group selection, resize and drag retain the rendered grid."""
from pathlib import Path
import json
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
reports=[]
for track,rownum in ((6,5),(6,0),(0,0)):
 exec(prefix);exec(helpers)
 try:
  enter_app(p,S);put('seqtrack',track);put('seqhead',0);put('seqfocus',0);put('drumrow',rownum);put('seqdefaultdur',1,track*2);put('seqdefaultdur',0,track*2+1);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  for step in (2,6):put('seqcursor',step,track);put('dirty',1);p.tick(10);press('b');p.tick(80)
  def records():
   p.memory[0x4000]=1;e=[list(p.memory[0xa300+i*4:0xa304+i*4]) for i in range(2)];p.memory[0x4000]=0;return e
  put('seqcursor',0,track);put('dirty',1);p.tick(20)
  rebuild=[];ptr=S['_drum_render' if track==6 else '_seq_pixels'];p.hook_register(ptr>>16,ptr&65535,lambda _:rebuild.append(p._cycles()),None)
  p.button_press('a');p.tick(6)
  for _ in range(7):press('right',3)
  p.button_release('a');p.tick(40)
  assert v('seqgrouptrack')==track,(track,'selection missing')
  assert not rebuild,(track,'selection full render')
  def compare():
   p.tick(90);image=grid();debug=(list(p.memory[0xa500+rownum*4:0xa504+rownum*4]),list(p.memory[0xbd40+rownum*4:0xbd44+rownum*4]));put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid(),(track,rownum,'pixels',records(),debug,[(24+i%136,i//136,a,b) for i,(a,b) in enumerate(zip(image,grid())) if a!=b][:25]);rebuild.clear()
  compare()
  put('seqcursor',2,track);put('dirty',1);p.tick(10);p.button_press('b');p.tick(6)
  for key,dur in (('right',2),('left',1)):
   start=p._cycles();p.button_press(key);p.tick(1);p.button_release(key)
   for _ in range(120):
    if all(e[3]==dur for e in records()) and v('seqdrawvalid')==1 and v('padread')==v('padwrite'):break
    p.tick(1)
   ms=(p._cycles()-start)*1000/4194304
   assert all(e[3]==dur for e in records()),(track,'group resize',records())
   assert not rebuild,(track,'group resize full render');reports.append({'track':track,'row':rownum,'operation':'group resize '+key,'ready_ms':ms});compare()
  p.button_release('b');p.tick(20)
  put('seqcursor',2,track);put('dirty',1);p.tick(10);p.button_press('a');p.tick(6)
  for key,steps in (('right',[3,7]),('left',[2,6])):
   start=p._cycles();p.button_press(key);p.tick(1);p.button_release(key)
   for _ in range(120):
    if sorted(e[0] for e in records())==steps and v('seqdrawvalid')==1 and v('padread')==v('padwrite'):break
    p.tick(1)
   ms=(p._cycles()-start)*1000/4194304
   assert sorted(e[0] for e in records())==steps,(track,'group move',records());assert not rebuild,(track,'group move full render');reports.append({'track':track,'row':rownum,'operation':'group move '+key,'ready_ms':ms});compare()
  p.button_release('a');p.tick(20)
 finally:p.stop(save=False)
Path('build/stripped-groups.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))

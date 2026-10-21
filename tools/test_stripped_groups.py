"""Group selection, resize and drag retain the rendered grid."""
from pathlib import Path
import json,sys
rom=Path(sys.argv[sys.argv.index('--rom')+1]) if '--rom' in sys.argv else Path('build/GAYBOY.gb')
prefix=Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0]
prefix=prefix.replace("Path('build/GAYBOY.noi')","rom.with_suffix('.noi')").replace("'build/GAYBOY.gb',",'str(rom),')
helpers='def tilepixel'+Path('tools/test_stripped_fast_edits.py').read_text().split('def tilepixel')[1].split('for rownum,velocity')[0]
reports=[]
for track,rownum,size in ((6,5,2),(6,0,2),(0,0,2),(6,0,6),(6,5,6),(0,0,6)):
 steps0=[2,6] if size==2 else list(range(2,14,2));anchor=steps0[0]
 exec(prefix);exec(helpers)
 try:
  enter_app(p,S);put('seqtrack',track);put('seqhead',0);put('seqfocus',0);put('drumrow',rownum);put('seqdefaultdur',1,track*2);put('seqdefaultdur',0,track*2+1);put('seqdrawvalid',0);put('dirty',1);p.tick(180)
  for step in steps0:put('seqcursor',step,track);put('dirty',1);p.tick(10);press('b');p.tick(80)
  def records():
   p.memory[0x4000]=1;e=[list(p.memory[0xa300+i*4:0xa304+i*4]) for i in range(size)];p.memory[0x4000]=0;return e
  put('seqcursor',0,track);put('dirty',1);p.tick(20)
  rebuild=[];ptr=S['_drum_render' if track==6 else '_seq_pixels'];p.hook_register(ptr>>16,ptr&65535,lambda _:rebuild.append(p._cycles()),None)
  p.button_press('a');p.tick(6)
  selection_times=[]
  for _ in range(7 if size==2 else 13):
   start=p._cycles();p.button_press('right');p.tick(1);p.button_release('right');p.tick(1)
   for tick in range(120):
    if v('seqcursor',track)==_+1 and v('padread')==v('padwrite') and v('seqdrawvalid')==1:break
    p.tick(1)
   selection_times.append((p._cycles()-start)*1000/4194304)
  reports.append({'track':track,'row':rownum,'notes':size,'operation':'selection extend','ready_ms':max(selection_times)})
  p.button_release('a');p.tick(40)
  assert v('seqgrouptrack')==track,(track,'selection missing')
  assert not rebuild,(track,'selection full render')
  def compare():
   p.tick(90);image=grid();debug=(list(p.memory[0xa500+rownum*4:0xa504+rownum*4]),list(p.memory[0xbd40+rownum*4:0xbd44+rownum*4]));put('seqdrawvalid',0);put('dirty',1);p.tick(180);assert image==grid(),(track,rownum,'pixels',records(),debug,[(24+i%136,i//136,a,b) for i,(a,b) in enumerate(zip(image,grid())) if a!=b][:25]);rebuild.clear()
  compare()
  put('seqcursor',anchor,track);put('dirty',1);p.tick(10);p.button_press('b');p.tick(6)
  for key,dur in (('right',2),('left',1)):
   start=p._cycles();p.button_press(key);p.tick(1);p.button_release(key)
   for _ in range(120):
    if all(e[3]==dur for e in records()) and v('seqdrawvalid')==1 and v('padread')==v('padwrite'):break
    p.tick(1)
   ms=(p._cycles()-start)*1000/4194304
   assert all(e[3]==dur for e in records()),(track,'group resize',records())
   assert not rebuild,(track,'group resize full render');reports.append({'track':track,'row':rownum,'notes':size,'operation':'group resize '+key,'ready_ms':ms});compare()
  p.button_release('b');p.tick(20)
  put('seqcursor',anchor,track);put('dirty',1);p.tick(10);p.button_press('a');p.tick(6)
  for key,steps in (('right',[n+1 for n in steps0]),('left',steps0)):
   start=p._cycles();p.button_press(key);p.tick(1);p.button_release(key)
   for _ in range(120):
    if sorted(e[0] for e in records())==steps and v('seqdrawvalid')==1 and v('padread')==v('padwrite'):break
    p.tick(1)
   ms=(p._cycles()-start)*1000/4194304
   assert sorted(e[0] for e in records())==steps,(track,'group move',records());assert not rebuild,(track,'group move full render');reports.append({'track':track,'row':rownum,'notes':size,'operation':'group move '+key,'ready_ms':ms});compare()
  if size==2:
   before=[e[1] for e in records()]
   press('down' if track==6 else 'up');p.tick(40)
   delta=1
   # Drum display order differs from its stored voice IDs.
   expected=[((n-1-10+delta)+10+1 if rownum<2 else n+delta) for n in before] if track==6 else [n+delta for n in before]
   assert [e[1] for e in records()]==expected,(track,rownum,'vertical move',records(),expected)
   assert not rebuild,(track,'vertical group move full render');compare()
   press('up' if track==6 else 'down');p.tick(40);assert [e[1] for e in records()]==before;compare()
  p.button_release('a');p.tick(20)
 finally:p.stop(save=False)
Path(sys.argv[sys.argv.index('--output')+1] if '--output' in sys.argv else 'build/stripped-groups.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))

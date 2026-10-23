"""Selection edge cache stays pixel-correct across tile reuse and rebuilds."""
from pathlib import Path
from io import BytesIO
exec(Path('tools/test_header_refcounts.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,symbols)
 install([[],[[0,61,100,16],[0,63,90,16],[4,65,80,8]],[],[],[],[],[]],1)
 for cycle in range(3):
  for right,high in ((4,64),(8,64),(12,64),(8,64),(4,64),(4,66),(8,66),(12,66),(8,66),(4,66)):
   put('seqgrouptrack',1);put('seqgroupx0',0);put('seqgroupx1',right);put('seqgroupy0',60);put('seqgroupy1',high);put('seqdrawvalid',2);put('dirty',1);p.tick(120);refs()
   expected=grid();retained=BytesIO();p.save_state(retained)
   put('seqdrawvalid',0);put('seqfontdirty',0);put('dirty',1);p.tick(240)
   assert grid()==expected,('selection cache mismatch',cycle,right,high)
   retained.seek(0);p.load_state(retained);refs()
 print('PASS selection variants preserve pixels and reference counts across full tile-cache replacement')
finally:p.stop(save=False)

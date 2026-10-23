"""Selection must remain available while a three-note resize redraw is pending."""
from pathlib import Path
def make_test(s):
 a=s.index('  profiler.begin();rows=[]');b=s.index('  # Compare ordinary cell input',a)
 s=s[:a]+'''  profiler.begin();rows=[]
  # Grow and return to the initial length; the latest target is short but
  # the accumulated tail redraw is deliberately still pending.
  for _ in range(10):tap('right')
  for _ in range(10):tap('left')
  key('b',False)
  assert [e[3] for e in chord()]==[4,4,4]
  tap('right');assert get('seqcursor',1)==4
  print('BEFORE NEW SELECTION',mode,state(),flush=True)
  assert p.memory[0,0xa469],('test did not exercise pending composition',mode)
  generation=u16('pattern_generation');key('a',True);assert get('seqapending')==4
  tap('left');start=p._cycles()
  for _ in range(240):
   p.tick(1)
   if get('rollcache',5)==1 and get('rollcache',6)==3 and get('rollcache',7)==4 and get('rollcache',8)==60 and get('rollcache',9)==60:break
  else:raise AssertionError(('selection did not publish during pending composition',mode,state()))
  print('NEW SELECTION FEEDBACK',mode,round((p._cycles()-start)/4194.304,2),state(),flush=True)
  assert p.memory[0,0xa469],('selection waited for note rebuild',mode)
  for _ in range(3):tap('left')
  for _ in range(8):tap('up')
  key('a',False);p.tick(600)
  assert u16('pattern_generation')==generation,'selection mutated note data'
  assert not pixel_report('PENDING SELECTION FINAL '+str(mode))
  final=state();profile=profiler.end()
'''+s[b:]
 return s.replace("'build/chord-resize-pixels-'", "'build/chord-resize-pending-selection-'")
wrapper=Path('tools/repro_chord_resize_pixels.py').read_text()
wrapper=wrapper.replace("exec(compile(s,'tools/repro_chord_resize_ui.py','exec'))", "s=make_test(s)\nexec(compile(s,'tools/repro_chord_resize_ui.py','exec'))")
exec(compile(wrapper,'tools/repro_chord_resize_pixels.py','exec'))

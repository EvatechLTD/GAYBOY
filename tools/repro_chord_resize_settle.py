from pathlib import Path
s=Path('tools/repro_chord_resize_hold.py').read_text()
s=s.replace("key('right',False);p.tick(60);print('RELEASE60',mode,state(),[e[3] for e in chord()],flush=True)", "key('right',False);start=p._cycles()\n  for settleframes in range(1200):\n   p.tick(1)\n   if not p.memory[0,0xa469] and get('seqdrawvalid')==1:break\n  print('RELEASE_SETTLE',mode,round((p._cycles()-start)/4194.304,2),settleframes,state(),flush=True)")
# This wrapper rewrites the original reproduction; perform the substitution
# inside its generated code, before that code is executed.
if s==Path('tools/repro_chord_resize_hold.py').read_text():raise AssertionError('probe substitution failed')
exec(compile(s,'tools/repro_chord_resize_hold.py','exec'))

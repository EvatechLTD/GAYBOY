"""Exhaustive native LFO lookup/clamp check using the actual assembled kernel."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,symbols)
 start=symbols['_lfo_irq_pitch'];data=rom.read_bytes();code=data[start:symbols['_lfo_irq_tick']]
 # The kernel's first BC immediate in work RAM addresses its private point table.
 table=next(code[i+1]|code[i+2]<<8 for i in range(len(code)-2) if code[i]==1 and 0xc000<=(code[i+1]|code[i+2]<<8)<0xe000)
 notes=[data[symbols['_notes']+i*2]|data[symbols['_notes']+i*2+1]<<8 for i in range(140)]
 cases=iter((c,n,o,f) for c in range(3) for n in range(128) for o in range(-96,97) for f in (-128,-64,-1,0,1,64,127))
 current=[None];count=[0];done=[False]
 def next_case():
  try:c,n,o,f=next(cases)
  except StopIteration:done[0]=True;return
  current[0]=(c,n,o,f);p.memory[table+c*128]=o&255;p.memory[table+c*128+1]=f&255
  p.register_file.A=c;p.register_file.D=0;p.register_file.E=n
 def returned(_):
  if done[0]:return
  c,n,o,f=current[0];expected=max(0,min(2047,notes[max(0,min(139,n+(12 if c==2 else 0)+o))]+f))
  assert ((p.register_file.B<<8)|p.register_file.C)==expected,(current[0],((p.register_file.B<<8)|p.register_file.C),expected)
  count[0]+=1;next_case()
 p.memory[0xff07]=0;p.memory[0xffff]=0;p.memory[0xff40]&=127;put('lphase',0)
 for i,b in enumerate((0xcd,start&255,start>>8,0x18,0xfb)):p.memory[0,0x100+i]=b
 p.hook_register(0,0x103,returned,None);p.register_file.SP=0xdff0;p.register_file.PC=0x100;next_case()
 for _ in range(10000):
  p.tick(1)
  if done[0]:break
 assert done[0],count[0]
 print('PASS assembled LFO note/coarse/fine bounds:',count[0],'cases',flush=True)
finally:p.stop(save=False)

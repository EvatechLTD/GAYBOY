"""Cached LFO validation must react to ownership without an edit generation."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def key(n,down):
 mask={'a':16,'select':64}[n];(p.button_press if down else p.button_release)(n)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))
try:
 enter_app(p,symbols);offset=0
 for c in range(7):
  events=[[0,61,127,64]] if c<3 else []
  word('seqeventoffsets',offset,2*c);word('seqeventcounts',len(events),2*c);word('seqlength',64,2*c)
  for e in events:p.memory[1,0xa300+offset*4:0xa304+offset*4]=e;offset+=1
  if c<3:put('evalpatch',1,16*c+8);put('evalpatch',64,16*c+9)
 word('seqbpm',120);word('seqglobalbpm',120);word('pattern_generation',1);put('seqirqdirty',1)
 key('select',True);key('a',True);key('a',False);key('select',False);p.tick(900)
 assert get('lfo_irq_mask')==7
 fixture=BytesIO();p.save_state(fixture)
 generation=get('pattern_generation')|(get('pattern_generation',1)<<8)
 for c in range(3):
  for field in ('finepitch','bend','tablemode'):
   fixture.seek(0);p.load_state(fixture)
   i=c if field=='tablemode' else 2*c
   put(field,1,i);p.tick(90)
   assert get('lfo_irq_mask')==7&~(1<<c),(c,field,'did not release',get('lfo_irq_mask'))
   put(field,0,i)
   if field=='tablemode':word('finepitch',0,c*2);word('bend',0,c*2)
   p.tick(90)
   assert get('lfo_irq_mask')==7,(c,field,'did not recover',get('lfo_irq_mask'))
  fixture.seek(0);p.load_state(fixture)
  put('mono_owned',1<<c);p.tick(90);assert not get('lfo_irq_mask')&(1<<c)
  put('mono_owned',0);p.tick(90);assert get('lfo_irq_mask')==7
 assert generation==get('pattern_generation')|(get('pattern_generation',1)<<8)
 print('PASS cached LFO ownership reacts to fine detune,bend,tables and mono ownership without note/config generation changes')
finally:p.stop(save=False)

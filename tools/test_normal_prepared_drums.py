"""Graphical drum edits publish without disturbing timer phase or clipboards."""
from pathlib import Path
exec(Path('tools/test_prepared_drums.py').read_text().split('\ntry:\n')[0])

def key(n,down):
 mask={'a':16,'b':32,'start':128,'select':64,'right':1,'left':2,'up':4,'down':8}[n]
 (p.button_press if down else p.button_release)(n)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',n,down))

def tap(n):key(n,True);key(n,False)

def error(nominal):
 gaps=[(y['cycle']-x['cycle'])/4194.304 for x,y in zip(noise_hits,noise_hits[1:])]
 assert len(gaps)>8
 return gaps,max(abs(g-round(g/nominal)*nominal) for g in gaps)

try:
 setup_fixture();put('page',8);put('seqtrack',6);put('selected',2);put('seqhead',0);put('seqfocus',0);put('drumrow',0);put('seqcursor',8,6);put('dirty',1);p.tick(120)
 key('select',True);tap('a');key('select',False);p.tick(120)
 assert get('seqplaying') and not get('smooth_playback_active') and get('drum_irq_active')
 initial=get('seqeventcounts',12)
 tap('b');assert get('seqeventcounts',12)==initial-1
 noise_hits.clear();p.tick(300);gaps,err=error(125)
 assert get('drum_irq_active') and err<1,(err,gaps)
 assert any(abs(g-250)<1 for g in gaps),gaps
 print('PASS graphical erase publishes a missing hat with continuous drum phase')
 tap('b');assert get('seqeventcounts',12)==initial
 p.tick(120);noise_hits.clear();p.tick(300);gaps,err=error(125)
 assert err<1 and max(gaps)<126,(err,gaps)
 print('PASS graphical plot restores hat without duplicate attack or lost hit')
 for bpm in (137,240,120):
  word('seqbpm',bpm);word('seqglobalbpm',bpm);word('pattern_generation',u16('pattern_generation')+1);put('seqirqdirty',1);put('eval_moddirty',1)
  # Raw debug writes may land inside seq_irq_prepare, after its dirty read.
  for _ in range(10):put('seqirqdirty',1);p.tick(1)
  p.tick(120);noise_hits.clear();p.tick(300);gaps,err=error(15000/bpm)
  assert get('drum_irq_active') and err<1.3,(bpm,err,p.memory[0xff06],get('drum_irq_pending'),get('waveengine'),u16('seqbpm'),gaps)
  print('PASS live tempo',bpm,'max drum grid error ms',round(err,3))
 key('select',True);tap('a');key('select',False)
 assert not get('seqplaying') and not get('drum_irq_active')
finally:p.stop(save=False)

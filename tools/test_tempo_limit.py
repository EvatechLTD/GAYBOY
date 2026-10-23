"""Tempo UI and loaded metadata obey the 30..240 BPM bounds."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
def press(k):
 p.button_press(k);p.tick(10);p.button_release(k);p.tick(15)
def bpm():return get('seqbpm')|get('seqbpm',1)<<8
try:
 if args.save:
  p.memory[1,0xa06b]=44;p.memory[1,0xa06c]=1
 enter_app(p,symbols)
 if args.save:assert bpm()==240,('loaded tempo',bpm())
 put('page',18);put('mx',64,4);word('seqbpm',230);word('seqglobalbpm',230);put('dirty',1);p.tick(80)
 p.button_press('a');p.tick(3)
 for _ in range(3):press('right')
 p.button_release('a');p.tick(30)
 assert bpm()==240,bpm()
 put('page',10);put('seqtrack',1);put('seqfocus',1);put('seqhead',0);word('seqbpm',239);word('seqglobalbpm',239);put('dirty',1);p.tick(80)
 p.button_press('b');p.tick(3)
 for _ in range(3):press('up')
 p.button_release('b');p.tick(30)
 assert bpm()==240,bpm()
 print('PASS 240 BPM cap in mixer, sequencer and saved metadata')
finally:p.stop(save=False)

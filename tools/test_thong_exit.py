"""Leaving the arranger rebuilds the normal roll instead of retaining its scratch."""
from pathlib import Path
import numpy as np
exec(Path('tools/test_shared_ui_tiles.py').read_text().split('\ntry:\n')[0])
try:
 enter_app(p,symbols);put('sticky_start',1);choose(28);p.tick(60)
 original=np.asarray(p.screen.image).copy()[24:136]
 for _ in range(2):
  tap('start')
  for _ in range(24):
   if get('navchoice')==54:break
   tap('down')
  assert get('navchoice')==54;tap('a');p.tick(60);assert get('page')==29
  tap('b');tap('right');tap('b');choose(28);p.tick(90)
  assert np.array_equal(original,np.asarray(p.screen.image)[24:136]),'Arranger scratch was retained as roll tiles'
 print('PASS repeated arranger-to-sequencer returns preserve exact grid pixels')
finally:p.stop(save=False)

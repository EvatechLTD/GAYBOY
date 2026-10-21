"""Drive the three drum preset entry points with actual Game Boy buttons."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])

try:
 enter_app(p,S)
 menu(17)
 for voice,bank in enumerate(('NHH HARDWARE 1','NSN HARDWARE 1','PK HARDWARE 1')):
  assert v('drumsynthvoice')==voice
  row(0,0);assert 'LOAD PRESET' in text(40)
  press('a');assert v('tonepresetopen') and bank in text(0)
  if voice==2:
   for _ in range(12):press('down')
   assert 'RIMSHOT' in text(0)
  press('a');assert not v('tonepresetopen') and v('page')==17
  if voice==2:assert v('pulsekickpatch',1)==84
  row(0,1);press('a');assert v('tonepresetopen') and 'SAVE PRESET' in text(0)
  assert 'HARDWARE 1' not in text(0)
  press('select');assert not v('tonepresetopen')
  row(0,2);press('a');assert 'HARDWARE FACTORY 1' in text(0)
  press('a');assert bank in text(0)
  press('select');assert not v('tonepresetopen')
  if voice<2:press('select')
 p.screen.image.save('build/drumsynth-presets-ui.png')
 print('PASS: real button load/save/bank entry on NHH, NSN and PK; factory browsing, rimshot and Select return')
finally:p.stop(save=False)

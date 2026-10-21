"""Master Select+Start toggles restart/panic across pages and menu modes."""
from pathlib import Path
exec(Path('tools/test_stripped_ui.py').read_text().split('\ntry:')[0])
def master(reverse=False):
 first,second=('start','select') if reverse else ('select','start')
 p.button_press(first);p.tick(3);p.button_press(second);p.tick(80);p.button_release(second);p.button_release(first);p.tick(80)
try:
 enter_app(p,S)
 # Simulate a held voice outside sequencer ownership.
 put('active',1);put('keycount',1);put('held',60);p.memory[0xff12]=0xf8;p.memory[0xff14]=0x80
 master();assert v('seqplaying') and not any(v('active',i) for i in range(4)),'Restart retained a held voice'
 master();assert not v('seqplaying')
 for target in (8,11,16,18,23,20,2,10):
  menu(target);original=v('page');master();assert v('seqplaying') and v('page')==original,(target,'restart',v('page'))
  master();assert not v('seqplaying') and not v('navopen'),(target,'panic')
  assert not any(v('active',i) for i in range(4)),(target,'active voice after panic')
 print('PASS: master play/panic on sequencer, tone, Settings, mixer, Kits, files, MOD and Seq Settings with Select held before Start')
finally:p.stop(save=False)

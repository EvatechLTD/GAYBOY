"""Select cancels pattern loading without replacing live note/patch data."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])
try:
 enter_app(p,symbols)
 original=bytes(p.memory[1,0xa300:0xa700]);patch=bytes(get('evalpatch',i) for i in range(128));slot=get('mx',1)
 put('page',19);put('dirty',1);p.tick(80)
 label=bytes(get('canvas',15*20+i)+32 for i in range(16))
 assert label==b'SELECT TO CANCEL',label
 p.button_press('select')
 for _ in range(120):
  p.tick(1)
  if get('page')==18:break
 assert get('page')==18
 p.button_release('select');p.tick(20)
 assert bytes(p.memory[1,0xa300:0xa700])==original
 assert bytes(get('evalpatch',i) for i in range(128))==patch
 assert get('mx',1)==slot
 print('PASS load-pattern cancel tooltip and Select exit preserve live pad')
finally:p.stop(save=False)

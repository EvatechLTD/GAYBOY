"""Sync and Mixer Settings skip retired PO without changing numeric mode IDs."""
from pathlib import Path
exec(Path('tools/test_wave_saved_tempo.py').read_text().split('\ntry:')[0])

def key(k,down):
 mask={'a':16,'b':32,'up':4,'down':8,'right':1,'left':2}[k]
 (p.button_press if down else p.button_release)(k)
 for _ in range(600):
  p.tick(1)
  if bool(get('lastpad')&mask)==down:return
 raise AssertionError(('input timeout',k,down))

def tap(k):key(k,True);key(k,False)

try:
 enter_app(p,symbols);put('page',27);put('dirty',1);p.tick(30)
 key('b',True)
 for expected in (1,2,3,5,6,6):
  tap('up');assert get('syncmode')==expected,('Sync type',expected,get('syncmode'))
 for expected in (5,3,2,1,0):
  tap('down');assert get('syncmode')==expected,('Sync reverse',expected,get('syncmode'))
 key('b',False)
 put('page',16);put('pageconfig',0);put('eval_row',0);put('dirty',1);p.tick(30)
 tap('a');assert get('page')==28
 tap('down');tap('down');assert get('mx',4)==2
 key('b',True)
 for expected in (1,2,3,5,6):
  tap('up');assert get('syncmode')==expected,('Mixer type',expected,get('syncmode'))
 for expected in (5,3,2,1,0):
  tap('down');assert get('syncmode')==expected,('Mixer reverse',expected,get('syncmode'))
 tap('right');assert get('syncmode')==6
 tap('left');assert get('syncmode')==0
 key('b',False)
 print('PASS Sync/Mixer mode navigation skips PO; GATE=5/TWINK=6; large edits terminate')
finally:p.stop(save=False)
